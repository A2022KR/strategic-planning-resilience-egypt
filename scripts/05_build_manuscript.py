"""Assemble the submission files from the analysis outputs.

Run from the repository root after scripts 01-04:  python scripts/05_build_manuscript.py
- Fills the tables in manuscript/manuscript.md from outputs/*.csv
- Numbers citations ([@key]) in order of first appearance, Vancouver style, from manuscript/references.csv
- Writes to manuscript/build/: manuscript.md/.docx, additional_file_1_supplementary.md/.docx and the
  STROBE and CHERRIES checklists (pandoc required for .docx; python-docx for line numbers and spacing)
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
SAMPLE_LABELS = {"Full sample": "Full sample", "Screened 'Yes' only": "Screened respondents",
                 "Excluding straight-liners": "Excluding straight-liners",
                 "Excluding repeat profiles": "Excluding repeat profiles"}


def f(x, d=2):
    return f"{x:.{d}f}".replace("-", "−")


def pval(p):
    return "< 0.001" if p < 0.001 else f"= {f(p, 3)}"


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
    return (f"**Table 1** Sample characteristics (N = {n})\n\n"
            + md_table(pd.DataFrame(rows, columns=["Characteristic", "Category", "n", "%"])))


def table2():
    s = pd.read_csv(OUT / "scale_descriptives.csv")
    c = pd.read_csv(OUT / "correlations.csv")
    full = s[s.Sample == "Full sample"].set_index("Construct")
    excl = s[s.Sample == "Excluding straight-liners"].set_index("Construct")
    cf = c[c.Sample == "Full sample"].set_index("Pair")
    ce = c[c.Sample == "Excluding straight-liners"].set_index("Pair")

    def r(a, b):
        return f"{f(cf.loc[f'{a}-{b}', 'Pearson_r'])} ({f(ce.loc[f'{a}-{b}', 'Pearson_r'])})"

    rows = []
    for k in ["SP", "CD", "IR"]:
        rows.append((f"{NAMES[k]} ({k})", int(full.loc[k, "Items"]),
                     f"{f(full.loc[k, 'Mean'])} ({f(excl.loc[k, 'Mean'])})",
                     f"{f(full.loc[k, 'SD'])} ({f(excl.loc[k, 'SD'])})",
                     f(full.loc[k, "Pct_at_ceiling"], 1),
                     f"{f(full.loc[k, 'Cronbach_alpha'])} ({f(excl.loc[k, 'Cronbach_alpha'])})",
                     "—" if k == "SP" else r("SP", k), "—" if k != "IR" else r("CD", "IR")))
    t = pd.DataFrame(rows, columns=["Construct", "Items", "Mean", "SD", "% scoring 7", "Cronbach's α",
                                    "r with SP", "r with CD"])
    return ("**Table 2** Descriptive statistics, reliability and correlations of scale scores\n\n" + md_table(t)
            + "\n\nValues are for the full sample (N = 416); values in parentheses exclude respondents who gave the "
              "same answer to all 20 items (n = 207). Scale scores are item means (range 1–7); % scoring 7 is the "
              "share of respondents with the maximum scale score. Correlations are Pearson's r; all P < 0.001.")


def table3():
    fit = pd.read_csv(OUT / "cfa_fit_wlsmv.csv")
    fit = fit[fit.Sample.isin(["Full sample", "Excluding straight-liners"])]
    fit.columns = fit.columns.str.replace(".", "_", regex=False)
    rows = []
    for r in fit.itertuples(index=False):
        rows.append((f"{SAMPLE_LABELS[r.Sample]} (n = {r.N})", r.Model,
                     f(r.chisq_scaled, 1), int(r.df_scaled), f(r.cfi_scaled, 3), f(r.tli_scaled, 3),
                     f"{f(r.rmsea_scaled, 3)} [{f(r.rmsea_ci_lower_scaled, 3)}, {f(r.rmsea_ci_upper_scaled, 3)}]",
                     f(r.srmr, 3)))
    a = pd.DataFrame(rows, columns=["Sample", "Model", "χ²", "df", "CFI", "TLI", "RMSEA [90% CI]", "SRMR"])

    rel = pd.read_csv(OUT / "reliability_cr_ave.csv")
    lat = pd.read_csv(OUT / "latent_correlations.csv")
    ht = pd.read_csv(OUT / "htmt.csv")
    rows = []
    for smp in ["Full sample", "Excluding straight-liners"]:
        rl = rel[rel.Sample == smp].set_index("Construct")
        for k in ["SP", "CD", "IR"]:
            rows.append((SAMPLE_LABELS[smp], k, f(rl.loc[k, "CompositeReliability"]), f(rl.loc[k, "AVE"]), "", "", ""))
        for p in ["SP-CD", "SP-IR", "CD-IR"]:
            l = lat[(lat.Sample == smp) & (lat.Pair == p)].iloc[0]
            h = ht[(ht.Sample == smp) & (ht.Pair == p)].iloc[0]
            rows.append((SAMPLE_LABELS[smp], p.replace("-", "–"), "", "", f(l.r),
                         f"[{f(l.ci_lower)}, {f(l.ci_upper)}]", f(h.HTMT)))
    b = pd.DataFrame(rows, columns=["Sample", "Construct / pair", "CR", "AVE", "Latent r", "95% CI", "HTMT"])
    cmp_ = pd.read_csv(OUT / "cfa_model_comparison.csv")
    cf = cmp_[cmp_.Sample == "Full sample"].set_index("Comparison")
    note = (f"Ordinal CFA, WLSMV estimator; χ² and fit indices are scaled. Scaled χ² difference tests (full sample): "
            f"three- versus two-factor Δχ² = {f(cf.loc['3-factor vs 2-factor', 'delta_chisq'], 1)}, Δdf = 2, "
            f"P {pval(cf.loc['3-factor vs 2-factor', 'p'])}; three- versus one-factor "
            f"Δχ² = {f(cf.loc['3-factor vs 1-factor', 'delta_chisq'], 1)}, Δdf = 3, "
            f"P {pval(cf.loc['3-factor vs 1-factor', 'p'])}. Results for screened respondents and after excluding "
            "repeat profiles are in the repository (outputs/). CR, composite reliability; AVE, average variance "
            "extracted; HTMT, heterotrait–monotrait ratio (polychoric).")
    return ("**Table 3** Measurement model: fit, reliability and discriminant validity\n\n*a. Model fit*\n\n"
            + md_table(a) + "\n\n*b. Reliability and discriminant validity (three-factor model)*\n\n" + md_table(b)
            + "\n\n" + note)


def table4():
    sem = pd.read_csv(OUT / "sem_mediation_wlsmv.csv")
    full = sem[sem.Sample == "Full sample"].set_index("Path")
    lab = {"a": "a: SP → CD", "b": "b: CD → IR (SP held constant)", "cp": "c′: SP → IR (CD held constant)",
           "ind": "Indirect effect (a × b)", "total": "Total effect (c)", "prop": "Proportion mediated"}
    rows = []
    for p in ["a", "b", "cp"]:
        rows.append((lab[p], f(full.loc[p, "Std_estimate"]), "—", pval(full.loc[p, "p"]).lstrip("= ")))
    for p in ["ind", "total", "prop"]:
        rows.append((lab[p], f(full.loc[p, "Std_estimate"]),
                     f"[{f(full.loc[p, 'MC_CI_lower'])}, {f(full.loc[p, 'MC_CI_upper'])}]",
                     "—" if p == "prop" else pval(full.loc[p, "p"]).lstrip("= ")))
    a = pd.DataFrame(rows, columns=["Path", "β", "95% Monte Carlo CI", "P"])

    obs = pd.read_csv(OUT / "mediation_observed_bootstrap.csv")
    rows = []
    for spec in ["Full sample", "Full sample + controls"]:
        o = obs[obs.Specification == spec].set_index("Path")
        rows.append((spec.replace("Full sample + controls", "Adjusted for covariates").replace("Full sample", "Unadjusted"),
                     int(o.N.iloc[0]),
                     *(f"{f(o.loc[k, 'B'])} [{f(o.loc[k, 'CI_lower'])}, {f(o.loc[k, 'CI_upper'])}]"
                       for k in ["a (SP→CD)", "b (CD→IR | SP)", "c′ (SP→IR | CD)", "indirect (a×b)",
                                 "proportion mediated"])))
    b = pd.DataFrame(rows, columns=["Model", "n", "a", "b", "c′", "Indirect", "Proportion mediated"])
    r2 = full.loc["a"]
    return ("**Table 4** Mediation of the association between strategic planning and institutional resilience by "
            "capacity development (full sample)\n\n*a. Latent structural equation model (standardised WLSMV estimates)*\n\n"
            + md_table(a)
            + f"\n\nR² = {f(r2.R2_CD)} for capacity development and {f(r2.R2_IR)} for institutional resilience.\n\n"
              "*b. Observed-score regression (unstandardised coefficients on the 1–7 scale; 95% percentile bootstrap "
              "CI, 5,000 resamples)*\n\n" + md_table(b)
            + "\n\nCovariates: gender, age group, organisation type (private hospital versus other) and experience "
              "(>15 versus ≤15 years); n is lower in the adjusted model because of missing covariate data.")


def table5():
    sem = pd.read_csv(OUT / "sem_mediation_wlsmv.csv")
    alt = pd.read_csv(OUT / "sem_alternative_models.csv")
    fit = pd.read_csv(OUT / "cfa_fit_wlsmv.csv")
    fit = fit[fit.Model.str.startswith("3-factor")].set_index("Sample")
    rows = []
    for s in SAMPLE_LABELS:
        d = sem[sem.Sample == s].set_index("Path")
        rows.append((SAMPLE_LABELS[s], int(d.N.iloc[0]), f(d.loc["a", "Std_estimate"]), f(d.loc["b", "Std_estimate"]),
                     f"{f(d.loc['cp', 'Std_estimate'])} (P {pval(d.loc['cp', 'p'])})",
                     f"{f(d.loc['ind', 'Std_estimate'])} [{f(d.loc['ind', 'MC_CI_lower'])}, {f(d.loc['ind', 'MC_CI_upper'])}]",
                     f(fit.loc[s, "cfi.scaled"], 3), f(fit.loc[s, "rmsea.scaled"], 3)))
    a = pd.DataFrame(rows, columns=["Sample", "n", "a", "b", "c′ (P)", "Indirect [95% CI]", "CFI", "RMSEA"])

    rows = []
    full = alt[alt.Sample == "Full sample"].set_index("Model")
    labels = {"Common method factor added": "Common latent method factor added",
              "Reverse order (SP -> IR -> CD)": "Reverse order: SP → IR → CD",
              "Merged CD+IR (SP -> CDIR)": "CD and IR merged into one factor"}
    for m, lab in labels.items():
        r = full.loc[m]
        cp = "—" if pd.isna(r.c_prime) else f"{f(r.c_prime)} (P {pval(r.p_c_prime)})"
        ind = "—" if pd.isna(r.indirect) else f"{f(r.indirect)} (P {pval(r.p_indirect)})"
        rows.append((lab, f(r.a), "—" if pd.isna(r.b) else f(r.b), cp, ind, f"{f(r.chisq, 1)} ({int(r.df)})",
                     f(r.cfi, 3), f(r.rmsea, 3)))
    b = pd.DataFrame(rows, columns=["Model", "a", "b", "c′ (P)", "Indirect (P)", "χ² (df)", "CFI", "RMSEA"])
    meth = full.loc["Common method factor added", "mean_method_loading"]
    return ("**Table 5** Robustness of the mediation model across samples and alternative specifications\n\n"
            "*a. Hypothesised model re-estimated in each analysis sample (standardised WLSMV estimates)*\n\n"
            + md_table(a)
            + "\n\n*b. Alternative specifications (full sample, N = 416)*\n\n" + md_table(b)
            + "\n\nScreened respondents: excludes 74 respondents who answered before the eligibility question was added. "
              "Straight-liners: identical answers to all 20 items. Repeat profiles: submissions identical to an earlier "
              "one on all demographic fields, job title and items. In the method-factor model all items load equally on "
              f"an orthogonal method factor (mean standardised loading {f(meth)}); this model did not converge after "
              "excluding straight-liners. In the reverse-order model, a is SP → IR, b is IR → CD and c′ is SP → CD; it is "
              "statistically equivalent to the hypothesised model. In the merged model, a is SP → combined factor. "
              "CIs are 95% Monte Carlo intervals (20,000 draws).")


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
    obs = pd.read_csv(OUT / "mediation_observed_bootstrap.csv")
    obs_t = obs.assign(Estimate=[f"{f(r.B)} [{f(r.CI_lower)}, {f(r.CI_upper)}]" for r in obs.itertuples()])
    obs_t = obs_t.pivot_table(index=["Specification", "N"], columns="Path", values="Estimate", aggfunc="first",
                              sort=False).reset_index()
    obs_t = obs_t[["Specification", "N", "a (SP→CD)", "b (CD→IR | SP)", "c′ (SP→IR | CD)", "indirect (a×b)",
                   "proportion mediated"]]
    obs_t.columns = ["Specification", "n", "a", "b", "c′", "Indirect", "Proportion mediated"]
    parts = ["# Additional file 1: Supplementary tables", "",
             "Strategic Planning and Institutional Resilience in Cairo's Health Sector: Examining the Mediating Role "
             "of Capacity Development in the Context of Environmental Crisis Management", "",
             "**Table S1** Sample flow", "", md_table(flow.rename(columns={"step": "Step"})), "",
             "**Table S2** Questionnaire items (English and Arabic)", "",
             md_table(code[["variable", "construct", "description_en", "item_ar"]].rename(
                 columns={"variable": "Item", "construct": "Construct", "description_en": "English",
                          "item_ar": "Arabic"})),
             "", "All items were rated on a seven-point scale (1 = strongly disagree; 7 = strongly agree).", "",
             "**Table S3** Item statistics and standardised factor loadings", "",
             md_table(pd.DataFrame([(r.Item, f(r.Mean), f(r.SD), f(r.Pct_7, 1), f(r.Pct_le4, 1),
                                     f(r.Corrected_item_total_r), f(lf[r.Item]), f(le[r.Item]))
                                    for r in items.itertuples()],
                                   columns=["Item", "Mean", "SD", "% 7", "% 1–4", "Item–rest r",
                                            "Loading (full)", "Loading (excl. straight-liners)"])),
             "", "**Table S4** Response-style diagnostics and Harman single-factor test", "",
             md_table(style.assign(Value=style.Value.map(lambda v: f(v, 1) if v % 1 else int(v)))), "",
             md_table(harman.assign(Sample=harman.Sample.map(SAMPLE_LABELS)).rename(
                 columns={"First_component_pct_variance": "% variance, first component",
                          "Eigenvalues_gt_1": "Eigenvalues > 1"})), "",
             "**Table S5** Observed-score mediation in all analysis samples (unstandardised coefficients; 95% "
             "percentile bootstrap CI, 5,000 resamples)", "",
             md_table(obs_t.assign(Specification=obs_t.Specification.str.replace("Screened 'Yes' only",
                                                                                  "Screened respondents"))), ""]
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
        nums = sorted(set(nums))
        spans, start = [], nums[0]
        for a, b in zip(nums, nums[1:] + [None]):
            if b != a + 1:
                spans.append(str(start) if start == a else (f"{start}, {a}" if a == start + 1 else f"{start}–{a}"))
                start = b
        return "[" + ", ".join(spans) + "]"

    text = re.sub(r"\[(@[^\]]+)\]", repl, text)
    reflist = "\n".join(f"{i}. {refs[k]}" for i, k in enumerate(order, start=1))
    unused = sorted(set(refs) - set(order))
    return text, reflist, unused


def format_docx(path, line_numbers):
    """Double spacing, page numbers and (optionally) continuous line numbers, as journals request."""
    try:
        from docx import Document
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Pt, RGBColor
    except ImportError:
        print("python-docx not installed; skipping layout formatting of", path.name)
        return
    doc = Document(path)
    for name in ("Normal", "Body Text", "First Paragraph", "Compact"):
        if name in [s.name for s in doc.styles]:
            st = doc.styles[name]
            st.font.name, st.font.size = "Times New Roman", Pt(12)
            st.paragraph_format.line_spacing = 2.0 if line_numbers else 1.15
    for st in doc.styles:
        if st.type == 1 and st.name and st.name.lower().startswith(("title", "heading")):
            st.font.color.rgb = RGBColor(0, 0, 0)
            st.font.name = "Times New Roman"
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.line_spacing = 1.0
                    for run in p.runs:
                        run.font.size = Pt(9)
    sect = doc.sections[0]
    if line_numbers:
        ln = OxmlElement("w:lnNumType")
        ln.set(qn("w:countBy"), "1")
        ln.set(qn("w:restart"), "continuous")
        sect._sectPr.append(ln)
    p = sect.footer.paragraphs[0]
    p.alignment = 1
    run = p.add_run()
    for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)
    doc.save(path)


def pandoc(src, dst, line_numbers=False):
    subprocess.run(["pandoc", src, "-o", dst, "--resource-path=."], cwd=BUILD, check=True)
    format_docx(BUILD / dst, line_numbers)


def main():
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    text = (MS / "manuscript.md").read_text(encoding="utf-8")
    refs = pd.read_csv(MS / "references.csv").set_index("key").citation.to_dict()
    text, reflist, unused = number_citations(text, refs)
    if unused:
        print("Note: references not cited:", ", ".join(unused))
    text = text.replace("<!-- REFERENCES -->", reflist)
    text = text.replace("<!-- TABLES -->", "\n\n".join([table1(), table2(), table3(), table4(), table5()]))
    (BUILD / "manuscript.md").write_text(text, encoding="utf-8")
    (BUILD / "additional_file_1_supplementary.md").write_text(supplementary(), encoding="utf-8")
    for name in ("strobe_checklist", "cherries_checklist"):
        shutil.copy(MS / "checklists" / f"{name}.md", BUILD / f"{name}.md")
    for fig in ("fig1_model", "fig2_item_distributions"):
        for ext in ("png", "pdf", "tiff"):
            shutil.copy(ROOT / "figures" / f"{fig}.{ext}", BUILD / f"{fig}.{ext}")
    if not shutil.which("pandoc"):
        print("pandoc not found; wrote Markdown only to", BUILD)
        return
    pandoc("manuscript.md", "manuscript.docx", line_numbers=True)
    pandoc("additional_file_1_supplementary.md", "additional_file_1_supplementary.docx")
    pandoc("strobe_checklist.md", "STROBE_checklist.docx")
    pandoc("cherries_checklist.md", "CHERRIES_checklist.docx")
    if (MS / "cover_letter.md").exists():
        shutil.copy(MS / "cover_letter.md", BUILD / "cover_letter.md")
        pandoc("cover_letter.md", "cover_letter.docx")
    print("Wrote submission files to", BUILD)


if __name__ == "__main__":
    main()
