"""Small contract and reproducibility checks."""
from fractions import Fraction as Q
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import refreshing
from examples.compute_examples import evaluate
from verification.reporting import serial


class RefreshingTests(unittest.TestCase):
    def test_equality_retains(self):
        result = refreshing.run_policy((Q(0), Q(1, 2)), Q(1), "clipped")
        self.assertEqual(result["starts"], [0])
        self.assertEqual(result["cost"], Q(3, 2))

    def test_cap_can_be_attained_in_middle_regime(self):
        result = refreshing.run_policy((Q(0), Q(3, 5)), Q(1), "clipped")
        self.assertEqual(result["starts"], [0, 1])
        self.assertEqual(result["cost"], Q(2))
        self.assertLess(result["cost"] ** 2, Q(5, 2) ** 2 * 2 * Q(3, 5))

    def test_oracle_matches_independent_segmentation(self):
        path = (Q(0), Q(1), Q(0), Q(2))
        partitions = list(refreshing.all_segmentations(path))
        for charge in (Q(1, 4), Q(1), Q(4)):
            expected = min((charge * count + distortion, count)
                           for count, distortion, starts in partitions)
            cost, count, starts = refreshing.frontier_dp(path, charge)
            self.assertEqual((cost, count), expected)
            self.assertEqual(refreshing.schedule_cost(path, starts, charge)[0], cost)

    def test_included_example_data(self):
        data = json.loads((ROOT / "data/adaptive_examples.json").read_text())
        for case in data["cases"]:
            path = tuple(Q(value) for value in case["path"])
            metadata = dict(case["metadata"])
            metadata["V"] = Q(metadata["V"])
            recomputed = evaluate(case["case_id"], case["family"], path, metadata)
            self.assertEqual(serial(recomputed), case)

    def test_imports_do_not_run_commands(self):
        modules = ["examples.compute_examples", "verification.verify_refreshing",
                   "verification.check_clipped_cap", "verification.check_prefix_transfer"]
        environment = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-c", ";".join("import " + m for m in modules)],
                                    cwd=folder, env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
