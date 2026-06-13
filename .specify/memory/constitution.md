# StreamWise Constitution

Governing principles and development guidelines for the StreamWise project — a movie and series discovery and recommendation platform. This document supersedes ad-hoc decisions during specification, planning, and implementation.

**Planning reference:** `docs/STREAMWISE-PLANNING.md`

---

## Core Principles

### I. Product Scope — Discovery Hub, Not a Player

StreamWise is a **discovery and recommendation platform**, not a video streaming service.

- Users browse trending and newly released titles, rate and like content, and receive personalized feeds.
- The platform shows **where to watch** (Netflix, Prime, Disney+, Max, etc.) via TMDB watch/providers for Brazil (`BR`).
- Video playback, DRM, and deep integration with streaming provider players are **explicitly out of scope**.
- Every feature must answer: *"What should I watch, where is it, and why does it fit me?"*

### II. Train/Serve Separation (NON-NEGOTIABLE)

Machine learning training and online serving MUST remain separate.

- **Training:** Python + TensorFlow/Keras, offline pipeline, versioned artifacts (`model_versions`).
- **Serving:** FastAPI loads pre-trained models; users never train models in the browser or at request time.
- **Catalog sync:** Scheduled jobs (cron/worker) ingest TMDB data independently of model training.
- Retraining runs on a schedule (weekly) or after a defined threshold of new platform interactions — never blocking user requests.

### III. Hybrid Recommendation Architecture

Recommendations MUST follow a two-stage hybrid pattern:

1. **Retrieval:** pgvector similarity search over title embeddings → top ~200 candidates.
2. **Ranking:** Two-Tower neural model scores user–title compatibility (0–1).
3. **Reranking:** Streaming affinity boost; MMR diversity reranking in P1+.

Do not replace the neural ranker with vector search alone, or brute-force score the entire catalog. The course-project pattern (encode user + item → MLP) evolves into Two-Tower; do not regress to in-browser training on static JSON.

### IV. Data Sources and Responsibilities

| Source | Role | Update frequency |
|---|---|---|
| **TMDB API** | Live catalog: trending, releases, metadata, BR streaming providers | Daily sync |
| **MovieLens 25M** | Collaborative filtering training data | Batch import |
| **StreamWise interactions** | Real user likes, ratings, affinity signals | Runtime + periodic retrain |

- TMDB is the **single external catalog API** for MVP.
- MovieLens provides historical training signal; TMDB `links.csv` / `tmdb_id` bridges datasets where applicable.
- Platform interactions (`like`, `rating ≥ 4` = positive) feed retraining after MVP launch.

### V. Scope Discipline — P0 Before P1 Before P2

Implementation MUST respect priority tiers defined in `docs/STREAMWISE-PLANNING.md`:

**P0 (MVP — required before calling the product "launchable"):**
- Auth, PostgreSQL + pgvector, Docker Compose
- TMDB daily sync (trending, releases, BR providers)
- Interactions: like, rating, watchlist, watched
- Onboarding: genres + streaming services
- Synopsis embeddings + similar-title search
- Two-Tower (MovieLens) + hybrid "For you" feed
- `user_streaming_affinity` boost (explicit onboarding + implicit from likes)
- README with architecture diagram

**P1 (StreamWise Plus):** MMR diversity, NL search, Tonight mode, explainability tags, ML metrics dashboard, series progress.

**P2 (advanced):** Trakt/CSV import, email digest, Multi-Armed Bandit, parental filters, price comparison, catalog diff.

No P1 or P2 feature may delay or block P0 completion. New scope requires updating the spec and this constitution via amendment.

### VI. ML Quality Gate

The MVP is not complete without measurable recommendation quality.

- Report **Precision@10** and **NDCG@10** on a held-out user set.
- Compare against at least two baselines: **TMDB popularity** and **content-only (pgvector)**.
- Document metrics in README and store summary in `model_versions.metrics`.
- Accuracy on training data alone is insufficient; holdout evaluation is mandatory.

### VII. Simplicity and YAGNI

Prefer a **maintainable monolith** over premature distribution.

- Local development: Docker Compose (API + PostgreSQL + frontend).
- No microservices, Kubernetes, or custom LLM training in MVP.
- No paid third-party APIs (e.g. RapidAPI streaming availability) until P2+ with justification.
- Single region for streaming providers in MVP: **Brazil (BR)**.
- Acceptable alternatives (Qdrant instead of pgvector, Vite instead of Next.js) require a documented amendment — default stack is FastAPI + PostgreSQL/pgvector + Next.js + Tailwind.

---

## Technology Constraints

### Required stack (default)

| Layer | Technology |
|---|---|
| API | FastAPI, OpenAPI documented |
| Database | PostgreSQL + pgvector |
| ML training | Python 3.11+, TensorFlow/Keras |
| Content embeddings | Sentence Transformers (synopsis → vectors) |
| Frontend | Next.js + Tailwind |
| Auth | JWT or NextAuth (email + Google OAuth) |
| Jobs | APScheduler or dedicated worker for TMDB sync |
| Model versioning | MLflow or DVC |
| Containers | Docker Compose |

### Repository structure (target)

```
apps/web/          # Next.js frontend
apps/api/          # FastAPI backend
ml/training/       # Offline training pipelines
ml/eval/           # Offline metrics scripts
infra/             # Docker, migrations, cron definitions
docs/              # Planning and architecture
specs/             # Spec Kit feature specifications
```

Legacy e-commerce TensorFlow.js code in the repo root is **deprecated**; new work lives under the structure above. Do not extend the old browser-training worker for production features.

### Security and secrets

- TMDB API keys and database credentials live in environment variables — never committed.
- Passwords hashed with industry-standard algorithms (bcrypt/argon2).
- Authenticated endpoints for all user-specific data (interactions, feed, profile).

---

## Development Workflow

### Spec-Driven Development (Spec Kit)

All major features follow the Spec Kit workflow:

1. `/speckit.constitution` — this document
2. `/speckit.specify` — functional requirements (what/why, not stack)
3. `/speckit.clarify` — resolve ambiguities before planning
4. `/speckit.plan` — technical design aligned with this constitution
5. `/speckit.tasks` — actionable, ordered tasks
6. `/speckit.analyze` — consistency check before implementation
7. `/speckit.implement` — execute tasks in priority order

Functional specs MUST NOT prescribe implementation details during `/speckit.specify`. Stack choices belong in `/speckit.plan`.

### Language and documentation

- **Code, commits, API schemas, and Spec Kit artifacts:** English.
- **User-facing UI copy:** English for MVP (i18n may come later).
- **README:** architecture diagram, setup instructions, ML metrics, and data pipeline overview are mandatory before MVP sign-off.

### Testing expectations

| Area | Requirement |
|---|---|
| API | Integration tests for auth, catalog, interactions, recommendations |
| ML | Offline eval script producing Precision@10, NDCG@10 vs baselines |
| Data pipeline | Smoke test for TMDB sync (mock or sandbox) |
| Frontend | Critical path tests for login and feed rendering (minimum) |

TDD for every line is not required; tests MUST cover contracts and ML quality gates defined above.

### Git and versioning

- Feature work on branches created via Spec Kit git extension (e.g. `001-streamwise`).
- Semantic commits preferred; constitution and spec changes committed with the feature they govern.
- Model artifacts versioned in `model_versions`, not overwritten without a version bump.

---

## Recommendation Behavior Rules

These rules encode product logic discussed in planning — implementations MUST comply:

1. **Cold start:** Trending catalog + onboarding genres/streaming services + optional seed titles; vector search until sufficient interaction history exists.
2. **Streaming affinity:** Update `user_streaming_affinity` when users like titles; boost candidates on high-affinity platforms.
3. **Filtering:** Exclude titles marked watched or disliked from "For you" unless explicitly requested.
4. **Explainability (P1+):** Each feed card includes at least one human-readable reason tag (genre match, platform, trending, similar title).
5. **Community signal:** Maintain `streamwise_avg_rating` and `like_count` on titles from platform interactions, distinct from TMDB scores.

---

## Explicitly Out of Scope (MVP)

The following are forbidden in P0 unless this constitution is amended:

- Video playback or embedded streaming players
- Microservices architecture or Kubernetes deployment
- Training custom LLMs for recommendations
- Multi-country provider catalogs beyond BR
- Full social network (follow friends, activity feed)
- Native mobile apps before web MVP is complete
- Real-time model training triggered by single user likes

---

## Governance

### Authority

This constitution is the highest-level technical and product constraint document for StreamWise. When `spec.md`, `plan.md`, or implementation conflicts with this file, **this constitution wins** until formally amended.

### Amendment process

1. Document the proposed change and rationale.
2. Update `docs/STREAMWISE-PLANNING.md` if scope or priorities shift.
3. Revise this file with incremented **Version** and **Last Amended** date.
4. Re-run `/speckit.analyze` on active specs if the change affects in-flight work.

### Compliance

- `/speckit.plan` and `/speckit.tasks` MUST reference P0/P1/P2 tiers.
- `/speckit.implement` MUST NOT introduce out-of-scope items without a spec update.
- Complexity beyond this document (new services, datasets, or models) requires written justification in the plan's `research.md`.

### Runtime guidance

For day-to-day development context (stack details, shell commands, current plan), agents SHOULD read:

- `docs/STREAMWISE-PLANNING.md`
- Active feature directory under `specs/`
- `.cursor/rules/specify-rules.mdc`

---

**Version**: 1.0.0 | **Ratified**: 2026-06-11 | **Last Amended**: 2026-06-11
