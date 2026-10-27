"""Recompute actual planning and ideal-simulation evidence without rewriting it."""

import json
import sys
from hashlib import sha256
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from robotic_telescope.mount import simulate
from robotic_telescope.pointing import calculate_plan, load_request


def main():
    root = Path(__file__).resolve().parents[1]
    demo = root / "demo"
    metrics = json.loads((demo / "metrics.json").read_text())
    saved = json.loads((demo / "plan.json").read_text())
    request, payload = load_request(demo / "request.json")
    assert sha256(payload).hexdigest() == metrics["input_sha256"]
    current = calculate_plan(request)
    assert saved["utc"] == current["utc"]
    assert saved["iers"] == json.loads(json.dumps(current["iers"])) == metrics["iers"]
    for name in ["sun_altitude_deg", "sun_azimuth_deg"]:
        np.testing.assert_allclose(saved[name], current[name], rtol=0, atol=1e-8)
    for old, new in zip(saved["targets"], current["targets"], strict=True):
        for name in ["altitude_deg", "azimuth_deg", "sun_separation_deg"]:
            np.testing.assert_allclose(old[name], new[name], rtol=0, atol=1e-8)
        for name in [
            "id",
            "eligible",
            "eligible_samples",
            "total_samples",
            "sampled_windows",
            "eligible_adjacent_span_seconds",
            "violations",
            "rejection_counts",
        ]:
            assert old[name] == new[name]
    rows, simulation = simulate()
    assert rows == json.loads((demo / "mount-trace.json").read_text())
    assert simulation == metrics["simulation"]
    modules = sorted((root / "src/robotic_telescope").glob("*.py"))
    assert (
        sha256(b"".join(p.name.encode() + p.read_bytes() for p in modules)).hexdigest()
        == metrics["source_sha256"]
    )
    print(
        "Recorded study: UTC/frames/IERS/source/input, all target samples/windows, and ideal fault/rate trace verified."
    )


if __name__ == "__main__":
    main()
