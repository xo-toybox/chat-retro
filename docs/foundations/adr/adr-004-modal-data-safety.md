# ADR-004: Use Modal Labs for GPU Compute

| Status | Date |
|--------|------|
| Contingent | 2025-12-27 |

## Status Note

This decision applies only if the agent chooses GPU-accelerated embeddings. With the shift to agentic architecture (ADR-001), embedding strategy is emergent, not prescribed. The agent may choose:

- No embeddings (pattern analysis without clustering)
- API embeddings (OpenAI, Voyage)
- Local embeddings (CPU/Apple Silicon)
- Modal (GPU-accelerated open models)

This ADR documents the security evaluation for Modal, should the agent determine GPU embeddings are beneficial.

## Context

This project processes personal chat conversation data (ChatGPT exports) and may require programmatic GPU compute. Example workloads include embedding models for semantic search and exploration pattern analysis.

**Key requirements:**
- Data privacy for sensitive personal conversations
- GPU-level performance for embedding workloads
- Reasonable cost for sporadic batch workloads

## Decision Drivers

1. **Data privacy**: personal chat data should not be used for model training or accessed by provider staff
2. **Performance**: GPU-level speed for embedding workloads
3. **Model flexibility**: ability to choose, swap, or fine-tune models
4. **Cost**: sporadic usage; avoid paying for idle resources
5. **Simplicity**: minimal infrastructure setup and maintenance

## Considered Options

1. **Modal Labs**: serverless GPU, run open/fine-tuned models, SOC 2 certified
2. **Embedding APIs**: Voyage (zero-retention opt-out), OpenAI (ZDR on request); ~~Gemini (free tier but data trains models)~~
3. **Local GPU (VRAM-constrained)**: Apple Silicon / consumer GPU, open models only
4. **Local CPU-only**: no GPU, slower but no external trust required

## Decision

**Use Modal Labs** for GPU workloads on personal chat data, if the agent determines GPU embeddings are needed.

## Security Evaluation

### Certifications & Compliance

| Certification | Status | Notes |
|--------------|--------|-------|
| SOC 2 Type II | ✅ Completed | Report available via [trust.modal.com](https://trust.modal.com) |
| HIPAA | ✅ Supported | Enterprise plan with BAA; Volumes v2 compliant |
| PCI | ✅ Compliant | Stripe integration, no card data stored |
| GDPR | ✅ Supported | DPA available at modal.com/legal/dpa |

### Data Handling

| Aspect | Policy | Risk Assessment |
|--------|--------|-----------------|
| **Function inputs/outputs** | Never accessed by Modal staff; deleted after retrieval | Low |
| **Retention period** | Max 7-day TTL, then auto-deleted | Low |
| **Source code access** | Never accessed | Low |
| **Volumes/Images** | Never accessed | Low |
| **Logs/metadata** | Stored; accessed only with user permission for troubleshooting | Low |

### Infrastructure Security

| Control | Implementation |
|---------|----------------|
| **Workload isolation** | gVisor sandboxing (same as Google Cloud Run/GKE); does not protect against hardware side channels; some syscall compatibility limits |
| **Encryption in transit** | TLS 1.3 for all public APIs |
| **Encryption at rest** | All user data encrypted |
| **Employee access** | SSO + phishing-resistant MFA required |
| **Code security** | Memory-safe languages (Rust, Python); Dependabot; external pen testing |

### Risk Matrix

| Threat | Likelihood | Impact | Mitigation |
|--------|------------|--------|------------|
| Modal staff viewing data | Very Low | High | Policy prohibits; SOC 2 audited |
| Cross-tenant data leakage | Very Low | High | gVisor isolation |
| Data persisting beyond need | Low | Medium | 7-day max TTL; deleted after retrieval |
| Transit interception | Very Low | High | TLS 1.3 |
| Breach of Modal infrastructure | Low | High | SOC 2 controls; bug bounty program |

## Implementation Guidelines

### Recommended Practices

```python
# ✅ DO: Process and discard, don't persist raw chat text on Modal
@app.function()
def embed_chats(chat_texts: list[str]) -> list[list[float]]:
    embeddings = model.encode(chat_texts)
    return embeddings  # Return only vectors, not source text

# ✅ DO: Use Secrets for API keys
@app.function(secrets=[modal.Secret.from_name("openai-secret")])
def process_with_openai():
    ...

# ✅ DO: Use Volumes v2 if caching is needed
volume = modal.Volume.from_name("embeddings-cache", create_if_missing=True)
```

### Data Flow

Local (raw text) → Modal (embed, then delete) → Local (vectors only)

### What NOT to Do

- ❌ Don't persist raw chat text in Modal Volumes (use local storage)
- ❌ Don't hardcode API keys in code
- ❌ Don't use Volumes v1 for sensitive data (use v2)
- ❌ Don't log sensitive content in function outputs

## Consequences

### Positive

- **Strong isolation**: gVisor provides defense-in-depth beyond standard containers
- **Verified compliance**: SOC 2 Type II provides third-party validation
- **Data minimization**: short retention (7 days max) reduces exposure window
- **No data access**: explicit policy against accessing customer data
- **Cost efficient**: pay only for compute time used

### Negative

- **Limited to open models**: no access to proprietary SOTA embeddings (Voyage, OpenAI); dependent on open-weights ecosystem
- **Vendor lock-in**: Modal-specific Python decorators in codebase
- **Trust required**: still relying on Modal's policy adherence
- **Limited audit trail**: ephemeral compute makes forensics harder if needed

### Neutral

- **Shared responsibility**: must implement own backup/recovery
- **Enterprise features require upgrade**: BAA and advanced controls need Enterprise plan

## Alternatives Analysis

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Modal** | SOC 2 Type II, gVisor isolation, full model control, pay-per-use | Limited to open/fine-tuned models; more setup than API | ✅ Selected (if GPU needed) |
| **Voyage API** | SOTA retrieval quality (proprietary models), zero-day retention opt-out | Data trains models unless opted out; no model customization | ⚠️ Viable for embeddings |
| **OpenAI Embeddings API** | Simple integration, ZDR available on request | 30-day default retention; ZDR requires enterprise contact | ⚠️ Viable with ZDR |
| **Local GPU (VRAM-constrained)** | Full control, no external trust, no ongoing cost | VRAM limits batch size; must quantize larger models | ⚠️ Viable for small batches |
| **Local CPU-only** | Full control, no external trust, runs anywhere | 10-100x slower; impractical for large datasets | ❌ Too slow |

## References

- [Modal Security Documentation](https://modal.com/docs/guide/security)
- [Modal Trust Portal](https://trust.modal.com)
- [Modal Data Processing Addendum](https://modal.com/legal/dpa)
- [Modal HIPAA Blog Post](https://modal.com/blog/hipaa)
- [gVisor Project](https://gvisor.dev/)
- [ADR-001: Agentic Architecture](adr-001-agentic-architecture.md)

## Changelog

| Date | Change |
|------|--------|
| 2025-12-27 | Renumbered from ADR-001; status changed to Contingent per agentic architecture shift |
| 2025-12-27 | Initial decision |

---

*Format: [MADR](https://adr.github.io/madr/)*
