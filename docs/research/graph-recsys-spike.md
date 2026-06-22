# Spike: Neo4j Graph Recommender (v2+)

**Status**: Research only — not implemented in StreamWise MVP  
**Date**: 2026-06-22

## Problem

Two-Tower + pgvector handles collaborative and content signals well, but cross-title relational patterns (same franchise, shared cast, director filmography) are implicit in embeddings only.

## Proposed graph model

```text
(User)-[:LIKED]->(Title)-[:HAS_GENRE]->(Genre)
(Title)-[:AVAILABLE_ON]->(Provider)
(Title)-[:SIMILAR_TO {score}]->(Title)   # from vector search or TMDB relations
(Person)-[:ACTED_IN]->(Title)
```

## Candidate retrieval flow

1. Seed from user likes → 2-hop neighborhood in Neo4j  
2. Score paths by edge weights (genre overlap, provider match, co-like frequency)  
3. Merge with Two-Tower top-N for hybrid rank

## Pros

- Explainable paths ("Because you liked X → same director")  
- Strong for franchise/sequel discovery  
- Natural fit for "more like this" expansion

## Cons

- Extra infra (Neo4j Aura or self-hosted)  
- TMDB cast/crew sync not in MVP catalog pipeline  
- Cold-start users still need Two-Tower / content vectors

## Recommendation

Defer to v2. If pursued, start with offline ETL from TMDB credits into a read-only graph and A/B against current hybrid feed on Recall@10.

## References

- [docs/STREAMWISE-PLANNING.md](../STREAMWISE-PLANNING.md) §13.3  
- Neo4j Graph Data Science — node similarity, personalized PageRank
