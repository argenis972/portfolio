.PHONY: dev-back dev-front test-back test-front test lint-back lint-front format-back lint

dev-back:
	cd backend && python -m uvicorn app.main:app --reload --port 8000

dev-front:
	cd frontend && npm run dev

test-back:
	cd backend && python -m pytest

test-front:
	cd frontend && npm run test

test: test-back test-front

lint-back:
	cd backend && ruff check . && mypy .

lint-front:
	cd frontend && npm run lint && npx tsc -b

format-back:
	cd backend && ruff format .

lint: lint-back lint-front
