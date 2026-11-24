.RECIPEPREFIX = >
.PHONY: up down logs pull-models test eval lint

up:
> docker compose up -d --build

down:
> docker compose down

logs:
> docker compose logs -f api bot

pull-models:
> sh infra/ollama/pull_models.sh

test:
> cd backend && pip install -e ".[dev]" && pytest

lint:
> cd backend && ruff check src tests

eval:
> cd backend && python -m daginquest.eval.run_eval --models $${MODELS:-qwen3:8b}
