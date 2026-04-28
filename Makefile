.PHONY: up down logs test test-mobile test-web lint fmt migrate seed clean shell-api

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m src.scripts.seed

test:
	docker compose exec api pytest tests/ -v --cov=src --cov-report=term-missing

test-unit:
	docker compose exec api pytest tests/unit/ -v

test-mobile:
	cd mobile && flutter test --coverage

test-web:
	cd web && npm test -- --coverage

lint:
	docker compose exec api ruff check src/ tests/
	docker compose exec api mypy src/
	docker compose exec api lint-imports

fmt:
	docker compose exec api ruff format src/ tests/

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

shell-api:
	docker compose exec api bash

# Local dev (sin Docker, requiere .venv activo)
test-local:
	cd backend && pytest tests/unit/ -v

lint-local:
	cd backend && ruff check src/ tests/ && mypy src/ && lint-imports
