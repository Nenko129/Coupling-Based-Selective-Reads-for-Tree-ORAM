"""Document target-gate finding; preserve every original configuration."""
from common import *
from start_ir_compressed_validation import validate_plan
from audit_ir_compressed import inputs,audit_record
from audit_ir_compressed_failure import audit_failure

def main():
    p=PACKAGE/'formal_ir_compressed_plan.json';plan=json.loads(p.read_text());validate_plan(plan);outcomes=[]
    for s in plan['pilots']:
        if s['beta']==14:
            f=PACKAGE/'results'/s['experiment_class']/f"{s['id']}.json";r=json.loads(f.read_text());audit_record(r,s,**inputs())
            outcomes.append(dict(status='passed',path=str(f.relative_to(PACKAGE)),sha256=sha(f)))
        else:
            f=PACKAGE/'results/failures'/f"{s['id']}.json";r=json.loads(f.read_text());a=audit_failure(r,s)
            outcomes.append(dict(status='incomplete_horizon',path=str(f.relative_to(PACKAGE)),sha256=sha(f),audit=a))
    dest=PACKAGE/'ir_compressed_observation_amendment.json';assert not dest.exists()
    save(dest,dict(original_plan_sha256=sha(p),pilot_outcomes=outcomes,specs_unchanged=True,expected_observations=75,
        sources={n:sha(Path(__file__).parent/n) for n in ('audit_ir_compressed_failure.py','dispatch_ir_compressed_observations.py')},
        reason='Target beta4 completed 6143/6144 at measurement endpoint with one foreground request and one pending group reset. All slot budgets and input specifications are retained.',
        amended_after_pilot=True,amended_before_formal_outcomes=True,scope='outcome handling only; no runtime, workload, capacity, timing, matrix or security model change',
        main_gate='beta14 target and all six small-domain drivers pass; beta4 outcome is separately audited as noncompletion, never labeled passed.',
        failure_policy='All 15 original beta4 cases remain. Continue after only audited fixed-horizon incompletion. Other errors and any main-cohort error still stop. No silent retry.',
        reporting='Report all planned outcomes and completion fractions. Incomplete windows are excluded from bytes/completed-request paired estimates and cannot produce a five-pair claim. No independent partial-answer digest is available in failure records.',
        raw_dependency=plan['dependencies'],generator_sha256=sha(__file__)))
    print(json.dumps(dict(status='amendment_saved',retained_formal_cases=75,pilot_completed=6143,pilot_offered=6144)))

if __name__=='__main__':main()

