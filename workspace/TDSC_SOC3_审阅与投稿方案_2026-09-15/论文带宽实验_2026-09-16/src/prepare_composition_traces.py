from workloads import stored_trace
for seed in range(101,106):
    for workload in ('uniform','hot90','zipf09','scan'):stored_trace(4096,6144,seed,workload)
print('20 composition input traces validated before remaining queued runs')
