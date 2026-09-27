"""Firmware build identifier: PlatformIO pre-script and arduino-cli helper.

ID = <git short sha | nogit>-src<hash>-<toolchain>

This is a human-readable LABEL, not the artifact identity. <hash> is a SHA-256
prefix over every file in the project's source roots (sketch/src_dir, the
configured lib/include/boards dirs, platformio.ini, root partition CSVs and the
build scripts in scripts/*.py) read from disk, tracked or not. Compiler flags,
board options and the installed core are NOT captured here.

The authoritative identity is the ELF SHA-256 that elf2image embeds in the app
image (--elf-sha256-offset 0xb0); the firmware prints it at runtime as
elf_sha256=... and evidence compares it with the recorded ELF hash. That value
changes with every build input by construction.

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


def build_inputs(project_dir, roots):
    files = [os.path.join(project_dir, "platformio.ini")] + sorted(glob.glob(os.path.join(project_dir, "*.csv")))
    files += sorted(glob.glob(os.path.join(project_dir, "scripts", "*.py")))
    for root in roots:
        for directory, dirs, names in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            files += [os.path.join(directory, name) for name in sorted(names)]
    return sorted({os.path.abspath(f) for f in files if os.path.isfile(f)})


def build_id(project_dir, roots, toolchain):
    digest = hashlib.sha256()
    for path in build_inputs(project_dir, roots):
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
    roots = [env.subst(v) for v in ("$PROJECT_SRC_DIR", "$PROJECT_LIB_DIR", "$PROJECT_INCLUDE_DIR", "$PROJECT_BOARDS_DIR")]
    ident = build_id(env.subst("$PROJECT_DIR"), roots, f"pio-{env['PIOENV']}")
    env.Append(CPPDEFINES=[("FIRMWARE_BUILD_ID", env.StringifyMacro(ident))])
    print(f"FIRMWARE_BUILD_ID={ident}")
elif __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Print the firmware build ID for a non-PlatformIO build.")
    parser.add_argument("--sketch", required=True, help="sketch/source folder that is compiled")
    parser.add_argument("--toolchain", default="cli")
    parser.add_argument("--project", default=os.getcwd())
    args = parser.parse_args()
    project = os.path.abspath(args.project)
    roots = [os.path.abspath(args.sketch)] + [os.path.join(project, d) for d in ("lib", "include", "boards")]
    print(build_id(project, roots, args.toolchain))
