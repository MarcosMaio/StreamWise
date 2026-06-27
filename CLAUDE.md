# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

StreamWise is a movie/series discovery platform (not a video player): TMDB-synced catalog, auth, community ratings, and a hybrid recommender (pgvector retrieval + Two-Tower ranking) personalized by likes and inferred streaming-platform affinity (Netflix, Prime, etc., Brazil region only for MVP).

Governing rules live in `.specify/memory/constitution.md` — read it before making architectural changes. Key non-negotiables from it:
- **Train/serve separation**: training (TensorFlow, offline, `ml/training/`) never happens inside the FastAPI request path. The API only loads versioned artifacts (`model_versions`).
- **Recommendation pipeline is two-stage**: pgvector similarity retrieval (~200 candidates) → Two-Tower ranking → streaming-affinity boost / MMR rerank. Don't replace the ranker with pure vector search or brute-force the whole catalog.
- **Single region (BR)**, single external catalog source (TMDB) for MVP — don't add other providers without a constitution amendment.
- P0/P1/P2 scope tiers are defined in `docs/STREAMWISE-PLANNING.md`; P1/P2 work must never block or delay P0.

Product/feature spec artifacts (Spec Kit) for the active feature live under `specs/001-streamwise/`: `spec.md`, `plan.md`, `data-model.md`, `research.md`, `quickstart.md`, `contracts/openapi.yaml`. Treat `contracts/openapi.yaml` as the source of truth for the REST contract.

## Monorepo layout

```
apps/api/     FastAPI REST backend (Python 3.11+)
apps/web/     Next.js 14 frontend (App Router, TypeScript, Tailwind)
ml/training/  Offline training pipelines (Two-Tower, MovieLens import, embeddings)
ml/eval/      Offline metrics / quality-gate scripts (Precision@10, NDCG@10 vs baselines)
jobs/         Background jobs: jobs/tmdb_sync (daily catalog sync), jobs/email (weekly digest)
infra/        Docker Compose, Postgres init, env templates
legacy/       Deprecated TF.js course demo — do not extend for production features
specs/        Spec Kit feature artifacts
```

## Commands

Everything is designed to run via Docker Compose from the repo root; there is no need for a local Python venv or `npm install` unless iterating directly inside `apps/api` or `apps/web`.

```bash
cp infra/.env.example infra/.env   # set TMDB_API_KEY and JWT_SECRET first
make init        # first-time bootstrap: up + TMDB sync
make up          # start all services (postgres, migrate, api, web, scheduler)
make down        # stop services
make build       # rebuild images
make logs        # tail all container logs
make sync        # one-shot TMDB catalog sync (stack must be up)
make test-api    # run API integration tests inside the container
make test-e2e    # Playwright smoke test (requires stack up; installs web deps + browsers)
make eval        # offline ML evaluation (MovieLens holdout) via the eval container
make retrain     # full retrain pipeline (MovieLens + platform likes) via the retrain container
make clean       # stop services and remove volumes (destructive)
```

Web: http://localhost:3000 — API + interactive docs: http://localhost:8000/docs

### Working inside `apps/api` directly (host Python)

```bash
cd apps/api
pip install -e ".[dev]"
pytest                                   # full suite (testpaths = tests, asyncio_mode = auto)
pytest tests/integration/test_catalog.py # single file
pytest tests/integration/test_catalog.py::test_name  # single test
ruff check .                             # lint (line-length 100, py311)
alembic upgrade head                     # apply migrations (apps/api/alembic/versions)
```

### Working inside `apps/web` directly

```bash
cd apps/web
npm install
npm run dev      # next dev
npm run build
npm run lint     # next lint
npm run test:e2e # playwright test (PLAYWRIGHT_SKIP_WEBSERVER=1 if stack already up)
```

### ML training/eval on host

```bash
cd ml/training && pip install -e .
python import_movielens.py --output-dir ../../ml/artifacts/movielens
python train_two_tower.py --config config.yaml
python ../eval/evaluate.py                          # from repo root: python ml/eval/evaluate.py
python ml/eval/evaluate.py --publish --with-db-checks
python ml/training/retrain_pipeline.py               # equivalent to `make retrain`
```

Retrain pipeline steps: export platform likes → merge with MovieLens → train Two-Tower → export embeddings → register `model_versions`. MLflow runs land in `ml/artifacts/mlruns/` (config: `ml/mlflow/config.yaml`). Scheduler runs this weekly (Sun 07:00 UTC).

## Architecture

```
postgres ──► migrate (one-shot) ──► api ──► web
                  │                  ▲
                  └──► scheduler ────┘
                  └──► sync (one-shot, profile init)
```

- **`apps/api/app/`**: standard FastAPI layering — `routers/` (HTTP layer) → `services/` (business logic) → `models/` (SQLAlchemy ORM) → `schemas/` (Pydantic I/O). `db/session.py` + `db/base.py` set up the async SQLAlchemy engine; migrations are Alembic (`apps/api/alembic/versions`, numbered sequentially — pgvector enablement is `001`).
- **Recommendation flow** (`app/services/recommendation_service.py`): `_retrieve_candidates` (pgvector top-~200 via `vector_search_service.py`) → falls back to `_trending_fallback` on cold start → `apply_session_context` (Tonight mode) → `parental_filter_service` → `_rank_candidates` (Two-Tower via `model_loader.py`, blended with streaming-affinity boost, `STREAMING_BOOST_ALPHA = 0.3`) → `mmr_reranker.py` for diversity → `explainability_service.py` attaches reason tags. `bandit_service.py` adds P2 multi-armed-bandit exploration.
- **Catalog sync** (`jobs/tmdb_sync/`): `sync_catalog.py` is the daily ETL entrypoint (run by `scheduler.py` or the one-shot `sync` Compose service/profile); `diff_catalog.py` and `snapshot_providers.py` support catalog-diff and provider-price features; status is written to `last_sync_status.json` (shared via the `tmdb_sync_status` volume).
- **Auth**: JWT-based (`app/core/jwt.py`, `app/core/security.py`, `app/dependencies/auth.py`); all user-specific routes require `Authorization: Bearer <access_token>`.
- **Rate limiting**: `app/middleware/rate_limit.py`, configured per-route-class (auth vs. search) via settings.
- **ML model loading**: `model_loader.py` loads versioned artifacts referenced by the `model_versions` table — never trains at request time (train/serve separation above).
- **Frontend** (`apps/web/src/`): Next.js App Router with route groups `(auth)` and `(main)`, plus `explore/`, `titles/`, `onboarding/`, `profile/`, `continue/`, `admin/`. `src/lib/*.ts` are typed API client wrappers per domain (catalog, recommendations, interactions, profile, admin, auth); `src/middleware.ts` handles auth/session routing at the edge.
- **Docker images**: `apps/api/Dockerfile` and `apps/web/Dockerfile` build the long-running services; `jobs/tmdb_sync/Dockerfile` and `ml/eval/Dockerfile` build one-shot job images, all orchestrated by `infra/docker-compose.yml` via Compose profiles (`init`, `test`, `eval`, `retrain`).

## Notes

- `legacy/` is a deprecated TensorFlow.js e-commerce demo unrelated to current architecture — do not extend it for new features.
- API contract changes must stay in sync with `specs/001-streamwise/contracts/openapi.yaml`.
- Quality gates (SC-004 through SC-007 in the constitution) are tracked via `ml/eval/evaluate.py` output and `model_versions.metrics` — don't claim a recommendation change is an improvement without re-running `make eval`.
