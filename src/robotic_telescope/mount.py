"""Ideal rate-limited axis motion and latched simulated faults; no device writer."""

import math
from dataclasses import dataclass


def number(value, low, high):
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        raise ValueError("Expected a finite numeric value within its supported bounds.")
    return float(value)


@dataclass
class Mount:
    azimuth_deg: float = 0.0
    altitude_deg: float = 0.0
    mode: str = "unhomed"
    homed: bool = False
    fault_reason: str | None = None
    time_s: float = 0.0
    target: tuple | None = None

    def snapshot(self):
        return {
            "time_s": self.time_s,
            "azimuth_deg": self.azimuth_deg,
            "logical_azimuth_deg": self.azimuth_deg % 360,
            "altitude_deg": self.altitude_deg,
            "mode": self.mode,
            "homed": self.homed,
            "fault_reason": self.fault_reason,
            "target_azimuth_deg": self.target[0] if self.target else None,
            "target_altitude_deg": self.target[1] if self.target else None,
        }

    def home(self):
        if self.mode not in ["unhomed", "idle"]:
            raise ValueError("Home declaration requires an unhomed or idle non-faulted simulator.")
        self.azimuth_deg, self.altitude_deg = 0.0, 0.0
        self.homed, self.mode, self.target = True, "idle", None
        return self.snapshot()

    def alias(self, az):
        number(az, 0, math.nextafter(360.0, 0.0))
        candidates = [x for x in [az - 360, az, az + 360] if -270 <= x <= 270]
        return min(candidates, key=lambda x: abs(x - self.azimuth_deg))

    def goto(self, az, alt):
        if not self.homed or self.mode != "idle":
            raise ValueError("Goto requires a homed idle simulator.")
        target = (self.alias(az), number(alt, 0, 85))
        self.target = target
        self.mode = "idle" if target == (self.azimuth_deg, self.altitude_deg) else "slewing"
        return self.snapshot()

    def step(self, dt):
        number(dt, 0.01, 1)
        self.time_s += dt
        if self.mode == "slewing":

            def move(current, target, rate):
                return current + max(-rate * dt, min(rate * dt, target - current))

            self.azimuth_deg = move(self.azimuth_deg, self.target[0], 3)
            self.altitude_deg = move(self.altitude_deg, self.target[1], 2)
            if (
                abs(self.azimuth_deg - self.target[0]) < 1e-9
                and abs(self.altitude_deg - self.target[1]) < 1e-9
            ):
                self.azimuth_deg, self.altitude_deg = self.target
                self.mode = "idle"
        return self.snapshot()

    def track(self, az, alt, dt):
        number(dt, 0.01, 1)
        if not self.homed or self.mode not in ["idle", "tracking"]:
            raise ValueError("Tracking requires a homed idle/tracking simulator.")
        target_az = self.alias(az)
        number(alt, -90, 90)
        if not 0 <= alt <= 85:
            self.inject_fault("altitude_limit")
            return self.snapshot()
        if (
            abs(target_az - self.azimuth_deg) > 3 * dt + 1e-10
            or abs(alt - self.altitude_deg) > 2 * dt + 1e-10
        ):
            self.inject_fault("tracking_rate")
            return self.snapshot()
        self.azimuth_deg, self.altitude_deg = target_az, float(alt)
        self.target, self.mode = (target_az, float(alt)), "tracking"
        self.time_s += dt
        return self.snapshot()

    def inject_fault(self, reason):
        if not isinstance(reason, str) or not 1 <= len(reason) <= 80:
            raise ValueError("A bounded fault reason is required.")
        if self.mode == "fault":
            return self.snapshot()
        self.fault_reason, self.mode, self.target = reason, "fault", None
        return self.snapshot()

    def clear_fault(self):
        if self.mode != "fault":
            raise ValueError("There is no latched fault to clear.")
        self.fault_reason, self.homed, self.mode = None, False, "unhomed"
        return self.snapshot()


def simulate():
    mount = Mount()
    rows = [
        {**mount.snapshot(), "event": "initial"},
        {**mount.home(), "event": "home_declaration"},
        {**mount.goto(350, 45), "event": "goto"},
    ]
    while mount.mode == "slewing":
        rows.append({**mount.step(0.2), "event": "slew_step"})
    for _ in range(300):
        rows.append(
            {
                **mount.track((mount.azimuth_deg + 0.004) % 360, mount.altitude_deg + 0.001, 0.2),
                "event": "track_step",
            }
        )
    position = (mount.azimuth_deg, mount.altitude_deg)
    rows.append({**mount.inject_fault("simulated_limit_switch"), "event": "fault_injection"})
    for _ in range(25):
        rows.append({**mount.step(0.2), "event": "fault_hold"})
    frozen = position == (mount.azimuth_deg, mount.altitude_deg)
    rows.append({**mount.clear_fault(), "event": "clear_fault_requires_rehome"})
    rates = [
        abs(b["azimuth_deg"] - a["azimuth_deg"]) / (b["time_s"] - a["time_s"])
        for a, b in zip(rows, rows[1:])
        if b["time_s"] > a["time_s"]
    ]
    alt_rates = [
        abs(b["altitude_deg"] - a["altitude_deg"]) / (b["time_s"] - a["time_s"])
        for a, b in zip(rows, rows[1:])
        if b["time_s"] > a["time_s"]
    ]
    metrics = {
        "source_kind": "ideal_simulation",
        "samples": len(rows),
        "elapsed_seconds": mount.time_s,
        "max_azimuth_speed_deg_s": max(rates),
        "max_altitude_speed_deg_s": max(alt_rates),
        "azimuth_travel_deg": sum(
            abs(b["azimuth_deg"] - a["azimuth_deg"])
            for a, b in zip(rows, rows[1:])
            if b["time_s"] > a["time_s"]
        ),
        "fault_position_frozen": frozen,
        "final_state": mount.mode,
        "limits": {
            "azimuth_deg": [-270, 270],
            "altitude_deg": [0, 85],
            "azimuth_rate_deg_s": 3,
            "altitude_rate_deg_s": 2,
        },
        "interpretation": "Ideal scripted state/rate model only; no telescope, sensor, or motor was tested.",
    }
    return rows, metrics
