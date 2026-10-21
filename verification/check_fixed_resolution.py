#!/usr/bin/env python3
"""Exact finite-grid checks of the policy that follows every state change."""
from fractions import Fraction as Q
from itertools import product
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import refreshing
from refreshing import all_segmentations
from verification.reporting import file_record, write_report

ALPHABET = (Q(0), Q(1), Q(2))
SPACING = Q(1)
CHARGES = (Q(1, 4), Q(1), Q(3))
MAX_T = 5


def check_fixed_resolution():
    paths = partitions = objectives = 0
    largest_ratio = {charge: Q(0) for charge in CHARGES}
    for T in range(1, MAX_T + 1):
        for path in product(ALPHABET, repeat=T):
            paths += 1
            changes = [t for t in range(1, T) if path[t] != path[t - 1]]
            K = len(changes)
            following_starts = [0] + changes
            retained = path[0]
            following_distortion = Q(0)
            chosen = set(following_starts)
            for t, observation in enumerate(path):
                if t in chosen:
                    retained = observation
                following_distortion += abs(observation - retained)
            if following_distortion != 0 or len(following_starts) != K + 1:
                raise AssertionError("Following each change must give zero discrepancy")
            for N, D, starts in all_segmentations(path):
                partitions += 1
                # Reset boundaries account for at most N-1 changes. Within a
                # segment, each change is bounded by its two endpoint errors.
                if K > N - 1 + 2 * D / SPACING:
                    raise AssertionError("Change-count inequality failed")
                # Recompute D directly from segment endpoints, independently
                # of the retained-state replay used by all_segmentations.
                ends = starts[1:] + [T]
                direct_D = sum((abs(path[t] - path[s])
                                for s, end in zip(starts, ends)
                                for t in range(s, end)), Q(0))
                if direct_D != D or N != len(starts):
                    raise AssertionError("Segment cost replay failed")
                for charge in CHARGES:
                    objectives += 1
                    following_cost = charge * (K + 1)
                    comparator_cost = charge * N + D
                    factor = max(Q(1), 2 * charge / SPACING)
                    if following_cost > factor * comparator_cost:
                        raise AssertionError("Fixed-resolution cost bound failed")
                    largest_ratio[charge] = max(largest_ratio[charge],
                                                 following_cost / comparator_cost)
    if (paths, partitions, objectives) != (363, 4665, 13995):
        raise AssertionError("Unexpected finite-grid case count")
    return {"status": "PASS", "alphabet": ALPHABET, "spacing": SPACING,
            "max_horizon": MAX_T, "charges": CHARGES, "paths": paths,
            "partitions": partitions, "objective_checks": objectives,
            "change_count_inequality_checks": partitions,
            "change_following_zero_discrepancy_checks": paths,
            "inequality": "K <= N-1+2D/delta",
            "cost_bound": "lambda*(K+1) <= max(1,2lambda/delta)*(lambda*N+D)",
            "largest_cost_ratio_over_all_schedules_by_charge": largest_ratio}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "artifacts/fixed_resolution.json")
    args = parser.parse_args()
    report = check_fixed_resolution()
    report["code"] = {"verification": file_record(Path(__file__)),
                      "algorithms": file_record(Path(refreshing.__file__))}
    output = write_report(args.report, report)
    print(json.dumps({"status": report["status"], "report": output,
                      "paths": report["paths"], "partitions": report["partitions"],
                      "objective_checks": report["objective_checks"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
