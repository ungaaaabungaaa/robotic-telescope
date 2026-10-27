import math
import unittest

from robotic_telescope.mount import Mount, simulate


class MountTests(unittest.TestCase):
    def test_home_required_and_wrap_slew_has_bounded_rates_no_overshoot(self):
        mount = Mount()
        with self.assertRaises(ValueError):
            mount.goto(350, 45)
        mount.home()
        mount.goto(350, 45)
        previous = mount.snapshot()
        for _ in range(200):
            current = mount.step(0.2)
            self.assertLessEqual(
                abs(current["azimuth_deg"] - previous["azimuth_deg"]), 3 * 0.2 + 1e-10
            )
            self.assertLessEqual(
                abs(current["altitude_deg"] - previous["altitude_deg"]), 2 * 0.2 + 1e-10
            )
            previous = current
            if mount.mode == "idle":
                break
        self.assertEqual(mount.mode, "idle")
        self.assertAlmostEqual(mount.azimuth_deg, -10)
        self.assertAlmostEqual(mount.altitude_deg, 45)
        self.assertAlmostEqual(mount.snapshot()["logical_azimuth_deg"], 350)

    def test_rate_fault_freezes_position_and_clear_requires_rehome(self):
        mount = Mount()
        mount.home()
        mount.track(0.2, 0.1, 0.1)
        before = mount.snapshot()
        mount.track(20, 30, 0.1)
        self.assertEqual(mount.mode, "fault")
        self.assertEqual(mount.fault_reason, "tracking_rate")
        for _ in range(5):
            current = mount.step(1)
            self.assertEqual(current["azimuth_deg"], before["azimuth_deg"])
            self.assertEqual(current["altitude_deg"], before["altitude_deg"])
        with self.assertRaises(ValueError):
            mount.goto(0, 0)
        mount.clear_fault()
        self.assertEqual(mount.mode, "unhomed")
        with self.assertRaises(ValueError):
            mount.track(0, 0, 1)

    def test_cable_wrap_boundary_latches_without_a_position_jump(self):
        mount = Mount()
        mount.home()
        mount.goto(179, 20)
        while mount.mode == "slewing":
            mount.step(1)
        for target in range(180, 270):
            mount.track(target, 20, 1)
        self.assertAlmostEqual(mount.azimuth_deg, 269)
        mount.track(271, 20, 1)
        self.assertEqual(mount.mode, "fault")
        self.assertEqual(mount.azimuth_deg, 269)

    def test_invalid_commands_do_not_move_and_explicit_fault_stays_latched(self):
        mount = Mount()
        mount.home()
        for az, alt in [(360, 20), (-1, 20), (10, 86), (math.nan, 20), (10**1000, 20)]:
            with self.assertRaises(ValueError):
                mount.goto(az, alt)
            self.assertEqual(mount.azimuth_deg, 0)
        for dt in [0, 2, math.inf, True]:
            with self.assertRaises(ValueError):
                mount.step(dt)
        mount.inject_fault("simulated_limit_switch")
        with self.assertRaises(ValueError):
            mount.home()
        mount.clear_fault()
        mount.home()
        self.assertEqual(mount.mode, "idle")

    def test_scripted_simulation_is_reproducible_and_reports_real_model_bounds(self):
        rows, metrics = simulate()
        other, _ = simulate()
        self.assertEqual(rows, other)
        self.assertTrue(metrics["fault_position_frozen"])
        self.assertLessEqual(metrics["max_azimuth_speed_deg_s"], 3 + 1e-9)
        self.assertLessEqual(metrics["max_altitude_speed_deg_s"], 2 + 1e-9)
        self.assertEqual(rows[-1]["mode"], "unhomed")
        self.assertTrue(
            all(-270 <= r["azimuth_deg"] <= 270 and 0 <= r["altitude_deg"] <= 85 for r in rows)
        )


if __name__ == "__main__":
    unittest.main()
