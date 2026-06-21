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
NEXT_PUBLIC_API_URL=http://localhost:8000
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

- API health: `curl http://localhost:8000/health` → `{"status":"ok"}`
- Docs: http://localhost:8000/docs
- Web: http://localhost:3000

## 3. Day-to-day commands

```bash
make up          # start stack (re-runs migrate if needed)
make down        # stop all services
make logs        # tail logs
make sync        # manual TMDB catalog refresh
make test-api    # run API tests inside container
make eval        # offline ML evaluation (MovieLens holdout)
make clean       # stop and remove volumes (destructive)
```

Equivalent without Make:

```bash
docker compose -f infra/docker-compose.yml up --build -d
docker compose -f infra/docker-compose.yml --profile init run --rm sync
```

## 4. First user journey

1. Register at http://localhost:3000/register
2. Complete onboarding (genres + streaming platforms)
3. Browse **Trending** / **New releases** on home
4. Open a title → like / watchlist / rate
5. Check **For you** feed and **Profile** (`/profile`)

## 5. ML training (optional, host Python)

MovieLens import and Two-Tower training are offline jobs under `ml/training/`.

```bash
cd ml/training
pip install -e .
python import_movielens.py --output-dir ../../ml/artifacts/movielens
python train_two_tower.py --config config.yaml
```

Artifacts are written to `ml/artifacts/` and mounted read-only into the API container.

## 6. ML evaluation (P0 quality gate)

From the repository root (after MovieLens import):

```bash
make eval
```

Or on the host:

```bash
python ml/eval/evaluate.py
python ml/eval/evaluate.py --with-db-checks --publish
```

Outputs:

- `ml/artifacts/eval/metrics.json` — Precision@10, Recall@10, NDCG@10, Coverage
- Optional DB checks for SC-004 (platform affinity) and SC-005 (genre overlap)
- Optional publish step merges metrics into `model_versions.metrics`

See [README.md](../../README.md) for architecture diagram and metrics table placeholders.

## Typical workflow

1. `make init` on first clone
2. Register → onboarding → browse catalog
3. After code changes → `make build && make up`
4. Manual catalog refresh → `make sync`
5. Before MVP sign-off → `make eval` and update README metric table

## Troubleshooting

| Issue | Fix |
|---|---|
| `migrate` fails | Check postgres logs: `docker compose -f infra/docker-compose.yml logs postgres` |
| TMDB 401 / sync empty | Verify `TMDB_API_KEY` in `infra/.env`, then `make sync` |
| Web can't reach API | Ensure `NEXT_PUBLIC_API_URL=http://localhost:8000` in `infra/.env` |
| Empty home feed | Run `make sync` to populate titles |
| Eval script missing data | Run `ml/training/import_movielens.py` first |
| Port conflict | Set `API_PORT`, `WEB_PORT`, or `POSTGRES_PORT` in `infra/.env` |

## Key paths

| Artifact | Path |
|---|---|
| Spec | `specs/001-streamwise/spec.md` |
| Plan | `specs/001-streamwise/plan.md` |
| API contract | `specs/001-streamwise/contracts/openapi.yaml` |
| Docker compose | `infra/docker-compose.yml` |
| Makefile | `Makefile` |
| ML eval | `ml/eval/evaluate.py` |
