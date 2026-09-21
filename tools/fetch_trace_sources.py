"""Optional download with original SHA256 checks; never rewrites frozen receipts."""
from pathlib import Path
import argparse,hashlib,json,urllib.request
from reproduce import ROOT,EVAL
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args()
dest=a.out.resolve();assert not dest.is_relative_to(ROOT),'Use an external directory'
dest.mkdir(parents=True,exist_ok=True)
r=json.loads((ROOT/'workspace'/EVAL/'datasets/download_receipt.json').read_text(encoding='utf-8'))
for item in r['files']:
    f=dest/item['filename']
    if not f.exists():
        partial=f.with_suffix(f.suffix+'.part')
        urllib.request.urlretrieve(item['url'],partial)
        assert hashlib.sha256(partial.read_bytes()).hexdigest()==item['sha256'],f.name
        partial.replace(f)
    assert hashlib.sha256(f.read_bytes()).hexdigest()==item['sha256'],f.name
    print('verified',f.name)
