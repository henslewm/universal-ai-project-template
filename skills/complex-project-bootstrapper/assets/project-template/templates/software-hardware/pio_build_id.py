"""PlatformIO pre-script: inject FIRMWARE_BUILD_ID from build metadata.

ID = <git short sha>[-dirty]-src<hash>-pio-<env>

<hash> is a SHA-256 prefix over every file under src_dir plus platformio.ini
(relative path and bytes), tracked or not. Two builds share an ID only when
their sources are byte-identical, so serial evidence cannot bind to the wrong
experiment built from different uncommitted changes on the same HEAD. Falls
back to "nogit" outside a Git checkout.
"""
import hashlib
import os
import subprocess

Import("env")  # noqa: F821 - provided by PlatformIO/SCons

PROJECT_DIR = env.subst("$PROJECT_DIR")  # noqa: F821
SRC_DIR = env.subst("$PROJECT_SRC_DIR")  # noqa: F821


def _git(*args):
    return subprocess.run(["git", *args], cwd=PROJECT_DIR,
                          capture_output=True, text=True, check=True).stdout.strip()


def _source_hash():
    digest = hashlib.sha256()
    files = [os.path.join(PROJECT_DIR, "platformio.ini")]
    for root, dirs, names in os.walk(SRC_DIR):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        files += [os.path.join(root, n) for n in sorted(names)]
    for path in files:
        digest.update(os.path.relpath(path, PROJECT_DIR).replace("\\", "/").encode())
        digest.update(b"\0")
        with open(path, "rb") as handle:
            digest.update(handle.read())
        digest.update(b"\0")
    return digest.hexdigest()[:8]


try:
    sha = _git("rev-parse", "--short=10", "HEAD")
    dirty = "-dirty" if _git("status", "--porcelain") else ""
    source = sha + dirty
except (OSError, subprocess.CalledProcessError):
    source = "nogit"

build_id = f"{source}-src{_source_hash()}-pio-{env['PIOENV']}"  # noqa: F821
env.Append(CPPDEFINES=[("FIRMWARE_BUILD_ID", env.StringifyMacro(build_id))])  # noqa: F821
print(f"FIRMWARE_BUILD_ID={build_id}")
