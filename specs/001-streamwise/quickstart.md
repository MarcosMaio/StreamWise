# Quickstart: StreamWise Local Development

**Feature**: `001-streamwise` | **Date**: 2026-06-11

## Prerequisites

- Docker & Docker Compose v2+
- TMDB API key ([themoviedb.org](https://www.themoviedb.org/settings/api))

No local Python venv or Node install required for the default workflow.

## 1. Configure environment

```bash
cp infra/.env.example infra/.env
```

Edit `infra/.env` and set at minimum:

```env
TMDB_API_KEY=your_key_here
JWT_SECRET=change-me-in-production
```

## 2. Start the full stack (Docker)

From the repository root:

```bash
make init
```

This will:

1. Build all images (api, web, scheduler)
2. Start **postgres** and run **migrate** (Alembic + seed)
3. Start **api** (FastAPI) and **web** (Next.js)
4. Start **scheduler** (TMDB daily sync at 06:00 UTC)
5. Run a one-shot **sync** to populate the catalog

### Services

| Container | Responsibility |
|---|---|
| `streamwise-postgres` | PostgreSQL 16 + pgvector |
| `streamwise-migrate` | One-shot: migrations + genre/provider seed |
| `streamwise-api` | REST API (port 8000) |
| `streamwise-web` | Next.js UI (port 3000) |
| `streamwise-scheduler` | Background TMDB sync cron |
| `streamwise-sync` | One-shot catalog sync (`--profile init`) |

Verify:

- API: `http://localhost:8000/health` → `{"status":"ok"}`
- Docs: `http://localhost:8000/docs`
- Web: `http://localhost:3000`

## 3. Day-to-day commands

```bash
make up          # start stack (re-runs migrate if needed)
make down        # stop all services
make logs        # tail logs
make sync        # manual TMDB catalog refresh
make test-api    # run API tests inside container
make clean       # stop and remove volumes (destructive)
```

Equivalent without Make:

```bash
docker compose -f infra/docker-compose.yml up --build -d
docker compose -f infra/docker-compose.yml --profile init run --rm sync
```

## 4. ML training (optional, host or future ML container)

MovieLens import and Two-Tower training remain offline jobs under `ml/`. These can run on the host with Python or be containerized in a later phase.

```bash
cd ml/training
python import_movielens.py --data-dir ./data/ml-25m --sample 100000
python train_two_tower.py --config config.yaml
```

## Typical workflow

1. `make init` on first clone
2. Register at `http://localhost:3000` → browse trending/new releases
3. After code changes → `make build && make up`
4. Manual catalog refresh → `make sync`

## Troubleshooting

| Issue | Fix |
|---|---|
| `migrate` fails | Check postgres logs: `docker compose -f infra/docker-compose.yml logs postgres` |
| TMDB 401 / sync empty | Verify `TMDB_API_KEY` in `infra/.env`, then `make sync` |
| Web can't reach API | Ensure `NEXT_PUBLIC_API_URL=http://localhost:8000` in `infra/.env` |
| Empty home feed | Run `make sync` to populate titles |
| Port conflict | Set `API_PORT`, `WEB_PORT`, or `POSTGRES_PORT` in `infra/.env` |

## Key paths

| Artifact | Path |
|---|---|
| Spec | `specs/001-streamwise/spec.md` |
| Plan | `specs/001-streamwise/plan.md` |
| API contract | `specs/001-streamwise/contracts/openapi.yaml` |
| Docker compose | `infra/docker-compose.yml` |
| Makefile | `Makefile` |
