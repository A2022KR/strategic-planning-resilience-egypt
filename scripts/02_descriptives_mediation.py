"""Descriptives, reliability, response-style diagnostics and observed-score mediation.

Run from the repository root:  python scripts/02_descriptives_mediation.py
Reads data/sem_df.csv and writes tables to outputs/.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
SEED = 20250520
N_BOOT = 5000

SCALES = {
    "SP": [f"sp{i}" for i in range(1, 11)],
    "CD": [f"cd{i}" for i in range(1, 6)],
    "IR": [f"ir{i}" for i in range(1, 6)],
}
ITEMS = sum(SCALES.values(), [])


def cronbach_alpha(x):
    k = x.shape[1]
    return k / (k - 1) * (1 - x.var(ddof=1).sum() / x.sum(axis=1).var(ddof=1))


def add_scores(df):
    df = df.copy()
    for name, cols in SCALES.items():
        df[name] = df[cols].mean(axis=1)
    return df


def design(df, x, controls):
    cols = [x] + controls
    X = df[cols].to_numpy(float)
    return np.column_stack([np.ones(len(df)), X])


def ols(X, y):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def mediation(df, controls, rng):
    """Percentile-bootstrap mediation SP -> CD -> IR (unstandardised, 1-7 metric)."""
    d = df.dropna(subset=["SP", "CD", "IR"] + controls).reset_index(drop=True)
    sp, cd, ir = (d[c].to_numpy(float) for c in ("SP", "CD", "IR"))
    C = d[controls].to_numpy(float) if controls else np.empty((len(d), 0))
    one = np.ones(len(d))

    def fit(idx):
        Xa = np.column_stack([one[idx], sp[idx], C[idx]])
        Xb = np.column_stack([one[idx], sp[idx], cd[idx], C[idx]])
        a = ols(Xa, cd[idx])[1]
        cp, b = ols(Xb, ir[idx])[1:3]
        c = ols(Xa, ir[idx])[1]
        return a, b, cp, c, a * b

    est = fit(np.arange(len(d)))
    boots = np.array([fit(rng.integers(0, len(d), len(d))) for _ in range(N_BOOT)])
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    rows = []
    for k, name in enumerate(["a (SP→CD)", "b (CD→IR | SP)", "c′ (SP→IR | CD)", "c (total SP→IR)", "indirect (a×b)"]):
        rows.append({"Path": name, "B": est[k], "CI_lower": lo[k], "CI_upper": hi[k]})
    prop = boots[:, 4] / boots[:, 3]
    rows.append({"Path": "proportion mediated", "B": est[4] / est[3],
                 "CI_lower": np.percentile(prop, 2.5), "CI_upper": np.percentile(prop, 97.5)})
    return len(d), rows


def main():
    df = add_scores(pd.read_csv(ROOT / "data" / "sem_df.csv"))
    rng = np.random.default_rng(SEED)

    # Item descriptives
    item_rows = []
    for name, cols in SCALES.items():
        for c in cols:
            s = df[c]
            item_rows.append({"Construct": name, "Item": c, "Mean": s.mean(), "SD": s.std(),
                              "Pct_7": 100 * s.eq(7).mean(), "Pct_le4": 100 * s.le(4).mean(),
                              "Skew": stats.skew(s), "Corrected_item_total_r":
                                  np.corrcoef(s, df[[x for x in cols if x != c]].mean(axis=1))[0, 1]})
    pd.DataFrame(item_rows).round(3).to_csv(OUT / "item_descriptives.csv", index=False)

    samples = {
        "Full sample": df,
        "Screened 'Yes' only": df[df.screening == "yes"],
        "Excluding straight-liners": df[df.straightline == 0],
    }

    # Scale descriptives, reliability and correlations
    scale_rows, corr_rows = [], []
    for sname, d in samples.items():
        for name, cols in SCALES.items():
            scale_rows.append({"Sample": sname, "N": len(d), "Construct": name, "Items": len(cols),
                               "Mean": d[name].mean(), "SD": d[name].std(), "Median": d[name].median(),
                               "Pct_at_ceiling": 100 * d[name].eq(7).mean(),
                               "Cronbach_alpha": cronbach_alpha(d[cols])})
        for x, y in [("SP", "CD"), ("SP", "IR"), ("CD", "IR")]:
            r, p = stats.pearsonr(d[x], d[y])
            rho, _ = stats.spearmanr(d[x], d[y])
            corr_rows.append({"Sample": sname, "Pair": f"{x}-{y}", "Pearson_r": r, "p": p, "Spearman_rho": rho})
    pd.DataFrame(scale_rows).round(3).to_csv(OUT / "scale_descriptives.csv", index=False)
    pd.DataFrame(corr_rows).round(4).to_csv(OUT / "correlations.csv", index=False)

    # Response-style diagnostics
    within_sd = df[ITEMS].std(axis=1)
    style = pd.DataFrame([
        ("Respondents", len(df)),
        ("Identical answer on all 20 items", int(df.straightline.sum())),
        ("  of which all 7 ('strongly agree')", int(df[ITEMS].eq(7).all(axis=1).sum())),
        ("Median % of items answered 7", float(np.median(100 * df[ITEMS].eq(7).mean(axis=1)))),
        ("Median within-person SD", float(within_sd.median())),
        ("Any item answered 1-3 (disagreement)", int(df[ITEMS].le(3).any(axis=1).sum())),
    ], columns=["Indicator", "Value"])
    style.to_csv(OUT / "response_style.csv", index=False)

    # Harman single-factor check: share of variance on first unrotated component
    harman_rows = []
    for sname, d in samples.items():
        eig = np.sort(np.linalg.eigvalsh(np.corrcoef(d[ITEMS].T)))[::-1]
        harman_rows.append({"Sample": sname, "First_component_pct_variance": 100 * eig[0] / eig.sum(),
                            "Eigenvalues_gt_1": int((eig > 1).sum())})
    pd.DataFrame(harman_rows).round(2).to_csv(OUT / "harman_single_factor.csv", index=False)

    # Observed-score mediation (percentile bootstrap)
    df_c = df.copy()
    df_c["age_40_49"] = (df_c.age_group == "40–49").astype(float).where(df_c.age_group.notna())
    df_c["age_50plus"] = (df_c.age_group == "50+").astype(float).where(df_c.age_group.notna())
    df_c["exp_gt15"] = (df_c.experience_group == ">15").astype(float).where(df_c.experience_group.notna())
    controls = ["female", "age_40_49", "age_50plus", "private_hospital", "exp_gt15"]
    med_rows = []
    specs = [
        ("Full sample", df_c, []),
        ("Full sample + controls", df_c, controls),
        ("Screened 'Yes' only", df_c[df_c.screening == "yes"], []),
        ("Excluding straight-liners", df_c[df_c.straightline == 0], []),
        ("Excluding straight-liners + controls", df_c[df_c.straightline == 0], controls),
    ]
    for sname, d, ctrl in specs:
        n, rows = mediation(d, ctrl, rng)
        for r in rows:
            med_rows.append({"Specification": sname, "N": n, **r})
    pd.DataFrame(med_rows).round(3).to_csv(OUT / "mediation_observed_bootstrap.csv", index=False)

    print(pd.DataFrame(scale_rows).round(3).to_string(index=False))
    print(pd.DataFrame(med_rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
