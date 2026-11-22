"""pytest entry point: runs the headless end-to-end suite in tests/run_checks.py in a subprocess."""
import os
import subprocess
import sys
from pathlib import Path


def test_end_to_end_suite():
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, str(Path(__file__).with_name("run_checks.py"))],
                       capture_output=True, text=True, encoding="utf-8", env=env, timeout=900)
    out = (r.stdout or "") + (r.stderr or "")
    print(out[-3000:])
    assert r.returncode == 0, out[-4000:]
    assert "checks passed" in out
