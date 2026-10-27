# Contributing

Run lint/format, behavior tests, recorded-output verification, the build, and installed-wheel checks before a pull request. Explain the input, change, evidence, and limits. Keep UTC/time scales, coordinate frames, angular units, WGS84 conventions, and sample/interval denominators explicit.

Changes to IERS data, target constants, coordinate assumptions, or simulation constraints need a new recorded run with hashes and source attribution. Reject unsupported data ranges; do not turn off accuracy warnings or downloads policy to make a test pass. Distinguish observed/predicted Earth-orientation data, computed sky positions, and physical telescope measurements.

Add behavior fixtures for frame/time/unit regressions, horizon/zenith/solar boundaries, cable wrap, rate bounds, no overshoot, latched faults, and home declarations. A round trip is an internal consistency check, not physical accuracy evidence. Do not describe command quantization or ideal tracking as measured pointing precision.

Do not commit private observing locations, instrument identifiers, credentials, virtual environments, native dependency wheels, or caches. No hardware writer should be added without an explicit interface, validated bench evidence, and a separate safety/acceptance review.
