"""Manuscript figures.

Run from the repository root after scripts 01-03:  python scripts/04_figures.py
Writes figures/fig1_model.png, figures/fig2_item_distributions.png (and .pdf).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})


def fig1_model():
    med = pd.read_csv(ROOT / "outputs" / "sem_mediation_wlsmv.csv")
    full = med[med.Sample == "Full sample"].set_index("Path")
    excl = med[med.Sample == "Excluding straight-liners"].set_index("Path")

    def lab(path):
        star = "" if full.loc[path, "p"] >= 0.05 else "***" if full.loc[path, "p"] < 0.001 else "*"
        return f"{full.loc[path, 'Std_estimate']:.2f}{star}\n[{excl.loc[path, 'Std_estimate']:.2f}]"

    fig, ax = plt.subplots(figsize=(7.2, 2.9))
    ax.set_xlim(0, 10); ax.set_ylim(0, 4.2); ax.axis("off")
    boxes = {"SP": (0.2, 2.3, "Strategic\nplanning\n(10 items)"),
             "CD": (3.9, 2.3, "Capacity\ndevelopment\n(5 items)"),
             "IR": (7.6, 2.3, "Institutional\nresilience\n(5 items)")}
    for x, y, text in boxes.values():
        ax.add_patch(FancyBboxPatch((x, y), 2.2, 1.5, boxstyle="round,pad=0.05", fc="#eef3f8", ec="#1f3b57", lw=1.2))
        ax.text(x + 1.1, y + 0.75, text, ha="center", va="center", fontsize=9)
    arrow = dict(arrowstyle="-|>", lw=1.3, color="#1f3b57", mutation_scale=12)
    ax.annotate("", xy=(3.85, 3.05), xytext=(2.45, 3.05), arrowprops=arrow)
    ax.annotate("", xy=(7.55, 3.05), xytext=(6.15, 3.05), arrowprops=arrow)
    ax.plot([1.3, 1.3, 8.7], [2.25, 1.45, 1.45], color="#7a8794", lw=1.1, ls="--")
    ax.annotate("", xy=(8.7, 2.25), xytext=(8.7, 1.45),
                arrowprops=dict(arrowstyle="-|>", lw=1.1, color="#7a8794", ls="--", mutation_scale=12))
    ax.text(3.15, 3.2, "a = " + lab("a"), ha="center", va="bottom", fontsize=8)
    ax.text(6.85, 3.2, "b = " + lab("b"), ha="center", va="bottom", fontsize=8)
    ax.text(5.0, 1.55, "c′ = " + lab("cp").replace("\n", "  "), ha="center", fontsize=8, color="#4a5560")
    ind = full.loc["ind"]
    ax.text(5.0, 0.7,
            f"Indirect a×b = {ind.Std_estimate:.2f} (95% Monte Carlo CI {ind.MC_CI_lower:.2f}–{ind.MC_CI_upper:.2f});"
            f"  R²(CD) = {full.loc['a', 'R2_CD']:.2f}, R²(IR) = {full.loc['a', 'R2_IR']:.2f}",
            ha="center", fontsize=8)
    ax.text(5.0, 0.2, "Standardised WLSMV estimates, full sample (N = 416); [ ] excluding straight-liners (n = 207). "
            "***p < 0.001", ha="center", fontsize=7, color="#4a5560")
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"fig1_model.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def fig2_distributions():
    df = pd.read_csv(ROOT / "data" / "sem_df.csv")
    items = [f"sp{i}" for i in range(1, 11)] + [f"cd{i}" for i in range(1, 6)] + [f"ir{i}" for i in range(1, 6)]
    cats = [("1–4", lambda s: s.le(4)), ("5", lambda s: s.eq(5)), ("6", lambda s: s.eq(6)), ("7", lambda s: s.eq(7))]
    colors = ["#c0504d", "#f2c48d", "#9dc3e6", "#1f4e79"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.2), gridspec_kw={"width_ratios": [3, 1.3]})
    ax = axes[0]
    left = pd.Series(0.0, index=items)
    for (lab, f), col in zip(cats, colors):
        vals = pd.Series({i: 100 * f(df[i]).mean() for i in items})
        ax.barh(items, vals, left=left, color=col, label=lab, height=0.75)
        left += vals
    ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("% of respondents (N = 416)")
    ax.legend(title="Response", ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=8)
    for y in (9.5, 14.5):
        ax.axhline(y, color="grey", lw=0.6)
    ax.set_title("a  Item responses", loc="left", fontsize=9, pad=24)

    ax = axes[1]
    n_seven = df[items].eq(7).sum(axis=1)
    ax.hist(n_seven, bins=[x - 0.5 for x in range(22)], color="#1f4e79", edgecolor="white")
    ax.set_xlabel("Items answered 7 (of 20)"); ax.set_ylabel("Respondents")
    ax.set_title("b  Ceiling responding", loc="left", fontsize=9, pad=24)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"fig2_item_distributions.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig1_model()
    fig2_distributions()
    print("figures written to", FIG)
