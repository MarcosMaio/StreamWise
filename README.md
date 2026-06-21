# StreamWise

**StreamWise** is a movie and series discovery platform with hybrid ML recommendations, vector search, TMDB live catalog, user auth, and Brazil streaming availability.

## Quick start (Docker)

Requires only **Docker** and **Docker Compose** — no local Python venv or npm install.

```bash
cp infra/.env.example infra/.env
# Edit infra/.env — set TMDB_API_KEY and JWT_SECRET

make init
```

Open:

- Web: http://localhost:3000
- API: http://localhost:8000/docs

### Commands

| Command | Description |
|---|---|
| `make init` | First-time bootstrap (up + TMDB sync) |
| `make up` | Start all services |
| `make down` | Stop services |
| `make sync` | Manual TMDB catalog sync |
| `make test-api` | Run API tests in container |
| `make logs` | Tail container logs |

### Architecture (containers)

```text
postgres ──► migrate (one-shot) ──► api ──► web
                  │                  ▲
                  └──► scheduler ────┘
                  └──► sync (one-shot, profile init)
```

## Documentation

| Resource | Description |
|---|---|
| [specs/001-streamwise/quickstart.md](specs/001-streamwise/quickstart.md) | Full Docker workflow |
| [docs/STREAMWISE-PLANNING.md](docs/STREAMWISE-PLANNING.md) | Product and architecture planning |
| [specs/001-streamwise/plan.md](specs/001-streamwise/plan.md) | Implementation plan |
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

## Legacy demo

The original **E-commerce Recommendation System** (TensorFlow.js) lives in [`legacy/`](legacy/).

## Branch

Active feature branch: `001-streamwise`
