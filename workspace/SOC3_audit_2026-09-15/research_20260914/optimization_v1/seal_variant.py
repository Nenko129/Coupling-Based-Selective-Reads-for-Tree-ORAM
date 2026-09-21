"""Bind this research variant separately from the original SOC2 contract."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((ROOT/'numerics/recompute_receipt.json').read_text())
for name,digest in receipt['source_and_outputs_sha256'].items():assert sha(ROOT/'numerics'/name)==digest
files=list((ROOT/'src').glob('*.py'))+list((ROOT/'proofs').glob('*.md'))
files += [ROOT/'numerics'/n for n in receipt['source_and_outputs_sha256']]
files += [ROOT/'numerics/recompute.py',ROOT/'numerics/recompute_receipt.json']
contract=dict(scope_id='SOC3-GC-m2-Z4A3-Z7A6-2026-09-14',
    profiles=[dict(Z=4,A=3,kinds=['sde','r0'],m=2),dict(Z=7,A=6,kinds=['r0'],m=2)],
    offsets=dict(sde_Z4A3=2,r0_Z4A3=6,r0_Z7A6=12),
    serializer=dict(version=3,frame=36,tag=64,nonce=16,compact_headers={'Z4':204,'Z7':300},fused_neutral=True),
    request_model='Fixed histories independent of ORAM coins; single serial nonrollback fail-stop client.',
    artifact_sha256={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(set(files))},
    proof_assistant_formalized=False,
    interpretation='Research-level source/proof/numeric identity. This is not a deployment attestation or the original SOC2 contract.')
(ROOT/'variant_contract.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
print('Variant contract bound',len(contract['artifact_sha256']),'artifacts')
