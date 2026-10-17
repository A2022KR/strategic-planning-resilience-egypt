"""Check that re-running the analysis reproduces the committed outputs.

Usage (from the repository root):
    cp -r outputs /tmp/outputs_committed          # snapshot before re-running
    make analysis
    python tests/check_reproducibility.py /tmp/outputs_committed

Numeric columns must agree within TOLERANCE (outputs are rounded to 3 decimals);
text columns must match exactly. Exits non-zero on any difference.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 0.002


def compare(committed, fresh):
    a, b = pd.read_csv(committed), pd.read_csv(fresh)
    if list(a.columns) != list(b.columns) or len(a) != len(b):
        return [f"shape or columns differ: {a.shape} vs {b.shape}"]
    problems = []
    for col in a.columns:
        x, y = a[col], b[col]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            xv, yv = x.to_numpy(float), y.to_numpy(float)
            bad = ~(np.isclose(xv, yv, atol=TOLERANCE, rtol=0) | (np.isnan(xv) & np.isnan(yv)))
            if bad.any():
                i = int(np.argmax(bad))
                problems.append(f"{col}: row {i} committed {xv[i]} vs fresh {yv[i]}")
        elif not x.astype(str).equals(y.astype(str)):
            problems.append(f"{col}: text values differ")
    return problems


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    committed_dir, fresh_dir = Path(sys.argv[1]), ROOT / "outputs"
    failures = 0
    for committed in sorted(committed_dir.glob("*.csv")):
        fresh = fresh_dir / committed.name
        problems = [f"missing after re-run"] if not fresh.exists() else compare(committed, fresh)
        status = "OK " if not problems else "FAIL"
        print(f"{status} {committed.name}")
        for p in problems:
            print(f"     {p}")
        failures += bool(problems)
    if failures:
        sys.exit(f"{failures} output file(s) did not reproduce")
    print("All outputs reproduced.")


if __name__ == "__main__":
    main()
