#!/usr/bin/env python3
"""Run the predefined seeded synthetic benchmark with exact rational costs."""
from fractions import Fraction as Q
from pathlib import Path
from random import Random
from statistics import median
import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import refreshing
from refreshing import check_policy_bounds, frontier_dp, run_policy, variation
from verification.reporting import file_record, serial

PROTOCOL = Path(__file__).with_name("protocol.json")


def generate_path(family, T, seed):
    """Generate a path without reference to charges, policies, or their costs."""
    rng = Random(seed)
    if family == "random_walk":
        path = [Q(0)]
        for _ in range(1, T):
            path.append(path[-1] + rng.choice((Q(-1, 8), Q(0), Q(1, 8))))
        parameters = {"increments": [Q(-1, 8), Q(0), Q(1, 8)]}
    elif family == "burst_plateau":
        start = rng.randrange(1, T // 3 + 1)
        width = rng.choice((3, 4, 5))
        amplitude = rng.choice((-1, 1)) * Q(2 * seed + 1, 4)
        path = [amplitude * Q(min(max(t - start + 1, 0), width), width)
                for t in range(T)]
        parameters = {"start": start, "width": width, "amplitude": amplitude}
    elif family == "regime_switch":
        changes = 3 + seed % 2
        indices = [j * T // (changes + 1) for j in range(1, changes + 1)]
        level = Q(0)
        path = [level]
        increments = []
        jitters = [Q(0)]
        for t in range(1, T):
            if t in indices:
                step = rng.choice((Q(-1), Q(-1, 2), Q(1, 2), Q(1)))
                increments.append(step)
                level += step
            jitter = rng.choice((Q(-1, 8), Q(0), Q(0), Q(0), Q(1, 8)))
            jitters.append(jitter)
            path.append(level + jitter)
        parameters = {"change_indices": indices, "level_increments": increments,
                      "jitter": jitters}
    else:
        raise ValueError(f"Unknown path family: {family}")
    return tuple(path), parameters


def replay(path, starts, charge):
    """Independently replay a schedule and return its exact cost components."""
    if not starts or starts[0] != 0 or starts != sorted(set(starts)):
        raise ValueError("Refresh indices must start at zero and increase strictly")
    if starts[-1] >= len(path) or starts[0] < 0:
        raise ValueError("Refresh index outside the path")
    chosen = set(starts)
    retained = None
    distortion = Q(0)
    for t, observation in enumerate(path):
        if t in chosen:
            retained = observation
        error = abs(observation - retained)
        if (t == 0 or t in chosen) and error != 0:
            raise AssertionError("Initial and refresh discrepancies must be zero")
        distortion += error
    return {"cost": charge * len(starts) + distortion,
            "distortion": distortion, "count": len(starts), "starts": starts}


def evaluate_case(path, charge, policies):
    oracle_cost, oracle_count, oracle_starts = frontier_dp(path, charge)
    oracle = replay(path, oracle_starts, charge)
    if oracle["cost"] != oracle_cost or oracle["count"] != oracle_count:
        raise AssertionError("Oracle schedule does not realize its reported cost")
    T, V = len(path), variation(path)
    results = []
    for name in policies:
        if name == "offline":
            computed = oracle
        elif name in ("anytime", "clipped"):
            computed = check_policy_bounds(path, charge, name)
        elif name == "fixed":
            computed = run_policy(path, charge, name)
        elif name == "always":
            computed = replay(path, list(range(T)), charge)
        elif name == "initial":
            computed = replay(path, [0], charge)
        else:
            raise ValueError(f"Unknown policy: {name}")
        checked = replay(path, computed["starts"], charge)
        for field in ("cost", "distortion", "count"):
            if checked[field] != computed[field]:
                raise AssertionError(f"Exact schedule replay failed: {name}/{field}")
        if checked["cost"] < oracle_cost:
            raise AssertionError(f"Policy cost below the oracle: {name}")
        checked.update({"policy": name, "cost_over_offline": checked["cost"] / oracle_cost,
                        "cost_over_sqrt_lambda_T_V": (
                            float(checked["cost"]) / math.sqrt(float(charge * T * V))
                            if V else None)})
        results.append(checked)
    return results


def aggregate(records, families, policies):
    summary = []
    for family in families:
        for policy in policies:
            selected = [row for row in records
                        if row["family"] == family and row["policy"] == policy]
            entry = {"family": family, "policy": policy, "cases": len(selected)}
            for field in ("cost", "distortion", "count", "cost_over_offline",
                          "cost_over_sqrt_lambda_T_V"):
                values = [row[field] for row in selected if row[field] is not None]
                entry["median_" + field] = median(values) if values else None
                entry["max_" + field] = max(values) if values else None
            summary.append(entry)
    return summary


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: (json.dumps(serial(row[key]), separators=(",", ":"))
                                   if isinstance(row[key], (dict, list, tuple))
                                   else serial(row[key])) for key in fieldnames})


def run(output_dir):
    start = time.perf_counter()
    protocol = json.loads(PROTOCOL.read_text())
    output_dir.mkdir(parents=True, exist_ok=True)
    # Write the fixed protocol before generating any path or evaluating a cost.
    (output_dir / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    paths = []
    distinct = set()
    for family in protocol["families"]:
        for T in protocol["horizons"]:
            for seed in protocol["seeds"]:
                path, parameters = generate_path(family, T, seed)
                if len(path) != T or path[0] != 0 or path in distinct:
                    raise AssertionError("Expected distinct paths with initial state zero")
                distinct.add(path)
                paths.append({"path_id": f"{family}_T{T}_seed{seed}", "family": family,
                              "T": T, "seed": seed, "parameters": parameters,
                              "path": path, "variation": variation(path)})
    if len(paths) != 72:
        raise AssertionError("The predefined protocol must produce 72 paths")
    refreshing.COUNTS.clear()
    records = []
    for item in paths:
        for charge_string in protocol["charges"]:
            charge = Q(charge_string)
            for result in evaluate_case(item["path"], charge, protocol["policies"]):
                records.append({"path_id": item["path_id"], "family": item["family"],
                                "T": item["T"], "seed": item["seed"],
                                "parameters": item["parameters"], "path": item["path"],
                                "variation": item["variation"], "lambda": charge,
                                **result})
    if len(records) != 72 * 4 * 6:
        raise AssertionError("The predefined protocol must produce 1728 policy records")
    summary = aggregate(records, protocol["families"], protocol["policies"])
    report = {"status": "PASS", "protocol": protocol,
              "code": {"benchmark": file_record(Path(__file__)),
                       "protocol": file_record(PROTOCOL),
                       "algorithms": file_record(Path(refreshing.__file__))},
              "python_version": platform.python_version(),
              "path_count": len(paths), "path_charge_cases": len(paths) * 4,
              "policy_records": len(records), "paths": paths,
              "records": records, "summary": summary,
              "checks": {"exact_replays": len(records),
                         "zero_initial_and_refresh_discrepancies": len(records),
                         "costs_at_least_offline": len(records),
                         "analytical_bound_counts": dict(refreshing.COUNTS)},
              "elapsed_seconds": round(time.perf_counter() - start, 3)}
    (output_dir / "results.json").write_text(json.dumps(serial(report), indent=2) + "\n")
    fields = ["path_id", "family", "T", "seed", "lambda", "variation", "policy",
              "cost", "distortion", "count", "starts", "cost_over_offline",
              "cost_over_sqrt_lambda_T_V", "parameters", "path"]
    write_csv(output_dir / "cases.csv", records, fields)
    write_csv(output_dir / "summary.csv", summary, list(summary[0]))
    concise = [{"family": row["family"], "policy": row["policy"],
                "median_ratio": str(row["median_cost_over_offline"]),
                "max_ratio": str(row["max_cost_over_offline"])} for row in summary]
    print(json.dumps({"status": "PASS", "paths": len(paths), "path_charge_cases": 288,
                      "policy_records": len(records),
                      "elapsed_seconds": report["elapsed_seconds"], "summary": concise}))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/benchmarks")
    args = parser.parse_args()
    run(args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
