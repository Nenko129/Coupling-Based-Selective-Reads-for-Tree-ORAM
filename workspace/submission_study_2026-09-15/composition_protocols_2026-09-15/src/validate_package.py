"""Validate executed records and read-only provenance; seal this new package only."""
from pathlib import Path
from collections import defaultdict
from fractions import Fraction
from datetime import datetime,timezone
import ast,hashlib,json,math,statistics

OUT=Path(__file__).resolve().parents[1];PREP=OUT.parent;ROOT=PREP.parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def close(a,b):assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-9),(a,b)
def gain(old,new):return 100*(1-new/old)

def frozen_manifest(path):
    data=read(path);files=data.get('files',data)
    for relative,expected in files.items():
        p=(path.parent/relative).resolve()
        assert p.is_relative_to(path.parent.resolve()),relative
        assert p.is_file(),str(p)
        assert digest(p)==expected,str(p)
    return {'manifest':str(path),'manifest_sha256':digest(path),'files_verified':len(files),'unchanged':True}

def main():
    # None of these validation steps writes to the older evidence directories.
    older=[ROOT/'SOC3_audit_2026-09-15/BUNDLE_MANIFEST.json',PREP/'MANIFEST.sha256.json',
           PREP/'细化准备_2026-09-15/PREPARATION_MANIFEST.sha256.json',
           PREP/'四框架Selective扩展_2026-09-15/MANIFEST.sha256.json',
           PREP/'树状ORAM组合候选筛选_2026-09-15/MANIFEST.sha256.json']
    preservation=[frozen_manifest(p) for p in older]
    results=OUT/'results';short=read(results/'experiment_rows.json');long=read(results/'long_trace_rows.json')
    summary=read(results/'experiment_summary.json');ls=read(results/'long_trace_summary.json')
    assert len(short)==summary['rows']==216 and len(long)==ls['rows']==8
    assert len({(r['family'],r['workload'],r['seed'],r['backend']) for r in short})==216
    assert len({(r['family'],r['backend']) for r in long})==8
    groups=defaultdict(list)
    for r in short:groups[(r['family'],r['workload'],r['seed'])].append(r)
    for g in groups.values():
        assert len(g)==8 and len({r['schedule_sha256'] for r in g})==1
        assert all(r['correctness_checked'] for r in g)
    for family in ['free_compressed','rho']:
        assert len({r['schedule_sha256'] for r in long if r['family']==family})==1
    for r in short+long:
        bills=r['serialized_bills'];Q=r['measured_requests']
        assert all(sum(b['components'].values())==b['total_bytes'] for b in bills)
        close(r['bytes_per_request'],sum(b['total_bytes'] for b in bills)/Q)
        close(r['rpc_per_request'],sum(b['rpc'] for b in bills)/Q)
        assert all(not b['peak_memory_measured'] for b in bills)
    for a in summary['aggregate']:
        mean=a['mean_bytes_per_request']
        for backend,v in mean.items():
            rs=[r for r in short if (r['family'],r['workload'],r['backend'])==(a['family'],a['workload'],backend)]
            assert len(rs)==3;close(v,statistics.mean(r['bytes_per_request'] for r in rs))
        for field,old,new in [('pure_GC_vs_Deferred_pct','Deferred','SDE'),('SDE_vs_Path_pct','Path','SDE'),
                              ('pure_GC_Ring43_pct','Ring43','GC-Ring43'),('R0_vs_Ring43_pct','Ring43','R0-43'),
                              ('R0_vs_Ring76_pct','Ring76','R0-76')]:
            close(a[field],gain(mean[old],mean[new]))
        best_ring=min(['Ring43','Ring76'],key=mean.get);best_r0=min(['R0-43','R0-76'],key=mean.get)
        assert (best_ring,best_r0)==(a['two_profile_tuned_Ring'],a['two_profile_tuned_R0'])
        close(a['two_profile_tuned_gain_pct'],gain(mean[best_ring],mean[best_r0]))
    for a in ls['summary']:
        vals={r['backend']:r['bytes_per_request'] for r in long if r['family']==a['family']}
        assert vals==a['bytes_per_request']
        close(a['SDE_vs_Deferred_pct'],gain(vals['Deferred'],vals['SDE']))
        close(a['R0_vs_Ring43_pct'],gain(vals['Ring43'],vals['R0-43']))
    bindings=[]
    for name,h in summary['source_hashes'].items():
        p=OUT/'src'/name;assert digest(p)==h,str(p)
        bindings.append({'file':name,'sha256':h})
    functional=read(results/'prototype_checks.json');finite=read(results/'transfer_reduction_checks.json')
    assert functional['status']==finite['status']=='passed'
    assert len(functional['functional_cases'])==24 and len(functional['tamper_cases'])==6
    assert all(r['rejected_and_no_retry_io'] for r in functional['tamper_cases'])
    assert len(finite['configs'])==24 and finite['completed_boundaries_checked']==4329472
    assert all(Fraction(c['largest_exact_home_mean'])<=Fraction(c['poisson_rate_bound']) for c in finite['configs'])
    cert=read(results/'certificate_reuse.json')
    for c in cert['rows']:
        assert c['h']==c['L']+1
        assert c['r']==c['R']-(c['A']-1+(c['Z'] if c['rootless'] else 0))
        assert c['N_max']<=c['A']*2**(c['L']-1)
        assert c['h']<=(24 if c['Z']==7 else 31) and 0<=c['r']<=280
        assert digest(Path(c['grid']))==c['grid_sha256']
        assert Fraction(c['lifetime_upper_exact'])==c['Q_slot_bound']*Fraction(c['per_boundary_upper_exact'])
        assert Fraction(c['lifetime_upper_exact'])<=Fraction(1,2**132)
    assert len(cert['out_of_domain_rejections'])==2 and all(c['rejected'] for c in cert['out_of_domain_rejections'])
    derived=read(results/'derived_comparisons.json')
    assert len(derived['long_trace_breakdown'])==8
    for c in derived['rho_dilution']:
        close(c['total_saving_pct'],c['baseline_backend_share_pct']*c['backend_saving_pct']/100)
    for p in (OUT/'src').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
    contract=read(OUT/'variant_contract.json')
    assert contract['admissions_per_backend_slot_max']==1 and not contract['native_full_paper_reproduction']
    frozen=ROOT/'SOC3_audit_2026-09-15'
    selected=[frozen/'proofs/01_fusion.md',frozen/'proofs/02_parameterized_reduction.md',frozen/'proofs/03_numerical_audit.md']
    selected += [frozen/'research_20260914/optimization_v1/src'/name for name in ['optimized_oram.py','optimized_cost.py','fused_logical.py']]
    selected += sorted({Path(c['grid']) for c in cert['rows']})
    papers=[]
    for filename,title,url,sections in [
        ('free.pdf','Freecursive ORAM','https://people.csail.mit.edu/devadas/pubs/freecursive.pdf','unified tree / PLB; compressed PosMap; PMMAC'),
        ('ro.pdf','rho: Relaxed Hierarchical ORAM','https://users.cs.utah.edu/~rajeev/pubs/asplos19.pdf','exclusive caches; rho-tree; scheduling; ECC/compact')]:
        p=Path('C:/Users/12038/Desktop/for gpt')/filename
        papers.append({'title':title,'primary_url':url,'local_paper':str(p),'sha256':digest(p) if p.exists() else None,
                       'reviewed_mechanisms':sections,'access_note':'user-provided paper; public primary URL separately checked'})
    sources={'date':'2026-09-15','papers':papers,
             'frozen_dependencies':[{'path':str(p),'sha256':digest(p)} for p in selected],
             'prior_screening':str(PREP/'树状ORAM组合候选筛选_2026-09-15/候选评估与组合建议.md'),
             'new_theorem_status':'relative extension argument under explicit contract; no claim of new independent third-party audit'}
    (OUT/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
    receipt={'status':'passed','checked_at_utc':datetime.now(timezone.utc).isoformat(),
             'preserved_earlier_packages':preservation,'source_bindings_captured_by_main_experiment':bindings,
             'short_cases':216,'long_cases':8,'paired_short_schedule_groups':len(groups),'paired_long_schedule_groups':2,
             'all_serialized_components_sum_to_actual_bill':True,'all_reported_summary_ratios_recomputed':True,
             'functional_cases':24,'tamper_cases':6,'finite_parameter_configs':24,'finite_completed_boundaries':4329472,
             'certificate_rows':len(cert['rows']),'certificate_out_of_domain_rejections':2,
             'scope':'result/provenance validation by the producing agent, not independent protocol security certification',
             'known_limits':['native paper systems not fully reproduced','fixed public test keys',
                             'rho actual frame count is allowed leakage','rho backend still has trusted flat PosMap',
                             'no true peak trusted-memory or network-latency measurements','only two Z/A/S tuning profiles',
                             'frontend PRF hybrid/call budget awaits independent audit']}
    (OUT/'validation_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={p.relative_to(OUT).as_posix():digest(p) for p in sorted(OUT.rglob('*'))
              if p.is_file() and p.name!='MANIFEST.sha256.json' and '__pycache__' not in p.parts}
    (OUT/'MANIFEST.sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    assert all(digest(OUT/name)==h for name,h in manifest.items())
    print(json.dumps({'status':'passed','files_sealed':len(manifest),'earlier_packages':preservation,
                      'cases':224,'boundaries':4329472},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
