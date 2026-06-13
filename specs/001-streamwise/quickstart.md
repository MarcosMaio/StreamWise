# Quickstart: StreamWise Local Development

**Feature**: `001-streamwise` | **Date**: 2026-06-11

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- TMDB API key ([themoviedb.org](https://www.themoviedb.org/settings/api))
- (Optional) GPU for faster embedding/training — CPU works for dev subsets

## 1. Clone and configure environment

```bash
cp infra/.env.example infra/.env
```

Edit `infra/.env`:

```env
DATABASE_URL=postgresql+asyncpg://streamwise:streamwise@localhost:5432/streamwise
TMDB_API_KEY=your_key_here
JWT_SECRET=change-me-in-production
MODEL_PATH=ml/artifacts/two_tower/v1
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 2. Start infrastructure

```bash
docker compose -f infra/docker-compose.yml up -d postgres
```

PostgreSQL initializes with pgvector extension via `infra/postgres/init.sql`.

## 3. API setup

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # or copy DATABASE_URL from infra/.env
alembic upgrade head
python scripts/seed_genres_providers.py
uvicorn app.main:app --reload --port 8000
```

Verify: `http://localhost:8000/health` → `{"status":"ok"}`

OpenAPI docs: `http://localhost:8000/docs`

## 4. Run TMDB catalog sync (first load)

```bash
cd jobs/tmdb_sync
source ../../apps/api/.venv/bin/activate
python sync_catalog.py --region BR
```

Populates `titles`, `streaming_providers`, and triggers embedding generation.

## 5. Import MovieLens subset (training bootstrap)

```bash
cd ml/training
python import_movielens.py --data-dir ./data/ml-25m --sample 100000
python generate_embeddings.py
python train_two_tower.py --config config.yaml
```

Full 25M import optional; use `--sample` for faster dev iteration.

## 6. Evaluate model (constitution quality gate)

```bash
cd ml/eval
python evaluate.py --model ../artifacts/two_tower/v1 --k 10
```

Expect output: Precision@10, NDCG@10 vs popularity and content baselines.

## 7. Frontend setup

```bash
cd apps/web
npm install
npm run dev
```

Open: `http://localhost:3000`

## 8. Full stack via Docker Compose (optional)

```bash
docker compose -f infra/docker-compose.yml up --build
```

Services: `postgres`, `api`, `web`, `scheduler` (daily TMDB sync).

## Typical dev workflow

1. Change API code → auto-reload via uvicorn
2. Change schema → create Alembic revision → `alembic upgrade head`
3. After TMDB sync → check `GET /catalog/trending`
4. Register user → complete onboarding → like titles → `GET /recommendations/for-you`

## Running tests

```bash
# API integration tests
cd apps/api && pytest tests/ -v

# ML eval (not unit tests — offline metrics)
cd ml/eval && python evaluate.py
```

## Key paths

| Artifact | Path |
|---|---|
| Spec | `specs/001-streamwise/spec.md` |
| Plan | `specs/001-streamwise/plan.md` |
| API contract | `specs/001-streamwise/contracts/openapi.yaml` |
| Constitution | `.specify/memory/constitution.md` |
| Planning doc | `docs/STREAMWISE-PLANNING.md` |

## Troubleshooting

| Issue | Fix |
|---|---|
| pgvector extension missing | Re-run `infra/postgres/init.sql` or recreate volume |
| TMDB 401 | Check `TMDB_API_KEY` in `.env` |
| Empty "For you" feed | Ensure model artifact exists and user has likes or completed onboarding |
| Slow embedding generation | Use MovieLens/title subset; run batch overnight |

## Next Spec Kit step

```text
/speckit.tasks
```

Generates `specs/001-streamwise/tasks.md` from this plan.
