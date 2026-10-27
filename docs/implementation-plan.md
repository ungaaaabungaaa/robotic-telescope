# Robotic Telescope implementation plan

Approved source: `Bootstrap-Musem-of-candy` to `robotic-telescope`. Original main `d6d844be448efeaaa16a7250e99eae285fe36f64`, repository ID `R_kgDOIIXOlA`, 17 stars. Preserve and verify a remote archive before rebuilding. The old tutorial tree has no license or instructions; reuse no legacy code/images. MyPortfolio stays read-only. Use approved project15 v3 line-art cover as labeled concept art.

## First usable result

An offline observing planner with explicit ICRS-to-vacuum-topocentric AltAz pointing, sampled altitude/darkness/solar-separation constraints, actual visibility/sky-track plots, an ideal two-axis mount controller simulation, and a parts/calibration/build guide. No telescope, camera, motor, physical pointing precision, automatic acquisition, real solar-safety interlock, or observation is claimed as verified.

Use Astropy rather than inventing UTC/UT1/precession equations. Default runs use a fixed historical Bengaluru-location example and cited small target coordinate examples, with no online name resolution. Disable automatic IERS/leap-second downloads, open the bundled fixed IERS-A table, reject times outside both UT1 and polar-motion coverage, record observed/predicted status and table hash/version, and use pressure0 (no refraction). RA is degrees in ICRS, longitude east-positive in WGS84, times UTC. Proper motion, distance/parallax, weather, terrain and physical alignment are outside this release.

## Steps

1. Save history, record license findings, and write the bounded CLI/request/mount-state contract. Define timestamps, units, target limits, constraints, sampled-window denominators and output schema before code. Risk: high.
2. Implement validated request parsing and coordinate/time processing with official Astropy/IERS references. Add the published Bear Mountain/M33 altitude example as an external regression, coordinate round-trip checks, UTC/degree/unit/error cases, out-of-IERS-range rejection, and pure visibility-boundary tests. Risk: high.
3. Implement mount states (unhomed, idle, slewing, tracking, fault), nearest valid unwrapped azimuth within cable limits, bounded rate steps, no overshoot, fault latching, no motion while faulted, and rehome requirement after clearing faults. Use a deterministic scripted simulation; no device writes or pretend driver. Test azimuth wrap/cable bounds/rate violations and invalid transitions. Risk: high.
4. Export actual computed planning samples/windows, simulated mount traces, figures, and an offline static report with source/input/settings/IERS provenance. Sampled visibility does not establish continuous interval safety, a collision-free slew, actual weather, or a completed observation. Risk: medium.
5. Add README, scientific/mount/build guides, MIT license for new code, history/date transparency, approved cover, tests, exact dependencies, package resources, source/wheel integration checks and six-platform/version CI. Risk: medium.
6. Run the fixed historical demo, meaningful behavior tests, recorded-output verification, installed-wheel checks outside the source tree, plot/browser QA, then commit/push/PR. Root independently reviews and merges after green CI. Keep the shared temporary scientific runtime until final Telescope cleanup; remove all task-only storage only after remote verification. Risk: high.

## Interfaces

`telescope-lab demo --output NEW_DIR` runs the fixed planning example and scripted mount simulation. `plan --request REQUEST.json --output NEW_DIR` calculates a bounded custom plan. `simulate --output NEW_DIR` runs the deterministic ideal-mount state/rate/fault scenario. Help/version are supported. No command uses an instrument, network service, account, or existing output directory. No generated concept image is presented as a real telescope build.

## Execution checkpoint

The complete offline demo ran locally with Astropy 8.0.2 / PyERFA 2.0.1.5 and pinned IERS data 0.2026.10.19.0.52.1. Finite UT1/PM rows cover MJD 41684–61682 (1973-01-02 to 2027-10-04); all 361 default samples use observed IERS-B. M31 has 171/361 eligible samples and 170 adjacent minutes, M33 has 221/361 and 220 minutes, M42 has 361/361 and 360 minutes. The ideal controller has 443 records over 87.6 s, bounded 3/2 degree-per-second rates within floating-point tolerance, frozen position during the injected fault, and final unhomed state. Home declarations are labeled separately and excluded from timed-motion accounting.

Sixteen behavior tests pass with 96.81% combined line/branch coverage. The published M33 reference, inverse frame consistency, predicted-status labeling, and unsupported-time rejection are checked. One ERFA dubious-year warning remains visible in the deliberate 2099 rejection test. Raw request JSON is validated and used for computation before its hash is reported, including boolean/numeric mismatch regression; extreme integer inputs fail cleanly without float overflow.

Recorded UTC/frames/IERS/input/source data, all target/Sun samples and windows, and the complete mount trace were recomputed successfully. An installed wheel outside the source tree ran bundled/default/custom plans, ideal simulation, reports/figures and version with external connection creation blocked. Actual plots and browser report/details were inspected. Mobile viewport and physical hardware/pointing/solar-protection acceptance remain unverified.

Recorded source SHA256: 55d060faa137be8e5535534c953bb4b3ce5685165e0117a6629cd5bb768865f6. Commit/PR/CI and independent final review are the next checkpoint. Root owns merge and post-backup cleanup.
