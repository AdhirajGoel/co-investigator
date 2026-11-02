#!/usr/bin/env python3
"""Create a separate scientific workspace or check its local setup."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', '.venv', 'node_modules', '.DS_Store')


def check(root: Path) -> bool:
    root = root.expanduser().resolve()
    failures = []
    for f in ('AGENTS.md', 'CLAUDE.md', 'requirements-tools.txt', 'docs/skills.md', 'tools/workspace.py'):
        if not (root / f).is_file(): failures.append(f'Missing {f}')
    skills = root / '.agents/skills'
    names = sorted(p.name for p in skills.iterdir() if p.is_dir()) if skills.is_dir() else []
    if not names: failures.append('No scientific skills found')
    for name in names:
        canonical = skills / name
        entry = canonical / 'SKILL.md'
        if not canonical.resolve().is_relative_to(root):
            failures.append(f'Skill escapes project: {name}')
            continue
        if not entry.is_file():
            failures.append(f'Missing SKILL.md: {name}')
            continue
        content = entry.read_text(encoding='utf-8')
        match = re.match(r'\A---\n(.*?)\n---\n', content, re.S)
        if not match or not re.search(r'^name:\s*'+re.escape(name)+r'\s*$', match[1], re.M) or not re.search(r'^description:\s*\S', match[1], re.M):
            failures.append(f'Invalid skill metadata: {name}')
        alias = root / '.claude/skills' / name
        if not alias.is_symlink() or alias.resolve() != canonical.resolve():
            failures.append(f'Claude skill link mismatch: {name}')
        for file in canonical.rglob('*'):
            if file.is_symlink() and not file.resolve().is_relative_to(root):
                failures.append(f'External skill asset link: {name}/{file.name}')
    marker = root / 'project.json'
    if marker.exists():
        data = json.loads(marker.read_text())
        if data.get('schema_version') != 1 or not data.get('name') or not data.get('question'):
            failures.append('Invalid project.json')
        for folder in ('context','literature','research','plans','experiments','data','syntheses','reviews','tools'):
            if not (root / folder).is_dir(): failures.append(f'Missing project directory: {folder}')
        for f in ('context/project-context.md','context/collaboration.md','context/decisions.md','context/project-log.md','tools/registry.md'):
            if not (root / f).is_file(): failures.append(f'Missing project record: {f}')
    else:
        if not (root / 'templates/project/context/project-context.md').is_file():
            failures.append('Missing project templates')
    print('Framework structure: '+('FAIL' if failures else 'PASS'))
    print(f'Scientific skills: {len(names)}')
    for name in names: print('  '+name)
    print('Claude/Codex shared skill links: '+('FAIL' if any('link' in f for f in failures) else 'PASS'))
    for cmd in ('curl','pdfinfo','pdftotext','pdftoppm','node','npm'):
        print(f'Optional command {cmd}: '+('available' if shutil.which(cmd) else 'not installed'))
    for mod in ('openpyxl','pdfplumber'):
        print(f'Optional Python package {mod}: '+('available' if importlib.util.find_spec(mod) else 'not installed'))
    for failure in failures: print('ERROR: '+failure)
    return not failures


def initialize(dest: Path, name: str, question: str) -> None:
    name, question = name.strip(), question.strip()
    if not name or not question: raise ValueError('Project name and research question must be non-empty')
    dest = dest.expanduser().absolute()
    # lexists behavior also rejects dangling links; resolve only after this check.
    if dest.exists() or dest.is_symlink(): raise ValueError('Destination already exists; choose a new directory')
    dest = dest.resolve()
    if dest.is_relative_to(ROOT): raise ValueError('Choose a project folder outside this template checkout')
    if not (ROOT / 'templates/project').is_dir(): raise ValueError('Project templates are unavailable')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.mkdir()  # exclusive creation protects an existing destination
    try:
        for file in (ROOT / 'templates/project').rglob('*'):
            if file.is_file():
                target = dest / file.relative_to(ROOT / 'templates/project')
                target.parent.mkdir(parents=True, exist_ok=True)
                text = file.read_text().replace('{{name}}', name).replace('{{question}}', question)
                target.write_text(text, encoding='utf-8')
        for folder in ('literature','research','plans','experiments','data','syntheses','reviews','tools'):
            (dest / folder).mkdir(exist_ok=True)
        shutil.copytree(ROOT / '.agents/skills', dest / '.agents/skills', ignore=IGNORE)
        (dest / '.claude/skills').mkdir(parents=True)
        for skill in (dest / '.agents/skills').iterdir():
            if skill.is_dir():
                (dest / '.claude/skills' / skill.name).symlink_to('../../.agents/skills/'+skill.name, target_is_directory=True)
        shutil.copytree(ROOT / 'templates', dest / 'templates', ignore=IGNORE)
        shutil.copytree(ROOT / 'docs', dest / 'docs', ignore=IGNORE)
        for f in ('tools/workspace.py', 'requirements-tools.txt', 'LICENSE', 'START_HERE.md'):
            shutil.copy2(ROOT / f, dest / f)
        (dest / 'project.json').write_text(json.dumps({'schema_version':1,'name':name,'question':question},indent=2)+'\n')
    except Exception:
        print('Setup stopped. The partially created destination has been retained for inspection.', file=sys.stderr)
        raise
    print('Workspace created. No research data were imported.')
    print('Next: personalize context/project-context.md and context/collaboration.md with the scientist.')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    init = sub.add_parser('init', help='Create a new workspace without overwriting existing files')
    init.add_argument('destination', type=Path)
    init.add_argument('--name', required=True)
    init.add_argument('--question', required=True)
    verify = sub.add_parser('check', help='Check workspace structure and optional dependencies without installing anything')
    verify.add_argument('directory', nargs='?', default=ROOT, type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'init':
            initialize(args.destination, args.name, args.question)
            return 0 if check(args.destination) else 1
        return 0 if check(args.directory) else 1
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Setup error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
