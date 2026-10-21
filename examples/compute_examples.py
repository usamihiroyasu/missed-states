#!/usr/bin/env python3
"""Compute exact costs and decisions on burst-plateau and ramp paths."""
from fractions import Fraction as Q
from pathlib import Path
import argparse
import csv
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import refreshing as core
from verification.reporting import serial

T = 64
LAM = Q(1)
SELECTED_IDS = ("burst_s1_m4_V1over2", "burst_s1_m4_V2over1")

def burst(start,length,V):
    return [Q(0) if t<start else V*min(t-start+1,length)/length for t in range(T)]


def regime(V):
    return 'small' if V<=LAM/T else 'middle' if V<=LAM*T else 'large'


def exact_trace(path,starts,lam):
    refreshset=set(starts);cache=0;count=0;D=Q(0);trace=[]
    for t,state in enumerate(path):
        refresh=t in refreshset
        if refresh:cache=t;count+=1
        error=abs(state-path[cache]);D+=error
        assert not refresh or error==0
        trace.append({'t':t,'state':state,'cache_index':cache,'cache_state':path[cache],
                      'refresh':refresh,'post_discrepancy':error,'cumulative_distortion':D,
                      'cumulative_refresh_count':count,'cumulative_cost':D+lam*count})
    return trace


def evaluate(case_id,family,path,meta):
    V=core.variation(path);assert V==meta['V']
    dpcost,n,starts=core.frontier_dp(path,LAM,canonical=True)
    cost,D=core.schedule_cost(path,starts,LAM)
    assert cost==dpcost
    records={'offline':{'cost':cost,'distortion':D,'refresh_cost':LAM*n,
                         'count':n,'starts':starts,'trace':exact_trace(path,starts,LAM)}}
    for kind in ['anytime','clipped']:
        p=core.check_policy_bounds(path,LAM,kind)
        full=exact_trace(path,p['starts'],LAM)
        assert full[-1]['cumulative_cost']==p['cost']
        by_t={x['t']:x for x in p['trace']}
        for t in range(1,T):
            step=by_t[t]
            full[t].update({'S':step['S'],'threshold_squared':step['threshold_squared'],
                           'pre_decision_drift_squared':step['pre_decision_drift_squared']})
            assert full[t]['refresh']==step['refresh']
        records[kind]={'cost':p['cost'],'distortion':p['distortion'],
                       'refresh_cost':LAM*p['count'],'count':p['count'],
                       'starts':p['starts'],'trace':full}
        assert p['cost']>=cost
    return {'case_id':case_id,'family':family,'T':T,'lambda':LAM,'V':V,
            'clipped_regime':regime(V),'metadata':meta,'path':path,'policies':records}

def compute_cases():
    cases=[]
    for start in [1,17,49,57]:
        for length in [1,4]:
            for V in [Q(1,4),Q(1,2),Q(2)]:
                meta={'start':start,'length':length,'V':V,'plateau_begins_at':start+length-1,
                      'stationary_opportunities_after_burst':T-start-length}
                case_id=f'burst_s{start}_m{length}_V{V.numerator}over{V.denominator}'
                cases.append(evaluate(case_id,'burst_plateau',burst(start,length,V),meta))
    for k in range(-3,16):
        V=Q(2**k,64) if k>=0 else Q(1,64*2**(-k))
        path=[V*Q(t,T-1) for t in range(T)]
        row=evaluate(f'ramp_k{k}','variation_regime_ramp',path,{'k':k,'V':V,'slope':V/(T-1)})
        exact=min(core.ramp_formula(T,n,V/(T-1),LAM) for n in range(1,T+1))
        assert row['policies']['offline']['cost']==exact
        cases.append(row)

    return cases


def write_csv(path, cases, traces=False):
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        if traces:
            writer.writerow(["case_id", "policy", "t", "state", "cache_index",
                             "refresh", "post_discrepancy", "cumulative_cost"])
            for case in cases:
                for name, record in case["policies"].items():
                    for step in record["trace"]:
                        writer.writerow([case["case_id"], name, step["t"], step["state"],
                                         step["cache_index"], step["refresh"],
                                         step["post_discrepancy"], step["cumulative_cost"]])
        else:
            writer.writerow(["case_id", "V", "policy", "cost", "distortion",
                             "refresh_cost", "refresh_count", "refresh_indices"])
            for case in cases:
                for name, record in case["policies"].items():
                    writer.writerow([case["case_id"], case["V"], name, record["cost"],
                                     record["distortion"], record["refresh_cost"],
                                     record["count"], " ".join(map(str, record["starts"]))])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/examples")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cases = compute_cases()
    selected = [next(case for case in cases if case["case_id"] == name)
                for name in SELECTED_IDS]
    for filename, records in [("path_results.json", cases),
                              ("adaptive_examples.json", selected)]:
        output = {"T": T, "lambda": LAM, "cases": records}
        (args.output_dir / filename).write_text(json.dumps(serial(output), indent=2) + "\n")
    write_csv(args.output_dir / "costs.csv", cases)
    write_csv(args.output_dir / "traces.csv", cases, traces=True)
    print(json.dumps({"paths": len(cases), "illustrated_paths": len(selected)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
