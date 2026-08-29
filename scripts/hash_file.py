#!/usr/bin/env python3
"""Print SHA-256 and basic metadata for a source or evidence file."""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    args = parser.parse_args()
    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        parser.error(f"Not a file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    print(f"path: {path}")
    print(f"size_bytes: {stat.st_size}")
    print(f"modified_utc: {datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()}")
    print(f"sha256: {digest.hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
