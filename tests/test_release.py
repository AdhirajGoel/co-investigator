"""Disposable software fixtures; no research examples or biological datasets."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
LIT=ROOT/'.agents/skills/literature-pdf-download/scripts'
sys.path.insert(0,str(LIT))
import corpus
import fetch_oa


def run(*args):
    return subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True)


def pdf_bytes():
    # A one-page, non-scientific PDF constructed solely for parser verification.
    stream=b'BT /F1 12 Tf 20 60 Td (Software verification fixture with enough readable text.) Tj ET'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 100] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    out=bytearray(b'%PDF-1.4\n');offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(out));out.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    start=len(out);out.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:out.extend(f'{offset:010d} 00000 n \n'.encode())
    out.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
    return bytes(out)


class WorkspaceTests(unittest.TestCase):
    def test_init_check_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'project'
            result=run(ROOT/'tools/workspace.py','init',p,'--name','Fixture project','--question','Software setup check')
            self.assertEqual(result.returncode,0,result.stderr+result.stdout)
            self.assertIn('Fixture project',(p/'context/project-context.md').read_text())
            self.assertEqual(list((p/'data').iterdir()),[])
            for s in (p/'.agents/skills').iterdir():
                self.assertEqual((p/'.claude/skills'/s.name).resolve(),s.resolve())
            before=(p/'context/project-context.md').read_bytes()
            self.assertNotEqual(run(ROOT/'tools/workspace.py','init',p,'--name','Changed','--question','Changed').returncode,0)
            self.assertEqual(before,(p/'context/project-context.md').read_bytes())
            (p/'.claude/skills/read-pdf').unlink()
            self.assertNotEqual(run(p/'tools/workspace.py','check',p).returncode,0)

    def test_blank_question_and_template_destination_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'unused'
            self.assertNotEqual(run(ROOT/'tools/workspace.py','init',p,'--name','Fixture','--question',' ').returncode,0)
            self.assertFalse(p.exists())
        self.assertNotEqual(run(ROOT/'tools/workspace.py','init',ROOT/'do-not-create','--name','Fixture','--question','Fixture').returncode,0)
        self.assertFalse((ROOT/'do-not-create').exists())


class LiteratureTests(unittest.TestCase):
    def record(self,root):
        return {'id':'fixture','doi':'10.example/software-fixture','section':'papers','dest':str(root/'papers/fixture.pdf'),'status':'pending','attempts':[],'pdf_url':'https://example.org/fixture.pdf'}

    def test_reject_escape_and_duplicates_before_fetch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rec=self.record(root);p=root/'records.json'
            for records in ([rec,rec],[dict(rec,dest=str(root.parent/'outside.pdf'))],[dict(rec,section='../escape')],[]):
                p.write_text(json.dumps(records))
                with self.assertRaises(ValueError):corpus.load_records(p,root)

    @unittest.skipUnless(shutil.which('pdfinfo'),'Poppler not installed')
    def test_atomic_download_and_manifest_reconciliation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rec=self.record(root);p=root/'records.json';p.write_text(json.dumps([rec]))
            original=subprocess.run
            def fake_curl(args,**kwargs):
                if args[0]=='curl':
                    Path(args[args.index('--output')+1]).write_bytes(pdf_bytes())
                    return subprocess.CompletedProcess(args,0,'','')
                return original(args,**kwargs)
            with patch.object(fetch_oa.subprocess,'run',side_effect=fake_curl):
                self.assertTrue(fetch_oa.download(rec,0))
            dest=Path(rec['dest']);before=dest.read_bytes()
            with patch.object(fetch_oa.subprocess,'run',side_effect=fake_curl):
                self.assertTrue(fetch_oa.download(rec,0))
            self.assertEqual(dest.read_bytes(),before)
            self.assertTrue(corpus.reconcile([rec],p,root,0))
            manifest=json.loads((root/'manifest.json').read_text())
            self.assertEqual(manifest[0]['status'],'verified')
            self.assertEqual(manifest[0]['page_count'],1)
            (root/'extra.pdf').write_bytes(pdf_bytes())
            self.assertFalse(corpus.reconcile([rec],p,root,0))
            self.assertTrue((root/'MISSING.md').exists())

    @unittest.skipUnless(shutil.which('pdfinfo'),'Poppler not installed')
    def test_html_response_never_published_and_existing_file_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rec=self.record(root);original=subprocess.run
            def html(args,**kwargs):
                if args[0]=='curl':
                    Path(args[args.index('--output')+1]).write_text('<html>Not a PDF</html>')
                    return subprocess.CompletedProcess(args,0,'','')
                return original(args,**kwargs)
            with patch.object(fetch_oa.subprocess,'run',side_effect=html):self.assertFalse(fetch_oa.download(rec,0))
            dest=Path(rec['dest']);self.assertFalse(dest.exists())
            dest.write_text('Preserve this existing file')
            self.assertFalse(fetch_oa.download(rec,0))
            self.assertEqual(dest.read_text(),'Preserve this existing file')


class PdfTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pdfinfo') and shutil.which('pdftotext'),'Poppler not installed')
    def test_read_real_pdf_and_reuse_cache(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.pdf';p.write_bytes(pdf_bytes())
            tool=ROOT/'.agents/skills/read-pdf/pdf_cache.py'
            cache=Path(d)/'cache'
            a=run(tool,'ingest',p,'--cache-root',cache)
            self.assertEqual(a.returncode,0,a.stderr)
            self.assertTrue(json.loads(a.stdout)['page_count_verified'])
            b=run(tool,'ingest',p,'--cache-root',cache)
            self.assertTrue(json.loads(b.stdout)['cache_reused'])
            c=run(tool,'read',p,'--cache-root',cache,'--pages','1')
            self.assertIn('Software verification fixture',c.stdout)
            output=Path(d)/'export.md'
            exported=run(tool,'export',p,output,'--cache-root',cache)
            self.assertEqual(exported.returncode,0,exported.stderr)
            self.assertIn('Software verification fixture',output.read_text())
            before=p.read_bytes()
            self.assertNotEqual(run(tool,'export',p,p,'--cache-root',cache).returncode,0)
            self.assertEqual(p.read_bytes(),before)
            self.assertNotEqual(run(tool,'export',p,output,'--cache-root',cache).returncode,0)
            self.assertEqual(run(ROOT/'.agents/skills/read-pdf/test_pdf_cache.py').returncode,0)


@unittest.skipUnless(importlib.util.find_spec('openpyxl'),'Optional openpyxl not installed')
class SequenceTests(unittest.TestCase):
    def test_both_strands_and_malformed_inputs(self):
        import openpyxl
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);sheet=root/'fixture.xlsx';seq=root/'sequences';seq.mkdir()
            wb=openpyxl.Workbook();ws=wb.active;ws.title='Plasmids';ws.append(['Plasmid','Spacer (final)']);ws.append(['fixture','ACGA']);wb.save(sheet)
            f=seq/'fixture.fasta';f.write_text('>fixture\nTTTTCGTTTT\n')
            tool=ROOT/'.agents/skills/sgrna-sequence-verification/scripts/verify_sgRNA.py'
            args=[tool,'--xlsx',sheet,'--fasta-dir',seq,'--backbone-len','6']
            ok=run(*args);self.assertEqual(ok.returncode,0,ok.stderr+ok.stdout);self.assertIn('rev',ok.stdout)
            before=sheet.read_bytes()
            self.assertNotEqual(run(*args,'--csv',sheet).returncode,0)
            self.assertEqual(sheet.read_bytes(),before)
            self.assertEqual(run(*args,'--csv',root/'results.csv').returncode,0)
            f.write_text('>first\nTTTTCGTTTT\n>second\nACGA\n')
            self.assertNotEqual(run(*args).returncode,0)
            f.write_text('>fixture\nTTTTCGTTTT\n');ws.append([None,'ACGA']);wb.save(sheet)
            self.assertNotEqual(run(*args).returncode,0)


if __name__=='__main__':unittest.main()
