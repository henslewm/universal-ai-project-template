#!/usr/bin/env python3
"""Prepare a ChatGPT, Claude or Mistral web Project: zip its files and copy its instructions."""

from __future__ import annotations

if __name__ == "__main__":  # A Ctrl+C while the imports below load also exits 130 (#31).
    import cli_exit
    cli_exit.guard_startup()

import argparse
import re
import shutil
import subprocess
import sys
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
    instructions, file_list = root / instructions_name, root / list_name
    for path in (instructions, file_list):
        if not path.is_file():
            print(f"Web setup refused: missing {path}")
            return 1
    names = listed_files(file_list)
    missing = [name for name in names if not (root / name).is_file()]
    if not names or missing:
        print("Web setup refused: " + (f"missing {', '.join(missing)}" if missing else f"no files listed in {list_name}"))
        return 1
    archive = root / f"web-setup-{args.client}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in names:
            bundle.write(root / name, name)
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
