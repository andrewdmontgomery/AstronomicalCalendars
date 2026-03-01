PYTHON := python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
SKILL_VALIDATOR := /Users/andrew/.codex/skills/.system/skill-creator/scripts/quick_validate.py

.PHONY: help venv install test validate-skills run

help:
	@printf "Targets:\n"
	@printf "  make venv             Create the local Python virtual environment\n"
	@printf "  make install          Install pinned Python dependencies into .venv\n"
	@printf "  make test             Run the Python test suite\n"
	@printf "  make validate-skills  Validate all local skills using the skill validator\n"
	@printf "  make run YEAR=2026 CALENDAR=astronomy-all  Run the pipeline CLI\n"

$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)

venv: $(VENV)/bin/activate

install: $(VENV)/bin/activate requirements-dev.txt
	$(VENV_PIP) install -r requirements-dev.txt

test: $(VENV)/bin/activate
	PYTHONPATH=src $(VENV_PYTHON) -m pytest

validate-skills: $(VENV)/bin/activate
	$(VENV_PYTHON) $(SKILL_VALIDATOR) skills/source-astronomy-events
	$(VENV_PYTHON) $(SKILL_VALIDATOR) skills/source-planetary-events
	$(VENV_PYTHON) $(SKILL_VALIDATOR) skills/reconcile-event-catalog
	$(VENV_PYTHON) $(SKILL_VALIDATOR) skills/build-ical-calendar

run: $(VENV)/bin/activate
	PYTHONPATH=src $(VENV_PYTHON) -m astronomical_calendars run --calendar $(CALENDAR) --year $(YEAR)
