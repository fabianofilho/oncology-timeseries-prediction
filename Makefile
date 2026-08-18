PYTHON ?= python3
PIP ?= pip
VENV ?= .venv
ACTIVATE = . $(VENV)/bin/activate

UF ?= SP
YEARS ?= 2010-2023

.PHONY: venv setup-base setup-full extract-sim validate benchmark uncertainty test

venv:
	$(PYTHON) -m venv $(VENV)

setup-base: venv
	$(ACTIVATE) && $(PIP) install --upgrade pip
	$(ACTIVATE) && $(PIP) install -r requirements.txt

setup-full: setup-base
	$(ACTIVATE) && $(PIP) install -r requirements-optional.txt

extract-sim:
	$(ACTIVATE) && PYTHONPATH=src $(PYTHON) scripts/extract_sim_real.py \
		--uf $(UF) \
		--years $(YEARS) \
		--cid-prefix C \
		--raw-output data/raw/sim_onco_$(UF)_$(YEARS).csv \
		--series-output results/series/serie_onco_$(UF)_sim_real_$(YEARS).csv \
		--meta-output data/processed/sim_onco_extraction_metadata.json

validate:
	$(ACTIVATE) && PYTHONPATH=src $(PYTHON) scripts/validate_real_dataset.py \
		--raw-csv data/raw/sim_onco_$(UF)_$(YEARS).csv \
		--series-csv results/series/serie_onco_$(UF)_sim_real_$(YEARS).csv \
		--meta-json data/processed/sim_onco_extraction_metadata.json \
		--expected-cid-prefix C \
		--min-series-points 120 \
		--report-output results/data_reality_report_$(YEARS).json

benchmark:
	$(ACTIVATE) && PYTHONPATH=src $(PYTHON) scripts/run_benchmark.py \
		--input-csv results/series/serie_onco_$(UF)_sim_real_$(YEARS).csv \
		--date-col date \
		--value-col value \
		--freq MS \
		--horizon 6 \
		--min-train-size 60 \
		--models sarima,prophet,timesfm \
		--output-prefix results/benchmark_onco_$(UF)_$(YEARS)

uncertainty:
	$(ACTIVATE) && PYTHONPATH=src $(PYTHON) scripts/run_uncertainty.py \
		--predictions-csv results/benchmark_onco_$(UF)_$(YEARS)_predictions.csv \
		--models sarima,prophet,timesfm \
		--output-prefix results/uncertainty_onco_$(UF)_$(YEARS)

test:
	$(ACTIVATE) && PYTHONPATH=src $(PYTHON) -m pytest
