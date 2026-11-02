"""Offline regressions for optional literature routes and browser capture."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_release import LIT, pdf_bytes
import get_routes


class RouteTests(unittest.TestCase):
    def routes(self, records, response, email=False):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'records.json'
            source.write_text(json.dumps(records))
            output = io.StringIO()
            argv = ['get_routes.py', str(source)] + (['--email', 'fixture@example.org'] if email else [])
            with patch.object(sys, 'argv', argv), patch.object(get_routes, 'curl', side_effect=response), patch.object(get_routes.time, 'sleep'), contextlib.redirect_stdout(output):
                get_routes.main()
            return json.loads(output.getvalue())

    def test_epmc_pdf_survives_both_identifier_routes(self):
        item = {'id': '12345678', 'doi': '10.example/fixture', 'isOpenAccess': 'Y', 'fullTextUrlList': {'fullTextUrl': [{'documentStyle': 'pdf', 'availability': 'Open access', 'url': 'https://example.org/fixture.pdf', 'site': 'repository'}]}}
        calls = []
        def response(url):
            calls.append(url)
            return json.dumps({'resultList': {'result': [item]}})
        for record in ({'pmid': 12345678}, {'doi': '10.example/fixture'}):
            with self.subTest(record=record):
                calls.clear()
                result = self.routes([dict(record, id='fixture')], response, email=True)[0]
                self.assertEqual(result['pdf_url'], 'https://example.org/fixture.pdf')
                self.assertEqual(result['host'], 'repository')
                self.assertEqual(result['id'], 'fixture')
                self.assertEqual(len(calls), 1)

    def test_open_access_without_a_route_still_tries_unpaywall(self):
        calls = []
        def response(url):
            calls.append(url)
            if 'unpaywall' in url:
                return json.dumps({'is_oa': True, 'best_oa_location': {'url_for_pdf': 'https://example.org/fixture.pdf', 'host_type': 'repository'}})
            return json.dumps({'resultList': {'result': [{'doi': '10.example/fixture', 'isOpenAccess': 'Y'}]}})
        result = self.routes([{'doi': '10.example/fixture'}], response, email=True)[0]
        self.assertEqual(result['pdf_url'], 'https://example.org/fixture.pdf')
        self.assertEqual(len(calls), 2)
        calls.clear()
        result = self.routes([{'doi': '10.example/fixture'}], response)[0]
        self.assertIsNone(result['pdf_url'])
        self.assertEqual(len(calls), 1)


@unittest.skipUnless(shutil.which('node') and shutil.which('pdfinfo'), 'Node and Poppler are required')
class BrowserTests(unittest.TestCase):
    def test_capture_validation_defaults_and_process_ownership(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fixture = root / 'fixture.bin'
            fixture.write_bytes(pdf_bytes().replace(b'trailer\n', b'%' + b'x' * 40000 + b'\ntrailer\n'))
            script = r"""
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { EventEmitter } from 'node:events';
const { captureGoto, downloadRecord, publishPdf, landingUrl, loadRecords, assertTaskBrowser } = await import(process.argv[2]);
const root = process.argv[3], bytes = fs.readFileSync(path.join(root, 'fixture.bin'));
const dest = path.join(root, 'papers', 'fixture.pdf');
const record = {id: 'fixture', pmid: '12345678', section: 'papers', dest};
const recordsPath = path.join(root, 'records.json');
fs.writeFileSync(recordsPath, JSON.stringify([record]));
assert.deepEqual(loadRecords(recordsPath, root)[0].attempts, []);
assert.equal(landingUrl(record), 'https://pubmed.ncbi.nlm.nih.gov/12345678/');
assert.equal(landingUrl({...record, doi:'10.example/fixture'}), 'https://doi.org/10.example/fixture');
assert.equal(publishPdf(Buffer.from('%PDF-' + 'invalid'.repeat(10000)), dest), false);
assert.equal(fs.existsSync(dest), false);
class Page extends EventEmitter {
  async goto() {
    this.emit('response', {headers: () => ({'content-type': 'application/pdf'}), url: () => 'https://example.org/fixture.pdf', body: () => new Promise(resolve => setTimeout(() => resolve(bytes), 40))});
  }
  async waitForTimeout() {}
}
const page = new Page();
assert.equal(await captureGoto(page, 'https://example.org/fixture.pdf', dest), true);
assert.deepEqual(fs.readFileSync(dest), bytes);
assert.equal(page.listenerCount('response'), 0);
assert.equal(page.listenerCount('download'), 0);
assert.throws(() => publishPdf(bytes, dest), /EEXIST/);
assert.deepEqual(fs.readFileSync(dest), bytes);
assert.deepEqual(fs.readdirSync(path.dirname(dest)), ['fixture.pdf']);
fs.unlinkSync(dest);
page.goto = async () => page.emit('download', {path: async () => path.join(root, 'fixture.bin')});
assert.equal(await captureGoto(page, 'https://example.org/attachment', dest), true);
await assert.rejects(captureGoto(page, 'file:///etc/passwd', dest), /HTTPS/);
fs.unlinkSync(dest);
const visited = [];
page.title = async () => '';
page.goto = async url => {
  visited.push(url);
  if (url.endsWith('.pdf')) page.emit('download', {path: async () => path.join(root, 'fixture.bin')});
};
page.evaluate = async () => [visited.length === 1 ? 'https://example.org/article' : 'https://example.org/fixture.pdf'];
assert.equal(await downloadRecord(page, record), true);
assert.deepEqual(visited, ['https://pubmed.ncbi.nlm.nih.gov/12345678/', 'https://example.org/article', 'https://example.org/fixture.pdf']);
page.goto = async () => {};
page.title = async () => 'Verify you are human';
await assert.rejects(downloadRecord(page, record), {code: 'HUMAN_ACTION_REQUIRED'});


const profile = path.join(root, 'task profile');
fs.mkdirSync(profile);
fs.writeFileSync(path.join(profile, 'science-literature-port'), '9222');
fs.writeFileSync(path.join(profile, 'science-literature-pid'), '123');
const command = `Chrome --user-data-dir=${profile} --remote-debugging-port=9222`;
const run = (name) => ({status:0, stdout:name === 'ps' ? command : 'p123\n'});
assertTaskBrowser(profile, '9222', run);
for (const wrong of [command.replace(profile, profile + '-other'), command.replace('9222', '92220')]) {
  assert.throws(() => assertTaskBrowser(profile, '9222', () => ({status:0, stdout:wrong})), /task-owned/);
}
assert.throws(() => assertTaskBrowser(profile, '9222', name => ({status:0, stdout:name === 'ps' ? command : 'p456\n'})), /does not own/);
"""
            js = root / 'check.mjs'
            js.write_text(script)
            result = subprocess.run(['node', str(js), (LIT / 'browser_grab.mjs').as_uri(), str(root)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
