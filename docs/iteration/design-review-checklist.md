# Design Doc Review

## Spec Coverage

Walk each section of spec.md and verify the design addresses it:

- [ ] All output types covered (visualization, reflection, learning)
- [ ] All session modes covered (first, incremental, refresh)
- [ ] Export formats handled (ChatGPT, Claude)
- [ ] Privacy constraints satisfied
- [ ] Artifact requirements met (self-contained HTML)
- [ ] Scale constraints addressed (10k conversations)
- [ ] Success criteria measurable in the design

## ADR Compliance

- [ ] Uses SDK built-in tools per ADR-001
- [ ] State is local-only per ADR-002
- [ ] HTML artifacts self-contained per ADR-003
- [ ] GPU compute via Modal if used per ADR-004

## Functional Review

Not a checklist. Read for:

- Does the data flow make sense end-to-end?
- Are there gaps where the design says "TBD" or is vague?
- Would you be able to implement this without asking clarifying questions?
- Do the components have clear responsibilities and interfaces?

## Ops Readiness

### SDK & Dependencies

- [ ] Verified against current SDK documentation (APIs change)
- [ ] Tooling choice justified (built-in vs MCP vs custom Python)
- [ ] Dependency versions pinned or ranges specified
- [ ] SDK limitations acknowledged

### Resilience

- [ ] API timeout/error handling
- [ ] Rate limiting strategy
- [ ] Malformed input handling
- [ ] Corrupt state recovery
- [ ] User interrupt (Ctrl+C) behavior
- [ ] Partial progress preserved on failure

### Session Management

- [ ] Session resumption mechanics specified
- [ ] Checkpoint frequency for long operations
- [ ] State schema versioning (for future migrations)

### Agent Coordination

- [ ] Subagent handoff protocol (context in, findings out)
- [ ] Side effects isolated (who can write state)
- [ ] Duplicate work prevention
- [ ] Context window management for long sessions

### Observability

- [ ] Logging approach specified
- [ ] Privacy constraints on logs (no conversation content)
- [ ] Usage/cost reporting to user
- [ ] Debugging without exposing sensitive data

### Testing

- [ ] Unit test strategy for custom components
- [ ] Integration test approach for agent behavior
- [ ] Test fixtures for export formats
- [ ] Evaluation criteria for agent output quality

### Error UX

- [ ] User-facing error messages (actionable, not stack traces)
- [ ] Recovery instructions when applicable
- [ ] Graceful degradation where possible
