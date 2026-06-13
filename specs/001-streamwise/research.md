# Research: StreamWise Platform

**Feature**: `001-streamwise` | **Date**: 2026-06-11

Consolidated technology decisions for implementation planning. All items resolved — no open NEEDS CLARIFICATION markers.

---

## 1. Catalog and streaming metadata API

**Decision**: TMDB API v3 as the single catalog source for MVP.

**Rationale**:
- Free tier sufficient for portfolio/dev with rate limiting and caching
- Endpoints cover trending, now_playing, on_the_air, title details, and `watch/providers` for Brazil
- `links.csv` from MovieLens maps `movieId` → `tmdb_id` for training enrichment

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| OMDb | No trending/sync endpoints; supplement only |
| RapidAPI Streaming Availability | Paid; TMDB providers adequate for MVP |
| Trakt | OAuth complexity; defer to P2 for watchlist import |

**Integration pattern**: Dedicated `jobs/tmdb_sync/` worker; store `tmdb_id` as external key; upsert idempotent on daily cron.

---

## 2. Vector storage and similarity search

**Decision**: PostgreSQL 16 + pgvector extension; 384-dim vectors from `all-MiniLM-L6-v2`.

**Rationale**:
- Constitution mandates pgvector; avoids second database to operate
- Cosine similarity via `<=>` operator; IVFFlat index for MVP scale (~10k–60k titles)
- Separate columns: `content_vector` (synopsis) and `model_vector` (Two-Tower item tower output)

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| Qdrant | Valid but adds infra; pgvector sufficient for MVP |
| In-memory brute force | Does not scale; course project anti-pattern |

**Best practice**: Normalize embeddings before storage; rebuild IVFFlat after bulk insert.

---

## 3. Recommendation model architecture

**Decision**: Two-Tower neural network (TensorFlow/Keras); hybrid inference with retrieval + rank.

**Rationale**:
- Evolves course project concat-MLP into industry-standard recsys pattern
- User tower: user_id embedding + genre prefs + streaming affinity vector + aggregated like history
- Item tower: title_id embedding + genre multi-hot + year normalized + synopsis embedding projection + provider multi-hot
- Score: dot product + sigmoid (binary like prediction) or cosine on tower outputs

**Training data**:
- Primary: MovieLens 25M ratings (rating ≥ 4 → positive, ≤ 2 → negative)
- Fine-tune: StreamWise `interactions` after sufficient volume
- Bridge: enrich MovieLens movies with TMDB metadata where `links.csv` matches

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| In-browser TensorFlow.js | Violates constitution train/serve split |
| Pure content-based only | Misses collaborative signal (spec FR-020) |
| Matrix factorization only | Weaker portfolio story vs Two-Tower + vectors |

**Serving**: Load `.keras` or SavedModel in API process; score top-K candidates only (~200).

---

## 4. Streaming affinity inference

**Decision**: Recompute `user_streaming_affinity` as normalized counts of liked titles per provider; apply multiplicative boost at rerank (α = 0.3).

**Rationale**:
- Matches product spec and planning doc worked example
- Explicit onboarding selections initialize affinity; implicit likes refine it
- Simple, explainable, no extra model required for MVP

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| Learn affinity in Two-Tower only | Harder to debug/explain for portfolio demo |
| Real-time graph propagation | Over-engineered for MVP |

---

## 5. Authentication

**Decision**: Email/password with bcrypt hashes + JWT access tokens (15 min) and refresh tokens (7 days); optional Google OAuth via NextAuth → API token exchange.

**Rationale**:
- Spec FR-001, FR-002; standard web app pattern
- FastAPI validates JWT on protected routes; Next.js stores session via httpOnly cookie pattern

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| Session-only cookies without API tokens | Complicates Next.js ↔ FastAPI separation |
| Auth0 | External dependency; overkill for portfolio |

---

## 6. Frontend framework

**Decision**: Next.js 14 App Router + Tailwind CSS + shadcn/ui components.

**Rationale**:
- Constitution default stack; SSR for SEO on public landing; strong portfolio signal
- App Router colocates pages: `/`, `/titles/[id]`, `/onboarding`, `/profile`, `/explore`

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| Extend legacy vanilla JS | Does not meet professional restructuring goal |
| Vite + React SPA | Acceptable per constitution but Next.js preferred |

---

## 7. ML operations and evaluation

**Decision**: MLflow (local file store) for model versioning; `ml/eval/evaluate.py` for offline metrics.

**Rationale**:
- Constitution ML quality gate requires Precision@10, NDCG@10 vs baselines
- Store summary JSON in `model_versions.metrics` table

**Baselines to implement**:
1. Popularity (TMDB trending order)
2. Content-only (pgvector synopsis similarity)
3. Two-Tower collaborative
4. Full hybrid (retrieval + Two-Tower + streaming boost)

---

## 8. Job scheduling

**Decision**: Separate `jobs/tmdb_sync` Python script invoked by Docker Compose `scheduler` service (cron: daily 06:00 UTC) or host cron in dev.

**Rationale**:
- Decouples sync from API request lifecycle
- Failed sync degrades gracefully (spec edge case: stale catalog flag on API responses)

**Alternatives considered**:
| Alternative | Rejected because |
|---|---|
| APScheduler inside FastAPI | Couples sync failures to API process |
| Celery + Redis | Extra infra for MVP |

---

## 9. Monorepo layout and migration from legacy code

**Decision**: New code under `apps/`, `ml/`, `jobs/`; move existing e-commerce demo to `legacy/` when Phase I starts.

**Rationale**:
- Clear separation from course artifact
- Avoids breaking Spec Kit paths at repo root

---

## 10. P1 features (deferred research notes)

Documented for future phases — not blocking MVP plan:

| Feature | Approach sketch |
|---|---|
| MMR diversity | Maximal Marginal Relevance on ranked list using genre vectors |
| NL search | Query embedding + pgvector + SQL filters (duration, platform) |
| Tonight mode | Session context stored in Redis or JWT claims; filter before rank |
| Series progress | `user_series_progress` table; UI "Continue watching" |
| Explainability | Rule-based tags from genre match, affinity provider, source like title |
