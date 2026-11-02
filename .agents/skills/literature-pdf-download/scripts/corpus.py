#!/usr/bin/env python3
"""Validate a literature corpus and reconcile its manifests without network access."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def load_records(path, root):
    root = Path(root).expanduser().resolve()
    records = json.loads(Path(path).read_text())
    if not isinstance(records, list) or not records:
        raise ValueError('Corpus must be a non-empty JSON array')
    ids, destinations = set(), set()
    for r in records:
        if not isinstance(r, dict): raise ValueError('Each record must be an object')
        ident = r.get('id')
        if not isinstance(ident, str) or not ident.strip() or ident in ids:
            raise ValueError('Record IDs must be non-empty unique strings')
        ids.add(ident)
        if not (r.get('pmid') or r.get('doi')): raise ValueError('Every record needs a PMID or DOI')
        section = r.get('section')
        if not isinstance(section, str) or not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*', section):
            raise ValueError('Section must be a safe relative label')
        dest = Path(r.get('dest',''))
        if not dest.is_absolute() or not dest.resolve().is_relative_to(root / section):
            raise ValueError('PDF destination must be absolute and inside its corpus section')
        if dest.suffix.lower() != '.pdf' or dest.resolve() in destinations:
            raise ValueError('PDF destinations must be unique .pdf paths')
        if dest.is_symlink(): raise ValueError('PDF destination cannot be a symbolic link')
        destinations.add(dest.resolve())
        if r.get('status','pending') not in ('pending','downloaded','verified','missing','blocked'):
            raise ValueError('Invalid record status')
        if not isinstance(r.get('attempts',[]),list): raise ValueError('Attempts must be an array')
        r.setdefault('attempts',[])
    return records


def verify(path, min_kb=30):
    p=Path(path)
    if not p.is_file(): return False, 0, None, 'File missing'
    size=p.stat().st_size
    with p.open('rb') as f: header=f.read(5)
    if header != b'%PDF-' or size <= min_kb*1024:
        return False,size,None,'Invalid PDF signature or file below minimum size'
    if not shutil.which('pdfinfo'): return False,size,None,'Install Poppler for PDF page validation'
    result=subprocess.run(['pdfinfo',str(p)],capture_output=True,text=True,timeout=30)
    match=re.search(r'^Pages:\s+(\d+)\s*$',result.stdout,re.M)
    if result.returncode or not match or int(match[1])<1:
        return False,size,None,'PDF parser could not read a positive page count'
    return True,size,int(match[1]),''


def atomic_json(path,data):
    path=Path(path)
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(data,indent=2)+'\n')
    temp.replace(path)


def reconcile(records,path,root,min_kb=30):
    root=Path(root).resolve()
    root.mkdir(parents=True,exist_ok=True)
    expected={Path(r['dest']).resolve() for r in records}
    extras=[str(p.relative_to(root)) for p in root.rglob('*.pdf') if p.resolve() not in expected]
    for r in records:
        valid,size,pages,reason=verify(r['dest'],min_kb)
        r.update(bytes=size,page_count=pages,validated_at=now())
        r['status']='verified' if valid else ('blocked' if 'Install' in reason else 'missing')
        r['validation_note']=reason
        r.setdefault('route_used',None)
    atomic_json(path,records)
    atomic_json(root/'manifest.json',records)
    counts={s:sum(r['status']==s for r in records) for s in ('verified','missing','blocked')}
    lines=['# Literature manifest','',f"Corpus: {len(records)} papers. Verified: {counts['verified']}; missing: {counts['missing']}; blocked: {counts['blocked']}.",'','| ID | Section | File | Status | Route | Pages |','|---|---|---|---|---|---|']
    for r in records:
        def clean(v): return str(v or '').replace('|','/').replace('\n',' ')
        lines.append('| '+' | '.join(clean(v) for v in (r['id'],r['section'],str(Path(r['dest']).resolve().relative_to(root)),r['status'],r['route_used'],r['page_count']))+' |')
    if extras: lines+=['','Unregistered PDFs:']+['- '+x for x in extras]
    (root/'MANIFEST.md').write_text('\n'.join(lines)+'\n')
    missing=[r for r in records if r['status']!='verified']
    if missing or extras:
        text=['# Unresolved literature','']
        for r in missing:
            text += [f"## {r['id']}",f"PMID: {r.get('pmid','')}; DOI: {r.get('doi','')}",r['validation_note'],'Attempts: '+json.dumps(r['attempts']), 'Next: install the missing validator or inspect another authorized full-text route; then rerun corpus validation.','']
        if extras: text+=['Register or move these unmatched PDFs before reporting completion:']+extras
        (root/'MISSING.md').write_text('\n'.join(text)+'\n')
    elif (root/'MISSING.md').exists(): (root/'MISSING.md').unlink()
    print(f"{counts['verified']}/{len(records)} PDFs verified; {counts['missing']} missing; {counts['blocked']} blocked; {len(extras)} unregistered")
    return not missing and not extras


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('records',type=Path);ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--min-kb',type=int,default=30)
    a=ap.parse_args()
    if a.min_kb<0: ap.error('--min-kb must be non-negative')
    try: return 0 if reconcile(load_records(a.records,a.root),a.records,a.root,a.min_kb) else 1
    except (OSError,ValueError,subprocess.TimeoutExpired) as e: ap.exit(1,str(e)+'\n')

if __name__=='__main__': raise SystemExit(main())
