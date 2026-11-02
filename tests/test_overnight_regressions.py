"""Offline regressions for formula coverage, skill aliases, and browser checkpoints."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
import zipfile

from test_release import ROOT, LIT, pdf_bytes, run


@unittest.skipUnless(importlib.util.find_spec('openpyxl'), 'Optional openpyxl not installed')
class FormulaCoverageTests(unittest.TestCase):
    def fixture(self, root, cached=None, cache_type='str', formulas=True):
        import openpyxl
        sheet = root / 'fixture.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Plasmids'
        ws.append(['Plasmid', 'Spacer (final)'])
        ws.append(['fixture', 'ACGA'])
        ws.append(['="other"', '="ACGA"'] if formulas else ['other', 'ACGA'])
        wb.save(sheet)
        wb.close()
        (root / 'fixture.fasta').write_text('>fixture\nTTTACGATTT\n')
        if cached is not None:
            # openpyxl writes formulas without caches; model saved Excel results in OOXML.
            with zipfile.ZipFile(sheet) as archive:
                entries = {name: archive.read(name) for name in archive.namelist()}
            xml = ET.fromstring(entries['xl/worksheets/sheet1.xml'])
            ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for address, value in zip(('A3', 'B3'), cached):
                cell = xml.find(f'.//s:c[@r="{address}"]', ns)
                cell.set('t', cache_type)
                cell.find('s:v', ns).text = value
            entries['xl/worksheets/sheet1.xml'] = ET.tostring(xml)
            with zipfile.ZipFile(sheet, 'w') as archive:
                for name, content in entries.items():
                    archive.writestr(name, content)
        return sheet

    def verify(self, root, sheet):
        return run(ROOT / '.agents/skills/sgrna-sequence-verification/scripts/verify_sgRNA.py',
                   '--xlsx', sheet, '--fasta-dir', root, '--backbone-len', '6')

    def test_required_formulas_without_usable_caches_cannot_disappear(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for cached, kind in ((None, 'str'), (('', ''), 'str'),
                                 (('other', ''), 'str'), (('#VALUE!', '#VALUE!'), 'e')):
                with self.subTest(cached=cached):
                    result = self.verify(root, self.fixture(root, cached, kind))
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertNotIn('ALL PASS', result.stdout)
                    self.assertIn('cached formula value', result.stderr)
                    self.assertRegex(result.stderr, r'Cell [AB]3')

    def test_cached_formulas_keep_the_same_coverage_as_literal_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for formulas in (False, True):
                with self.subTest(formulas=formulas):
                    sheet = self.fixture(root, ('other', 'ACGA') if formulas else None,
                                         formulas=formulas)
                    missing = self.verify(root, sheet)
                    self.assertNotEqual(missing.returncode, 0, missing.stdout)
                    self.assertIn('1/2 passed', missing.stdout)
                    self.assertIn('NO_FASTA', missing.stdout)
            (root / 'other.fasta').write_text('>fixture\nTTTACGATTT\n')
            complete = self.verify(root, sheet)
            self.assertEqual(complete.returncode, 0, complete.stderr + complete.stdout)
            self.assertIn('2/2 passed', complete.stdout)


@unittest.skipUnless(shutil.which('node'), 'Node is required')
class BrowserEntryTests(unittest.TestCase):
    def test_claude_alias_runs_the_same_cli(self):
        paths = [LIT / 'browser_grab.mjs',
                 ROOT / '.claude/skills/literature-pdf-download/scripts/browser_grab.mjs']
        results = [subprocess.run(['node', str(script), '--help'], capture_output=True, text=True,
                                  timeout=10) for script in paths]
        self.assertEqual(results[0].returncode, 0, results[0].stderr)
        self.assertIn('Usage:', results[0].stdout)
        self.assertEqual(results[1].returncode, 0, results[1].stderr)
        self.assertEqual(results[1].stdout, results[0].stdout)
        for script in paths:
            malformed = subprocess.run(['node', str(script), 'records.json'], capture_output=True,
                                       text=True, timeout=10)
            self.assertNotEqual(malformed.returncode, 0)
            self.assertIn('Provide corpus root and task profile', malformed.stderr)


@unittest.skipUnless(shutil.which('node') and shutil.which('pdfinfo'), 'Node and Poppler are required')
class BrowserCheckpointTests(unittest.TestCase):
    def test_completed_and_failed_records_survive_interrupt_or_cleanup_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fixture = root / 'fixture.bin'
            fixture.write_bytes(pdf_bytes().replace(b'trailer\n', b'%' + b'x' * 40000 + b'\ntrailer\n'))
            profile = root / 'profile'
            profile.mkdir()
            (profile / 'science-literature-pid').write_text('123')
            (profile / 'science-literature-port').write_text('9222')
            (root / 'child-stub.mjs').write_text(r'''
import { spawnSync as actualSpawn } from 'node:child_process';
export function spawnSync(command, args, options) {
  if (command === 'ps') return {status:0, stdout:`Chrome --user-data-dir=${process.env.PROBE_PROFILE} --remote-debugging-port=9222`};
  if (command === 'lsof') return {status:0, stdout:'p123\n'};
  return actualSpawn(command, args, options);
}
''')
            (root / 'playwright-stub.mjs').write_text('''
import fs from 'node:fs';
import { EventEmitter } from 'node:events';
class Page extends EventEmitter {
  count = 0;
  async goto() {
    this.count++;
    if (this.count === 1) this.emit('response', {headers:()=>({'content-type':'application/pdf'}), url:()=> 'https://example.org/fixture.pdf', body:async()=>fs.readFileSync(process.env.PROBE_PDF)});
    else if (process.env.PROBE_MODE === 'interrupt') {
      fs.writeFileSync(process.env.PROBE_MARKER, 'second record started');
      await new Promise(resolve=>setTimeout(resolve, 60000));
    }
  }
  async waitForTimeout() {}
  async title() {return '';}
  async evaluate() {return [];}
  async close() {}
}
export const chromium = {connectOverCDP: async()=>({contexts:()=>[{newPage:async()=>new Page()}], close:async()=>{
  if (process.env.PROBE_MODE === 'cleanup-failure') throw new Error('Fixture cleanup failure');
}})};
''')
            (root / 'loader.mjs').write_text('''
export function resolve(specifier, context, nextResolve) {
  if (specifier === 'child_process') return {url:new URL('./child-stub.mjs', import.meta.url).href, shortCircuit:true};
  if (specifier === 'playwright') return {url:new URL('./playwright-stub.mjs', import.meta.url).href, shortCircuit:true};
  return nextResolve(specifier, context);
}
''')
            for mode in ('interrupt', 'cleanup-failure', 'normal'):
                with self.subTest(mode=mode):
                    corpus_root = root / mode
                    corpus_root.mkdir()
                    records = [dict(id=name, doi='10.example/' + name, section='papers',
                                    dest=str(corpus_root / 'papers' / (name + '.pdf')),
                                    status='pending', attempts=[], pdf_url='https://example.org/' + name + '.pdf')
                               for name in ('first', 'second')]
                    source = corpus_root / 'records.json'
                    source.write_text(json.dumps(records))
                    marker = corpus_root / 'second-started'
                    env = dict(os.environ, PYTHON=sys.executable, PROBE_PROFILE=str(profile),
                               PROBE_PDF=str(fixture), PROBE_MODE=mode, PROBE_MARKER=str(marker))
                    process = subprocess.Popen(['node', '--experimental-loader', str(root / 'loader.mjs'),
                                                str(LIT / 'browser_grab.mjs'), str(source), '--root',
                                                str(corpus_root), '--profile', str(profile)], env=env,
                                               text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    try:
                        if mode == 'interrupt':
                            deadline = time.monotonic() + 10
                            while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                                time.sleep(.02)
                            self.assertTrue(marker.exists(), 'Second record was not reached')
                            process.send_signal(signal.SIGINT)
                        out, err = process.communicate(timeout=10)
                    finally:
                        if process.poll() is None:
                            process.terminate()
                        process.communicate(timeout=5)
                    self.assertTrue(Path(records[0]['dest']).exists(), out + err)
                    saved = json.loads(source.read_text())
                    self.assertEqual(saved[0].get('route_used'), 'dedicated-browser')
                    self.assertEqual(saved[0]['attempts'][0]['outcome'], 'downloaded')
                    if mode == 'interrupt':
                        self.assertEqual(process.returncode, -signal.SIGINT, out + err)
                        self.assertEqual(saved[1]['attempts'], [])
                    else:
                        self.assertEqual(saved[1]['attempts'][0]['outcome'], 'failed')
                    if mode == 'cleanup-failure':
                        self.assertIn('Fixture cleanup failure', err)
                    # Reconciliation must retain the completed file's provenance on resume.
                    run(LIT / 'corpus.py', source, '--root', corpus_root)
                    resumed = json.loads(source.read_text())[0]
                    self.assertEqual(resumed['status'], 'verified')
                    self.assertEqual(resumed['attempts'], saved[0]['attempts'])
                    self.assertEqual(resumed['route_used'], 'dedicated-browser')


if __name__ == '__main__':
    unittest.main()
