"""Build the anonymised analytic dataset from the raw Google Form export.

Usage:
    python scripts/01_prepare_data.py path/to/raw_form_responses.csv

The raw export is NOT part of this repository: it contains timestamps, job
titles and free-text entries. This script keeps only the 20 Likert items and
coarsened demographics, and writes:

    data/sem_df.csv               analytic dataset (one row per respondent)
    data/demographics_summary.csv sample profile (aggregated)
    outputs/sample_flow.csv       inclusion/exclusion counts
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

ITEMS = [f"sp{i}" for i in range(1, 11)] + [f"cd{i}" for i in range(1, 6)] + [f"ir{i}" for i in range(1, 6)]

# Column positions in the Form export (0-based)
COL_TIMESTAMP, COL_SCREEN, COL_GENDER, COL_AGE = 0, 1, 2, 3
COL_ORG, COL_EXPERIENCE = 5, 7
COL_FIRST_ITEM = 8

AGE_MAP = {"Under 30": "<40", "30–39": "<40", "40–49": "40–49", "50 or older": "50+"}
EXP_MAP = {"Less than 5 years": "≤15", "5–10 years": "≤15", "11–15 years": "≤15", "More than 15 years": ">15"}


def english(label):
    """Keep the English half of a bilingual 'English / Arabic' label."""
    return label.split(" / ")[0].strip() if isinstance(label, str) else label


def main(raw_path):
    raw = pd.read_csv(raw_path)
    assert raw.shape[1] == 28, f"unexpected column count {raw.shape[1]}"
    item_cols = raw.columns[COL_FIRST_ITEM:COL_FIRST_ITEM + 20]
    for k, col in enumerate(item_cols, start=1):
        assert col.startswith(f"{k}."), f"item {k} out of order: {col[:40]!r}"

    likert = raw[item_cols].apply(lambda s: s.str.extract(r"^(\d)")[0].astype(float))
    likert.columns = ITEMS

    screen = raw.iloc[:, COL_SCREEN].map(english)
    ts = pd.to_datetime(raw.iloc[:, COL_TIMESTAMP])

    flow = [("Form submissions", len(raw))]
    screened_out = screen.eq("No")
    flow.append(("Excluded: screening question answered 'No' (questionnaire skipped)", int(screened_out.sum())))
    incomplete = likert.isna().any(axis=1) & ~screened_out
    flow.append(("Excluded: incomplete Likert responses", int(incomplete.sum())))
    keep = ~screened_out & ~incomplete

    df = likert[keep].astype(int).copy()
    df.insert(0, "screening", screen[keep].fillna("not_asked").str.lower().values)
    gender = raw.iloc[:, COL_GENDER].map(english)[keep]
    age = raw.iloc[:, COL_AGE].map(english)[keep]
    org = raw.iloc[:, COL_ORG].map(english)[keep]
    exp = raw.iloc[:, COL_EXPERIENCE].map(english)[keep]

    # Coarsened, non-identifying demographics for use as controls
    df["female"] = gender.map({"Female": 1, "Male": 0}).values
    df["age_group"] = age.map(AGE_MAP).values
    df["private_hospital"] = org.map(lambda x: 1 if x == "Private Hospital" else (0 if isinstance(x, str) else None)).values
    df["experience_group"] = exp.map(EXP_MAP).values

    # Response-style flag: identical answer on all 20 items
    df["straightline"] = (df[ITEMS].nunique(axis=1) == 1).astype(int)

    # Possible repeat submission: identical to an earlier response on every
    # demographic field, job title and all 20 items. Job title is used only
    # here and is not exported.
    profile = raw.iloc[:, COL_GENDER:COL_FIRST_ITEM].fillna("NA").astype(str).apply(
        lambda r: "|".join(r.str.strip().str.lower()), axis=1)[keep]
    answers = df[ITEMS].astype(str).apply("".join, axis=1)
    order = ts[keep].argsort(kind="stable").values
    key = (profile + "#" + answers).iloc[order]
    dup = pd.Series(key.duplicated(keep="first").values, index=key.index).reindex(df.index)
    df["duplicate_profile"] = dup.astype(int)

    # Order rows by submission time, then drop the time itself
    df = df.iloc[ts[keep].argsort(kind="stable").values].reset_index(drop=True)
    df.insert(0, "id", range(1, len(df) + 1))

    flow.append(("Analytic sample", len(df)))
    flow.append(("  of which passed screening question ('Yes')", int(df.screening.eq("yes").sum())))
    flow.append(("  of which responded before screening question was added", int(df.screening.eq("not_asked").sum())))
    flow.append(("  of which straight-lined (same answer on all 20 items)", int(df.straightline.sum())))
    flow.append(("  of which identical to an earlier response (demographics, job title, all items)",
                 int(df.duplicate_profile.sum())))

    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "outputs").mkdir(exist_ok=True)
    df.to_csv(ROOT / "data" / "sem_df.csv", index=False)
    pd.DataFrame(flow, columns=["step", "n"]).to_csv(ROOT / "outputs" / "sample_flow.csv", index=False)

    rows = []
    for var, series in [("gender", gender), ("age_group", age), ("organisation_type", org), ("experience_years", exp)]:
        counts = series.fillna("Missing").value_counts()
        for cat, n in counts.items():
            rows.append((var, cat, int(n), round(100 * n / len(series), 1)))
    pd.DataFrame(rows, columns=["variable", "category", "n", "percent"]).to_csv(
        ROOT / "data" / "demographics_summary.csv", index=False)

    for step, n in flow:
        print(f"{n:>5}  {step}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
