from __future__ import annotations

import re
import sys

PII_PATTERNS = [
    re.compile(r"\b\d{13,19}\b"),  # credit card like
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS key
    re.compile(r"(?i)secret|password|token"),
]


def scan_path(path: str) -> int:
    violations = 0
    with open(path, "rb") as f:
        data = f.read().decode(errors="ignore")
    for pat in PII_PATTERNS:
        if pat.search(data):
            violations += 1
            print(f"Potential secret/PII found in {path}: pattern {pat.pattern}")
    return violations


if __name__ == "__main__":
    total = 0
    for p in sys.argv[1:]:
        total += scan_path(p)
    sys.exit(1 if total else 0)
