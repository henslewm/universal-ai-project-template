"""Firmware build identifier: PlatformIO pre-script and arduino-cli helper.

ID = <git short sha | nogit>-src<hash>-<toolchain>

Invariant: <hash> is a SHA-256 prefix over the relative path and bytes of every
file in the build-input roots -- the sketch/src directory, lib/, include/,
boards/, platformio.ini and partition CSVs in the project root -- read straight
from disk, whether tracked, untracked or git-ignored. Only build outputs and VCS
metadata (.pio, .git, build) are skipped. Git is never consulted for content, so
the ID changes exactly when a build input changes; the commit is only a label.

PlatformIO: `extra_scripts = pre:scripts/pio_build_id.py` defines FIRMWARE_BUILD_ID
(toolchain = pio-<env>, source root = src_dir).
arduino-cli (PowerShell, project root; pass the sketch folder):
    $id = python scripts/pio_build_id.py --sketch firmware/BLEScanner_WORKING_v7 --toolchain cli
    arduino-cli compile ... --build-property "compiler.cpp.extra_flags='-DFIRMWARE_BUILD_ID=`"$id`"'"
(the single quotes keep the double quotes through arduino-cli's own argument splitter)
"""
import argparse
import glob
import hashlib
import os
import subprocess

SKIP_DIRS = {".pio", ".git", "build", "__pycache__"}


def build_inputs(project_dir, source_dir):
    roots = [source_dir] + [os.path.join(project_dir, d) for d in ("lib", "include", "boards")]
    files = [os.path.join(project_dir, "platformio.ini")] + sorted(glob.glob(os.path.join(project_dir, "*.csv")))
    for root in roots:
        for directory, dirs, names in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            files += [os.path.join(directory, name) for name in sorted(names)]
    return sorted({os.path.abspath(f) for f in files if os.path.isfile(f)})


def build_id(project_dir, source_dir, toolchain):
    digest = hashlib.sha256()
    for path in build_inputs(project_dir, source_dir):
        digest.update(os.path.relpath(path, project_dir).replace("\\", "/").encode() + b"\0")
        with open(path, "rb") as handle:
            digest.update(handle.read() + b"\0")
    try:
        label = subprocess.run(["git", "rev-parse", "--short=10", "HEAD"], cwd=project_dir,
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        label = "nogit"
    return f"{label}-src{digest.hexdigest()[:8]}-{toolchain}"


try:
    Import("env")  # noqa: F821 - defined only when PlatformIO/SCons runs this file
except NameError:
    env = None

if env is not None:
    ident = build_id(env.subst("$PROJECT_DIR"), env.subst("$PROJECT_SRC_DIR"), f"pio-{env['PIOENV']}")
    env.Append(CPPDEFINES=[("FIRMWARE_BUILD_ID", env.StringifyMacro(ident))])
    print(f"FIRMWARE_BUILD_ID={ident}")
elif __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Print the firmware build ID for a non-PlatformIO build.")
    parser.add_argument("--sketch", required=True, help="sketch/source folder that is compiled")
    parser.add_argument("--toolchain", default="cli")
    parser.add_argument("--project", default=os.getcwd())
    args = parser.parse_args()
    print(build_id(os.path.abspath(args.project), os.path.abspath(args.sketch), args.toolchain))
