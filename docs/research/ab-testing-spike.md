# Spike: A/B Ranker Testing

**Status**: Research only — not implemented in StreamWise MVP  
**Date**: 2026-06-22

## Goal

Compare recommendation rankers (popularity, content-only, Two-Tower, full hybrid + MMR) in production without degrading user experience.

## Proposed design

| Layer | Approach |
|---|---|
| Assignment | Hash `user_id` → bucket A/B (sticky) |
| Variant A | Current hybrid pipeline (control) |
| Variant B | Candidate change (e.g. higher MMR λ, no bandit exploration) |
| Metrics | CTR on For You cards, like rate within 24h, provider match (SC-004) |
| Logging | `bandit_events` + new `experiment_assignments` table |

## Minimum viable experiment

1. Feature flag `EXPERIMENT_RANKER_B` in API config  
2. 50/50 split for users with ≥5 likes  
3. Run 2 weeks; primary metric: like rate on top-10 impressions  
4. Secondary: NDCG@10 offline on holdout refreshed weekly

## Guardrails

- Exclude new users (<5 likes) — cold start unchanged  
- Cap exploration slots when experiment active  
- Auto-revert if error rate or empty-feed rate spikes

## Tooling options

- **Lightweight**: env flag + Postgres event log (MVP-friendly)  
- **Heavier**: GrowthBook, Optimizely, or custom MLflow experiments linked to `model_versions`

## Recommendation

Start with env-flag A/B and existing `bandit_events` schema before adopting a third-party experimentation platform.

## References

- Constitution ML quality gate (offline baselines required first)  
- `ml/eval/evaluate.py` for offline pre-check before any online test
