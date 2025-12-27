# Chat Retrospective

Explore your AI conversation history to surface patterns in what you reached for, how you framed problems, and what threads you kept returning to.

## Documentation

```
docs/
├── spec.md                     # What we're building
├── design-review-checklist.md  # Review guide for design docs
├── adr/                        # Why we made key decisions
│   ├── 001-agentic-architecture.md
│   ├── 002-local-state-only.md
│   ├── 003-offline-artifacts.md
│   └── 004-modal-data-safety.md
└── design/
    └── design.md               # How we're building it (derived)
```

**spec.md** and **adr/** are source of truth. **design/** is derived. Regenerate it from the spec when implementation approach changes.
