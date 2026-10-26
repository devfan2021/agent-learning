.PHONY: install chat serve eval db-up db-down logs

install:
	uv sync

chat:
	uv run python -m scripts.chat

serve:
	uv run uvicorn app.main:app --reload --port 8000

eval:
	uv run python -m evals.run

db-up:
	docker compose up -d db

db-down:
	docker compose down

logs:
	docker compose logs -f app
