#!/usr/bin/env python3
"""Exact finite checks of policies, segmentation, and ramp costs."""
from fractions import Fraction as Q
from itertools import product
from pathlib import Path
import argparse
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import refreshing
from refreshing import (
    CheckFailure, COUNTS, all_segmentations, check, check_policy_bounds,
    frontier_dp, ramp_formula, run_policy, schedule_cost, variation,
)
from verification.reporting import file_record, serial, write_report

ALPHABET = (Q(-1), Q(0), Q(1))
LAMBDAS = (Q(1, 4), Q(1), Q(4))
MAX_T = 7

def short_path_checks():
    paths = segmentations = dp_comparisons = 0
    for T in range(1, MAX_T+1):
        for path in product(ALPHABET, repeat=T):
            paths += 1
            best = {lam: None for lam in LAMBDAS}
            for n, distortion, starts in all_segmentations(path):
                segmentations += 1
                for lam in LAMBDAS:
                    candidate = (lam*n+distortion, n)
                    if best[lam] is None or candidate < best[lam]:
                        best[lam] = candidate
            for lam in LAMBDAS:
                dp_cost, dp_n, dp_starts = frontier_dp(path, lam)
                check((dp_cost, dp_n) == best[lam],
                      'all segmentations equal frontier DP', path=path, lam=lam,
                      exhaustive=best[lam], dp=(dp_cost, dp_n))
                check(schedule_cost(path, dp_starts, lam)[0] == dp_cost,
                      'frontier DP parent schedule realizes cost', path=path, lam=lam)
                dp_comparisons += 1
                check_policy_bounds(path, lam, 'anytime')
                if T >= 2:
                    check_policy_bounds(path, lam, 'clipped')
                if variation(path) == 0:
                    p = run_policy(path, lam, 'anytime')
                    check(p['starts'] == [0] and p['cost'] == lam,
                          'zero variation and T1 initial-only cost', path=path, lam=lam)
    return {'unique_paths': paths, 'max_horizon': MAX_T,
            'alphabet': list(ALPHABET), 'charges': list(LAMBDAS),
            'refresh_subsets_enumerated': segmentations,
            'exhaustive_vs_DP_comparisons': dp_comparisons}


def short_ramp_checks():
    comparisons = subsets = 0
    for T in range(1, MAX_T+1):
        for slope in (Q(1,7), Q(1), Q(3,2)):
            path = [slope*t for t in range(T)]
            best_distortion = {}
            for n, distortion, starts in all_segmentations(path):
                subsets += 1
                best_distortion[n] = min(best_distortion.get(n, distortion), distortion)
            for lam in (Q(0),)+LAMBDAS:
                for n in range(1, T+1):
                    expected = ramp_formula(T, n, slope, lam)
                    check(lam*n+best_distortion[n] == expected,
                          'ramp all segmentations equal fixed-N formula',
                          T=T, n=n, slope=slope, lam=lam)
                    comparisons += 1
    return {'ramp_paths': MAX_T*3, 'refresh_subsets_enumerated': subsets,
            'fixed_N_formula_comparisons': comparisons}


def exact_boundary_checks():
    cases = [
        ('anytime T2 equality', (Q(0),Q(1)), Q(1), 'anytime', [0]),
        ('anytime equality then strict trigger', (Q(0),Q(1),Q(1),Q(2)), Q(1), 'anytime', [0,2,3]),
        ('clipped lower boundary and equality', (Q(0),Q(1,4),Q(1,4),Q(1,4)), Q(1), 'clipped', [0]),
        ('clipped interior root equality', (Q(0),Q(-1,4),Q(1,2),Q(1,2)), Q(1), 'clipped', [0]),
        ('clipped upper cap equality', (Q(0),Q(2),Q(1)), Q(1), 'clipped', [0,1])
    ]
    records = []
    for label, path, lam, kind, starts in cases:
        p = check_policy_bounds(path, lam, kind)
        check(p['starts'] == starts, 'targeted strict-trigger refresh indices',
              fixture=label, path=path, lam=lam, expected=starts, actual=p['starts'])
        records.append({'name': label, 'path': path, 'lambda': lam,
                        'policy': kind, 'expected_refresh_indices': starts, 'result': p})
    regime_counts = {'small': 0, 'middle': 0, 'large': 0,
                     'V_equals_lambda_over_T': 0, 'V_equals_lambda_T': 0}
    for T in (2,3,5,7):
        for V in (Q(1,8),Q(1),Q(3),Q(12)):
            path = [Q(0)]*(T-1)+[V]
            for lam in (T*V/2, T*V, 2*T*V, V/(2*T), V/T, 2*V/T):
                p = check_policy_bounds(path, lam, 'clipped')
                regime = 'small' if V <= lam/T else 'middle' if V <= lam*T else 'large'
                regime_counts[regime] += 1
                regime_counts['V_equals_lambda_over_T'] += int(V == lam/T)
                regime_counts['V_equals_lambda_T'] += int(V == lam*T)
    # Equality tests on a ramp at threshold k/63, including its last point.
    path = [Q(t,63) for t in range(64)]
    for k in (1,2,7,31,63):
        for kind, lam in (('fixed', Q(64*k*k,63*63)), ('anytime', Q(k*k,63))):
            p = run_policy(path, lam, kind)
            check(k not in p['starts'] and (k+1 >= 64 or k+1 in p['starts']),
                  'ramp threshold equality is not a refresh', k=k, lam=lam, kind=kind)
    return {'explicit_traces': records, 'targeted_regime_case_counts': regime_counts,
            'ramp_equality_fixtures': 10,
            'T1_note': 'Anytime is checked atT1; clipped is not applied there because its theorem requiresT>=2.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "artifacts/verification.json")
    parser.add_argument("--manuscript", type=Path, help="Optional file to identify by hash")
    args = parser.parse_args()
    start = time.perf_counter()
    COUNTS.clear()
    report = {"status": "RUNNING", "max_horizon": MAX_T,
              "arithmetic": "fractions.Fraction", "check_counts": {}}
    try:
        report["code"] = {"algorithms": file_record(Path(refreshing.__file__)),
                          "verification": file_record(Path(__file__))}
        if args.manuscript is not None:
            report["manuscript"] = file_record(args.manuscript)
        report["short_paths"] = short_path_checks()
        report["short_ramps"] = short_ramp_checks()
        report["boundaries"] = exact_boundary_checks()
        report["status"] = "PASS"
    except Exception as failure:
        report["status"] = "FAIL"
        report["failure"] = {"type": type(failure).__name__,
                             "check": getattr(failure, "label", str(failure)),
                             "case": getattr(failure, "case", {})}
    report["check_counts"] = dict(COUNTS)
    report["elapsed_seconds"] = round(time.perf_counter() - start, 3)
    output = write_report(args.report, report)
    print(json.dumps({"status": report["status"], "report": output,
                      "elapsed_seconds": report["elapsed_seconds"]}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
