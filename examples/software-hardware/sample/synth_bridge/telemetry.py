"""Log analysis: pure text in, counts out. Bounded utility work for the cheapest tier."""
from __future__ import annotations

from collections import Counter


def summarize(lines) -> dict:
    counts: Counter[str] = Counter()
    readings = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        kind, _, rest = line.partition(" ")
        counts[kind] += 1
        if kind == "READING":
            try:
                readings.append(int(rest))
            except ValueError:
                counts["MALFORMED"] += 1
    return {"counts": dict(sorted(counts.items())),
            "reading_min": min(readings) if readings else None,
            "reading_max": max(readings) if readings else None}
