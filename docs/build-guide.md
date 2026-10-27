# Provisional build and calibration guide

No telescope assembly or hardware test has been performed for this release. This guide records the next engineering work. It is not a tested bill of materials, a procurement recommendation, or a ready-to-connect motor driver.

| Role | Design work before choosing a part | Evidence still needed |
| --- | --- | --- |
| Optical tube and support | Measure mass, balance, center of gravity, and clearance | Stable fixture, mechanical load and collision tests |
| Altitude and azimuth bearings/frame | Choose stiffness, bearing span, travel, and cable routing | Deflection, backlash, and full swept-volume checks |
| Motors, reduction, and drivers | Size torque and speed from the actual load/inertia; match voltage/current ratings | Bench direction, rate, temperature, and stall behavior |
| Position reference and limits | Choose home/limit sensing and independent physical stop behavior | Repeated homing, stuck-switch, disconnect, and travel-limit tests |
| Controller and power | Use correctly rated low-voltage interfaces and protected power | Electrical inspection and supervised fault tests |
| Camera/feedback, if added | Define an actual alignment or plate-solving interface | Measured star fields, pointing residuals, and tracking drift |

Do not connect the Python simulator directly to hardware. No protocol adapter, firmware, serial output, electrical design, or certified interlock is supplied.

## Resolution is not accuracy

For a worked design example, a hypothetical 200-full-step motor, 16 microsteps, and 144:1 reduction gives `360 / (200 × 16 × 144) = 0.00078125°`, or 2.8125 arcseconds per commanded microstep. This is command quantization only. It does not establish achievable torque, mechanical resolution, repeatability, backlash, encoder accuracy, or pointing precision. Those example parts/reduction have not been selected or tested for a build.

The simulator's 3°/s and 2°/s limits are software assumptions. They are not motor-performance measurements. A future hardware controller needs acceleration limits and validated braking behavior in addition to maximum rate.

## Physical sequence still pending

1. Establish a balanced, stable mechanical assembly with its actual travel and cable limits. Check the entire swept volume before adding automatic motion.
2. Verify electrical ratings, directions, and independent stop/limit behavior using supervised bench tests. Record the parts and measured settings; do not infer them from the simulation constants.
3. Establish a repeatable physical home reference. The simulator's `home()` declaration cannot substitute for this measurement.
4. Calibrate the real axes and optical alignment using suitable supervised reference observations. Record UTC source, site coordinates, atmosphere assumptions, target catalog/epoch, and image or encoder evidence.
5. Measure pointing residuals, backlash/reversal behavior, tracking drift, and repeatability on held-out targets and sessions. Keep failed acquisitions and faults in the results.
6. Test disconnects, missed reference signals, limits, power loss, and recovery before considering an actual driver integration.

The observing planner is not a solar-safety system. Never use it or its sample constraints to justify pointing an unprotected optical instrument at or near the Sun. A safe real system needs separately validated procedures and protection; none is established here.
