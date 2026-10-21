# The Cost of Missed States

Reference code for **The Cost of Missed States: Online Tracking with Current-Observation Resets**, by Hiroyasu Usami.

The implementation uses scalar paths with absolute distance and exact rational arithmetic. It includes fixed, anytime and clipped refresh policies; an offline segmentation oracle; finite verification suites; and four vector figures.

## Quick start

Python 3.10 or later is sufficient for the algorithms and checks. No third-party packages are required.

```python
from fractions import Fraction as Q
from refreshing import run_policy, frontier_dp

path = (Q(0), Q(1, 2))
policy = run_policy(path, Q(1), "clipped")
optimum, refresh_count, starts = frontier_dp(path, Q(1))
print(policy["cost"], optimum)  # 3/2 3/2
```

A refresh precedes the current output, costs the declared charge, and resets discrepancy to zero. Initialization is charged. Threshold comparisons are strict; equality retains the current state.

`fixed` uses the known final variation; `anytime` uses elapsed time and observed variation; `clipped` uses observed variation and the known horizon.

## Verification

Run from the repository directory:

```sh
python -m unittest discover -s tests
python verification/verify_refreshing.py
python verification/check_clipped_cap.py
python verification/check_prefix_transfer.py
python verification/check_fixed_resolution.py
```

The first verification command compares short paths with exhaustive segmentation and checks ramp formulas and threshold boundaries. The clipped-cap command covers 9,828 path/charge cases and named equality examples. The prefix command checks the nested-interval arithmetic at `b = 4`. The fixed-resolution command checks 4,665 partitions of short paths on `{0,1,2}` and 13,995 charged objectives against the change-following bound.

JSON results are written under `artifacts/`. Each command accepts `--report`. The first two also accept an optional `--manuscript` file for hashing; no manuscript is needed to run the code.

The optional [GitHub Actions template](../ci/verify.yml) runs these checks on Python 3.10, 3.12, and 3.13. To enable it, place it at `.github/workflows/verify.yml` in a repository where you can configure workflows.

## Synthetic benchmark

```sh
python benchmarks/run_benchmark.py
```

The fixed protocol in `benchmarks/protocol.json` evaluates 72 seeded paths: three horizons, eight seeds, and three families (random walks, burst–plateau paths, and regime switches). Four refresh charges give 288 path/charge cases. Each case compares the three threshold policies, always refreshing, retaining the initial state, and the exact offline oracle.

Results include exact rational costs, distortion, refresh indices, and cost ratios to the oracle. Family-level summaries report medians and maxima. JSON and CSV files default to `artifacts/benchmarks/`; use `--output-dir` to select another directory. Full recorded results for all 288 cases are in `data/benchmark/results.json`, with policy rows in `cases.csv` and family-level aggregates in `summary.csv`. The protocol remains in `benchmarks/protocol.json`. These finite synthetic simulations describe the stated path families; their observed ratios are not worst-case guarantees.

## Examples and figures

```sh
python examples/compute_examples.py
python -m pip install -r requirements-figures.txt
python figures/draw_actions.py
python figures/draw_nested_intervals.py
python figures/draw_adaptive_thresholds.py
python figures/draw_softmax_certificate.py
```

The example command computes 24 burst–plateau and 19 ramp paths, writing rational JSON and CSV results under `artifacts/examples/`. The adaptive figure uses the two included examples in `data/adaptive_examples.json`. With `T = 64` and charge `1`, their costs are:

| Variation | Offline | Anytime | Clipped |
| --- | ---: | ---: | ---: |
| 1/2 | 11/4 | 7 | 5 |
| 2 | 4 | 4 | 5 |

Figure generation requires ReportLab and an installed regular/bold pair of DejaVu Sans, Liberation Sans, or Noto Sans with the mathematical glyphs used in the figures. Font discovery checks common installation directories. Use `--font-dir /path/to/fonts` or set `REFRESHING_FONT_DIR` to select a font directory. No fonts are bundled.

All four drawing commands accept `--output-dir`; PDFs default to `artifacts/figures/`. The adaptive figure also accepts `--data` for regenerated example data.

## Citation and license

For the theoretical results, cite:

H. Usami, “The Cost of Missed States: Online Tracking with Current-Observation Resets,” unpublished manuscript, 2026.

When using the implementation, also cite the reference code. `CITATION.cff` records the paper as the preferred citation and retains the software metadata. `CITATIONS.bib` provides both BibTeX entries.

The code and included synthetic data are distributed under the MIT license in `LICENSE`.
