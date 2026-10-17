"""Assemble the manuscript from the analysis outputs.

Run from the repository root after scripts 01-04:  python scripts/05_build_manuscript.py
- Fills the tables in manuscript/manuscript.md from outputs/*.csv
- Numbers citations ([@key]) in order of first appearance using manuscript/references.csv
- Writes manuscript/build/manuscript.md, manuscript.docx and supplementary.docx (pandoc required)
"""
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
MS = ROOT / "manuscript"
BUILD = MS / "build"
NAMES = {"SP": "Strategic planning", "CD": "Capacity development", "IR": "Institutional resilience"}


def f(x, d=2):
    return f"{x:.{d}f}".replace("-", "−")


def md_table(df):
    head = "| " + " | ".join(df.columns) + " |"
    numeric = [all(re.fullmatch(r"[−\d.,\[\] ()P=<]*", str(v)) for v in df[c]) for c in df.columns]
    sep = "|" + "|".join("---:" if num and i else ":---" for i, num in enumerate(numeric)) + "|"
    rows = ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


def table1():
    d = pd.read_csv(ROOT / "data" / "demographics_summary.csv")
    labels = {"gender": "Gender", "age_group": "Age group", "organisation_type": "Organisation type",
              "experience_years": "Health-sector experience"}
    rows, last = [], None
    for r in d.itertuples():
        rows.append((labels[r.variable] if r.variable != last else "", r.category.replace(" (please specify)", ""),
                     r.n, f(r.percent, 1)))
        last = r.variable
    n = int(d[d.variable == "gender"].n.sum())
    return (f"**Table 1 | Sample characteristics (N = {n})**\n\n"
            + md_table(pd.DataFrame(rows, columns=["Characteristic", "Category", "n", "%"])))


def table2():
    s = pd.read_csv(OUT / "scale_descriptives.csv")
    c = pd.read_csv(OUT / "correlations.csv")
    full, excl = s[s.Sample == "Full sample"].set_index("Construct"), s[s.Sample == "Excluding straight-liners"].set_index("Construct")
    cf = c[c.Sample == "Full sample"].set_index("Pair")
    ce = c[c.Sample == "Excluding straight-liners"].set_index("Pair")

    def r(a, b):
        key = f"{a}-{b}" if f"{a}-{b}" in cf.index else f"{b}-{a}"
        return f"{f(cf.loc[key, 'Pearson_r'])} ({f(ce.loc[key, 'Pearson_r'])})"

    rows = []
    for k in ["SP", "CD", "IR"]:
        rows.append((f"{k}  {NAMES[k]}", int(full.loc[k, "Items"]),
                     f"{f(full.loc[k, 'Mean'])} ({f(excl.loc[k, 'Mean'])})",
                     f"{f(full.loc[k, 'SD'])} ({f(excl.loc[k, 'SD'])})",
                     f(full.loc[k, "Pct_at_ceiling"], 1),
                     f"{f(full.loc[k, 'Cronbach_alpha'])} ({f(excl.loc[k, 'Cronbach_alpha'])})",
                     "—" if k == "SP" else r("SP", k), "—" if k != "IR" else r("CD", "IR")))
    t = pd.DataFrame(rows, columns=["Construct", "Items", "Mean", "s.d.", "% scoring 7", "Cronbach's α", "r with SP", "r with CD"])
    return ("**Table 2 | Descriptive statistics, reliability and correlations of scale scores**\n\n" + md_table(t)
            + "\n\nValues are for the full sample (N = 416); values in parentheses exclude respondents who gave the "
              "same answer to all 20 items (n = 207). Scale scores are item means on a 1–7 scale. Correlations are "
              "Pearson's r; all P < 0.001.")


def table3():
    fit = pd.read_csv(OUT / "cfa_fit_wlsmv.csv")
    fit = fit[fit.Sample.isin(["Full sample", "Excluding straight-liners"])]
    fit.columns = fit.columns.str.replace(".", "_", regex=False)
    rows = []
    for r in fit.itertuples(index=False):
        rows.append((r.Sample.replace("Excluding straight-liners", "Excl. straight-liners") + f" (n = {r.N})", r.Model,
                     f(r.chisq_scaled, 1), int(r.df_scaled), f(r.cfi_scaled, 3), f(r.tli_scaled, 3),
                     f"{f(r.rmsea_scaled, 3)} [{f(r.rmsea_ci_lower_scaled, 3)}, {f(r.rmsea_ci_upper_scaled, 3)}]",
                     f(r.srmr, 3)))
    a = pd.DataFrame(rows, columns=["Sample", "Model", "χ²", "d.f.", "CFI", "TLI", "RMSEA [90% CI]", "SRMR"])

    rel = pd.read_csv(OUT / "reliability_cr_ave.csv")
    lat = pd.read_csv(OUT / "latent_correlations.csv")
    ht = pd.read_csv(OUT / "htmt.csv")
    rows = []
    for smp, lab in [("Full sample", "Full"), ("Excluding straight-liners", "Excl. straight-liners")]:
        rl = rel[rel.Sample == smp].set_index("Construct")
        for k in ["SP", "CD", "IR"]:
            rows.append((lab, k, f(rl.loc[k, "CompositeReliability"]), f(rl.loc[k, "AVE"]), "", "", ""))
        for p in ["SP-CD", "SP-IR", "CD-IR"]:
            l = lat[(lat.Sample == smp) & (lat.Pair == p)].iloc[0]
            h = ht[(ht.Sample == smp) & (ht.Pair == p)].iloc[0]
            rows.append((lab, p.replace("-", "–"), "", "", f(l.r), f"[{f(l.ci_lower)}, {f(l.ci_upper)}]", f(h.HTMT)))
    b = pd.DataFrame(rows, columns=["Sample", "Construct / pair", "CR", "AVE", "Latent r", "95% CI", "HTMT"])
    cmp_ = pd.read_csv(OUT / "cfa_model_comparison.csv")
    cf = cmp_[cmp_.Sample == "Full sample"].set_index("Comparison")
    note = (f"Ordinal CFA, WLSMV estimator; χ² and fit indices are scaled. Scaled χ² difference tests (full sample): "
            f"three- versus two-factor Δχ² = {f(cf.loc['3-factor vs 2-factor', 'delta_chisq'], 1)}, Δd.f. = 2, "
            f"P = {f(cf.loc['3-factor vs 2-factor', 'p'], 3)}; three- versus one-factor "
            f"Δχ² = {f(cf.loc['3-factor vs 1-factor', 'delta_chisq'], 1)}, Δd.f. = 3, P < 0.001. "
            "CR, composite reliability; AVE, average variance extracted; HTMT, heterotrait–monotrait ratio "
            "(polychoric).")
    return ("**Table 3 | Measurement model: fit, reliability and discriminant validity**\n\n*a, Model fit*\n\n"
            + md_table(a) + "\n\n*b, Reliability and discriminant validity (three-factor model)*\n\n" + md_table(b)
            + "\n\n" + note)


def table4():
    sem = pd.read_csv(OUT / "sem_mediation_wlsmv.csv")
    lab = {"a": "a: SP → CD", "b": "b: CD → IR (SP held constant)", "cp": "c′: SP → IR (CD held constant)", "ind": "Indirect (a × b)",
           "total": "Total (c)", "prop": "Proportion mediated"}
    samples = ["Full sample", "Screened 'Yes' only", "Excluding straight-liners"]
    rows = []
    for p in ["a", "b", "cp", "ind", "total", "prop"]:
        row = [lab[p]]
        for s in samples:
            r = sem[(sem.Sample == s) & (sem.Path == p)].iloc[0]
            if p in ("ind", "total", "prop"):
                row.append(f"{f(r.Std_estimate)} [{f(r.MC_CI_lower)}, {f(r.MC_CI_upper)}]")
            else:
                pv = "<0.001" if r.p < 0.001 else f(r.p, 3)
                row.append(f"{f(r.Std_estimate)} (P {'< 0.001' if pv.startswith('<') else '= ' + pv})")
        rows.append(row)
    ns = {s: int(sem[sem.Sample == s].N.iloc[0]) for s in samples}
    cols = ["Path"] + [f"{s.replace(chr(39) + 'Yes' + chr(39) + ' only', 'only')} (n = {ns[s]})" for s in samples]
    a = pd.DataFrame(rows, columns=cols)

    obs = pd.read_csv(OUT / "mediation_observed_bootstrap.csv")
    rows = []
    for spec in obs.Specification.unique():
        o = obs[obs.Specification == spec].set_index("Path")
        rows.append((spec, int(o.N.iloc[0]),
                     *(f"{f(o.loc[k, 'B'])} [{f(o.loc[k, 'CI_lower'])}, {f(o.loc[k, 'CI_upper'])}]"
                       for k in ["a (SP→CD)", "b (CD→IR | SP)", "c′ (SP→IR | CD)", "indirect (a×b)", "proportion mediated"])))
    b = pd.DataFrame(rows, columns=["Specification", "n", "a", "b", "c′", "Indirect", "Prop. mediated"])
    return ("**Table 4 | Mediation of the strategic planning–resilience association by capacity development**\n\n"
            "*a, Latent structural equation model (standardised WLSMV estimates)*\n\n" + md_table(a)
            + "\n\n*b, Observed-score regression (unstandardised, 1–7 metric; 95% percentile bootstrap CI, 5,000 resamples)*\n\n"
            + md_table(b)
            + "\n\nBrackets give 95% confidence intervals (Monte Carlo, 20,000 draws, in a; percentile bootstrap in b). "
              "Controls: gender, age group, organisation type (private hospital versus other) and experience "
              "(>15 versus ≤15 years).")


def supplementary():
    flow = pd.read_csv(OUT / "sample_flow.csv")
    code = pd.read_csv(ROOT / "data" / "codebook.csv")
    code = code[code.construct.notna()]
    items = pd.read_csv(OUT / "item_descriptives.csv")
    load = pd.read_csv(OUT / "cfa_loadings.csv")
    lf = load[load.Sample == "Full sample"].set_index("Item").Loading
    le = load[load.Sample == "Excluding straight-liners"].set_index("Item").Loading
    harman = pd.read_csv(OUT / "harman_single_factor.csv")
    style = pd.read_csv(OUT / "response_style.csv")
    parts = ["# Supplementary Information", "",
             "**Supplementary Table 1 | Sample flow**", "", md_table(flow.rename(columns={"step": "Step"})), "",
             "**Supplementary Table 2 | Questionnaire items (English and Arabic)**", "",
             md_table(code[["variable", "construct", "description_en", "item_ar"]].rename(
                 columns={"variable": "Item", "construct": "Construct", "description_en": "English", "item_ar": "Arabic"})),
             "", "All items were rated on a seven-point scale (1 = strongly disagree; 7 = strongly agree).", "",
             "**Supplementary Table 3 | Item statistics and standardised loadings**", "",
             md_table(pd.DataFrame([(r.Item, f(r.Mean), f(r.SD), f(r.Pct_7, 1), f(r.Pct_le4, 1),
                                     f(r.Corrected_item_total_r), f(lf[r.Item]), f(le[r.Item]))
                                    for r in items.itertuples()],
                                   columns=["Item", "Mean", "s.d.", "% 7", "% 1–4", "Item–rest r",
                                            "Loading (full)", "Loading (excl. straight-liners)"])),
             "", "**Supplementary Table 4 | Response-style diagnostics and Harman single-factor test**", "",
             md_table(style.assign(Value=style.Value.map(lambda v: f(v, 1) if v % 1 else int(v)))), "",
             md_table(harman.rename(columns={"First_component_pct_variance": "% variance, first component",
                                             "Eigenvalues_gt_1": "Eigenvalues > 1"})), ""]
    return "\n".join(parts)


def number_citations(text, refs):
    order = []

    def repl(m):
        keys = [k.strip().lstrip("@") for k in m.group(1).split(";")]
        nums = []
        for k in keys:
            if k not in refs:
                raise KeyError(f"unknown reference key {k}")
            if k not in order:
                order.append(k)
            nums.append(order.index(k) + 1)
        nums = sorted(nums)
        spans, start = [], nums[0]
        for a, b in zip(nums, nums[1:] + [None]):
            if b != a + 1:
                spans.append(str(start) if start == a else (f"{start},{a}" if a == start + 1 else f"{start}–{a}"))
                start = b
        return "^" + ",".join(spans) + "^"

    text = re.sub(r"\[(@[^\]]+)\]", repl, text)
    reflist = "\n".join(f"{i}. {refs[k]}" for i, k in enumerate(order, start=1))
    unused = sorted(set(refs) - set(order))
    return text, reflist, unused


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    text = (MS / "manuscript.md").read_text(encoding="utf-8")
    refs = pd.read_csv(MS / "references.csv").set_index("key").citation.to_dict()
    text, reflist, unused = number_citations(text, refs)
    if unused:
        print("Note: references not cited:", ", ".join(unused))
    text = text.replace("<!-- REFERENCES -->", reflist)
    text = text.replace("<!-- TABLES -->", "\n\n".join([table1(), table2(), table3(), table4()]))
    text = text.replace("](../figures/", "](figures/")
    shutil.copytree(ROOT / "figures", BUILD / "figures", dirs_exist_ok=True)
    (BUILD / "manuscript.md").write_text(text, encoding="utf-8")
    (BUILD / "supplementary.md").write_text(supplementary(), encoding="utf-8")
    if shutil.which("pandoc"):
        for name in ("manuscript", "supplementary"):
            subprocess.run(["pandoc", f"{name}.md", "-o", f"{name}.docx", "--resource-path=."], cwd=BUILD, check=True)
        print("Wrote", BUILD / "manuscript.docx", "and", BUILD / "supplementary.docx")
    else:
        print("pandoc not found; wrote Markdown only to", BUILD)


if __name__ == "__main__":
    main()
