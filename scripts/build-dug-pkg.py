#!/usr/bin/env python3
"""Build a local macOS Installer package for dug."""

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "dugout-mlb-data-analysis"
VERSION = "0.1.1"
INSTALL_ROOT = f"/usr/local/lib/{PACKAGE}"

LAUNCHER = f'''#!/bin/sh
for python in "$(command -v python3 2>/dev/null)" /opt/homebrew/bin/python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /usr/bin/python3; do
    if [ -x "$python" ] && "$python" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
        exec "$python" -c 'import sys; sys.path.insert(0, "{INSTALL_ROOT}"); from dugout.cli import main; raise SystemExit(main())' "$@"
    fi
done
printf '%s\\n' 'dug requires Python 3.10 or newer. Install Python, then run dug again.' >&2
exit 1
'''


def build(output_dir: Path) -> Path:
    if shutil.which("pkgbuild") is None:
        raise RuntimeError("pkgbuild is required; build this package on macOS")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{PACKAGE}-{VERSION}.pkg"
    with tempfile.TemporaryDirectory(prefix="dug-pkg-") as temporary:
        root = Path(temporary) / "root"
        executable = root / "usr" / "local" / "bin" / "dug"
        executable.parent.mkdir(parents=True)
        executable.write_text(LAUNCHER, encoding="utf-8")
        executable.chmod(0o755)
        module_dir = root / INSTALL_ROOT.lstrip("/") / "dugout"
        module_dir.mkdir(parents=True)
        for source in sorted((ROOT / "cli" / "dugout").glob("*.py")):
            shutil.copy2(source, module_dir / source.name)
        subprocess.run(
            ["pkgbuild", "--root", str(root),
             "--identifier", "com.ryansmith19.dugout-mlb-data-analysis",
             "--version", VERSION, "--install-location", "/", str(output)],
            check=True,
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    print(build(args.output_dir))


if __name__ == "__main__":
    main()
