"""Offline regressions for schema ambiguity, sequence identity, and checkpoints."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_release import ROOT, pdf_bytes, run
import fetch_oa


@unittest.skipUnless(importlib.util.find_spec('openpyxl'), 'Optional openpyxl not installed')
class SequenceReviewTests(unittest.TestCase):
    def verify(self, root, header, rows, *extra):
        import openpyxl
        sheet = root / 'fixture.xlsx'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Plasmids'
        ws.append(header)
        for row in rows:
            ws.append(row)
        wb.save(sheet)
        wb.close()
        return run(ROOT / '.agents/skills/sgrna-sequence-verification/scripts/verify_sgRNA.py',
                   '--xlsx', sheet, '--fasta-dir', root, '--backbone-len', '6', *extra)

    def test_exact_header_wins_over_parent_plasmid(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'parent.fasta').write_text('>fixture\nTTTACGATTT\n')
            result = self.verify(root, ['Parent plasmid', ' Plasmid ', 'Spacer (final)'],
                                 [['parent', 'clone', 'ACGA']])
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('NO_FASTA', result.stdout)
            self.assertNotIn('ALL PASS', result.stdout)

    def test_ambiguous_headers_and_overrides_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'clone.fasta').write_text('>fixture\nTTTACGATTT\n')
            for header, row, extra in [
                (['Parent plasmid', 'Child plasmid', 'Spacer (final)'], ['clone', 'clone', 'ACGA'], []),
                (['Plasmid', ' plasmid ', 'Spacer (final)'], ['clone', 'clone', 'ACGA'], []),
                (['Plasmid', 'Plasmid', 'Spacer (final)'], ['clone', 'clone', 'ACGA'], ['--plasmid-col', 'Plasmid']),
                (['Plasmid', 'Spacer (final)', 'Gene', 'Gene'], ['clone', 'ACGA', 'one', 'two'], ['--gene-col', 'Gene']),
                (['Plasmid', 'Spacer (final)'], ['clone', 'ACGA'], ['--gene-col', 'Missing']),
            ]:
                with self.subTest(header=header, extra=extra):
                    result = self.verify(root, header, [row], *extra)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertNotIn('ALL PASS', result.stdout)

    def test_unique_fallback_header_and_separator_matching_still_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'clone-1.fasta').write_text('>fixture\nTTTACGATTT\n')
            result = self.verify(root, ['Sample plasmid ID', 'Spacer (final) sequence'], [['clone', 'ACGA']])
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shared_fasta_marks_both_rows_ambiguous(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'clone-1.fasta').write_text('>fixture\nTTTACGATTT\n')
            for rows in ([['clone', 'ACGA'], ['clone-1', 'ACGA']], [['clone-1', 'ACGA'], ['clone', 'ACGA']]):
                with self.subTest(rows=rows):
                    result = self.verify(root, ['Plasmid', 'Spacer (final)'], rows)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn('0/2 passed', result.stdout)
                    self.assertIn('AMBIGUOUS_FASTA', result.stdout)

    def test_symlink_aliases_do_not_count_as_independent_sequences(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'clone.fasta').write_text('>fixture\nTTTACGATTT\n')
            (root / 'other.fasta').symlink_to(root / 'clone.fasta')
            result = self.verify(root, ['Plasmid', 'Spacer (final)'], [['clone', 'ACGA'], ['other', 'ACGA']])
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('0/2 passed', result.stdout)
            self.assertIn('AMBIGUOUS_FASTA', result.stdout)


class DownloadReviewTests(unittest.TestCase):
    def records(self, root):
        return [dict(id=ident, doi='10.example/' + ident, section='papers',
                     dest=str(root / 'papers' / (ident + '.pdf')), status='pending', attempts=[],
                     pdf_url=('https' if ident == 'first' else 'http') + '://example.org/fixture.pdf')
                for ident in ('first', 'second')]

    @unittest.skipUnless(shutil.which('pdfinfo'), 'Poppler not installed')
    def test_completed_download_checkpoint_survives_invalid_later_route(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            records = self.records(root)
            source = root / 'records.json'
            source.write_text(json.dumps(records))
            original = subprocess.run
            def fake_curl(args, **kwargs):
                if args[0] == 'curl':
                    Path(args[args.index('--output') + 1]).write_bytes(pdf_bytes())
                    return subprocess.CompletedProcess(args, 0, '', '')
                return original(args, **kwargs)
            argv = ['fetch_oa.py', str(source), '--root', str(root), '--min-kb', '0']
            with patch.object(sys, 'argv', argv), patch.object(fetch_oa.subprocess, 'run', side_effect=fake_curl), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    fetch_oa.main()
            saved = json.loads(source.read_text())
            self.assertTrue(Path(records[0]['dest']).exists())
            self.assertEqual(saved[0]['attempts'][0]['outcome'], 'downloaded')
            self.assertEqual(saved[0]['route_used'], 'direct-pdf')

    def test_current_record_checkpoint_survives_interrupt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'records.json'
            source.write_text(json.dumps(self.records(root)))
            def interrupted(record, min_kb):
                record['attempts'].append({'route': 'direct-pdf', 'outcome': 'failed'})
                raise KeyboardInterrupt
            argv = ['fetch_oa.py', str(source), '--root', str(root)]
            with patch.object(sys, 'argv', argv), patch.object(fetch_oa, 'download', side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    fetch_oa.main()
            saved = json.loads(source.read_text())
            self.assertEqual(saved[0]['attempts'], [{'route': 'direct-pdf', 'outcome': 'failed'}])
            self.assertEqual(saved[1]['attempts'], [])


if __name__ == '__main__':
    unittest.main()
