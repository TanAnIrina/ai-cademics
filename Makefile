# AI-cademics — common tasks. Run `make help` for the list.

.DEFAULT_GOAL := help
.PHONY: help install backend frontend test lint build up down logs clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install backend (dev) and frontend dependencies
	cd backend && pip install -r requirements-dev.txt
	cd frontend && npm install

backend: ## Run the backend dev server on :8000
	cd backend && uvicorn app.main:app --reload --port 8000

frontend: ## Run the frontend dev server on :5173
	cd frontend && npm run dev

test: ## Run the backend test suite
	cd backend && python -m pytest

lint: ## Lint the backend with ruff
	cd backend && python -m ruff check .

build: ## Production build of the frontend
	cd frontend && npm run build

up: ## Build & start the full stack with docker compose (http://localhost:8080)
	docker compose up --build -d

down: ## Stop the docker compose stack
	docker compose down

logs: ## Tail docker compose logs
	docker compose logs -f

clean: ## Remove local build artifacts and the dev database
	rm -rf frontend/dist frontend/node_modules
	rm -f backend/aicademics.db backend/aicademics.db-*
	find backend -type d -name __pycache__ -prune -exec rm -rf {} +
