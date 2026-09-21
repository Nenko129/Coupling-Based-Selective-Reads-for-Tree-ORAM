"""Temporal-locality replay without guessing the source LBA unit."""
from common import *
import bz2,csv,random

def main():
    summary=[];N=16384;K=6144
    for name in ('Financial1','WebSearch1'):
        source=PACKAGE/'datasets/raw'/f'{name}.spc.bz2'
        with bz2.open(source,'rt') as stream:
            reader=csv.reader(stream)
            for index,seed in enumerate(range(101,106)):
                native=[]
                for _ in range(K):
                    raw=next(reader);asu,lba,size=int(raw[0]),int(raw[1]),int(raw[2]);op=raw[3].strip().upper()
                    assert op in ('R','W') and size>=0
                    native.append((asu,lba,size,op,raw[4].strip()))
                keys=sorted({(r[0],r[1]) for r in native});assert len(keys)<=N
                perm=list(range(N));random.Random(271828+seed).shuffle(perm)
                mapping={k:perm[i] for i,k in enumerate(keys)}
                rows=[(mapping[r[:2]],i+1 if r[3]=='W' else None) for i,r in enumerate(native)]
                path=PACKAGE/'datasets/prepared'/f'{name}_startkey_N{N}_seed{seed}.json'
                record=dict(source=str(source.relative_to(PACKAGE)),source_sha256=sha(source),source_records=[index*K,(index+1)*K],
                     N=N,warmup=2048,requests=4096,trace_seed=seed,rows=rows,
                     mapping=[dict(asu=k[0],lba=k[1],oram_address=v) for k,v in mapping.items()],
                     unique_start_keys=len(keys),source_read_fraction=sum(r[3]=='R' for r in native)/K,
                     source_mean_request_bytes=sum(r[2] for r in native)/K,first_timestamp=native[0][4],last_timestamp=native[-1][4],
                     semantics='one fixed-size ORAM record per source command start key (ASU,LBA); temporal locality replay',
                     restrictions=['not full block-device replay','source lengths not expanded or charged as ORAM useful bytes',
                                   'timestamps not used for pacing','bijective randomized mapping preserves repeated-key equality, not physical spatial distances',
                                   'no modulo folding; source LBA byte unit not assumed'],
                     actual_storage_application_claim=False)
                save(path,record)
                summary.append({k:v for k,v in record.items() if k not in ('rows','mapping')})
    save(PACKAGE/'datasets/prepared_windows.json',dict(status='prepared_not_executed',windows=summary,selection='first five consecutive 6144-command windows, fixed before ORAM evaluation'))
    print(json.dumps(dict(windows=len(summary),commands=sum(K for _ in summary),source_files=2)))
if __name__=='__main__':main()
