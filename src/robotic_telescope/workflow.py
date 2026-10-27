"""Static plans and actual simulation output, with no hardware or network writer."""

import csv
import html
import json
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

import numpy as np

from . import __version__
from .mount import simulate
from .pointing import RESOURCES, calculate_plan, load_request, validate_request


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def provenance():
    modules = sorted(Path(__file__).parent.glob("*.py"))
    return {
        "schema_version": 1,
        "package_version": __version__,
        "created_utc": datetime.now(UTC).isoformat(),
        "source_sha256": sha256(
            b"".join(p.name.encode() + p.read_bytes() for p in modules)
        ).hexdigest(),
        "dependency_versions": {
            p: version(p) for p in ["numpy", "astropy", "astropy-iers-data", "pyerfa", "matplotlib"]
        },
    }


def plot_plan(output, request, plan):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    hours = np.arange(len(plan["utc"])) * request["step_seconds"] / 3600
    colors = ["#315c68", "#ba6d3d", "#528f81", "#846b95"]
    fig, ax = plt.subplots(figsize=(11, 5.5), constrained_layout=True)
    ax.plot(hours, plan["sun_altitude_deg"], color="#b69361", ls=":", label="Computed Sun")
    for index, target in enumerate(plan["targets"]):
        color = colors[index % len(colors)]
        mask = np.array(target["eligible"])
        ax.plot(hours, target["altitude_deg"], color=color, lw=1, alpha=0.45)
        ax.scatter(
            hours[mask],
            np.array(target["altitude_deg"])[mask],
            s=9,
            color=color,
            label=target["id"] + " eligible samples",
        )
    rule = request["constraints"]
    for value, label in [
        (rule["min_altitude_deg"], "Minimum target altitude"),
        (rule["max_altitude_deg"], "Zenith exclusion boundary"),
        (rule["max_sun_altitude_deg"], "Maximum Sun altitude"),
    ]:
        ax.axhline(value, color="#555550", lw=0.7, ls="--", label=label)
    ax.set(
        xlabel="Elapsed hours after " + request["start_utc"],
        ylabel="Vacuum topocentric altitude (degrees)",
        title="Computed planning samples · no telescope observation",
        ylim=(-90, 90),
        xlim=(hours[0], hours[-1]),
    )
    ax.grid(alpha=0.15)
    ax.legend(loc="lower left", fontsize=8, ncol=2)
    fig.savefig(output / "altitude.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(
        figsize=(7, 7), subplot_kw={"projection": "polar"}, constrained_layout=True
    )
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    for index, target in enumerate(plan["targets"]):
        alt = np.array(target["altitude_deg"])
        az = np.deg2rad(target["azimuth_deg"])
        above = alt >= 0
        eligible = np.array(target["eligible"])
        ax.scatter(az[above], 90 - alt[above], color="#cecec6", s=4)
        ax.scatter(
            az[eligible],
            90 - alt[eligible],
            color=colors[index % len(colors)],
            s=9,
            label=target["id"],
        )
    ax.set(ylim=(0, 90), yticks=[0, 30, 60, 90], yticklabels=["90°", "60°", "30°", "0°"])
    ax.set_title(
        "Computed sky tracks · north 0°, east 90°\nColored points pass the sampled constraints",
        pad=22,
    )
    ax.legend(loc="upper right", bbox_to_anchor=(1.15, 1.12))
    fig.savefig(output / "sky.png", dpi=150)
    plt.close(fig)


def plot_mount(output, rows):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True, constrained_layout=True)
    time = [r["time_s"] for r in rows]
    axes[0].plot(time, [r["azimuth_deg"] for r in rows], color="#315c68")
    axes[0].set_ylabel("Unwrapped azimuth (deg)")
    axes[1].plot(time, [r["altitude_deg"] for r in rows], color="#ba6d3d")
    axes[1].set_ylabel("Altitude (deg)")
    states = ["unhomed", "idle", "slewing", "tracking", "fault"]
    axes[2].step(time, [states.index(r["mode"]) for r in rows], where="post", color="#528f81")
    axes[2].set(
        yticks=range(5),
        yticklabels=states,
        ylabel="Simulated state",
        xlabel="Simulation clock (seconds)",
    )
    for ax in axes:
        ax.grid(alpha=0.15)
    fig.suptitle("Ideal scripted mount · no motor, sensor, or homing trajectory tested")
    fig.savefig(output / "mount.png", dpi=150)
    plt.close(fig)


def write_report(output, metrics, request=None, plan=None):
    detail = ""
    if plan is not None:
        detail += f"<p>UTC start: <b>{html.escape(request['start_utc'])}</b>. WGS84 observer: {request['observer']['latitude_deg']}° latitude, {request['observer']['longitude_deg']}° east longitude, {request['observer']['height_m']} m assumed height. Pressure 0 hPa; no refraction.</p>"
        detail += "<table><caption>Sampled target eligibility</caption><thead><tr><th>Target</th><th>Eligible / samples</th><th>Adjacent eligible span</th><th>Maximum eligible altitude</th></tr></thead><tbody>"
        for target in plan["targets"]:
            altitude = target["max_eligible_altitude_deg"]
            detail += (
                f"<tr><th>{html.escape(target['id'])}</th><td>{target['eligible_samples']} / {target['total_samples']}</td>"
                f"<td>{target['eligible_adjacent_span_seconds'] / 60:.1f} min</td>"
                f"<td>{'none' if altitude is None else f'{altitude:.2f}°'}</td></tr>"
            )
        detail += "</tbody></table><p>Span counts adjacent eligible samples, not points × step. It is a sampled estimate, not a guaranteed continuous observing window.</p>"
        predicted = sum(code == 2 for code in plan["iers"]["ut1_status"])
        detail += f"<p>Bundled IERS data: {len(plan['utc']) - predicted} observed / {predicted} predicted UT1 samples. Unsupported Earth-orientation times are rejected.</p>"
        detail += '<img src="altitude.png" alt="Actual computed target and Sun altitude samples"/><img class="sky" src="sky.png" alt="Actual computed polar sky tracks; colored eligible samples"/>'
    if "simulation" in metrics:
        sim = metrics["simulation"]
        detail += (
            f"<h2>Ideal mount state and motion</h2><p>{sim['samples']} state records; {sim['elapsed_seconds']:.1f} simulated seconds. "
            f"Maximum clock-step rates: azimuth {sim['max_azimuth_speed_deg_s']:.3f}°/s, altitude {sim['max_altitude_speed_deg_s']:.3f}°/s. "
            f"Fault position frozen: <b>{sim['fault_position_frozen']}</b>. Clearing the fault returns to unhomed.</p>"
            "<p>Home is a declaration of a known zero; it is not a simulated physical homing move. This scripted motion is separate from the astronomical tracks and does not establish tracking accuracy.</p>"
            '<img src="mount.png" alt="Actual ideal mount state and rate-limited axis simulation"/>'
        )
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>Robotic Telescope · Offline Lab</title>
<style>body{{margin:0;background:#f2f1eb;color:#22302f;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1080px;margin:auto;padding:38px 24px}}h1{{font:clamp(2.2rem,6vw,4.5rem)/1.1 Georgia,serif;letter-spacing:-.04em;margin:.35em 0}}.label{{font:12px ui-monospace,monospace;letter-spacing:.1em}}.notice{{padding:18px;border-left:4px solid #b1683d;background:#e9e3d8}}img{{display:block;max-width:100%;height:auto;margin:24px 0;border:1px solid #d0cfc5}}.sky{{max-width:min(100%,700px)}}table{{display:block;overflow:auto;border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:10px;border-bottom:1px solid #ccc;text-align:left}}caption{{text-align:left;font-weight:bold}}code{{overflow-wrap:anywhere}}a{{color:#245e65}}</style></head><body><main>
<p class="label">ROBOTIC TELESCOPE / OFFLINE PLANNING + IDEAL SIMULATION</p><h1>Pointing, before hardware.</h1><p class="notice"><b>No hardware operation or physical pointing accuracy has been verified.</b> Computed sky positions and an ideal mount model are separate evidence. No telescope observation is represented here.</p>
{detail}<details><summary>Frames, constraints, and limits</summary><p>Fixed ICRS directions transform to vacuum topocentric AltAz at the stated UTC/location, with bundled Earth-rotation data. Azimuth is north 0° / east 90°. No refraction, proper motion, distance/parallax, local terrain, weather, moonlight, field rotation, real alignment, or motor dynamics are validated.</p><p>The solar-separation rule checks target samples only. It does not certify a safe slew path or eye/equipment protection. Do not connect this simulator to a telescope or use it to point at/near the Sun.</p><p>Source SHA256: <code>{metrics["source_sha256"]}</code>. No external map, name resolution, telemetry, or data download is used.</p></details>
<p><a href="metrics.json">Metrics and provenance</a> · <a href="request.json">Request and assumptions</a></p><p>October 2026 implementation. Physical assembly, calibration, and supervised tests remain pending.</p></main></body></html>"""
    (output / "index.html").write_text(page, encoding="utf-8")


def export_plan(output, request, payload, include_simulation=False):
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    if not isinstance(payload, bytes) or len(payload) > 128_000:
        raise ValueError("Request provenance requires bounded input bytes.")
    try:
        parsed = validate_request(json.loads(payload))
    except ValueError as error:
        raise ValueError(
            "Request provenance bytes must contain a valid documented request."
        ) from error
    if parsed != request:
        raise ValueError("Request object must match the bounded input bytes used for provenance.")
    plan = calculate_plan(parsed)
    metrics = provenance() | {
        "source_kind": "computed_coordinates_and_ideal_simulation"
        if include_simulation
        else "computed_coordinates",
        "input_sha256": sha256(payload).hexdigest(),
        "iers": plan["iers"],
        "targets": [
            {
                k: t[k]
                for k in [
                    "id",
                    "eligible_samples",
                    "total_samples",
                    "eligible_adjacent_span_seconds",
                    "max_eligible_altitude_deg",
                    "rejection_counts",
                ]
            }
            for t in plan["targets"]
        ],
        "interpretation": "Computed sampled visibility only; no observation, physical tracking accuracy, or certified solar/slew protection.",
    }
    output.mkdir(parents=True)
    (output / "request.json").write_bytes(payload)
    save_json(output / "plan.json", plan)
    with (output / "pointing.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "target_id",
                "utc",
                "altitude_deg",
                "azimuth_deg",
                "sun_altitude_deg",
                "sun_separation_deg",
                "eligible",
                "violations",
            ]
        )
        for target in plan["targets"]:
            for i, utc in enumerate(plan["utc"]):
                writer.writerow(
                    [
                        target["id"],
                        utc.removesuffix("Z") + "Z",
                        target["altitude_deg"][i],
                        target["azimuth_deg"][i],
                        plan["sun_altitude_deg"][i],
                        target["sun_separation_deg"][i],
                        target["eligible"][i],
                        ";".join(key for key, value in target["violations"].items() if value[i]),
                    ]
                )
    plot_plan(output, request, plan)
    if include_simulation:
        rows, simulation = simulate()
        metrics["simulation"] = simulation
        save_simulation(output, rows)
    save_json(output / "metrics.json", metrics)
    write_report(output, metrics, request, plan)
    return metrics


def save_simulation(output, rows):
    save_json(output / "mount-trace.json", rows)
    with (output / "mount-trace.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    plot_mount(output, rows)


def export_simulation(output):
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    rows, simulation = simulate()
    output.mkdir(parents=True)
    metrics = provenance() | {"source_kind": "ideal_simulation", "simulation": simulation}
    save_simulation(output, rows)
    save_json(output / "metrics.json", metrics)
    save_json(
        output / "request.json", {"scenario": "scripted ideal mount; no celestial-target commands"}
    )
    write_report(output, metrics)
    return metrics


def export_demo(output):
    request, payload = load_request(RESOURCES / "demo-request.json")
    return export_plan(output, request, payload, include_simulation=True)
