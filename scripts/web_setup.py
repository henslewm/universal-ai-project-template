#!/usr/bin/env python3
"""Prepare a ChatGPT, Claude or Mistral web Project: zip its files and copy its instructions."""

from __future__ import annotations

if __name__ == "__main__":  # A Ctrl+C while the imports below load also exits 130 (#31).
    import cli_exit
    cli_exit.guard_startup()

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import cli_exit

# Each client's instructions file and the doc whose list names the files to upload.
CLIENTS = {
    "chatgpt": (".chatgpt/PROJECT_INSTRUCTIONS.md", ".chatgpt/PROJECT_FILES.md", "ChatGPT"),
    "claude": (".claude-web/PROJECT_INSTRUCTIONS.md", ".claude-web/PROJECT_KNOWLEDGE.md", "Claude"),
    "mistral": (".mistral/PROJECT_INSTRUCTIONS.md", ".mistral/PROJECT_KNOWLEDGE.md", "Mistral Vibe"),
}
LIST_ITEM = re.compile(r"^\s*(?:\d+\.|-)\s+`([^`]+)`\s*$")


def listed_files(doc: Path) -> list[str]:
    """The files named as list items in the client's setup doc, so the doc stays the single source."""
    return [match.group(1) for line in doc.read_text(encoding="utf-8").splitlines()
            if (match := LIST_ITEM.match(line))]


def inside(root: Path, name: str) -> Path | None:
    """The regular file `name` names under `root`; None for an absolute, escaping or symlinked path."""
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    path = root / relative
    # Every component is checked, so a symlinked directory cannot carry the path outside the root.
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink():
            return None
    resolved = path.resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        return None
    return resolved


def copy_to_clipboard(text: str) -> bool:
    if sys.platform == "win32":
        commands = [["clip"]]
    elif sys.platform == "darwin":
        commands = [["pbcopy"]]
    else:
        commands = [["wl-copy"], ["xclip", "-selection", "clipboard"]]
    for command in commands:
        if shutil.which(command[0]):
            # clip reads the console code page; UTF-16 keeps non-ASCII text intact on Windows.
            data = text.encode("utf-16" if command[0] == "clip" else "utf-8")
            if subprocess.run(command, input=data, check=False).returncode == 0:
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", required=True, choices=sorted(CLIENTS))
    parser.add_argument("--root", default=".", help="Project root (default: current directory)")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    instructions_name, list_name, label = CLIENTS[args.client]
    instructions, file_list = inside(root, instructions_name), inside(root, list_name)
    for name, path in ((instructions_name, instructions), (list_name, file_list)):
        if path is None:
            print(f"Web setup refused: missing {root / name} (or it is a link or lies outside the project)")
            return 1
    names = listed_files(file_list)
    paths = {name: inside(root, name) for name in names}
    missing = [name for name, path in paths.items() if path is None]
    if not names or missing:
        print("Web setup refused: " + (f"missing {', '.join(missing)} (or a link or a path outside the project)"
                                       if missing else f"no files listed in {list_name}"))
        return 1
    archive = root / f"web-setup-{args.client}.zip"
    if archive.is_symlink() or (archive.exists() and not archive.is_file()):
        print(f"Web setup refused: {archive} is a link or not a regular file; remove it first")
        return 1
    # Build beside the target and rename over it, so an existing link is never followed or truncated.
    handle, temporary = tempfile.mkstemp(prefix=".web-setup-", suffix=".zip", dir=root)
    os.close(handle)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as bundle:
            for name, path in paths.items():
                bundle.write(path, name)
        os.replace(temporary, archive)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    copied = copy_to_clipboard(instructions.read_text(encoding="utf-8"))
    print(f"{label} web Project setup")
    print(f"1. Create a new Project in {label}.")
    if copied:
        print("2. Paste into the Project instructions: they are already on your clipboard.")
    else:
        print(f"2. Paste the contents of {instructions} into the Project instructions.")
    print(f"3. Upload the files inside {archive} ({len(names)} files) to the Project.")
    print("Connect GitHub to the Project too, so chats read the latest files instead of stale copies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_exit.run(main))
