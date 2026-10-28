"""Explicit UTC/ICRS/WGS84 planning with bounded bundled Earth-orientation data."""

import json
import os
import re
import stat
from datetime import datetime
from functools import lru_cache
from hashlib import sha256
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

import numpy as np

from .mount import number

RESOURCES = Path(str(files("robotic_telescope").joinpath("resources")))
DEMO_REQUEST = json.loads((RESOURCES / "demo-request.json").read_bytes())


def read_request_bytes(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 128_000:
        raise ValueError("Request must be a bounded regular non-symlink file.")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    with os.fdopen(os.open(path, flags), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 128_000:
            raise ValueError("Request type or size changed.")
        payload = stream.read(128_001)
    if len(payload) > 128_000:
        raise ValueError("Request exceeds its byte bound.")
    return payload


def exact_keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError("Request fields do not match the documented schema.")


def validate_request(request):
    exact_keys(
        request,
        [
            "schema_version",
            "observer",
            "start_utc",
            "duration_seconds",
            "step_seconds",
            "constraints",
            "targets",
        ],
    )
    if type(request["schema_version"]) is not int or request["schema_version"] != 1:
        raise ValueError("Unsupported request version.")
    observer = request["observer"]
    exact_keys(observer, ["latitude_deg", "longitude_deg", "height_m"])
    number(observer["latitude_deg"], -90, 90)
    number(observer["longitude_deg"], -180, 180)
    number(observer["height_m"], -500, 9000)
    if not isinstance(request["start_utc"], str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", request["start_utc"]
    ):
        raise ValueError("Start time must be an explicit UTC ISO datetime ending Z.")
    if datetime.fromisoformat(request["start_utc"]).year < 2000:
        raise ValueError("Start year must be at least 2000.")
    duration, step = request["duration_seconds"], request["step_seconds"]
    if (
        type(duration) is not int
        or type(step) is not int
        or not 60 <= duration <= 43200
        or not 30 <= step <= 300
        or duration % step
        or duration // step + 1 > 1441
    ):
        raise ValueError("Duration/step must be bounded integers with an exact endpoint grid.")
    rule = request["constraints"]
    exact_keys(
        rule,
        ["min_altitude_deg", "max_altitude_deg", "max_sun_altitude_deg", "min_sun_separation_deg"]
        + (["horizon_sectors"] if isinstance(rule, dict) and "horizon_sectors" in rule else []),
    )
    number(rule["min_altitude_deg"], 0, 80)
    number(rule["max_altitude_deg"], 1, 85)
    if rule["min_altitude_deg"] >= rule["max_altitude_deg"]:
        raise ValueError("Altitude limits must increase.")
    number(rule["max_sun_altitude_deg"], -18, -6)
    number(rule["min_sun_separation_deg"], 20, 180)
    sectors = rule.get("horizon_sectors", [])
    if not isinstance(sectors, list) or len(sectors) > 16:
        raise ValueError("Provide at most sixteen horizon sectors.")
    for sector in sectors:
        exact_keys(sector, ["start_azimuth_deg", "end_azimuth_deg", "min_altitude_deg"])
        start = number(sector["start_azimuth_deg"], 0, np.nextafter(360.0, 0.0))
        end = number(sector["end_azimuth_deg"], 0, np.nextafter(360.0, 0.0))
        number(sector["min_altitude_deg"], 0, 85)
        if start == end:
            raise ValueError("Horizon sector endpoints must differ; start>end wraps north.")
    targets = request["targets"]
    if not isinstance(targets, list) or not 1 <= len(targets) <= 32:
        raise ValueError("Provide one to thirty-two fixed ICRS targets.")
    ids = set()
    for target in targets:
        exact_keys(target, ["id", "ra_deg", "dec_deg", "source"])
        if (
            not isinstance(target["id"], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", target["id"])
            or target["id"] in ids
        ):
            raise ValueError("Target IDs must be safe and unique.")
        ids.add(target["id"])
        number(target["ra_deg"], 0, np.nextafter(360.0, 0.0))
        number(target["dec_deg"], -90, 90)
        if not isinstance(target["source"], str) or not 1 <= len(target["source"]) <= 500:
            raise ValueError("A bounded coordinate source/assumption note is required.")
    return request


def load_request(path):
    payload = read_request_bytes(path)
    return validate_request(json.loads(payload)), payload


@lru_cache(maxsize=1)
def orientation_table():
    from astropy.utils import iers

    path = Path(iers.IERS_A_FILE)
    return iers.IERS_A.open(str(path)), sha256(path.read_bytes()).hexdigest()


def coordinates(observer, targets, utc_strings):
    import astropy.units as u
    import erfa
    from astropy.coordinates import AltAz, EarthLocation, SkyCoord, angular_separation, get_sun
    from astropy.time import Time
    from astropy.utils import iers

    if not 1 <= len(targets) <= 32 or not 1 <= len(utc_strings) <= 1441:
        raise ValueError("Coordinate count exceeds the planning bounds.")
    with (
        iers.conf.set_temp("auto_download", False),
        iers.conf.set_temp("iers_degraded_accuracy", "error"),
    ):
        times = Time([stamp.removesuffix("Z") for stamp in utc_strings], format="isot", scale="utc")
        table, table_hash = orientation_table()
        mjd = np.asarray(table["MJD"], dtype=float)
        ut1_finite = np.isfinite(np.asarray(table["UT1_UTC"], dtype=float))
        pm_finite = np.isfinite(np.asarray(table["PM_x"], dtype=float)) & np.isfinite(
            np.asarray(table["PM_y"], dtype=float)
        )
        coverage = {
            name: [float(mjd[valid][0]), float(mjd[valid][-1])]
            for name, valid in [("ut1", ut1_finite), ("polar_motion", pm_finite)]
        }

        _, ut1_status = table.ut1_utc(times, return_status=True)
        _, _, pm_status = table.pm_xy(times, return_status=True)
        if np.any(ut1_status < 0) or np.any(pm_status < 0):
            raise ValueError("Requested time is outside bundled IERS UT1/polar-motion coverage.")
        location = EarthLocation.from_geodetic(
            observer["longitude_deg"] * u.deg,
            observer["latitude_deg"] * u.deg,
            observer["height_m"] * u.m,
            ellipsoid="WGS84",
        )
        with iers.earth_orientation_table.set(table):
            frame = AltAz(obstime=times, location=location, pressure=0 * u.hPa)
            sun = get_sun(times).transform_to(frame)
            sky = SkyCoord(
                ra=np.array([t["ra_deg"] for t in targets])[:, None] * u.deg,
                dec=np.array([t["dec_deg"] for t in targets])[:, None] * u.deg,
                frame="icrs",
            )
            projected = sky.transform_to(frame)
            separation = angular_separation(projected.az, projected.alt, sun.az, sun.alt).to_value(
                u.deg
            )
        arrays = [projected.alt.deg, projected.az.deg, sun.alt.deg, sun.az.deg, separation]
        if not all(np.isfinite(array).all() for array in arrays):
            raise ValueError("Pointing calculation returned non-finite coordinates.")
        return {
            "utc": [stamp + "Z" for stamp in times.utc.isot.tolist()],
            "sun_altitude_deg": sun.alt.deg.tolist(),
            "sun_azimuth_deg": sun.az.deg.tolist(),
            "targets": [
                {
                    "id": target["id"],
                    "altitude_deg": projected.alt.deg[i].tolist(),
                    "azimuth_deg": projected.az.deg[i].tolist(),
                    "sun_separation_deg": separation[i].tolist(),
                }
                for i, target in enumerate(targets)
            ],
            "iers": {
                "table_sha256": table_hash,
                "finite_row_coverage_mjd_utc": coverage,
                "coverage_note": "Finite-row bounds; every requested UT1 and polar-motion interpolation status is also checked.",
                "package_version": version("astropy-iers-data"),
                "ut1_status": ut1_status.tolist(),
                "polar_motion_status": pm_status.tolist(),
                "status_meaning": {
                    "0": "observed IERS-B",
                    "1": "observed IERS-A",
                    "2": "predicted IERS-A",
                },
                "erfa_leap_seconds": erfa.leap_seconds.get().tolist(),
                "auto_download": False,
            },
            "frame": "ICRS fixed directions to vacuum topocentric AltAz; WGS84; UTC with IERS UT1/polar motion",
        }


def horizon_floor(azimuth, rule):
    azimuth = np.asarray(azimuth)
    floor = np.full(azimuth.shape, -90.0)
    for sector in rule.get("horizon_sectors", []):
        start, end = sector["start_azimuth_deg"], sector["end_azimuth_deg"]
        inside = (
            (azimuth >= start) & (azimuth <= end)
            if start < end
            else ((azimuth >= start) | (azimuth <= end))
        )
        floor = np.where(inside, np.maximum(floor, sector["min_altitude_deg"]), floor)
    return floor


def visibility_conditions(alt, sun_alt, sun_separation, rule, azimuth=None):
    alt, sun_alt, sun_separation = np.asarray(alt), np.asarray(sun_alt), np.asarray(sun_separation)
    conditions = {
        "nonfinite": ~(np.isfinite(alt) & np.isfinite(sun_alt) & np.isfinite(sun_separation)),
        "below_min_altitude": alt < rule["min_altitude_deg"],
        "above_max_altitude": alt > rule["max_altitude_deg"],
        "sun_too_high": sun_alt > rule["max_sun_altitude_deg"],
        "near_sun": sun_separation < rule["min_sun_separation_deg"],
    }
    if rule.get("horizon_sectors"):
        azimuth = np.asarray(azimuth, dtype=float)
        if azimuth.shape != alt.shape:
            raise ValueError("Horizon checks require matching target azimuth samples.")
        conditions["nonfinite"] |= ~np.isfinite(azimuth) | (azimuth < 0) | (azimuth >= 360)
        conditions["below_horizon_mask"] = alt < horizon_floor(azimuth, rule)
    return conditions


def visibility(alt, sun_alt, sun_separation, rule, azimuth=None):
    return ~np.logical_or.reduce(
        list(visibility_conditions(alt, sun_alt, sun_separation, rule, azimuth).values())
    )


def sampled_windows(mask, utc, step):
    runs, start = [], None
    for index, eligible in enumerate([*mask, False]):
        if eligible and start is None:
            start = index
        if not eligible and start is not None:
            last = index - 1
            runs.append(
                {
                    "start_utc": utc[start].removesuffix("Z") + "Z",
                    "end_utc": utc[last].removesuffix("Z") + "Z",
                    "eligible_samples": last - start + 1,
                    "span_seconds": (last - start) * step,
                }
            )
            start = None
    return runs


def calculate_plan(request):
    import astropy.units as u
    from astropy.time import Time
    from astropy.utils import iers

    validate_request(request)
    seconds = np.arange(0, request["duration_seconds"] + 1, request["step_seconds"])
    with iers.conf.set_temp("auto_download", False):
        times = (
            Time(request["start_utc"].removesuffix("Z"), format="isot", scale="utc") + seconds * u.s
        )
        result = coordinates(request["observer"], request["targets"], times.utc.isot.tolist())
    rule = request["constraints"]
    for target in result["targets"]:
        alt = np.array(target["altitude_deg"])
        mask = visibility(
            alt,
            result["sun_altitude_deg"],
            target["sun_separation_deg"],
            rule,
            target["azimuth_deg"],
        )
        windows = sampled_windows(mask.tolist(), result["utc"], request["step_seconds"])
        conditions = visibility_conditions(
            alt,
            result["sun_altitude_deg"],
            target["sun_separation_deg"],
            rule,
            target["azimuth_deg"],
        )
        target["violations"] = {key: value.tolist() for key, value in conditions.items()}
        target["rejection_counts"] = {key: int(value.sum()) for key, value in conditions.items()}
        target.update(
            {
                "eligible": mask.tolist(),
                "eligible_samples": int(mask.sum()),
                "total_samples": len(mask),
                "eligible_sample_fraction": float(mask.mean()),
                "sampled_windows": windows,
                "eligible_adjacent_span_seconds": sum(w["span_seconds"] for w in windows),
                "max_sampled_altitude_deg": float(alt.max()),
                "max_eligible_altitude_deg": float(alt[mask].max()) if mask.any() else None,
            }
        )
    return result
