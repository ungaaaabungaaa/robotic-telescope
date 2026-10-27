import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from robotic_telescope.mount import Mount
from robotic_telescope.pointing import DEMO_REQUEST, load_request


class BoundaryTests(unittest.TestCase):
    def test_invalid_observer_frames_targets_and_constraints(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "request.json"
            cases = []
            for section, key, value in [
                ("observer", "latitude_deg", 91),
                ("observer", "latitude_deg", 10**1000),
                ("observer", "longitude_deg", -181),
                ("observer", "height_m", float("nan")),
                ("constraints", "max_altitude_deg", 86),
                ("constraints", "min_altitude_deg", 80),
                ("constraints", "min_sun_separation_deg", 0),
            ]:
                request = copy.deepcopy(DEMO_REQUEST)
                request[section][key] = value
                if key == "min_altitude_deg":
                    request["constraints"]["max_altitude_deg"] = 70
                cases.append(request)
            for key, value in [
                ("targets", []),
                ("targets", DEMO_REQUEST["targets"] * 11),
                ("schema_version", True),
                ("start_utc", "1999-01-01T00:00:00Z"),
            ]:
                cases.append({**DEMO_REQUEST, key: value})
            invalid = copy.deepcopy(DEMO_REQUEST)
            invalid["targets"][0]["id"] = "../private"
            cases.append(invalid)
            invalid = copy.deepcopy(DEMO_REQUEST)
            invalid["targets"][0]["source"] = ""
            cases.append(invalid)
            for request in cases:
                path.write_text(json.dumps(request))
                with self.assertRaises(ValueError):
                    load_request(path)

    @unittest.skipIf(os.name == "nt", "Symlink creation needs Windows developer privileges")
    def test_symlink_and_fifo_requests_are_rejected_without_reading(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "real").write_text(json.dumps(DEMO_REQUEST))
            (root / "link").symlink_to(root / "real")
            os.mkfifo(root / "fifo")
            for name in ["link", "fifo"]:
                with self.assertRaises(ValueError):
                    load_request(root / name)

    def test_mount_limit_fault_and_invalid_transitions_do_not_move(self):
        mount = Mount()
        with self.assertRaises(ValueError):
            mount.clear_fault()
        with self.assertRaises(ValueError):
            mount.inject_fault("")
        mount.home()
        mount.goto(30, 40)
        with self.assertRaises(ValueError):
            mount.goto(40, 50)
        with self.assertRaises(ValueError):
            mount.track(30, 40, 1)
        while mount.mode == "slewing":
            mount.step(1)
        before = mount.snapshot()
        mount.track(30, 86, 1)
        self.assertEqual(mount.fault_reason, "altitude_limit")
        self.assertEqual(mount.azimuth_deg, before["azimuth_deg"])
        self.assertEqual(mount.altitude_deg, before["altitude_deg"])
