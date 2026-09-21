"""Freeze only the completed public workload evidence, with independent answers."""
from common import *
import bz2,csv,statistics,math
from collections import defaultdict
from fractions import Fraction as F
from analyze_extended_results import audit_record,matched


def main():
    pp=PACKAGE/'formal_public_plan.json';plan=json.loads(pp.read_text());windows={};raw_hashes={}
    for name in ('Financial1','WebSearch1'):
        source=PACKAGE/'datasets/raw'/f'{name}.spc.bz2';raw_hashes[str(source.relative_to(PACKAGE))]=sha(source)
        with bz2.open(source,'rt') as f:
            reader=csv.reader(f)
            for index,seed in enumerate(range(101,106)):
                path=PACKAGE/'datasets/prepared'/f'{name}_startkey_N16384_seed{seed}.json';w=json.loads(path.read_text())
                assert w['source_sha256']==sha(source) and w['source_records']==[index*6144,(index+1)*6144]
                mapping={(x['asu'],x['lba']):x['oram_address'] for x in w['mapping']}
                assert len(mapping)==len(set(mapping.values()))==w['unique_start_keys']
                assert len(w['rows'])==6144 and (w['N'],w['warmup'],w['requests'])==(16384,2048,4096)
                versions=[0]*16384;ans=hashlib.sha256();seen=set();reads=0;size=0
                for i,(a,v) in enumerate(w['rows']):
                    raw=next(reader);key=(int(raw[0]),int(raw[1]));op=raw[3].strip().upper();assert op in ('R','W')
                    assert (a,v)==(mapping[key],None if op=='R' else i+1)
                    seen.add(key);reads+=op=='R';size+=int(raw[2])
                    if i==0:assert raw[4].strip()==w['first_timestamp']
                    if i==6143:assert raw[4].strip()==w['last_timestamp']
                    old=(a.to_bytes(8,'big')+bytes(56)) if versions[a]==0 else hashlib.shake_256(
                        b'SOC3-EVAL-PAYLOAD-v1'+a.to_bytes(8,'big')+versions[a].to_bytes(8,'big')).digest(64)
                    ans.update(old)
                    if v is not None:versions[a]=v
                assert seen==set(mapping) and reads/6144==w['source_read_fraction'] and size/6144==w['source_mean_request_bytes']
                windows[name+'_startkey',seed]=dict(path=str(path.relative_to(PACKAGE)),sha256=sha(path),source=w['source'],
                    source_sha256=w['source_sha256'],source_records=w['source_records'],unique_keys=len(mapping),
                    read_fraction=reads/6144,answer_sha256=ans.hexdigest(),commands=6144,semantics=w['semantics'],restrictions=w['restrictions'])
    records={};receipts=[];groups=defaultdict(list)
    for item in plan['items']:
        s=item['spec'];p=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json";r=json.loads(p.read_text())
        assert item['entry']=='composition' and audit_record(r,s,'composition')
        assert (s['N'],s['B'],s['warmup'],s['requests'])==(16384,64,2048,4096)
        w=windows[s['workload'],s['trace_seed']]
        assert r['trace']['path']==w['path'] and r['trace']['sha256']==w['sha256'] and r['answer_sha256']==w['answer_sha256']
        assert not r['native_full_paper_reproduction'] and not r['latency_claim'] and not r['true_client_peak_measured']
        seq=[b['next_sequence'] for b in r['setup']]
        assert all(b['first_sequence']==0 for b in r['setup'])
        for phase in ('warmup','measurement'):
            for i,b in enumerate(r['phases'][phase]['bills']):assert b['first_sequence']==seq[i];seq[i]=b['next_sequence']
        assert len(r['server_storage'])==len(seq)
        for obj in r['server_storage']:assert obj['total_bytes']==sum(obj['components'].values())
        records[s['id']]=r;receipts.append(dict(id=s['id'],path=str(p.relative_to(PACKAGE)),sha256=sha(p)))
        groups[s['family'],s['workload']].append(r)
    assert len(records)==80 and len(groups)==4
    effects=[];cells=[]
    for (family,workload),rs in sorted(groups.items()):
        by={(r['spec']['kind'],r['spec']['trace_seed']):r for r in rs};assert len(by)==20
        for kind in ('deferred','sde','ring','r0'):
            group=[by[kind,seed] for seed in range(101,106)]
            vals=[r['bytes_per_request'] for r in group]
            cells.append(dict(family=family,workload=workload,kind=kind,n=5,mean=statistics.mean(vals),range=[min(vals),max(vals)],
                rpc_mean=statistics.mean(r['rpc_per_request'] for r in group),ids=[r['spec']['id'] for r in group]))
        for base,new in (('deferred','sde'),('ring','r0')):
            pairs=[]
            for seed in range(101,106):
                a,b=by[base,seed],by[new,seed];matched(a,b)
                ignore={'id','kind'}
                assert {k:v for k,v in a['spec'].items() if k not in ignore}=={k:v for k,v in b['spec'].items() if k not in ignore}
                av=a['phases']['measurement']['total_bytes']/4096;bv=b['phases']['measurement']['total_bytes']/4096
                p=dict(seed=seed,baseline_id=a['spec']['id'],variant_id=b['spec']['id'],baseline_bytes=av,variant_bytes=bv,saving_pct=100*(1-bv/av))
                if family=='rho':
                    aa=a['phases']['measurement']['bills'];bb=b['phases']['measurement']['bills']
                    assert aa[0]['transcript_sha256']==bb[0]['transcript_sha256'] and aa[0]['total_bytes']==bb[0]['total_bytes']
                    front,back,newback=aa[0]['total_bytes'],aa[1]['total_bytes'],bb[1]['total_bytes']
                    assert F(back-newback,front+back)==F(back,front+back)*F(back-newback,back)
                    p.update(front_bytes=front/4096,backend_share=float(F(back,front+back)),backend_saving_pct=100*float(F(back-newback,back)))
                pairs.append(p)
            vals=[p['saving_pct'] for p in pairs]
            effects.append(dict(family=family,workload=workload,baseline=base,variant=new,n=5,mean=statistics.mean(vals),
                range=[min(vals),max(vals)],ci95=None,per_window=pairs,baseline_mean=statistics.mean(p['baseline_bytes'] for p in pairs),
                variant_mean=statistics.mean(p['variant_bytes'] for p in pairs)))
    upstream=json.loads((PACKAGE/'results/extended_statistics.json').read_text());public=next(a for a in upstream['audits'] if a['study']=='public')
    assert public['completed']==public['expected']==80 and public['bindings']==[dict(x,source_id=x['id'],alias=False) for x in receipts]
    for e in effects:
        prior=next(p for p in upstream['pairs'] if p['study']=='public' and (p['family'],p['workload'],p['baseline'],p['selective'])==(e['family'],e['workload'],e['baseline'],e['variant']))
        assert prior['effect']['n']==5 and prior['effect']['ci95'] is None
        assert math.isclose(prior['effect']['mean'],e['mean'],abs_tol=1e-12) and prior['effect']['range']==e['range']
    result=dict(status='passed',runs=80,comparisons=8,cells=cells,effects=effects,receipts=receipts,windows=list(windows.values()),
        raw_hashes=raw_hashes,plan_sha256=sha(pp),auditor_sha256=sha(__file__),helper_sha256=sha(Path(__file__).parent/'analyze_extended_results.py'),
        source_runtime=records[receipts[0]['id']]['source_hashes'],statistical_unit='five preselected adjacent window/seed pairs per workload; mean and observed range, no iid CI',
        security_proof=False,native_full_system=False,latency_claim=False,full_paper_complete=False)
    save(PACKAGE/'results/public_completed_audit.json',result)
    print(json.dumps(dict(status='passed',runs=80,comparisons=8,independently_replayed_commands=61440)))


if __name__=='__main__':main()
