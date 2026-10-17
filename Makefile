# Reproduce all outputs, figures and submission files from data/sem_df.csv.
# Step 1 (data/sem_df.csv from the raw export) needs the raw file:  make data RAW=path/to/export.csv
PY ?= python3
COMMITTED ?= /tmp/outputs_committed

.PHONY: all analysis figures manuscript check data install

all: analysis figures manuscript

install:
	$(PY) -m pip install -r requirements.txt
	Rscript scripts/install_r_packages.R

data:
	$(PY) scripts/01_prepare_data.py $(RAW)

analysis:
	$(PY) scripts/02_descriptives_mediation.py
	Rscript scripts/03_cfa_sem.R

figures:
	$(PY) scripts/04_figures.py

manuscript:
	$(PY) scripts/05_build_manuscript.py

check:
	$(PY) tests/check_reproducibility.py $(COMMITTED)
