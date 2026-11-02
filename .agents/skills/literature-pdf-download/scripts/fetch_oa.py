#!/usr/bin/env python3
"""Download authorized open PDF routes atomically and reconcile the corpus."""
import argparse
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlparse
from corpus import load_records,verify,now,reconcile


def download(record,min_kb):
    dest=Path(record['dest'])
    if verify(dest,min_kb)[0]: return True
    # Never replace an existing candidate; the scientist can inspect it first.
    if dest.exists():
        record['attempts'].append({'route':'existing-file','outcome':'blocked','timestamp':now(),'note':'Existing invalid file retained; move it explicitly before retrying'})
        return False
    candidates=[]
    if record.get('pmcid'):
        import re
        if not re.fullmatch(r'PMC\d+',record['pmcid']): raise ValueError('Invalid PMCID')
        candidates.append(('europepmc',f"https://europepmc.org/articles/{record['pmcid']}?pdf=render"))
    if record.get('pdf_url'): candidates.append(('direct-pdf',record['pdf_url']))
    for route,url in candidates:
        if urlparse(url).scheme != 'https' or not urlparse(url).hostname:
            raise ValueError('PDF routes must use HTTPS')
        dest.parent.mkdir(parents=True,exist_ok=True)
        temp=None
        try:
            with tempfile.NamedTemporaryFile(dir=dest.parent,suffix='.part',delete=False) as f: temp=Path(f.name)
            result=subprocess.run(['curl','--fail','--silent','--show-error','--location','--proto','=https','--proto-redir','=https','--max-time','120',url,'--output',str(temp)],capture_output=True,text=True,timeout=130)
            valid,_,_,reason=verify(temp,min_kb)
            ok=result.returncode==0 and valid
            record['attempts'].append({'route':route,'outcome':'downloaded' if ok else 'failed','timestamp':now(),'note':'' if ok else (reason or 'HTTP retrieval failed')})
            if ok:
                # Hard-link gives no-clobber publication of a complete download.
                import os
                os.link(temp,dest)
                record['route_used']=route
                return True
        except (OSError,subprocess.TimeoutExpired) as exc:
            record['attempts'].append({'route':route,'outcome':'failed','timestamp':now(),'note':type(exc).__name__})
        finally:
            if temp is not None: temp.unlink(missing_ok=True)
    return False


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('records',type=Path);ap.add_argument('ids',nargs='*');ap.add_argument('--root',type=Path,required=True);ap.add_argument('--min-kb',type=int,default=30)
    a=ap.parse_args()
    if a.min_kb<0: ap.error('--min-kb must be non-negative')
    try:
        records=load_records(a.records,a.root)
        if a.ids and set(a.ids)-{r['id'] for r in records}: ap.error('Unknown record ID requested')
        for r in records:
            if not a.ids or r['id'] in a.ids: download(r,a.min_kb)
        return 0 if reconcile(records,a.records,a.root,a.min_kb) else 1
    except (OSError,ValueError,subprocess.TimeoutExpired) as e: ap.exit(1,str(e)+'\n')

if __name__=='__main__': raise SystemExit(main())
