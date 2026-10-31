.PHONY: help install dev api web core core-test wasm test test-agents typecheck lint up down clean

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Install Python and Node dependencies
	cd packages/agents && pip install -e ".[dev]"
	cd packages/web && npm install

api: ## Run the agents API on :8000
	cd packages/agents && uvicorn app.main:app --reload --port 8000

web: ## Run the web app on :5173
	cd packages/web && npm run dev

core: ## cargo check the Rust engine
	cd packages/core && cargo check

core-test: ## Run Rust engine tests
	cd packages/core && cargo test

wasm: ## Build the engine to WebAssembly (needs wasm-pack)
	cd packages/core && wasm-pack build --target web

test-agents: ## Run agents API tests
	cd packages/agents && python -m pytest -q

typecheck: ## Type-check the web app
	cd packages/web && npx tsc --noEmit

test: core-test test-agents typecheck ## Run all checks

up: ## Start the stack with Docker Compose
	docker compose up --build

down:
	docker compose down

clean:
	rm -rf packages/core/target packages/core/pkg packages/web/node_modules packages/web/dist
	find packages/agents -name __pycache__ -type d -prune -exec rm -rf {} +
