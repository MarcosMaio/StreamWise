# Tasks: StreamWise Platform

**Input**: Design documents from `/specs/001-streamwise/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md  
**Scope reference**: `docs/STREAMWISE-PLANNING.md` (P0 MVP → P1 StreamWise Plus → P2 advanced → v2+ backlog)

**Organization**: Phases follow the planning roadmap. User story labels `[USn]` map to `spec.md`. Tasks include exact file paths per `plan.md` monorepo layout.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependency on incomplete tasks in same batch)
- **[USn]**: User story from spec.md
- **[ML]**: Machine learning / offline pipeline task
- **[P1+] / [P2+]**: Priority tier from planning doc (post-MVP)

---

## Phase 1: Project Setup & Monorepo Scaffold

**Purpose**: Initialize repository structure, tooling, and local infrastructure skeleton  
**Planning ref**: §12 Phase 1 — Foundation

- [x] T001 Create monorepo directory structure (`apps/api/`, `apps/web/`, `ml/training/`, `ml/eval/`, `ml/artifacts/`, `jobs/tmdb_sync/`, `infra/`) per `specs/001-streamwise/plan.md`
- [x] T002 [P] Add root `.gitignore` entries for `.venv`, `node_modules`, `ml/artifacts/`, `.env`, `__pycache__`
- [x] T003 [P] Create `infra/.env.example` with DATABASE_URL, TMDB_API_KEY, JWT_SECRET, MODEL_PATH, EMBEDDING_MODEL, NEXT_PUBLIC_API_URL
- [x] T004 [P] Create `infra/docker-compose.yml` with postgres, api, web, scheduler services
- [x] T005 [P] Create `infra/postgres/init.sql` enabling pgvector extension (`CREATE EXTENSION IF NOT EXISTS vector`)
- [x] T006 [P] Scaffold `apps/api/pyproject.toml` with FastAPI, SQLAlchemy, Alembic, asyncpg, httpx, python-jose, passlib, pgvector dependencies
- [x] T007 [P] Scaffold `apps/api/app/main.py` with FastAPI app factory and `/health` endpoint
- [x] T008 [P] Scaffold `apps/api/app/config.py` loading settings from environment variables
- [x] T009 [P] Create `apps/api/Dockerfile` for API container
- [x] T010 [P] Scaffold `apps/web/package.json` with Next.js 14, Tailwind, TypeScript
- [x] T011 [P] Create `apps/web/tailwind.config.ts` and `apps/web/src/app/layout.tsx` base layout
- [x] T012 [P] Create `apps/web/Dockerfile` for web container
- [x] T013 [P] Create `apps/web/src/lib/api-client.ts` HTTP client wrapper pointing to `NEXT_PUBLIC_API_URL`
- [x] T014 Move legacy e-commerce demo to `legacy/` (preserve `src/`, `data/`, `index.html` from course project)
- [x] T015 Update root `README.md` stub pointing to `docs/STREAMWISE-PLANNING.md` and `specs/001-streamwise/quickstart.md`

**Checkpoint**: `docker compose -f infra/docker-compose.yml up postgres` starts; API `/health` returns ok when run locally

---

## Phase 2: Database Schema & API Foundation

**Purpose**: PostgreSQL schema, migrations, ORM models — blocks all feature work  
**Planning ref**: §9 Data model, §12 Phase 1

- [x] T016 Initialize Alembic in `apps/api/alembic/` with async SQLAlchemy engine config in `apps/api/alembic/env.py`
- [x] T017 Create migration `apps/api/alembic/versions/001_enable_pgvector.py` for vector extension
- [x] T018 Create migration `apps/api/alembic/versions/002_core_catalog.py` for `genres`, `titles`, `title_genres`, `streaming_providers`, `title_streaming_providers`
- [x] T019 Create migration `apps/api/alembic/versions/003_users_auth.py` for `users`, `oauth_accounts`
- [x] T020 Create migration `apps/api/alembic/versions/004_interactions.py` for `interactions`, `user_preferences`
- [x] T021 Create migration `apps/api/alembic/versions/005_embeddings.py` for `title_embeddings`, `user_embeddings`, `user_streaming_affinity`
- [x] T022 Create migration `apps/api/alembic/versions/006_model_versions.py` for `model_versions` table
- [x] T023 Create migration `apps/api/alembic/versions/007_series_progress.py` for `user_series_progress` (schema ready; UI in P1)
- [x] T024 [P] Implement SQLAlchemy models in `apps/api/app/models/user.py`
- [x] T025 [P] Implement SQLAlchemy models in `apps/api/app/models/title.py`
- [x] T026 [P] Implement SQLAlchemy models in `apps/api/app/models/interaction.py`
- [x] T027 [P] Implement SQLAlchemy models in `apps/api/app/models/embedding.py`
- [x] T028 [P] Implement SQLAlchemy models in `apps/api/app/models/provider.py`
- [x] T029 Create `apps/api/app/db/session.py` async session dependency and base declarative class
- [x] T030 Create seed script `apps/api/scripts/seed_genres_providers.py` for TMDB genre list and common BR streaming providers
- [x] T031 [P] Create Pydantic schemas in `apps/api/app/schemas/common.py` (pagination, errors)
- [x] T032 Add global exception handlers and structured logging in `apps/api/app/main.py`
- [x] T033 [P] Create `apps/api/tests/conftest.py` with test database fixture and httpx AsyncClient
- [x] T034 Document migration commands in `specs/001-streamwise/quickstart.md` (verify accuracy)

**Checkpoint**: `alembic upgrade head` succeeds; seed script populates genres and providers

---

## Phase 3: User Story 1 — Account Access (Priority: P1) 🎯

**Goal**: Register, login, JWT session, protected routes  
**Independent Test**: Register → logout → login → access protected `/users/me`  
**Spec**: US1 | **Planning**: P0 auth

- [x] T035 [P] [US1] Create Pydantic schemas in `apps/api/app/schemas/auth.py` (RegisterRequest, LoginRequest, AuthResponse)
- [x] T036 [P] [US1] Implement password hashing utilities in `apps/api/app/core/security.py`
- [x] T037 [P] [US1] Implement JWT create/verify in `apps/api/app/core/jwt.py`
- [x] T038 [US1] Implement `AuthService` in `apps/api/app/services/auth_service.py`
- [x] T039 [US1] Implement auth router `apps/api/app/routers/auth.py` (`POST /auth/register`, `POST /auth/login`)
- [x] T040 [US1] Add `get_current_user` dependency in `apps/api/app/dependencies/auth.py`
- [x] T041 [US1] Implement `POST /auth/oauth/google` in `apps/api/app/routers/auth.py` with token exchange
- [x] T042 [P] [US1] Create Next.js auth pages `apps/web/src/app/(auth)/login/page.tsx` and `register/page.tsx`
- [x] T043 [P] [US1] Configure NextAuth or JWT cookie storage in `apps/web/src/lib/auth.ts`
- [x] T044 [US1] Add auth middleware protecting routes in `apps/web/src/middleware.ts`
- [x] T045 [US1] Integration test `apps/api/tests/integration/test_auth.py` for register/login flow

**Checkpoint**: User can register and login via UI and API

---

## Phase 4: User Story 2 — Browse Trending & New Releases (Priority: P1)

**Goal**: Live catalog from TMDB sync; home trending/new sections  
**Independent Test**: After sync, `GET /catalog/trending` returns titles; home UI shows sections  
**Spec**: US2 | **Planning**: §12 Phase 2 — Live catalog

- [x] T046 [P] [US2] Implement TMDB HTTP client in `apps/api/app/services/tmdb_client.py` (trending, now_playing, on_the_air, details, watch/providers)
- [x] T047 [US2] Implement catalog upsert logic in `apps/api/app/services/catalog_service.py`
- [x] T048 [US2] Create sync script `jobs/tmdb_sync/sync_catalog.py` (trending, new releases, providers BR, upsert titles)
- [x] T049 [US2] Create scheduler entry `jobs/tmdb_sync/scheduler.py` and wire in `infra/docker-compose.yml` scheduler service (daily 06:00 UTC)
- [x] T050 [US2] Add stale-data flag logic when `last_synced_at` > 24h in `apps/api/app/services/catalog_service.py`
- [x] T176 [US2] Add TMDB sync health metrics and success-rate logging in `jobs/tmdb_sync/sync_catalog.py` and `jobs/tmdb_sync/scheduler.py` (SC-006: track ≥95% daily success; expose last run status for ops)
- [x] T051 [P] [US2] Implement `GET /catalog/trending` in `apps/api/app/routers/catalog.py`
- [x] T052 [P] [US2] Implement `GET /catalog/new` in `apps/api/app/routers/catalog.py`
- [x] T053 [P] [US2] Create Pydantic schemas in `apps/api/app/schemas/title.py` (TitleSummary, TitleListResponse)
- [x] T054 [P] [US2] Create home page `apps/web/src/app/(main)/page.tsx` with Trending and New Releases sections
- [x] T055 [P] [US2] Create reusable `apps/web/src/components/TitleCard.tsx` (poster, name, type badge)
- [x] T056 [US2] Integration test `apps/api/tests/integration/test_catalog.py` for trending endpoint after mock sync

**Checkpoint**: Daily sync populates DB; home displays trending and new release rows

---

## Phase 5: User Story 3 — Onboarding Preferences (Priority: P1)

**Goal**: Capture genres, streaming services, optional seed likes  
**Independent Test**: New user completes onboarding; preferences persist on profile  
**Spec**: US3 | **Planning**: P0 onboarding

- [x] T057 [P] [US3] Create Pydantic schema `PreferencesRequest` in `apps/api/app/schemas/user.py`
- [x] T058 [US3] Implement `UserPreferenceService` in `apps/api/app/services/user_preference_service.py`
- [x] T059 [US3] Implement `PUT /users/me/preferences` in `apps/api/app/routers/users.py`
- [x] T060 [US3] Set `onboarding_complete` flag and seed initial `user_streaming_affinity` from declared providers
- [x] T061 [P] [US3] Create onboarding flow `apps/web/src/app/onboarding/page.tsx` (genre multi-select, provider multi-select)
- [x] T062 [P] [US3] Create optional seed title picker step in `apps/web/src/app/onboarding/seed-titles/page.tsx`
- [x] T063 [US3] Redirect new users without `onboarding_complete` to onboarding via `apps/web/src/middleware.ts`
- [x] T064 [US3] Integration test `apps/api/tests/integration/test_onboarding.py`

**Checkpoint**: New user must complete onboarding before personalized feed

---

## Phase 6: User Story 4 — Title Detail & Streaming Availability (Priority: P1)

**Goal**: Detail page with synopsis, community stats, BR streaming badges  
**Independent Test**: Open title → see overview, StreamWise rating, Netflix/Prime badges  
**Spec**: US4 | **Planning**: P0 catalog detail

- [x] T065 [US4] Implement `GET /titles/{titleId}` in `apps/api/app/routers/titles.py` with providers and aggregates
- [x] T066 [P] [US4] Extend `TitleDetail` schema in `apps/api/app/schemas/title.py` with availability_note, streaming_providers
- [x] T067 [P] [US4] Create detail page `apps/web/src/app/titles/[id]/page.tsx`
- [x] T068 [P] [US4] Create `apps/web/src/components/StreamingBadges.tsx` for flatrate provider logos
- [x] T069 [P] [US4] Create `apps/web/src/components/CommunityRating.tsx` (avg rating + like count)
- [x] T070 [US4] Handle empty availability state with explicit messaging in `apps/web/src/app/titles/[id]/page.tsx`

**Checkpoint**: Title detail shows metadata and where to watch in Brazil

---

## Phase 7: User Story 5 — Record Interactions (Priority: P1)

**Goal**: Like, dislike, rate, watchlist, watched with aggregate updates  
**Independent Test**: Like + rate title → aggregates update → persist after refresh  
**Spec**: US5 | **Planning**: §12 Phase 3 — Interactions

- [x] T071 [P] [US5] Create Pydantic schemas in `apps/api/app/schemas/interaction.py`
- [x] T072 [US5] Implement `InteractionService` in `apps/api/app/services/interaction_service.py` (upsert, mutual exclusivity like/dislike)
- [x] T073 [US5] Implement aggregate updater for `like_count`, `streamwise_avg_rating` in `apps/api/app/services/title_aggregate_service.py`
- [x] T074 [US5] Implement `POST /titles/{titleId}/interactions` in `apps/api/app/routers/interactions.py`
- [x] T075 [US5] Trigger `user_streaming_affinity` recompute in `apps/api/app/services/affinity_service.py` after likes
- [x] T076 [P] [US5] Add interaction buttons component `apps/web/src/components/InteractionBar.tsx` (like, dislike, rate, watchlist, watched)
- [x] T077 [US5] Wire `InteractionBar` into `apps/web/src/app/titles/[id]/page.tsx`
- [x] T078 [US5] Integration test `apps/api/tests/integration/test_interactions.py`

**Checkpoint**: Interactions persist and update community aggregates

---

## Phase 8: Vector Search & Content Embeddings (Planning Phase 4)

**Goal**: Synopsis embeddings, pgvector similar-title retrieval  
**Independent Test**: Similar titles API returns genre-related neighbors  
**Planning ref**: §12 Phase 4 — Vector search, P0 similar search

- [x] T079 [ML] Add `sentence-transformers` to `ml/training/pyproject.toml` or `apps/api/pyproject.toml` dev deps
- [x] T080 [ML] Create embedding generator `ml/training/generate_embeddings.py` (overview → content_vector 384d)
- [x] T081 [ML] Batch embed all titles and upsert `title_embeddings.content_vector` with IVFFlat index creation script
- [x] T082 Implement vector search queries in `apps/api/app/services/vector_search_service.py` (cosine similarity, top-K)
- [x] T083 [US8] Implement `GET /titles/{titleId}/similar` in `apps/api/app/routers/titles.py` using vector search
- [x] T084 [P] [US8] Add "More like this" section in `apps/web/src/app/titles/[id]/page.tsx`
- [x] T085 Hook embedding generation into `jobs/tmdb_sync/sync_catalog.py` for new titles with overview text

**Checkpoint**: Similar titles work for embedded catalog entries

---

## Phase 9: User Story 6 — Personalized "For You" Feed (Priority: P1) 🎯

**Goal**: Hybrid recommendation — retrieval + Two-Tower rank + streaming boost  
**Independent Test**: User with ≥5 likes receives ≥10 personalized titles excluding watched/disliked (SC-003)  
**Spec**: US6 | **Planning**: §12 Phase 5 — Neural model, P0 hybrid feed

- [x] T086 [ML] Create MovieLens import script `ml/training/import_movielens.py` (ratings, movies, links → DB / parquet)
- [x] T087 [ML] Create training config `ml/training/config.yaml` (batch size, epochs, embedding dims, sample size for dev)
- [x] T088 [ML] Implement Two-Tower model in `ml/training/two_tower_model.py` (user tower + item tower)
- [x] T089 [ML] Implement training script `ml/training/train_two_tower.py` with binary labels (rating ≥4 / ≤2)
- [x] T090 [ML] Export model artifact to `ml/artifacts/two_tower/v1/` and register in `model_versions` table
- [x] T091 [ML] Generate `model_vector` item embeddings post-train in `ml/training/export_item_embeddings.py`
- [x] T092 Implement model loader in `apps/api/app/services/model_loader.py` (active version from `model_versions`)
- [x] T093 Implement `RecommendationService` in `apps/api/app/services/recommendation_service.py` (retrieval top-200 → rank → streaming boost α=0.3)
- [x] T094 Implement candidate filtering (exclude watched/disliked) in `apps/api/app/services/recommendation_service.py`
- [x] T095 Implement cold-start path using onboarding genres + vector search in `apps/api/app/services/recommendation_service.py`
- [x] T096 Implement trending fallback when model unavailable in `apps/api/app/services/recommendation_service.py`
- [x] T097 [US6] Implement `GET /recommendations/for-you` in `apps/api/app/routers/recommendations.py`
- [x] T098 [P] [US6] Create "For you" feed section in `apps/web/src/app/(main)/page.tsx`
- [x] T099 [P] [US6] Create `apps/web/src/components/RecommendationFeed.tsx` with loading and fallback states
- [x] T100 [US6] Integration test `apps/api/tests/integration/test_recommendations.py` with seeded user (≥5 likes per SC-003)

**Checkpoint**: Personalized feed returns ranked titles; cold start and fallback behave per spec edge cases

---

## Phase 10: User Story 7 — Filter by Streaming Platform (Priority: P2)

**Goal**: Filter catalog and feed by selected streaming services  
**Independent Test**: Netflix-only filter returns only Netflix-available titles in BR  
**Spec**: US7 | **Planning**: P0 filter (may ship with MVP)

- [x] T101 [US7] Add `provider_ids` query param filtering to `GET /catalog/trending`, `/catalog/new`, `/recommendations/for-you` in respective routers
- [x] T102 [P] [US7] Create `apps/web/src/components/ProviderFilter.tsx` multi-select filter chip bar
- [x] T103 [US7] Create explore page `apps/web/src/app/explore/page.tsx` with genre + platform + type filters
- [x] T104 [US7] Pre-select onboarding providers as default filter in `apps/web/src/components/ProviderFilter.tsx`

**Checkpoint**: Platform filter works on home, explore, and for-you feed

---

## Phase 11: User Story 8 — Discover Similar Titles & Search (Priority: P2)

**Goal**: NL/keyword search with semantic retrieval + filters  
**Independent Test**: Search "short funny series" returns relevant filtered results  
**Spec**: US8 | **Planning**: P1 NL search (basic search in P0/P2 phase)

- [ ] T105 [US8] Implement `GET /catalog/search` in `apps/api/app/routers/catalog.py` (query embedding + vector search + filters)
- [ ] T106 [P] [US8] Create search bar component `apps/web/src/components/SearchBar.tsx` on explore and home header
- [ ] T107 [US8] Integration test `apps/api/tests/integration/test_search.py`

**Checkpoint**: Text search returns semantically relevant titles

---

## Phase 12: User Story 9 — Profile & Taste Summary (Priority: P3)

**Goal**: Profile shows likes, watchlist, preferences, streaming affinity  
**Independent Test**: After likes, profile shows affinity weights matching liked providers  
**Spec**: US9

- [ ] T108 [US9] Implement `GET /users/me` in `apps/api/app/routers/users.py`
- [ ] T109 [US9] Implement `GET /users/me/likes` in `apps/api/app/routers/users.py`
- [ ] T177 [US9] Implement `GET /users/me/watchlist` in `apps/api/app/routers/users.py` (FR-024; filter interactions where `event_type=watchlist`)
- [ ] T110 [US9] Implement `GET /users/me/affinity` in `apps/api/app/routers/users.py`
- [ ] T111 [P] [US9] Create profile page `apps/web/src/app/profile/page.tsx` (likes, watchlist via T177, genres, affinity chart)
- [ ] T112 [P] [US9] Create `apps/web/src/components/AffinityChart.tsx` visualizing provider scores

**Checkpoint**: Profile reflects user taste and inferred streaming habits

---

## Phase 13: ML Evaluation & P0 Quality Gate (Planning Phase 6)

**Goal**: Offline metrics, baselines, portfolio documentation  
**Independent Test**: `ml/eval/evaluate.py` reports Precision@10 and NDCG@10 beating popularity baseline  
**Planning ref**: §15 Success metrics, constitution ML quality gate

- [ ] T113 [ML] Implement popularity baseline in `ml/eval/baselines.py`
- [ ] T114 [ML] Implement content-only baseline (pgvector) in `ml/eval/baselines.py`
- [ ] T115 [ML] Implement evaluation script `ml/eval/evaluate.py` (Precision@10, Recall@10, NDCG@10, Coverage)
- [ ] T178 [ML] Add SC-004 platform affinity metric to `ml/eval/evaluate.py`: for users with 5+ likes on one dominant BR provider, assert ≥60% of top-10 "For you" titles available on that provider
- [ ] T179 [ML] Add SC-005 genre overlap metric to `ml/eval/evaluate.py`: assert ≥70% of "More like this" results share ≥1 genre with source title when genre metadata exists
- [ ] T116 [ML] Store eval metrics JSON into `model_versions.metrics` via `ml/eval/publish_metrics.py`
- [ ] T117 [P] Add architecture diagram to root `README.md` (Mermaid: offline train, sync, online serve)
- [ ] T118 [P] Document ML metrics results section in root `README.md` (placeholders until eval run)
- [ ] T119 [P] Add API usage section to root `README.md` linking `specs/001-streamwise/contracts/openapi.yaml`
- [ ] T120 Validate full quickstart path in `specs/001-streamwise/quickstart.md` end-to-end and fix gaps

**Checkpoint**: P0 MVP complete per constitution — metrics script runs (SC-007, SC-004, SC-005); sync health tracked (SC-006); README documents architecture

---

## Phase 14: P1 — StreamWise Plus Enhancements

**Purpose**: Post-MVP product+ML differentiators  
**Planning ref**: §13.1, §14 P1, §12 Phase 7

### 14A: Explainability on recommendation cards

- [ ] T121 [P1+] Implement reason tag generator in `apps/api/app/services/explainability_service.py` (genre match, platform, trending, similar liked title)
- [ ] T122 [P1+] Add `reason_tags` to `RecommendationItem` in `apps/api/app/schemas/recommendation.py` and populate in `recommendation_service.py`
- [ ] T123 [P1+] Display reason tags in `apps/web/src/components/RecommendationFeed.tsx`

### 14B: Feed diversity (MMR)

- [ ] T124 [P1+] Implement MMR reranker in `apps/api/app/services/mmr_reranker.py` using genre vectors
- [ ] T125 [P1+] Integrate MMR as final step in `apps/api/app/services/recommendation_service.py` (λ configurable)
- [ ] T126 [ML] [P1+] Add diversity metric to `ml/eval/evaluate.py` (genre variety in top-10)

### 14C: Tonight mode (contextual recommendations)

- [ ] T127 [P1+] Add session context schema (time budget, mood, company) in `apps/api/app/schemas/context.py`
- [ ] T128 [P1+] Implement context filters in `apps/api/app/services/recommendation_service.py` before ranking
- [ ] T129 [P1+] Create `apps/web/src/components/TonightModePrompt.tsx` on home feed
- [ ] T130 [P1+] Persist tonight context in session storage via `apps/web/src/lib/tonight-context.ts`

### 14D: Natural language search enhancements

- [ ] T131 [P1+] Extend `GET /catalog/search` with duration/type/mood filter params in `apps/api/app/routers/catalog.py`
- [ ] T132 [P1+] Add example query chips UI in `apps/web/src/components/SearchBar.tsx` ("Short on Netflix", etc.)

### 14E: Series progress & Continue watching

- [ ] T133 [P1+] Implement `PUT /titles/{titleId}/progress` in `apps/api/app/routers/interactions.py` (season, episode)
- [ ] T134 [P1+] Implement `GET /users/me/continue-watching` in `apps/api/app/routers/users.py`
- [ ] T135 [P1+] Create `apps/web/src/app/(main)/continue/page.tsx` Continue Watching section
- [ ] T136 [P1+] Add progress indicator on series cards in `apps/web/src/components/TitleCard.tsx`

### 14F: ML metrics dashboard (admin/dev)

- [ ] T137 [P1+] Create internal metrics API `GET /admin/metrics/recommendations` in `apps/api/app/routers/admin.py` (protected)
- [ ] T138 [P1+] Create dashboard page `apps/web/src/app/admin/metrics/page.tsx` with charts (Precision@K, NDCG, baseline comparison)
- [ ] T139 [P1+] Wire dashboard to latest `model_versions.metrics` JSON

**Checkpoint**: StreamWise Plus features demonstrable per planning doc §13.4 package

---

## Phase 15: P2 — Advanced Differentiators

**Purpose**: Retention, exploration, and market-specific features  
**Planning ref**: §13.2, §14 P2

### 15A: Import watchlist (Trakt / CSV)

- [ ] T140 [P2+] Implement CSV import parser in `apps/api/app/services/import_service.py`
- [ ] T141 [P2+] Implement Trakt OAuth integration stub in `apps/api/app/routers/integrations.py` (optional env-gated)
- [ ] T142 [P2+] Create import UI `apps/web/src/app/profile/import/page.tsx`

### 15B: Weekly email digest

- [ ] T143 [P2+] Create digest job `jobs/email/weekly_digest.py` (top 5 recommendations per user)
- [ ] T144 [P2+] Add email template `jobs/email/templates/weekly_digest.html`
- [ ] T145 [P2+] Add SMTP settings to `infra/.env.example` and scheduler trigger in `infra/docker-compose.yml`

### 15C: Multi-Armed Bandit exploration slots

- [ ] T146 [P2+] Implement exploration slot injector (10–20% random catalog) in `apps/api/app/services/bandit_service.py`
- [ ] T147 [P2+] Integrate bandit into `GET /recommendations/for-you` response with `exploration` flag per item
- [ ] T148 [ML] [P2+] Log exploration impressions/clicks for offline analysis in `apps/api/app/models/bandit_event.py`

### 15D: Parental filter

- [ ] T149 [P2+] Store TMDB certification on titles via sync extension in `jobs/tmdb_sync/sync_catalog.py`
- [ ] T150 [P2+] Add user content filter preferences in `apps/api/app/models/user.py` (blocked genres, max rating)
- [ ] T151 [P2+] Apply parental filters in catalog and recommendation queries

### 15E: Price comparison (rent/buy vs flatrate)

- [ ] T152 [P2+] Expose rent/buy availability types in `TitleDetail` schema and sync from TMDB
- [ ] T153 [P2+] Create `apps/web/src/components/PriceBadge.tsx` showing subscription vs rental indicator

### 15F: Weekly streaming catalog diff

- [ ] T154 [P2+] Snapshot provider mappings daily in `jobs/tmdb_sync/snapshot_providers.py`
- [ ] T155 [P2+] Implement diff job `jobs/tmdb_sync/diff_catalog.py` detecting enter/leave events
- [ ] T156 [P2+] Create API `GET /catalog/changes` in `apps/api/app/routers/catalog.py`
- [ ] T157 [P2+] Create UI section `apps/web/src/components/CatalogChanges.tsx` ("Left Prime, joined Netflix")

**Checkpoint**: P2 features available behind feature flags or dedicated pages

---

## Phase 16: P2+ Backlog & Retraining Pipeline

**Purpose**: Operational ML maturity and v2+ items from planning doc §13.3  
**Planning ref**: §7.4 Retrain, §13.3 v2+

- [ ] T158 [ML] Implement scheduled retrain script `ml/training/retrain_pipeline.py` merging MovieLens + platform interactions
- [ ] T159 [ML] Integrate MLflow tracking in `ml/training/train_two_tower.py` (`ml/mlflow/` config)
- [ ] T160 [ML] Implement weekly retrain cron in `infra/docker-compose.yml` scheduler service
- [ ] T161 [P2+] Spike: document Neo4j graph recsys approach in `docs/research/graph-recsys-spike.md` (v2+ — no implementation required for MVP)
- [ ] T162 [P2+] Spike: document A/B ranker testing approach in `docs/research/ab-testing-spike.md`
- [ ] T163 [P2+] Spike: document fine-tune embeddings with likes in `docs/research/embedding-finetune-spike.md`

**Checkpoint**: Retrain pipeline documented and runnable manually

---

## Phase 17: Polish, Security & Cross-Cutting Concerns

**Purpose**: Production readiness, constitution compliance, final validation  
**Planning ref**: §19 Out of scope verification, constitution testing

- [ ] T164 [P] Add rate limiting middleware in `apps/api/app/middleware/rate_limit.py` for auth and search endpoints
- [ ] T165 [P] Add CORS configuration for web origin in `apps/api/app/main.py`
- [ ] T166 [P] Security review: ensure TMDB_API_KEY and JWT_SECRET never logged in `apps/api/app/config.py`
- [ ] T167 [P] Add input validation audit across all Pydantic schemas in `apps/api/app/schemas/`
- [ ] T168 Run full API integration test suite `apps/api/tests/integration/` and fix failures
- [ ] T169 [P] Add Playwright smoke test `apps/web/tests/e2e/smoke.spec.ts` (login → home → detail → like)
- [ ] T170 [P] Performance smoke: verify home and for-you meet SC-002 (<3s) and document results in `README.md`
- [ ] T171 Align OpenAPI spec `specs/001-streamwise/contracts/openapi.yaml` with implemented routes (diff audit)
- [ ] T172 [P] Add portfolio one-liner and bullet points from `docs/STREAMWISE-PLANNING.md` §16 to `README.md`
- [ ] T173 Remove or archive dead code under `legacy/` with note in `legacy/README.md`
- [x] T174 Run `/speckit.analyze` consistency check across spec, plan, tasks before `/speckit.implement`
- [ ] T175 Tag release `v0.1.0-mvp` after P0 checkpoint validation

**Checkpoint**: Project portfolio-ready; all P0 success criteria verifiable

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup)
  → Phase 2 (Foundation/DB) [BLOCKS ALL]
    → Phase 3 (US1 Auth)
      → Phase 4 (US2 Catalog/Sync)
        → Phase 5 (US3 Onboarding)
          → Phase 6 (US4 Detail)
            → Phase 7 (US5 Interactions)
              → Phase 8 (Vector Search)
                → Phase 9 (US6 Hybrid Feed) [P0 CORE]
                  → Phase 10–12 (US7, US8, US9) [can parallelize]
                    → Phase 13 (ML Eval & README) [P0 DONE]
                      → Phase 14 (P1 Plus)
                        → Phase 15 (P2)
                          → Phase 16 (Retrain/Spikes)
                            → Phase 17 (Polish)
```

### User Story Dependencies

| Story | Depends on | Can parallelize after |
|---|---|---|
| US1 Auth | Phase 2 | Phase 2 complete |
| US2 Catalog | US1 (auth for API) | US1 |
| US3 Onboarding | US1, US2 (titles exist) | US2 |
| US4 Detail | US2 | US2 |
| US5 Interactions | US1, US4 | US4 |
| US6 For You | US3, US5, Phase 8, ML train | Phase 8 + T089 |
| US7 Filters | US2, US6 | US6 |
| US8 Search | Phase 8 | Phase 8 |
| US9 Profile | US5 | US5 |

### Parallel Opportunities

**Batch A** (after Phase 2): T024–T028 models in parallel  
**Batch B** (after US2): T065–T070 detail UI + API in parallel  
**Batch C** (ML track): T086–T091 can run while UI phases 3–7 progress  
**Batch D** (P1): T121–T123 explainability parallel with T124–T126 MMR  
**Batch E** (P2): T140–T157 largely independent feature flags per sub-phase

---

## Parallel Example: Phase 9 (Hybrid Feed)

```bash
# ML track (developer A):
T086 import_movielens.py → T088 two_tower_model.py → T089 train_two_tower.py

# API track (developer B, after T082 vector search):
T092 model_loader.py → T093 recommendation_service.py → T097 recommendations router

# Frontend track (developer C, after T097):
T098 page.tsx → T099 RecommendationFeed.tsx
```

---

## Implementation Strategy

### MVP First (P0 — through Phase 13)

1. Complete Phases 1–2 (setup + foundation)
2. Complete Phases 3–7 (US1–US5 — auth, catalog, onboarding, detail, interactions)
3. Complete Phase 8 (vector search)
4. Complete Phase 9 (US6 — hybrid feed)
5. Complete Phases 10–12 (US7–US9 — filters, search, profile)
6. Complete Phase 13 (ML eval + README)
7. **STOP and VALIDATE** against spec success criteria SC-001 through SC-008 (SC-004/SC-005 via T178–T179; SC-006 via T176)
8. Tag `v0.1.0-mvp`

### StreamWise Plus (P1 — Phase 14)

Add explainability, MMR, Tonight mode, NL search enhancements, series progress, ML dashboard incrementally; re-run eval after MMR (T126).

### Advanced (P2 — Phases 15–16)

Enable feature flags per sub-phase; prioritize Trakt/CSV import and catalog diff for portfolio demos.

### Suggested MVP Task Subset (minimum demo)

`T001–T045` (setup + auth) + `T046–T056` (catalog) + `T057–T078` (onboarding + interactions) + `T079–T100` (vectors + feed) + `T113–T120` (eval + docs)

---

## Task Summary

| Phase | Description | Task IDs | Count |
|---|---|---|---|
| 1 | Setup & scaffold | T001–T015 | 15 |
| 2 | DB & API foundation | T016–T034 | 19 |
| 3 | US1 Auth | T035–T045 | 11 |
| 4 | US2 Catalog/Sync | T046–T056, T176 | 12 |
| 5 | US3 Onboarding | T057–T064 | 8 |
| 6 | US4 Title detail | T065–T070 | 6 |
| 7 | US5 Interactions | T071–T078 | 8 |
| 8 | Vector search | T079–T085 | 7 |
| 9 | US6 Hybrid feed | T086–T100 | 15 |
| 10 | US7 Platform filter | T101–T104 | 4 |
| 11 | US8 Search | T105–T107 | 3 |
| 12 | US9 Profile | T108–T112, T177 | 6 |
| 13 | ML eval & P0 docs | T113–T120, T178–T179 | 10 |
| 14 | P1 StreamWise Plus | T121–T139 | 19 |
| 15 | P2 Advanced | T140–T157 | 18 |
| 16 | Retrain & spikes | T158–T163 | 6 |
| 17 | Polish & release | T164–T175 | 12 |
| **Total** | | **T001–T179** | **179** |

---

## Notes

- All tasks use monorepo paths from `specs/001-streamwise/plan.md`
- `[ML]` tasks may require GPU; use MovieLens `--sample` for dev per quickstart.md
- Constitution requires integration tests — focused in auth, catalog, interactions, recommendations phases
- Do not implement video playback (constitution I, spec FR-027)
- Legacy course code stays in `legacy/` until Phase 17 cleanup
- Run `/speckit.implement` per phase or MVP subset; prefer phase checkpoints before proceeding
