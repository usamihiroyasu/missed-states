#!/usr/bin/env python3
"""Exact checks of the clipped per-opportunity cap on 9,828 cases and six fixtures."""
from collections import Counter
from fractions import Fraction
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
from verification import verify_refreshing as verifier
from verification.reporting import file_record, write_report

ALPHABET = (-1, 0, 1)
LAMBDAS = (Fraction(1, 4), Fraction(1), Fraction(4))
MAX_T = 7
CHECK_COUNTS = Counter()

class FocusedFailure(Exception):
    def __init__(self, label, case):
        self.label = label
        self.case = case
        super().__init__(label)


def require(condition, label, **case):
    if not condition:
        raise FocusedFailure(label, case)
    CHECK_COUNTS[label] += 1


def classify(T, variation, lam):
    if variation <= lam / T:
        return "small"
    return "middle" if variation <= lam * T else "large"


def check_per_opportunity(path, lam, result):
    """Independently replay costs from decisions, including initialization."""
    T = len(path)
    trace = result["trace"]
    context = {"path": path, "lambda": lam}
    require(len(trace) == T - 1, "trace length", **context)
    require(result["starts"][0] == 0, "mandatory initial refresh", **context)
    initial_post_error = abs(path[0] - path[0])
    initial_cost = lam + initial_post_error
    require(initial_post_error == 0 and initial_cost == lam,
            "initial cost and zero error", **context)

    total = initial_cost
    distortion = Fraction(0)
    cache = 0
    starts = [0]
    per_time_costs = [initial_cost]
    for expected_t, step in enumerate(trace, 1):
        t = step["t"]
        require(t == expected_t, "ordered decision indices", **context, t=t)
        if step["refresh"]:
            cache = t
            starts.append(t)
        post_error = abs(path[t] - path[cache])
        require(post_error == step["post_decision_discrepancy"],
                "independent post-decision error", **context, t=t)
        if step["refresh"]:
            require(post_error == 0, "refresh has zero post-error", **context, t=t)
        else:
            require(post_error <= lam, "retention error at most charge", **context, t=t)
        cost = (lam if step["refresh"] else Fraction(0)) + post_error
        require(cost <= lam, "per-opportunity cost at most charge", **context, t=t)
        total += cost
        distortion += post_error
        per_time_costs.append(cost)

    require(starts == result["starts"] and len(starts) == result["count"],
            "refresh indices and count agree", **context)
    require(distortion == result["distortion"], "distortion total agrees", **context)
    require(total == result["cost"] == distortion + lam * len(starts),
            "initial plus per-time cost agrees", **context)
    require(total <= lam * T, "global clipped cap", **context)
    if result["V"] == 0:
        require(starts == [0] and total == lam, "zero variation", **context)
    return per_time_costs


def enumerate_cases(verifier):
    regimes = Counter()
    cap_by_regime = Counter()
    by_horizon = {}
    by_lambda = {str(lam): {"cases": 0, "cap_attained": 0} for lam in LAMBDAS}
    total = paths = zero_variation = cap_attained = 0
    for T in range(2, MAX_T + 1):
        horizon = {"paths": 0, "cases": 0, "regimes": Counter(), "cap_attained": 0}
        for raw_path in product(ALPHABET, repeat=T):
            path = tuple(Fraction(value) for value in raw_path)
            paths += 1
            horizon["paths"] += 1
            for lam in LAMBDAS:
                result = verifier.check_policy_bounds(path, lam, "clipped")
                check_per_opportunity(path, lam, result)
                regime = classify(T, result["V"], lam)
                hit_cap = result["cost"] == lam * T
                total += 1
                horizon["cases"] += 1
                horizon["regimes"][regime] += 1
                horizon["cap_attained"] += int(hit_cap)
                by_lambda[str(lam)]["cases"] += 1
                by_lambda[str(lam)]["cap_attained"] += int(hit_cap)
                regimes[regime] += 1
                zero_variation += int(result["V"] == 0)
                cap_attained += int(hit_cap)
                cap_by_regime[regime] += int(hit_cap)
        by_horizon[str(T)] = horizon
    require(total == 9828 and paths == 3276, "declared enumeration size",
            cases=total, paths=paths)
    return {"paths": paths, "cases": total, "regime_counts": regimes,
            "cap_attained": cap_attained, "cap_attained_by_regime": cap_by_regime,
            "zero_variation_cases": zero_variation, "by_horizon": by_horizon,
            "by_lambda": by_lambda}


def named_fixtures(verifier):
    Q = Fraction
    fixtures = [
        ("T2 equality without refresh", (Q(0), Q(1, 2)), [0], Q(3, 2)),
        ("T2 middle cap attainment", (Q(0), Q(3, 5)), [0, 1], Q(2)),
        ("T2 upper variation join", (Q(0), Q(2)), [0, 1], Q(2)),
        ("T2 large cap attainment", (Q(0), Q(3)), [0, 1], Q(2)),
        ("T7 alternating large cap attainment", tuple(Q(2 * (t % 2)) for t in range(7)),
         list(range(7)), Q(7)),
        ("T7 zero variation", (Q(0),) * 7, [0], Q(1)),
    ]
    records = []
    for name, path, expected_starts, expected_cost in fixtures:
        lam = Q(1)
        result = verifier.check_policy_bounds(path, lam, "clipped")
        per_time = check_per_opportunity(path, lam, result)
        require(result["starts"] == expected_starts and result["cost"] == expected_cost,
                "named fixture refreshes and cost", fixture=name, path=path,
                expected_starts=expected_starts, actual=result)
        if name == "T2 equality without refresh":
            step = result["trace"][0]
            require(step["pre_decision_drift_squared"] == step["threshold_squared"]
                    and not step["refresh"], "exact equality retains", fixture=name)
        records.append({"name": name, "path": path, "lambda": lam,
                        "regime": classify(len(path), result["V"], lam),
                        "expected_refresh_indices": expected_starts,
                        "expected_cost": expected_cost,
                        "cap_attained": result["cost"] == lam * len(path),
                        "per_time_costs": per_time, "result": result})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "artifacts/clipped_cap.json")
    parser.add_argument("--manuscript", type=Path, help="Optional file to identify by hash")
    args = parser.parse_args()
    start = time.perf_counter()
    CHECK_COUNTS.clear()
    verifier.COUNTS.clear()
    report = {"status": "RUNNING", "arithmetic": "fractions.Fraction",
              "enumeration_specification": {"T": [2, MAX_T], "alphabet": list(ALPHABET),
                                             "lambdas": list(LAMBDAS), "cases": 9828}}
    try:
        report["code"] = {"algorithms": file_record(Path(refreshing.__file__)),
                          "verification": file_record(Path(verifier.__file__)),
                          "clipped_cap": file_record(Path(__file__))}
        if args.manuscript is not None:
            report["manuscript"] = file_record(args.manuscript)
        report["enumeration"] = enumerate_cases(verifier)
        report["fixtures"] = named_fixtures(verifier)
        report["boundaries"] = verifier.exact_boundary_checks()
        report["status"] = "PASS"
    except Exception as failure:
        report["status"] = "FAIL"
        report["failure"] = {"type": type(failure).__name__,
                             "check": getattr(failure, "label", str(failure)),
                             "case": getattr(failure, "case", {})}
    report["focused_check_counts"] = dict(CHECK_COUNTS)
    report["verifier_check_counts"] = dict(verifier.COUNTS)
    report["elapsed_seconds"] = round(time.perf_counter() - start, 3)
    output = write_report(args.report, report)
    print(json.dumps({"status": report["status"], "report": output,
                      "enumerated_cases": report.get("enumeration", {}).get("cases", 0),
                      "elapsed_seconds": report["elapsed_seconds"]}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
