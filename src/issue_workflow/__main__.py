"""Allow running as `python -m issue_workflow`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
