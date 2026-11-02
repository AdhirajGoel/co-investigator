#!/usr/bin/env python3
"""Classify access + collect download routes for a list of papers.

Input : a text file with one PMID or DOI per line (auto-detected), OR a records
        JSON [{"pmid":..,"doi":..}, ...].
Output: routes JSON to stdout (or --out): per paper
        {id, pmid, doi, oa, pmcid, pdf_url, host}

Usage : python3 get_routes.py ids.txt --email you@inst.edu [--out routes.json]
Uses curl (system) for all HTTP to avoid Python SSL/cert issues.
"""
import json, subprocess, re, argparse, time
from pathlib import Path
from urllib.parse import urlencode, quote

def curl(url):
    try:
        return subprocess.run(['curl','-s','--max-time','40',url],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ''

def epmc_route(item):
    urls = item.get('fullTextUrlList', {}).get('fullTextUrl', [])
    pdf = next((u for u in urls if u.get('documentStyle') == 'pdf'
                and u.get('availability') == 'Open access' and u.get('url')), {})
    return {'pmcid': item.get('pmcid') or '', 'doi': item.get('doi') or '',
            'oa': item.get('isOpenAccess') == 'Y' or bool(pdf),
            'pdf_url': pdf.get('url'), 'host': pdf.get('site')}


def europepmc(pmids):
    """Batch query (25/call) -> {pmid: {pmcid, oa, doi}}."""
    out = {}
    for i in range(0, len(pmids), 25):
        batch = pmids[i:i+25]
        q = '%20OR%20'.join(f'EXT_ID:{p}' for p in batch)
        url = (f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
               f"query=({q})%20AND%20SRC:MED&resultType=core&pageSize=100&format=json")
        try:
            d = json.loads(curl(url))
        except Exception:
            continue
        for r in d.get('resultList', {}).get('result', []):
            pmid = r.get('pmid') or r.get('id')
            out[str(pmid)] = epmc_route(r)
        time.sleep(0.2)
    return out

def unpaywall(doi, email):
    j = curl(f"https://api.unpaywall.org/v2/{quote(doi, safe='/')}?{urlencode({'email':email})}")
    try:
        d = json.loads(j)
    except Exception:
        return {}
    loc = d.get('best_oa_location') or {}
    return {'oa': bool(d.get('is_oa')), 'pdf_url': loc.get('url_for_pdf'),
            'host': loc.get('host_type')}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('--email', help='Optional contact email for Unpaywall; omitted means Europe PMC only')
    ap.add_argument('--out')
    args = ap.parse_args()

    raw = Path(args.input).read_text()
    records = []
    if raw.lstrip().startswith('['):
        records = json.loads(raw)
    else:
        for line in raw.splitlines():
            s = line.strip()
            if not s:
                continue
            if re.fullmatch(r'\d{6,9}', s):
                records.append({'pmid': s, 'doi': ''})
            elif s.lower().startswith('10.') or 'doi.org' in s:
                records.append({'pmid': '', 'doi': re.sub(r'^.*doi\.org/', '', s)})

    if not records or not all(isinstance(r, dict) and (r.get('pmid') or r.get('doi')) for r in records):
        ap.error('Provide a non-empty corpus of PMID/DOI records')
    pmids = [r['pmid'] for r in records if r.get('pmid')]
    epmc = europepmc(pmids) if pmids else {}

    out = []
    for r in records:
        pm = str(r.get('pmid') or '')
        e = epmc.get(pm, {})
        if not e and r.get('doi'):
            query = 'DOI:"'+str(r['doi']).replace('"','')+'"'
            url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?'+urlencode({'query':query,'format':'json','resultType':'core','pageSize':1})
            try:
                found = json.loads(curl(url)).get('resultList',{}).get('result',[])
                if found:
                    item=found[0]
                    e=epmc_route(item)
                    pm=pm or item.get('pmid','')
            except (ValueError,TypeError): pass
        doi = r.get('doi') or e.get('doi') or ''
        rec = {'id': r.get('id') or pm or doi, 'pmid': pm, 'doi': doi,
               'oa': e.get('oa', False), 'pmcid': e.get('pmcid', ''),
               'pdf_url': e.get('pdf_url'), 'host': e.get('host')}
        if not (rec['pmcid'] or rec['pdf_url']) and doi and args.email:
            up = unpaywall(doi, args.email)
            rec['oa'] = rec['oa'] or up.get('oa', False)
            rec['pdf_url'] = up.get('pdf_url')
            rec['host'] = up.get('host')
            time.sleep(0.1)
        out.append(rec)

    text = json.dumps(out, indent=1)
    if args.out:
        Path(args.out).write_text(text)
        n_pmc = sum(1 for r in out if r['pmcid'])
        n_pdf = sum(1 for r in out if r['pdf_url'])
        print(f"{len(out)} papers | {n_pmc} with PMC | {n_pdf} with direct PDF | "
              f"{sum(1 for r in out if not (r['pmcid'] or r['pdf_url']))} unresolved -> {args.out}")
    else:
        print(text)

if __name__ == '__main__':
    main()
