.PHONY: install run migrate migration test lint format shell clean

install:
		pip install -e ".[dev]"

run:
		uvicorn main:app --reload --host 0.0.0.0 --port 8000

migrate:
		alembic upgrade head

migration:
		alembic revision --autogenerate -m "$(message)"

test:
		pytest tests/ -v --cov=apps --cov-report=term-missing

lint:
	ruff check . && black --check . && isort --check-only .

format:
	black . && isort .

shell:
	python -c "import asyncio; from config.database import engine; print('DB connected')"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
