# Telescope lab contract — 0.1

This is an offline planner and ideal mount simulator. It never opens a device, sends a motor command, downloads a catalog/ephemeris, or makes an observation. Exit codes: 0 success, 2 CLI syntax, 1 controlled input/runtime failure. Output directories must be new.

- `telescope-lab demo --output NEW_DIR`: run the bundled fixed historical planning request and deterministic mount simulation, then export actual figures, JSON/CSV samples, and an offline HTML report.
- `telescope-lab plan --request REQUEST.json --output NEW_DIR`: compute a bounded custom sampled plan.
- `telescope-lab simulate --output NEW_DIR`: run the scripted ideal mount scenario with slew, tracking, injected fault, no motion while faulted, and clear-fault/rehome requirement.
- `--help` and `--version`: show the interface and package version.

## Planning request

A regular non-symlink JSON file <=128,000 bytes, with exact top-level keys:

- `schema_version`: integer 1.
- `observer`: exact keys `latitude_deg` [-90,90], `longitude_deg` [-180,180] east-positive, and `height_m` [-500,9000]. These are WGS84 geodetic coordinates, not a geocentric latitude or automatic site lookup.
- `start_utc`: ISO datetime ending Z, explicit UTC, year 2000 or later. A leap-second string cannot be a start value; Astropy handles elapsed-time additions within the supported Earth-orientation range. No implicit local timezone or current-time default.
- `duration_seconds`: integer 60..43200; `step_seconds`: integer 30..300. Duration must be an exact multiple of step. Include both endpoints; at most 1441 samples.
- `constraints`: four required keys `min_altitude_deg` [0,80], `max_altitude_deg` [1,85] greater than minimum, `max_sun_altitude_deg` [-18,-6], `min_sun_separation_deg` [20,180]. Values are planning assumptions, not certified hardware protections.
- `targets`: 1..32 objects with unique safe `id` (1..60 letters/digits/underscore/hyphen), `ra_deg` [0,360), `dec_deg` [-90,90], and `source` (string1..500). RA and Dec are fixed ICRS degrees; no RA-hour inference, online name resolution, proper motion, parallax, or moving-object target is supported.

Optional `constraints.horizon_sectors` is a list of at most 16 exact objects with `start_azimuth_deg`, `end_azimuth_deg` and `min_altitude_deg`. Endpoints are finite numbers in [0,360), must differ, and include both boundaries. Start greater than end crosses north. The altitude floor is 0..85 degrees. Overlaps use their highest floor, while the global minimum still applies. Empty/absent sectors preserve the default model. At each sample, a covered target below its sector floor has a `below_horizon_mask` rejection; counts can overlap other rejection reasons. Targets outside all sectors do not receive that reason. Exact input bytes retain these supplied assumptions. This is a discontinuous sampled mask, not measured terrain, interpolation, or a safe slew path.

Use Astropy ICRS -> topocentric AltAz with pressure 0 hPa (no atmospheric refraction), the given EarthLocation/time, and the built-in Sun model. Use the fixed bundled IERS-A table with automatic data/leap-second downloads disabled. Reject times outside either UT1 or polar-motion coverage; never silently substitute out-of-range values. Record the table/package hashes/versions and observed/predicted status. All reported azimuths are [0,360), north 0° / east 90°, with altitude above the mathematical local horizon.

Eligibility at a sample requires altitude>=minimum, altitude<=maximum, Sun altitude<=maximum, and target-Sun angular separation>=minimum. Boundary equality is included. Report each violated condition; counts may overlap. NaN/non-finite computed coordinates fail. Windows are runs of eligible sampled points, not guaranteed continuous intervals. A run's span is (last sample time - first sample time), so a single eligible sample has zero span; do not multiply the number of points by the sampling interval. Denominators are total sampled points. No terrain, cloud, seeing, moonlight, field rotation, refraction, tracking precision, or exposure-quality claim is made.

The solar constraint checks target samples only. It does not certify a safe slew path or protect eyes/equipment. Never connect this simulator to an optical instrument or point an unprotected telescope at/near the Sun based on these outputs.

## Ideal mount interface

States: `unhomed`, `idle`, `slewing`, `tracking`, `fault`. Initial position is azimuth0/altitude0, unhomed. `home()` is a simulated declaration of a known zero, not a modeled homing trajectory or real sensor input. A goto requires a homed idle mount and valid logical azimuth/altitude. Choose the nearest equivalent azimuth within mechanical [-270,270] degrees; altitude limits are [0,85]. Slew steps0.01..1s enforce maximum azimuth3deg/s and altitude2deg/s, with no overshoot. Rate bounds describe only the ideal software model, without acceleration, inertia, backlash, step loss, or motor dynamics.

`track(az,alt,dt)` requires idle/tracking and rejects a target that cannot be reached within those rate limits; the resulting rate/limit fault is latched before any move. `inject_fault(reason)` freezes motion. Goto/tracking are rejected while faulted. `clear_fault()` returns to unhomed; a new home declaration is required. Invalid numeric inputs fail without hidden movement. The simulator has no device/network writer and does not implement certified limits or solar protection.

## Outputs and evidence

Plan output includes exact input bytes/settings hashes, code digest, dependency/IERS provenance, timestamped Sun and target coordinates, eligibility masks, sampled windows/counts, and actual sky/altitude plots. Simulation output includes timestamped ideal positions/states/targets, fault reason, rate/travel checks, CSV/JSON trace, and actual plots. Demo combines these in static HTML with local relative figures. Generated README concept art is kept separate from computed plots. No physical telescope is presented as built or calibrated.

The first simulated fault reason stays latched while mode is `fault`. Later valid fault events do not replace it or move the axes. Only explicit `clear_fault()` clears the reason and returns to `unhomed`; a new home declaration is still required for motion.
