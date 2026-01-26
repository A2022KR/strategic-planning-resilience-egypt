# Strategic Planning and Institutional Resilience in Egypt — Replication Package

This repository contains replication materials (code, outputs, and an anonymised dataset) for the study:
**“Strategic Planning and Institutional Resilience in Egypt’s Public Health Sector”**.

## Contents
- `data/` — anonymised analytic dataset (item-level indicators only) and codebook
- `notebooks/` — Google Colab / Jupyter notebook used for the main analyses
- `scripts/` — helper scripts (Python and R) for CFA (WLSMV), HTMT, and mediation
- `outputs/` — tables and figures reported in the manuscript

## Software
- Python (Google Colab), 주요 packages: pandas, numpy, statsmodels, pingouin
- R (optional): lavaan, semTools (for ordinal CFA using WLSMV)

## Reproducibility
1. Open `notebooks/analysis_colab.ipynb` in Google Colab.
2. Run cells in order to reproduce descriptive statistics, reliability, CFA, HTMT, and mediation analyses.

## Data and ethics
This repository includes **code and an anonymised dataset** sufficient to reproduce the analyses reported in the manuscript.

To protect participant confidentiality, the shared dataset excludes direct identifiers and potentially identifying fields (e.g., timestamps, names, contact details, free-text responses such as job titles and “other/specify” entries). The dataset contains only the analytic variables required for replication (e.g., item-level indicators and non-identifying categorical demographics where applicable).

## Citation
If you use these materials, please cite the associated article (citation to be added upon publication).
