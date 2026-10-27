# Frames, time, and model limits

This lab computes an observing plan and runs a separate ideal mount-state scenario. It does not observe the sky, solve an image, align an optical axis, measure pointing residuals, or send commands to a device.

## Coordinates and time

Targets are fixed ICRS RA/Dec directions in degrees. Observer coordinates are east-positive longitude, geodetic latitude, and ellipsoidal height on WGS84. Times are explicitly UTC. Astropy transforms each direction to topocentric AltAz, including its time/frame machinery and Earth orientation. Azimuth increases from north through east. Pressure is zero, so the result has no atmospheric-refraction correction. See the official [coordinate guide](https://docs.astropy.org/en/stable/coordinates/).

The default target constants are small cited examples, not a downloaded catalog:

| Target | RA degrees | Dec degrees | Source |
| --- | ---: | ---: | --- |
| M31 | 10.68458 | 41.26917 | [Astropy coordinate example](https://docs.astropy.org/en/stable/coordinates/) |
| M33 | 23.46206906 | 30.66017511 | [Astropy observing example](https://docs.astropy.org/en/stable/coordinates/example_gallery_plot_obs_planning.html) |
| M42 H II region centroid | 83.82 | −5.3875 | [SIMBAD](https://simbad.unistra.fr/simbad/sim-id?Ident=M42), 05h35m16.8s / −05°23′15″ |

The M42 region centroid and rounding are a pointing example, not an optical alignment standard. No proper motion, finite-distance parallax, radial velocity, or moving-object ephemeris is supplied. These omissions matter for some real targets and precision work.

The independent reference regression uses the published M33 example at Bear Mountain (41.3° N, 74° W, 390 m) at **2012-07-13 03:00 UTC**, corresponding to 23:00 EDT the previous day. The documentation prints approximately 0.13° altitude. A separate inverse transformation checks internal frame/unit consistency around RA wrap; it does not establish physical pointing accuracy.

## Earth orientation and leap seconds

The application disables automatic IERS and leap-second downloads. It opens the declared `astropy-iers-data` package's IERS-A file directly and selects that table for the transformation. Requested UT1 and polar-motion statuses must both be supported. Status 0 is observed IERS-B, 1 observed IERS-A, and 2 predicted IERS-A. Negative out-of-range statuses fail before computing a plan. See [Astropy IERS data access](https://docs.astropy.org/en/stable/utils/iers.html) and the [IERS interpolation API](https://docs.astropy.org/en/stable/api/astropy.utils.iers.IERS.html).

For pinned data version `0.2026.10.19.0.52.1`, finite rows span MJD UTC 41684–61682 (1973-01-02 to 2027-10-04). These are row bounds, not a promise that every arbitrary input is supported; interpolation status is checked for every sample. The default historical run is entirely observed IERS-B. A supported 2027 test exercises predicted UT1 and polar-motion labels. A 2099 test is rejected and retains ERFA's dubious-year warning rather than hiding it.

The table SHA256, data package version, exact statuses, finite-row bounds, and active ERFA leap-second table are recorded. The fixed table hash is `0baf00f67a39ab362a3e4f07d2a1f084842178523f56bcf5a861e7ac084d411a`. Dates outside supported coverage require a separately reviewed data/version update; the software does not disable accuracy checks to make them pass.

## Sampled eligibility

At each point require target altitude within the inclusive min/max, Sun altitude at or below its limit, and target–Sun angular separation at or above its limit. The separation uses both directions in the same topocentric frame. All computed coordinates must be finite. Each violated condition is recorded; rejection counts can overlap.

A window is a run of consecutive eligible samples. Its span is last time minus first time. One isolated point has zero span. `eligible_sample_fraction` is a fraction of points, not an exposure-time fraction. The 60-second grid can miss shorter events and cannot guarantee continuous clearance. The Sun rule checks target samples, not the mount's full swept path. No terrain, obstruction, weather, seeing, cloud, moonlight, refraction, field rotation, exposure, or physical solar-protection validation is present.

## Ideal mount

The controller uses unhomed/idle/slewing/tracking/fault states and finite numeric bounds. It selects the nearest equivalent logical azimuth within its unwrapped cable range. Clock steps clamp ideal axis travel by the stated rates without overshoot. A tracking rate or altitude-limit violation latches a fault before a move. Faulted steps leave position unchanged; clearing the fault requires a new home declaration.

Home is a declared coordinate reset, not a simulated motor trajectory. Trace events label it explicitly; rate and travel summaries use positive-clock steps. The fixed scenario does not feed the astronomical tracks into a real controller. It models no acceleration, load, torque, backlash, vibration, encoder, lost steps, electrical interface, collision volume, or optical alignment. It establishes software behavior only.
