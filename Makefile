# StreamWise Docker commands (run from repo root or infra/)
COMPOSE = docker compose -f infra/docker-compose.yml

.PHONY: help up down build logs ps sync test-api eval retrain test-e2e clean

help:
	@echo "StreamWise — Docker workflow"
	@echo ""
	@echo "  make up        Build and start all services (postgres, migrate, api, web, scheduler)"
	@echo "  make sync      Run one-shot TMDB catalog sync (requires stack up)"
	@echo "  make init      up + sync (full first-time bootstrap)"
	@echo "  make down      Stop all services"
	@echo "  make build     Rebuild images"
	@echo "  make logs      Tail logs (all services)"
	@echo "  make ps        Show running containers"
	@echo "  make test-api  Run API integration tests in container"
	@echo "  make eval      Run offline ML evaluation (MovieLens holdout)"
	@echo "  make retrain   Run full retrain pipeline (MovieLens + platform likes)"
	@echo "  make test-e2e  Run Playwright smoke test (stack must be up)"
	@echo "  make clean     Stop and remove volumes (destructive)"

up:
	$(COMPOSE) up --build -d

init: up
	$(COMPOSE) --profile init run --rm sync

sync:
	$(COMPOSE) --profile init run --rm sync

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

test-api:
	$(COMPOSE) --profile test run --rm test-api

eval:
	$(COMPOSE) --profile eval run --rm --no-deps eval

retrain:
	$(COMPOSE) --profile retrain run --rm retrain

test-e2e:
	cd apps/web && npm install && npx playwright install chromium
	cd apps/web && PLAYWRIGHT_SKIP_WEBSERVER=1 npm run test:e2e

clean:
	$(COMPOSE) down -v
