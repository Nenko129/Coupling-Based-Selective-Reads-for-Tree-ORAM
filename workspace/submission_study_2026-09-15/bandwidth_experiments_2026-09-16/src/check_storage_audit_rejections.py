"""Ensure the space audit rejects plausible but inconsistent object ledgers."""
from common import *
import copy
from audit_storage_components import audit_materialized


def main():
    index=json.loads((PACKAGE/'results/storage_components_audit.json').read_text());rows={}
    for row in index['receipts']:
        s=row['spec'];key='rho' if s.get('family')=='rho' else ('cached' if s.get('family')=='AB' else 'core' if not s.get('family') else None)
        if key is not None and key not in rows:rows[key]=json.loads((PACKAGE/row['source']['path']).read_text())
    assert set(rows)=={'rho','cached','core'}
    probes=[]
    def check(label,key,edit):
        r=copy.deepcopy(rows[key]);edit(r)
        try:audit_materialized(r)
        except (AssertionError,KeyError):probes.append(label);return
        raise AssertionError(('corrupted resource ledger accepted',label))
    def inflate(r):r['server_storage']['components']['headers']+=1;r['server_storage']['total_bytes']+=1
    def transfer(r):r['server_storage']['components']['headers']-=64;r['server_storage']['components']['global_tags']+=64
    check('balanced_header_inflation','core',inflate)
    check('same_total_wrong_components','core',transfer)
    check('missing_bucket_record','core',lambda r:r['server_storage'].__setitem__('physical_bucket_records',0))
    check('wrong_terminal_size','core',lambda r:r.__setitem__('terminal_position_map_bytes',0))
    check('unreported_cache_object','cached',lambda r:r['cache_representation'].__setitem__('bytes',0))
    check('wrong_cache_cut','cached',lambda r:r['spec'].__setitem__('cached_levels',0))
    check('missing_rho_stash_reservation','rho',lambda r:r['frontend_memory_representation'].__setitem__('back_stash_reserved_bytes',0))
    check('hidden_full_posmap','rho',lambda r:r['frontend_memory_representation'].__setitem__('flat_backend_posmap_bytes',0))
    save(PACKAGE/'results/storage_audit_rejections.json',dict(status='passed',rejected=probes,checker_sha256=sha(__file__),
        resource_auditor_sha256=sha(Path(__file__).parent/'audit_storage_components.py'),resource_receipt_sha256=sha(PACKAGE/'results/storage_components_audit.json'),
        true_client_peak_measured=False))
    print(json.dumps(dict(status='passed',rejected=len(probes))))


if __name__=='__main__':main()
