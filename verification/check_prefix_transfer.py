#!/usr/bin/env python3
"""Exact arithmetic for the b=4 prefixed nested-interval construction."""
from pathlib import Path
from fractions import Fraction as F
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from verification.reporting import file_record, write_report


def check_prefix_transfer():
    b=s=4
    M=b**s
    C=M*M
    lengths=[C//(M//b**(i-1)) for i in range(1,s+1)]
    H=M+sum(lengths)
    assert H==M+(C-M)//(b-1)
    max_witness=0
    max_variation=0
    max_suffix=0
    argmax_witness=None
    for x in range(M):
        lefts=[(x//(M//b**i))*(M//b**i) for i in range(1,s+1)]
        assert lefts[-1]==x
        assert all(lefts[i]<=lefts[i+1] for i in range(s-1))
        prefix=x*(x-1)//2+(M-1-x)*(M-x)//2
        suffix=sum(L*(x-r) for L,r in zip(lengths,lefts))
        charge=C if x==0 else 2*C
        witness=charge+prefix+suffix
        variation=2*(M-1)+x-2*lefts[0]
        assert prefix<F(C,2)
        assert suffix<C
        assert witness<F(7*C,2)
        assert variation<3*M
        if witness>max_witness:max_witness=witness;argmax_witness=x
        max_variation=max(max_variation,variation)
        max_suffix=max(max_suffix,suffix)

    min_far=F(1)
    min_phase_lower=F(C)
    checks=0
    parent_count=0
    for i in range(1,s+1):
        m=M//b**(i-1)
        L=C//m
        assert L*m==C and m%b==0
        for start in range(0,M,m):
            parent_count+=1
            rs=[start+j*(m//b) for j in range(b)]
            for cache in range(M):
                far=sum(4*abs(cache-r)>=m for r in rs)
                farprob=F(far,b)
                expected_lower=F(sum(min(C,L*abs(cache-r)) for r in rs),b)
                assert farprob>=F(1,4)
                assert expected_lower>=F(C,16)
                min_far=min(min_far,farprob)
                min_phase_lower=min(min_phase_lower,expected_lower)
                checks+=1

    result={
        'status':'PASS',
        'b':b,'s':s,'M':M,'C':C,'phase_lengths':lengths,'known_horizon':H,
        'leaf_count':M,'phase_parent_count':parent_count,'cache_parent_checks':checks,
        'max_offline_witness_cost':max_witness,'argmax_witness_leaf':argmax_witness,
        'max_offline_witness_over_C':str(F(max_witness,C)),
        'uniform_offline_upper_bound_over_C':'7/2 (strict)',
        'max_suffix_distortion':max_suffix,
        'max_unscaled_variation':max_variation,'strict_variation_upper_bound':3*M,
        'max_scaled_variation_over_lambda':str(F(max_variation,C)),
        'minimum_far_child_probability':str(min_far),
        'minimum_conditional_phase_lower_bound_over_C':str(min_phase_lower/C),
        'scope':'b=4: exact witness costs, parent intervals, and phase expressions.'
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "artifacts/prefix_transfer.json")
    args = parser.parse_args()
    result = check_prefix_transfer()
    result["code"] = file_record(Path(__file__))
    output = write_report(args.report, result)
    print(json.dumps({"status": result["status"], "report": output,
                      "leaves": result["leaf_count"],
                      "cache_parent_checks": result["cache_parent_checks"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
