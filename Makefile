.PHONY: install dev run

env:
	@if [ -f .env ]; then \
		echo ".env already exists"; \
	else \
		printf "TOGETHER_API_KEY=\nOPENAI_API_KEY=\n" > .env; \
		echo "Created .env"; \
	fi

install: env
	python3 -m venv env
	. env/bin/activate && python3 -m pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload

run: dev