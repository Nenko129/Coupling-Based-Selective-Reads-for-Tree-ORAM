"""Download the cited public research traces with immutable source receipts."""
from common import *
import urllib.request,time,bz2,subprocess

def main():
    dest=PACKAGE/'datasets/raw';dest.mkdir(parents=True,exist_ok=True);rows=[]
    names=('SPC-Traces.pdf','Financial1.spc.bz2','WebSearch1.spc.bz2')
    for name in names:
        url='https://skulddata.cs.umass.edu/traces/storage/'+name;path=dest/name
        if not path.exists():
            # Windows curl uses the OS trust store. Do not disable TLS checks.
            subprocess.run(['curl.exe','--fail','--location','--silent','--show-error','--max-time','240',
                            '--output',str(path.with_suffix(path.suffix+'.part')),url],check=True)
            os.replace(path.with_suffix(path.suffix+'.part'),path)
        row=dict(filename=name,url=url,downloaded_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),bytes=path.stat().st_size,sha256=sha(path))
        if name.endswith('.bz2'):
            with bz2.open(path,'rt') as inp:row['first_record']=inp.readline().strip()
        rows.append(row);print(json.dumps(row),flush=True)
        save(PACKAGE/'datasets/download_receipt.json',dict(source_page='https://traces.cs.umass.edu/docs/traces/storage/',
             license_page='https://traces.cs.umass.edu/',attribution='UMass Trace Repository; HP, IBM and Storage Performance Council',
             license='Repository states CC BY 4.0 unless otherwise specified; preserve SPC documentation copyright notice',files=rows))
if __name__=='__main__':main()
