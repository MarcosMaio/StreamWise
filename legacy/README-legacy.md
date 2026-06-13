# StreamWise

**StreamWise** is a movie and series discovery platform with hybrid ML recommendations, vector search, TMDB live catalog, user auth, and Brazil streaming availability.

This repository is being rebuilt from a course e-commerce TensorFlow.js demo into a professional portfolio monorepo.

## Documentation

| Resource | Description |
|----------|-------------|
| [docs/STREAMWISE-PLANNING.md](docs/STREAMWISE-PLANNING.md) | Full product and architecture planning |
| [specs/001-streamwise/quickstart.md](specs/001-streamwise/quickstart.md) | Local development setup |
| [specs/001-streamwise/plan.md](specs/001-streamwise/plan.md) | Implementation plan |
| [specs/001-streamwise/spec.md](specs/001-streamwise/spec.md) | Feature specification |
| [.specify/memory/constitution.md](.specify/memory/constitution.md) | Project governance |

## Monorepo layout

```text
apps/api/     FastAPI REST backend
apps/web/     Next.js frontend
ml/           Offline training and evaluation
jobs/         Background jobs (TMDB sync)
infra/        Docker Compose and env templates
legacy/       Original course e-commerce TF.js demo
specs/        Spec Kit artifacts
```

## Quick start

```bash
cp infra/.env.example infra/.env
docker compose -f infra/docker-compose.yml up -d postgres
cd apps/api && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Verify API: `http://localhost:8000/health` → `{"status":"ok"}`

See [specs/001-streamwise/quickstart.md](specs/001-streamwise/quickstart.md) for the full workflow.

## Legacy demo

The original **E-commerce Recommendation System** (TensorFlow.js in-browser training) lives in [`legacy/`](legacy/). Run it from that folder with `npm start`.

## Branch

Active feature branch: `001-streamwise`
