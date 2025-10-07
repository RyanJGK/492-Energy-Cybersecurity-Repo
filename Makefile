PY ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PYBIN := $(VENV)/bin/python
DER := $(VENV)/bin/der-sim
UVICORN := $(VENV)/bin/uvicorn

.PHONY: help
help:
	@echo "Targets: setup-sim, run-sim, run-scenario, run-api, compose-up, compose-down, test"

$(VENV):
	$(PY) -m venv $(VENV)
	$(PYBIN) -m pip install -U pip setuptools wheel

.PHONY: setup-sim
setup-sim: $(VENV)
	$(PIP) install -e ".[sim]"

.PHONY: run-sim
run-sim: $(VENV)
	$(DER) powerflow --network ieee13

.PHONY: run-scenario
run-scenario: $(VENV) scenarios/sample_pv_curtail.json
	$(DER) scenario scenarios/sample_pv_curtail.json

.PHONY: run-api
run-api: $(VENV)
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

.PHONY: compose-up
compose-up:
	docker compose up -d

.PHONY: compose-down
compose-down:
	docker compose down -v

.PHONY: test
test: $(VENV)
	$(PYBIN) -m pytest -q
