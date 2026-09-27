"""Firmware build identifier: PlatformIO pre-script and arduino-cli helper.

ID = <git short sha>[-dirty<hash>]-<toolchain>

<hash> is a SHA-256 prefix over `git diff HEAD --binary` plus the path and
bytes of every untracked, non-ignored file, so any change that can affect the
build (sketch sources, lib/, include/, partitions, platformio.ini, scripts)
yields a different ID, and a clean tree yields the bare commit. Outside Git the
ID is "nogit-<hash of the source directories and platformio.ini>".

PlatformIO: `extra_scripts = pre:scripts/pio_build_id.py` defines FIRMWARE_BUILD_ID
(toolchain = pio-<env>).
arduino-cli (PowerShell, from the project root):
    $id = python scripts/pio_build_id.py cli
    arduino-cli compile ... --build-property "compiler.cpp.extra_flags='-DFIRMWARE_BUILD_ID=`"$id`"'"
(the single quotes keep the double quotes through arduino-cli's own argument splitter)
"""
import hashlib
import os
import subprocess
import sys


def _git(project_dir, *args):
    return subprocess.run(["git", *args], cwd=project_dir, capture_output=True, check=True).stdout


def _hash_paths(project_dir, roots):
    files = []
    for root in roots:
        if os.path.isfile(root):
            files.append(root)
        for directory, dirs, names in os.walk(root):
            dirs.sort()
            files += [os.path.join(directory, name) for name in sorted(names)]
    digest = hashlib.sha256()
    for path in files:
        digest.update(os.path.relpath(path, project_dir).replace("\\", "/").encode() + b"\0")
        with open(path, "rb") as handle:
            digest.update(handle.read() + b"\0")
    return digest.hexdigest()[:8]


def build_id(project_dir, toolchain, fallback_roots):
    try:
        sha = _git(project_dir, "rev-parse", "--short=10", "HEAD").decode().strip()
        diff = _git(project_dir, "diff", "HEAD", "--binary")
        untracked = sorted(p for p in _git(project_dir, "ls-files", "--others",
                                           "--exclude-standard", "-z").split(b"\0") if p)
        source = sha
        if diff or untracked:
            digest = hashlib.sha256(diff)
            for rel in untracked:
                digest.update(rel + b"\0")
                with open(os.path.join(project_dir, os.fsdecode(rel)), "rb") as handle:
                    digest.update(handle.read() + b"\0")
            source += "-dirty" + digest.hexdigest()[:8]
    except (OSError, subprocess.CalledProcessError):
        source = "nogit-" + _hash_paths(project_dir, [r for r in fallback_roots if os.path.exists(r)])
    return f"{source}-{toolchain}"


try:
    Import("env")  # noqa: F821 - defined only when PlatformIO/SCons runs this file
except NameError:
    env = None

if env is not None:
    project = env.subst("$PROJECT_DIR")
    roots = [env.subst(v) for v in ("$PROJECT_SRC_DIR", "$PROJECT_LIB_DIR", "$PROJECT_INCLUDE_DIR")]
    ident = build_id(project, f"pio-{env['PIOENV']}", roots + [os.path.join(project, "platformio.ini")])
    env.Append(CPPDEFINES=[("FIRMWARE_BUILD_ID", env.StringifyMacro(ident))])
    print(f"FIRMWARE_BUILD_ID={ident}")
elif __name__ == "__main__":
    project = os.getcwd()
    toolchain = sys.argv[1] if len(sys.argv) > 1 else "cli"
    print(build_id(project, toolchain,
                   [os.path.join(project, p) for p in ("src", "lib", "include", "platformio.ini")]))
