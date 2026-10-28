import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from robotic_telescope.pointing import (
    DEMO_REQUEST,
    coordinates,
    load_request,
    sampled_windows,
    validate_request,
    visibility,
    visibility_conditions,
)


class PointingTests(unittest.TestCase):
    def test_published_astropy_m33_bear_mountain_regression_with_network_disabled(self):
        observer = {"latitude_deg": 41.3, "longitude_deg": -74, "height_m": 390}
        target = {
            "id": "M33",
            "ra_deg": 23.46206906,
            "dec_deg": 30.66017511,
            "source": "Astropy example",
        }
        with patch("socket.create_connection", side_effect=AssertionError("Unexpected network")):
            result = coordinates(observer, [target], ["2012-07-13T03:00:00"])
        # Official Astropy observing example reports 0.13 degrees, rounded to two decimals.
        self.assertAlmostEqual(result["targets"][0]["altitude_deg"][0], 0.13, delta=0.006)
        self.assertTrue(result["iers"]["table_sha256"])
        self.assertEqual(result["iers"]["ut1_status"], [0])

    def test_outside_earth_orientation_coverage_fails_instead_of_extrapolating(self):
        with self.assertRaisesRegex(ValueError, "IERS"):
            coordinates(DEMO_REQUEST["observer"], DEMO_REQUEST["targets"], ["2099-01-01T00:00:00"])

    def test_inverse_consistency_and_supported_prediction_status(self):
        import astropy.units as u
        from astropy.coordinates import AltAz, EarthLocation, SkyCoord
        from astropy.time import Time
        from astropy.utils import iers

        from robotic_telescope.pointing import orientation_table

        observer = DEMO_REQUEST["observer"]
        target = {
            "id": "wrap",
            "ra_deg": 359.8,
            "dec_deg": -30,
            "source": "Synthetic frame-consistency direction",
        }
        result = coordinates(observer, [target], ["2025-01-15T14:00:00"])
        table, _ = orientation_table()
        with iers.conf.set_temp("auto_download", False), iers.earth_orientation_table.set(table):
            frame = AltAz(
                obstime=Time("2025-01-15T14:00:00", scale="utc"),
                location=EarthLocation.from_geodetic(
                    observer["longitude_deg"] * u.deg,
                    observer["latitude_deg"] * u.deg,
                    observer["height_m"] * u.m,
                ),
                pressure=0 * u.hPa,
            )
            recovered = SkyCoord(
                az=result["targets"][0]["azimuth_deg"][0] * u.deg,
                alt=result["targets"][0]["altitude_deg"][0] * u.deg,
                frame=frame,
            ).icrs
        original = SkyCoord(ra=359.8 * u.deg, dec=-30 * u.deg, frame="icrs")
        self.assertLess(recovered.separation(original).arcsec, 0.001)
        prediction = coordinates(observer, [target], ["2027-01-01T00:00:00"])
        self.assertEqual(prediction["iers"]["ut1_status"], [2])
        self.assertEqual(prediction["iers"]["polar_motion_status"], [2])

    def test_visibility_boundaries_and_nan_exclusion(self):
        rule = DEMO_REQUEST["constraints"]
        mask = visibility(
            np.array([20, 85, 19.9, 86, 40, 40, np.nan]),
            np.array([-12, -12, -20, -20, -11, -20, -20]),
            np.array([30, 30, 50, 50, 50, 29, 50]),
            rule,
        )
        self.assertEqual(mask.tolist(), [True, True, False, False, False, False, False])

    def test_horizon_sectors_wrap_boundaries_and_overlap_use_the_highest_floor(self):
        rule = {
            **DEMO_REQUEST["constraints"],
            "horizon_sectors": [
                {"start_azimuth_deg": 350, "end_azimuth_deg": 10, "min_altitude_deg": 40},
                {"start_azimuth_deg": 0, "end_azimuth_deg": 20, "min_altitude_deg": 50},
            ],
        }
        mask = visibility(
            np.array([40, 40, 49, 50, 20, 20, 40, 50]),
            np.full(8, -20),
            np.full(8, 50),
            rule,
            azimuth=np.array([350, 355, 0, 10, 21, 349, 5, np.nan]),
        )
        self.assertEqual(mask.tolist(), [True, True, False, True, True, True, False, False])

    def test_horizon_rejection_is_not_reported_outside_declared_sectors(self):
        rule = {
            **DEMO_REQUEST["constraints"],
            "horizon_sectors": [
                {"start_azimuth_deg": 350, "end_azimuth_deg": 10, "min_altitude_deg": 40}
            ],
        }
        conditions = visibility_conditions(
            np.array([10]), np.array([-20]), np.array([50]), rule, np.array([180])
        )
        self.assertTrue(conditions["below_min_altitude"][0])
        self.assertFalse(conditions["below_horizon_mask"][0])

    def test_horizon_sector_schema_is_bounded_and_strict(self):
        sector = {"start_azimuth_deg": 350, "end_azimuth_deg": 10, "min_altitude_deg": 40}
        invalid = [None, [sector] * 17, [{}], [{**sector, "unknown": 0}]]
        for change in [
            {"start_azimuth_deg": 360},
            {"end_azimuth_deg": 350},
            {"min_altitude_deg": 86},
            {"min_altitude_deg": True},
            {"end_azimuth_deg": float("nan")},
        ]:
            invalid.append([{**sector, **change}])
        for sectors in invalid:
            request = copy.deepcopy(DEMO_REQUEST)
            request["constraints"]["horizon_sectors"] = sectors
            with self.assertRaises(ValueError):
                validate_request(request)
        request = copy.deepcopy(DEMO_REQUEST)
        request["constraints"]["horizon_sectors"] = []
        self.assertEqual(validate_request(request), request)

    def test_sampled_windows_do_not_count_points_as_elapsed_intervals(self):
        times = [f"2025-01-15T14:0{i}:00" for i in range(6)]
        windows = sampled_windows([True, True, False, True, False, True], times, 60)
        self.assertEqual([x["span_seconds"] for x in windows], [60, 0, 0])
        self.assertEqual([x["eligible_samples"] for x in windows], [2, 1, 1])

    def test_bounded_request_units_times_and_unique_ids_are_strict(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "request.json"
            p.write_text(json.dumps(DEMO_REQUEST))
            request, payload = load_request(p)
            self.assertEqual(request, DEMO_REQUEST)
            self.assertEqual(payload, p.read_bytes())
            changes = [
                {"start_utc": "2025-01-15T14:00:00"},
                {"duration_seconds": 21601},
                {"step_seconds": True},
                {"unknown": 1},
                {"targets": [DEMO_REQUEST["targets"][0]] * 2},
            ]
            for change in changes:
                p.write_text(json.dumps({**DEMO_REQUEST, **change}))
                with self.assertRaises(ValueError):
                    load_request(p)
            invalid = copy.deepcopy(DEMO_REQUEST)
            invalid["targets"][0]["ra_deg"] = 360
            p.write_text(json.dumps(invalid))
            with self.assertRaises(ValueError):
                load_request(p)
            with p.open("wb") as stream:
                stream.truncate(128001)
            with self.assertRaises(ValueError):
                load_request(p)


if __name__ == "__main__":
    unittest.main()
