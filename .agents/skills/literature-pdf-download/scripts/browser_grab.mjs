import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawnSync } from 'child_process';

const dir = path.dirname(fileURLToPath(import.meta.url));
const python = process.env.PYTHON || 'python3';

export function assertTaskBrowser(profile, port, run = spawnSync) {
  if (!/^\d+$/.test(port) || Number(port) < 1024 || Number(port) > 65535) throw new Error('Invalid browser port');
  if (fs.readFileSync(path.join(profile, 'science-literature-port'), 'utf8').trim() !== port) throw new Error('Task profile port mismatch');
  const pid = fs.readFileSync(path.join(profile, 'science-literature-pid'), 'utf8').trim();
  if (!/^\d+$/.test(pid)) throw new Error('Invalid task browser PID');
  const command = run('ps', ['-p', pid, '-o', 'command='], { encoding: 'utf8' });
  const flag = value => new RegExp('(?:^|\\s)' + value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?=\\s|$)');
  if (command.status !== 0 || !flag('--user-data-dir=' + profile).test(command.stdout) || !flag('--remote-debugging-port=' + port).test(command.stdout)) throw new Error('Browser is not the task-owned process');
  const listener = run('lsof', ['-nP', '-a', '-p', pid, '-iTCP:' + port, '-sTCP:LISTEN', '-Fp'], { encoding: 'utf8' });
  if (listener.status !== 0 || !listener.stdout.split('\n').includes('p' + pid)) throw new Error('Task browser does not own the debugging port');
}

export function loadRecords(recordsPath, root) {
  const result = spawnSync(python, ['-c', 'from corpus import load_records; import sys,json; print(json.dumps(load_records(sys.argv[1],sys.argv[2])))', path.resolve(recordsPath), path.resolve(root)], { cwd: dir, encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr || 'Corpus validation failed');
  return JSON.parse(result.stdout);
}

export function publishPdf(bytes, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  const tempDir = fs.mkdtempSync(path.join(path.dirname(dest), '.pdf-'));
  const temp = path.join(tempDir, 'download.part');
  try {
    fs.writeFileSync(temp, bytes, { flag: 'wx' });
    const check = spawnSync(python, ['-c', 'from corpus import verify; import sys; ok,_,_,reason=verify(sys.argv[1]); print(reason); sys.exit(0 if ok else 1)', temp], { cwd: dir, encoding: 'utf8' });
    if (check.status !== 0) return false;
    fs.linkSync(temp, dest); // Publish a complete, parser-verified PDF without replacing any file.
    return true;
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

export function landingUrl(rec) {
  return rec.pdf_url || (rec.doi ? 'https://doi.org/' + rec.doi : 'https://pubmed.ncbi.nlm.nih.gov/' + rec.pmid + '/');
}

function patternUrls(doi = '') {
  const u = [];
  if (doi.startsWith('10.1002')) u.push(`https://onlinelibrary.wiley.com/doi/pdfdirect/${doi}?download=true`);
  if (doi.startsWith('10.1021')) u.push(`https://pubs.acs.org/doi/pdf/${doi}`);
  if (doi.startsWith('10.1089')) u.push(`https://www.liebertpub.com/doi/pdf/${doi}`);
  if (doi.startsWith('10.1177')) u.push(`https://journals.sagepub.com/doi/pdf/${doi}`);
  if (doi.startsWith('10.1039')) u.push(`https://pubs.rsc.org/en/content/articlepdf/${doi}`);
  if (doi.startsWith('10.1007') || doi.startsWith('10.1134')) u.push(`https://link.springer.com/content/pdf/${doi}.pdf`);
  if (doi.startsWith('10.1038')) u.push(`https://www.nature.com/articles/${doi.split('/')[1]}.pdf`);
  if (doi.startsWith('10.1126')) u.push(`https://www.science.org/doi/pdf/${doi}`);
  return u;
}

export async function captureGoto(page, url, dest) {
  if (new URL(url).protocol !== 'https:') throw new Error('Browser routes must use HTTPS');
  let saved = false, accepting = true;
  const pending = [];
  const publish = bytes => {
    if (accepting && !saved && bytes) saved = publishPdf(bytes, dest);
  };
  const response = resp => {
    const ct = resp.headers()['content-type'] || '';
    if (/application\/pdf/i.test(ct) || /\.pdf(\?|$)/i.test(resp.url())) {
      pending.push(resp.body().then(publish).catch(() => {}));
    }
  };
  const download = item => pending.push(item.path().then(file => { if (file) publish(fs.readFileSync(file)); }).catch(() => {}));
  page.on('response', response);
  page.on('download', download);
  let timer;
  try {
    await page.goto(url, { waitUntil: 'load', timeout: 50000 }).catch(() => {});
    await page.waitForTimeout(7000);
  } finally {
    page.off('response', response);
    page.off('download', download);
    // EventEmitter does not await async handlers; drain bodies before reporting success.
    await Promise.race([Promise.all(pending), new Promise(resolve => { timer = setTimeout(resolve, 30000); })]);
    accepting = false;
    clearTimeout(timer);
  }
  return saved;
}

export async function downloadRecord(page, rec) {
  const queue = [{ url: landingUrl(rec), depth: 0 }], seen = new Set();
  while (queue.length) {
    const { url, depth } = queue.shift();
    if (seen.has(url) || new URL(url).protocol !== 'https:') continue;
    seen.add(url);
    if (await captureGoto(page, url, rec.dest)) return true;
    const title = await page.title().catch(() => '');
    if (/just a moment|attention required|verify you|are you a robot/i.test(title)) {
      throw Object.assign(new Error('Human action required in the dedicated browser; rerun after the scientist resolves the challenge'), { code: 'HUMAN_ACTION_REQUIRED' });
    }
    // shortcut: follow two links for PubMed -> publisher -> PDF; inspect longer chains manually.
    if (depth >= 2) continue;
    const links = await page.evaluate(() => {
      const urls = [];
      const meta = document.querySelector('meta[name="citation_pdf_url"]');
      if (meta) urls.push(new URL(meta.content, location.href).href);
      for (const a of document.querySelectorAll('a')) {
        if (/pdfft|\/pdf\/|\.pdf(?:[?#]|$)|pdfdirect|articlepdf/i.test(a.href) || a.closest('.full-text-links-list')) urls.push(a.href);
      }
      return [...new Set(urls)];
    }).catch(() => []);
    if (depth === 0) links.push(...patternUrls(rec.doi));
    queue.push(...links.map(url => ({ url, depth: depth + 1 })));
  }
  return false;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes('--help') || !args.length) {
    console.log('Usage: node browser_grab.mjs records.json --root CORPUS --profile TASK_PROFILE [--port 9222]');
    return args.includes('--help') ? 0 : 2;
  }
  const recordsPath = args[0];
  function value(flag) { const i = args.indexOf(flag); return i >= 0 ? args[i + 1] : undefined; }
  const root = value('--root'), profile = value('--profile'), port = value('--port') || '9222';
  if (!root || !profile) throw new Error('Provide corpus root and task profile');
  assertTaskBrowser(profile, port);
  const records = loadRecords(recordsPath, root);
  function checkpoint() {
    fs.writeFileSync(recordsPath + '.tmp', JSON.stringify(records, null, 2) + '\n');
    fs.renameSync(recordsPath + '.tmp', recordsPath);
  }
  const { chromium } = await import('playwright');
  const browser = await chromium.connectOverCDP('http://127.0.0.1:' + port);
  let page;
  let ok = 0, humanAction = false;
  try {
    page = await browser.contexts()[0].newPage();
    for (const rec of records) {
      if (fs.existsSync(rec.dest)) { console.log(`${rec.id}: existing file retained for validation`); continue; }
      let saved = false, note = 'No PDF route found';
      try {
        saved = await downloadRecord(page, rec);
      } catch (error) { note = String(error); humanAction = error.code === 'HUMAN_ACTION_REQUIRED'; }
      rec.attempts.push({ route: 'dedicated-browser', outcome: saved ? 'downloaded' : 'failed', timestamp: new Date().toISOString(), note: saved ? '' : note });
      if (saved) { rec.route_used = 'dedicated-browser'; ok++; }
      checkpoint();
      console.log(`${rec.id}: ${saved ? 'downloaded' : note}`);
      if (humanAction) break;
    }
  } finally {
    checkpoint();
    if (!humanAction) await page?.close().catch(() => {});
    await browser.close(); // Disconnect; retain the dedicated browser for user-directed cleanup.
  }
  console.log(`${ok}/${records.length} downloaded via browser`);
  const audit = spawnSync(python, [path.join(dir, 'corpus.py'), path.resolve(recordsPath), '--root', path.resolve(root)], { stdio: 'inherit' });
  return audit.status ?? 1;
}

if (process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main();
}
