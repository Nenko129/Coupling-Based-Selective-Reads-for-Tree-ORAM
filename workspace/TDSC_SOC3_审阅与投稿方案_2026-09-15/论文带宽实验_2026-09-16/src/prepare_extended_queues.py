from common import *
from itertools import zip_longest

def make(name,plans,dependencies):
    inputs=[];hashes={}
    for p in plans:
        path=PACKAGE/p;hashes[p]=sha(path);inputs.append(json.loads(path.read_text())['items'])
    # Interleave calibration/public/sensitivity groups so each area progresses.
    items=[item for group in zip_longest(*inputs) for item in group if item is not None]
    path=PACKAGE/name;assert not path.exists()
    save(path,dict(items=items,source_plan_hashes=hashes,dependencies=dependencies,workers=1))

def main():
    make('extended_small_queue.json',['formal_calibration_plan.json','formal_public_plan.json','formal_frontend_sensitivity_plan.json'],
         [dict(pid=34580,completion='results/free_continuation_completion.json')])
    make('extended_scale_queue.json',['formal_slices_plan.json'],
         [dict(pid=47116,completion='results/formal_tuned_queue_completion.json')])
    print(json.dumps(dict(small_runs=340,scale_new_runs=125)))
if __name__=='__main__':main()
