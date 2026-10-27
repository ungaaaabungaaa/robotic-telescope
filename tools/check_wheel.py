"""Run the installed application outside its source tree with only external dependencies."""

import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def main():
    wheel = Path(sys.argv[1]).resolve(strict=True)
    repository = Path(__file__).resolve().parents[1]
    with zipfile.ZipFile(wheel) as archive:
        assert "robotic_telescope/resources/demo-request.json" in archive.namelist()
        assert sum(x.file_size for x in archive.infolist()) < 200_000
        assert not any(
            "__pycache__" in name or name.endswith(".pyc") for name in archive.namelist()
        )
    with tempfile.TemporaryDirectory(prefix="telescope-wheel-") as temporary:
        root = Path(temporary)
        target = root / "installed"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                "--no-compile",
                "--target",
                str(target),
                str(wheel),
            ],
            check=True,
            cwd=root,
        )
        external = [
            p
            for p in os.environ.get("PYTHONPATH", "").split(os.pathsep)
            if p and not Path(p).resolve().is_relative_to(repository)
        ]
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join([str(target), *external]),
            "MPLCONFIGDIR": str(root / "mpl"),
        }
        probe = r"""
import json
from pathlib import Path
import socket
from unittest.mock import patch
import robotic_telescope
from robotic_telescope.cli import main
from robotic_telescope.pointing import RESOURCES
assert Path(robotic_telescope.__file__).resolve().is_relative_to(Path('installed').resolve())
with patch.object(socket, 'create_connection', side_effect=AssertionError('Offline app tried external network')):
    assert main(['demo', '--output', 'study']) == 0
    assert main(['plan', '--request', str(RESOURCES / 'demo-request.json'), '--output', 'custom']) == 0
    assert main(['simulate', '--output', 'mount']) == 0
metrics = json.loads(Path('study/metrics.json').read_text())
plan = json.loads(Path('study/plan.json').read_text())
assert len(plan['utc']) == 361 and len(plan['targets']) == 3
assert metrics['simulation']['fault_position_frozen']
assert Path('study/altitude.png').stat().st_size > 1000
assert Path('mount/mount-trace.csv').is_file()
assert plan['targets'] == json.loads(Path('custom/plan.json').read_text())['targets']
print('Installed wheel: offline default/custom plans, bundled input, ideal simulation, reports, and figures passed.')
"""
        subprocess.run([sys.executable, "-c", probe], check=True, cwd=root, env=env)
        subprocess.run(
            [sys.executable, "-m", "robotic_telescope", "--version"], check=True, cwd=root, env=env
        )


if __name__ == "__main__":
    main()
