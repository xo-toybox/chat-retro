# ADR-003: Offline HTML Artifacts

| Status | Date |
|--------|------|
| Accepted | 2025-12-27 |

## Context

The project produces various outputs including HTML visualizations of conversation analysis. When the user requests an explorable visualization artifact, it needs to be viewable after the analysis session ends.

This ADR applies specifically to HTML visualization outputs. Other output types (markdown reflections, text insights) don't require these constraints.

## Decision

HTML visualization artifacts are single, fully self-contained files with no external dependencies.

## Requirements

| Requirement | Implementation |
|-------------|----------------|
| No network requests | All JS/CSS inlined |
| Works from filesystem | No server required; `file://` compatible |
| Long-term viewable | No CDN dependencies that could break |
| Single file | Easy to save, share, archive |

## Implementation

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Chat Retrospective - 2025-09</title>
  <style>
    /* All CSS inlined */
  </style>
</head>
<body>
  <div id="app"></div>
  
  <script>
    /* All JS inlined (including libraries like D3) */
  </script>
  
  <script>
    const DATA = {
      /* Analysis data embedded as JSON */
    };
  </script>
  
  <script>
    /* Visualization code */
  </script>
</body>
</html>
```

## Rationale

### Privacy

Artifact is derived from sensitive conversation data. External network requests:
- Could leak timing/usage information
- Could fail and break the artifact
- Are unnecessary for a personal tool

### Longevity

User should be able to open an artifact years later:
- CDNs may change URLs or go offline
- Library versions may be removed
- Self-contained file has no external failure modes

### Simplicity

Single file means:
- One thing to save
- One thing to back up
- One thing to share (if desired)
- No folder structure to maintain

## Trade-offs Accepted

| Trade-off | Assessment |
|-----------|------------|
| Larger file size (500KB–2MB) | Acceptable for personal tool |
| Agent must inline libraries | Solved problem; well-documented patterns |
| Harder to update visualization code | Regenerate artifact instead |

## Alternatives Considered

### CDN Dependencies

```html
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
```

**Rejected because:**
- Network requests from sensitive-data artifact
- Breaks when offline or CDN unavailable
- Not archival-stable

### Hybrid (CDN with Fallback)

**Rejected because:**
- Added complexity
- Still makes network requests by default
- Marginal file size benefit not worth it

### Separate Data + Viewer

```
retrospective-2025-09/
├── data.json
└── viewer.html
```

**Rejected because:**
- Two files to manage
- Easy to separate and break
- No significant benefit

## Consequences

### Positive

- Works offline, forever
- No privacy leakage via network
- Single file to manage
- Archival-stable

### Negative

- Larger file size
- Libraries must be inlined (agent complexity)
- Can't benefit from cached CDN resources

## Implementation Notes

### Recommended Libraries (Inline-Friendly)

| Library | Size (minified) | Use Case |
|---------|-----------------|----------|
| D3.js | ~250KB | Complex visualizations |
| Chart.js | ~200KB | Standard charts |
| Vanilla JS | 0KB | Simple interactions |

### Agent Instructions

When generating artifacts, agent should:
1. Use minimal library set needed for visualization
2. Inline all dependencies
3. Embed data as JSON in script tag
4. Test that output renders from `file://`

## References

- [ADR-001: Agentic Architecture](adr-001-agentic-architecture.md)
- [ADR-002: Local State Only](adr-002-local-state-only.md)
