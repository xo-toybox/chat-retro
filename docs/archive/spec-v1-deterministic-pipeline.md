# Spec v1: Deterministic Pipeline (Archived)

| Status | Date |
|--------|------|
| Archived | 2025-12-27 |

## Summary

This approach was conceptualized but not implemented. Superseded by agentic architecture (ADR-001).

## Original Concept

A fixed pipeline for analyzing ChatGPT conversation exports:

```
parse → chunk → embed → cluster → classify → render
```

### Key Characteristics

- **Local-first**: Designed for wide deployment with minimal dependencies
- **Deterministic**: Fixed classification rules (burst, thread, exploration, sporadic)
- **Cost-constrained**: Local embeddings (sentence-transformers), no API costs
- **Prescribed output**: `timeline.json` with fixed schema

### Classification Rules (Never Implemented)

| Pattern | Rule |
|---------|------|
| Burst | >N messages in <T hours |
| Thread | Recurring topic over weeks/months |
| Exploration | One-off deep dive |
| Sporadic | Low-frequency, no clear pattern |

### Stack (Planned)

- sklearn for clustering
- TF-IDF for topic labeling
- Threshold-based classification
- Static HTML output

## Why Archived

1. **Deployment path narrowed**: Cut from wide deployment to personal use only
2. **Quality ceiling**: Rule-based classification limited by rule design
3. **Claude API approved**: Enables higher-quality agentic analysis
4. **Better approach discovered**: Agent can derive patterns emergently rather than fitting data to prescribed categories

## See Also

- [ADR-001: Agentic Architecture](../adr/adr-001-agentic-architecture.md)
