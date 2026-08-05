.PHONY: install venv config reset-config dev run test tests smoke catalog-check

PYTHON ?= python3
VENV := env
VENV_PYTHON := $(VENV)/bin/python
ENV_FILE := .env.local

install: venv config
	@echo "Looping Louie is ready."
	@echo "Run 'make dev' to start the API."

venv:
	@if [ ! -x "$(VENV_PYTHON)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv "$(VENV)"; \
	fi
	@"$(VENV_PYTHON)" -m pip install --upgrade pip
	@"$(VENV_PYTHON)" -m pip install -r requirements.txt

config: venv
	@if [ -f "$(ENV_FILE)" ]; then \
		echo "$(ENV_FILE) already exists; keeping its encryption key."; \
	else \
		echo "Creating $(ENV_FILE)..."; \
		ENCRYPTION_KEY="$$("$(VENV_PYTHON)" -c \
			'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"; \
		printf '%s\n' \
			"LOUIE_ENCRYPTION_KEY=$$ENCRYPTION_KEY" \
			'LOUIE_DB_PATH=.looping-louie/data/looping-louie.db' \
			'LOUIE_CATALOG_STRICT_VERSIONING=false' \
			> "$(ENV_FILE)"; \
		chmod 600 "$(ENV_FILE)"; \
		echo "Created $(ENV_FILE) with a generated encryption key."; \
	fi

reset-config: venv
	@echo "Replacing $(ENV_FILE) and its encryption key..."
	@rm -f "$(ENV_FILE)"
	@$(MAKE) --no-print-directory config
	@echo "Existing encrypted provider credentials can no longer be decrypted."

dev:
	@if [ ! -x "$(VENV_PYTHON)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "$(ENV_FILE) not found. Run 'make config' first."; \
		exit 1; \
	fi
	@set -a; \
	. "./$(ENV_FILE)"; \
	set +a; \
	exec "$(VENV_PYTHON)" -m uvicorn src.app.main:app --reload

run: dev

test tests: venv
	@"$(VENV_PYTHON)" -m pytest -q

catalog-check: venv
	@"$(VENV_PYTHON)" scripts/check_catalog.py

smoke: venv config
	@ENV_FILE="$(ENV_FILE)" ./scripts/smoke_api.sh
