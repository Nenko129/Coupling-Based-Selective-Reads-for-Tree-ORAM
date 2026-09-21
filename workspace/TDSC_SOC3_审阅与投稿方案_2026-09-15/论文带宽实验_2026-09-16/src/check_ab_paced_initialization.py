"""Target-scale initialization, including the earlier failed Ring configuration."""
from common import *
import ab_cb_runtime as rt
import ab_paced_frontend as paced
from audit_ab_cb import bill
from meter import server_storage


def identity():return dict(runtime=rt.identity(),frontend=sha(Path(__file__).parent/'ab_paced_frontend.py'),checker=sha(__file__))


def main():
    source=identity();rows=[]
    for bottom,layout in ((None,'uniform'),(0,'bottom_d0')):
        for kind in ('ring','gc_ring','r0'):
            rt.install(dict(seed=5101,R=500,cached_levels=6,Y=4,bottom_dummy=bottom));paced.Backend=rt.Backend
            f=paced.PacedGeometryStepwiseFront(kind,N=4096,B=64,X=16,L=11,plb=8,seed=5101,profile=(5,5,7));b=f.backend
            assert f.total==4369 and b.tree.t==f.total*5 and b.tree.births==f.total
            assert b.tree.max_boundary<=500 and b.tree.logical_calls.useful.count==f.total
            init=b.io.snapshot();bill(init)
            # Every original data record must still be available with its exact
            # initial value; this also exercises recursive maps after loading.
            b.io.reset_meter()
            for address in range(4096):
                assert f.access(address)==rt.frontends.initial_payload(address,64)
            validation=b.io.snapshot();bill(validation)
            row=dict(kind=kind,layout=layout,population=f.total,initial_slots=f.total*5,setup_bill=init,
                validation_bill=validation,checked_data_records=4096,max_boundary_stash=b.tree.max_boundary,
                server_storage=server_storage(b.server),cache=b.io.cache_storage(),final_t=b.tree.t)
            rows.append(row)
            save(PACKAGE/'results/ab_paced_initialization_progress.json',dict(status='partial',source_hashes=source,cases=rows,expected_cases=6))
            print(json.dumps(dict(kind=kind,layout=layout,status='passed',initial_slots=f.total*5,max_stash=b.tree.max_boundary)),flush=True)
    assert source==identity()
    save(PACKAGE/'results/ab_paced_initialization_checks.json',dict(status='passed',source_hashes=source,cases=rows,
        prior_failure_preserved='ABPER_uniform_ring_uniform_seed101 initialization overflow at R500',
        measured_performance=False,capacity_certificate=False))


if __name__=='__main__':main()
