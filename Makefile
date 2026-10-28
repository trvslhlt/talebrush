.DEFAULT_GOAL := help
.PHONY: help up down logs build test control-check sketch-check clean check-env

COMPOSE := docker compose
URL := http://localhost:7082/talebrush

help: ## List the available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  make %-14s %s\n", $$1, $$2}'

check-env:
	@test -f .env || { echo "Missing .env. Run: cp .env.example .env, then add your ANTHROPIC_API_KEY."; exit 1; }
	@grep -qE '^ANTHROPIC_API_KEY=.+' .env || { echo "ANTHROPIC_API_KEY is empty in .env."; exit 1; }

up: check-env ## Build if needed and start TaleBrush
	$(COMPOSE) up -d --build --wait
	@echo "\nTaleBrush is running at $(URL)"

down: ## Stop TaleBrush
	$(COMPOSE) down

logs: ## Follow the logs of both services
	$(COMPOSE) logs -f

build: ## Rebuild the images
	$(COMPOSE) build

test: check-env ## Check the backend's API contract (a few real model calls)
	$(COMPOSE) exec -T backend python - < TaleBrush_Backend/tests/contract_test.py

control-check: check-env ## Check that fortune targets steer generation (about 30 requests)
	$(COMPOSE) exec -T backend python - < TaleBrush_Backend/tests/control_check.py

sketch-check: check-env ## Replay a 5-sentence sketch through the interface, timing each step
	$(COMPOSE) exec -T interface python - < TaleBrush_Interface/tests/sketch_check.py

clean: ## Remove containers, images and the event-log volume
	$(COMPOSE) down --volumes --rmi local
