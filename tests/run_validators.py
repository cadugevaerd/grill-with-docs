#!/usr/bin/env python3
"""Run every standalone validator deterministically on every supported OS."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VALIDATORS = tuple(sorted(ROOT.glob("validate_*.py")))


def main() -> int:
    if not VALIDATORS:
        print("No validators found", file=sys.stderr)
        return 2
    for validator in VALIDATORS:
        print(f"==> {validator.name}", flush=True)
        result = subprocess.run([sys.executable, str(validator)], cwd=ROOT.parent)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
