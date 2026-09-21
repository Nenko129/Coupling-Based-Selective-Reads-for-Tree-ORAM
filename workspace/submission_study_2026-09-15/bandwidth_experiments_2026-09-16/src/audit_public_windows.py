"""Independently compare all prepared windows to raw ASU/LBA/read-write records."""
from common import *
import bz2,csv

def main():
    checks=[]
    for name in ('Financial1','WebSearch1'):
        source=PACKAGE/'datasets/raw'/f'{name}.spc.bz2'
        with bz2.open(source,'rt') as stream:
            reader=csv.reader(stream)
            for index,seed in enumerate(range(101,106)):
                p=PACKAGE/'datasets/prepared'/f'{name}_startkey_N16384_seed{seed}.json'
                w=json.loads(p.read_text(encoding='utf-8'))
                assert sha(source)==w['source_sha256'] and w['source_records']==[index*6144,(index+1)*6144]
                mapping={(r['asu'],r['lba']):r['oram_address'] for r in w['mapping']}
                assert len(mapping)==len(set(mapping.values()))==w['unique_start_keys']
                seen=set();reads=0;sizes=0
                for i,entry in enumerate(w['rows']):
                    raw=next(reader);key=(int(raw[0]),int(raw[1]));op=raw[3].strip().upper();seen.add(key)
                    assert entry==[mapping[key],None if op=='R' else i+1]
                    assert op in ('R','W');reads+=op=='R';sizes+=int(raw[2])
                    if i==0:assert raw[4].strip()==w['first_timestamp']
                    if i==len(w['rows'])-1:assert raw[4].strip()==w['last_timestamp']
                assert seen==set(mapping) and len(w['rows'])==6144
                assert reads/6144==w['source_read_fraction'] and sizes/6144==w['source_mean_request_bytes']
                checks.append(dict(name=name,seed=seed,commands=6144,unique_keys=len(seen),prepared_file=str(p.relative_to(PACKAGE)),
                                   prepared_sha256=sha(p),raw_sha256=sha(source),read_fraction=reads/6144))
    save(PACKAGE/'datasets/window_audit.json',dict(status='passed',checks=checks,checker_sha256=sha(__file__),
         scope='exact command-key/op mapping; not source-length expansion or paced block-device replay'))
    print(json.dumps(dict(status='passed',windows=len(checks),commands=sum(r['commands'] for r in checks))))
if __name__=='__main__':main()
