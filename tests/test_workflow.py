import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from robotic_telescope.cli import main
from robotic_telescope.pointing import DEMO_REQUEST
from robotic_telescope.workflow import export_demo, export_plan


class WorkflowTests(unittest.TestCase):
    def test_full_offline_demo_has_exact_denominators_provenance_and_fault_hold(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "demo"
            with patch(
                "socket.create_connection", side_effect=AssertionError("Unexpected network")
            ):
                metrics = export_demo(out)
            self.assertEqual(metrics["source_kind"], "computed_coordinates_and_ideal_simulation")
            plan = json.loads((out / "plan.json").read_text())
            self.assertEqual(len(plan["utc"]), 361)
            for target in plan["targets"]:
                self.assertEqual(target["total_samples"], 361)
                self.assertEqual(target["eligible_samples"], sum(target["eligible"]))
                self.assertEqual(
                    target["eligible_adjacent_span_seconds"],
                    sum(w["span_seconds"] for w in target["sampled_windows"]),
                )
                self.assertLessEqual(target["eligible_adjacent_span_seconds"], 21600)
            self.assertTrue(metrics["simulation"]["fault_position_frozen"])
            self.assertTrue((out / "altitude.png").stat().st_size > 1000)
            self.assertTrue((out / "sky.png").is_file())
            self.assertTrue((out / "mount.png").is_file())
            self.assertIn("No hardware", (out / "index.html").read_text())
            with self.assertRaises(FileExistsError):
                export_demo(out)

    def test_custom_plan_and_cli_errors_leave_clear_file_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            request = root / "request.json"
            request.write_text(json.dumps({**DEMO_REQUEST, "duration_seconds": 600}))
            self.assertEqual(
                main(["plan", "--request", str(request), "--output", str(root / "plan")]), 0
            )
            self.assertEqual(main(["simulate", "--output", str(root / "sim")]), 0)
            self.assertEqual(
                main(["plan", "--request", str(root / "missing"), "--output", str(root / "bad")]), 1
            )
            self.assertFalse((root / "bad").exists())
            self.assertEqual(main(["simulate", "--output", str(root / "sim")]), 1)
            with self.assertRaises(FileExistsError):
                export_plan(root / "plan", DEMO_REQUEST, b"{}")
            with self.assertRaisesRegex(ValueError, "provenance"):
                export_plan(root / "mismatch", DEMO_REQUEST, b"{}")
            self.assertFalse((root / "mismatch").exists())
            typed_request = copy.deepcopy(DEMO_REQUEST)
            typed_request["targets"][0]["ra_deg"] = 1
            invalid_bytes = copy.deepcopy(typed_request)
            invalid_bytes["targets"][0]["ra_deg"] = True
            with self.assertRaises(ValueError):
                export_plan(
                    root / "typed_mismatch", typed_request, json.dumps(invalid_bytes).encode()
                )
            self.assertFalse((root / "typed_mismatch").exists())


if __name__ == "__main__":
    unittest.main()
