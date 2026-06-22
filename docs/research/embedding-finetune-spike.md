# Spike: Fine-Tune Content Embeddings with Likes

**Status**: Research only — not implemented in StreamWise MVP  
**Date**: 2026-06-22

## Current state

- Base model: `sentence-transformers/all-MiniLM-L6-v2` (384-dim)  
- Stored in `title_embeddings.content_vector`  
- User profile vector = mean of liked title vectors  
- Used for "More like this" and retrieval stage of For You

## Fine-tuning objective

Train embedding space so liked titles cluster closer to the user profile than random negatives.

## Data

| Source | Signal |
|---|---|
| MovieLens ratings | Weak/strong pairs (≥4 vs ≤2) |
| StreamWise likes | Positive pairs (user profile ↔ liked title) |
| StreamWise dislikes | Negative pairs (push apart) |

## Approaches

1. **Contrastive fine-tune** (Sentence Transformers `MultipleNegativesRankingLoss`)  
   - Anchors: liked titles; positives: same-user other likes; negatives: in-batch random  
2. **Matryoshka / adapter layers** — keep base frozen, train small projection (lower risk)  
3. **Periodic refresh** — re-embed catalog after fine-tune job in `retrain_pipeline.py`

## Pipeline integration (v2)

```text
retrain_pipeline.py
  → merge interactions
  → train Two-Tower
  → (optional) fine_tune_embeddings.py
  → regenerate title_embeddings.content_vector
  → export_item_embeddings (model_vector)
```

## Risks

- Catastrophic forgetting on cold titles with short overviews  
- GPU cost for full catalog re-embed  
- Need offline SC-005 regression (genre overlap) after each embed refresh

## Recommendation

Collect ≥10k platform likes before fine-tuning. Until then, mean-pooling liked synopsis vectors + Two-Tower `model_vector` remains sufficient for MVP.

## References

- `ml/training/generate_embeddings.py`  
- `apps/api/app/services/content_embedding_service.py`  
- SC-005 genre overlap metric in `ml/eval/evaluate.py`
