"""Bump APP_VERSION in app.py (the single source of truth) and show the release commands.

Usage:  python scripts/bump_version.py 1.4.0
"""
import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit("usage: python scripts/bump_version.py MAJOR.MINOR.PATCH   (example: 1.4.0)")
    new = sys.argv[1]
    text = APP.read_text(encoding="utf-8")
    m = re.search(r'APP_VERSION = "([^"]+)"', text)
    if not m:
        sys.exit("APP_VERSION not found in app.py")
    if m.group(1) == new:
        sys.exit(f"already at {new}")
    APP.write_text(text.replace(m.group(0), f'APP_VERSION = "{new}"', 1), encoding="utf-8")
    print(f"APP_VERSION: {m.group(1)} -> {new}\n\nNext steps:\n"
          f"  1. Add a '## [{new}] - YYYY-MM-DD' section to CHANGELOG.md\n"
          f"  2. git commit -am \"chore: release v{new}\"\n"
          f"  3. git tag -a v{new} -m \"v{new}\"\n"
          f"  4. git push origin main --follow-tags     (GitHub Actions builds the Windows .exe and publishes the release)")


if __name__ == "__main__":
    main()
