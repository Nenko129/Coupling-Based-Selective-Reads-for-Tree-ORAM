"""Read-only integrity check of the packages used by this experiment."""
from common import *

def main():
    base=PACKAGE.parent
    manifests=[ROOT/'SOC3_audit_2026-09-15/BUNDLE_MANIFEST.json',base/'MANIFEST.sha256.json',
               base/'细化准备_2026-09-15/PREPARATION_MANIFEST.sha256.json',base/'四框架Selective扩展_2026-09-15/MANIFEST.sha256.json',
               base/'树状ORAM组合候选筛选_2026-09-15/MANIFEST.sha256.json',base/'组合协议推进_2026-09-15/MANIFEST.sha256.json',
               base/'IR_AB_深入分析_2026-09-16/MANIFEST.sha256.json']
    rows=[]
    for path in manifests:
        obj=json.loads(path.read_text(encoding='utf-8'));files=obj.get('files',obj)
        for rel,expected in files.items():
            assert isinstance(expected,str) and len(expected)==64,(path,rel)
            assert sha(path.parent/rel)==expected,('frozen file changed',path.parent/rel)
        rows.append(dict(manifest=str(path.relative_to(ROOT)),manifest_sha256=sha(path),files_checked=len(files),unchanged=True))
    save(PACKAGE/'results/frozen_input_integrity.json',dict(status='passed',packages=rows))
    print(json.dumps(dict(status='passed',packages=len(rows),files=sum(r['files_checked'] for r in rows))))
if __name__=='__main__':main()
