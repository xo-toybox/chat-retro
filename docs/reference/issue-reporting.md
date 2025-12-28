# Issue Reporting Reference

Issue reporting enables both auto-capture of errors and manual bug reports. All issues flow through the same pipeline.

## Architecture

```
Auto-reports (state corruption, etc.)  ─┐
                                        ├─→ IssueReporter.save_draft_issue()
Manual reports (issue-workflow report-bug) ─┘
                                        │
                                        ↓
                            .chat-retro-runtime/issue-drafts/
                                        │
                                        ↓
                            issue-workflow process
```

## Shared Module

`IssueReporter` lives in `src/shared/issue_reporter.py` and is used by both `chat_retro` (auto-reports) and `issue_workflow` (manual reports, draft management).

```python
from shared import IssueReporter

reporter = IssueReporter()
reporter.save_draft_issue(
    title="State corruption: Invalid JSON",
    description="state.json failed to load...",
    category="bug",
    context={"error_type": "JSONDecodeError"},
)
```

## Auto-Report Triggers

| Trigger | Location | Category |
|---------|----------|----------|
| State corruption | `state.py:_report_corruption()` | bug |

Future hooks can add more triggers (tool failures, validation denials, etc.).

## Manual CLI

```bash
# Interactive bug report
issue-workflow report-bug

# List pending drafts
issue-workflow drafts

# Process drafts through pipeline
issue-workflow process
```

## Draft Format

Drafts use the shared `Issue` schema from `src/shared/issue_types.py`:

```json
{
  "id": "abc123...",
  "title": "Bug title",
  "description": "Details...",
  "category": "bug",
  "status": "draft",
  "context": {"schema_version": 1, "pattern_count": 5},
  "created": "2025-12-28T10:00:00",
  "updated": "2025-12-28T10:00:00"
}
```

## Storage

| Path | Contents | Git Status |
|------|----------|------------|
| `.chat-retro-runtime/issue-drafts/` | Raw drafts with sensitive context | gitignored |
| `.chat-retro-runtime/issues/` | Sanitized public issues | tracked |

## Adding Auto-Report Hooks

To add a new auto-report trigger:

1. Import `IssueReporter` from `shared`
2. Call `save_draft_issue()` at the error point
3. Include relevant context for debugging

Example pattern:
```python
from shared import IssueReporter

def _handle_error(error_type: str, detail: str) -> None:
    reporter = IssueReporter()
    reporter.save_draft_issue(
        title=f"Error: {error_type}",
        description=detail,
        category="bug",
        context={"error_type": error_type},
    )
```

## Related

- [ADR-005: Agentic Issue Workflow](../foundations/adr/adr-005-agentic-issue-workflow.md)
- [Runtime Files](./runtime-files.md)
