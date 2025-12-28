"""Claude Code CLI runner for issue workflow.

Executes Claude Code in non-interactive mode via subprocess.
Uses subscription pricing instead of API per-token costs.

See ADR-006 for migration rationale.
"""

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _extract_json_from_markdown(text: str) -> str | None:
    """Extract JSON from markdown code blocks.

    Handles formats like:
    ```json
    {...}
    ```
    or just:
    ```
    {...}
    ```

    Returns the first valid JSON found, or None.
    """
    # Try to find JSON in code blocks
    patterns = [
        r"```json\s*\n([\s\S]*?)\n```",  # ```json ... ```
        r"```\s*\n([\s\S]*?)\n```",  # ``` ... ```
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                json.loads(match.strip())
                return match.strip()
            except json.JSONDecodeError:
                continue

    return None


@dataclass
class RunResult:
    """Result from Claude Code CLI execution."""

    success: bool
    output: str
    error: str | None = None
    usage: dict | None = None
    parsed_data: dict | None = None  # Parsed JSON if output was valid JSON


class ClaudeCodeRunner:
    """Run Claude Code CLI in non-interactive mode.

    Uses `claude -p` for single-shot execution with JSON output.
    Each invocation is a fresh session (no cross-step memory).
    """

    def __init__(self, cwd: Path | None = None, max_turns: int = 10):
        """Initialize runner.

        Args:
            cwd: Working directory for Claude Code. Defaults to current directory.
            max_turns: Maximum agent iterations before stopping.
        """
        self.cwd = cwd or Path.cwd()
        self.max_turns = max_turns

    def run(
        self,
        prompt: str,
        allowed_tools: list[str] | None = None,
        timeout: int | None = 300,
        expected_fields: list[str] | None = None,
    ) -> RunResult:
        """Execute claude -p and return result.

        Args:
            prompt: The prompt to send to Claude.
            allowed_tools: List of tools to allow (e.g., ['Read', 'Grep']).
            timeout: Timeout in seconds. Default 5 minutes.
            expected_fields: List of field names to validate in JSON response.
                If provided, logs a warning when fields are missing.

        Returns:
            RunResult with success status, output, and optional error/usage info.
        """
        cmd = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--max-turns",
            str(self.max_turns),
        ]

        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                success=False,
                output="",
                error=f"Timeout after {timeout} seconds",
            )
        except FileNotFoundError:
            return RunResult(
                success=False,
                output="",
                error="Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code",
            )

        if result.returncode != 0:
            return RunResult(
                success=False,
                output="",
                error=result.stderr or f"Exit code {result.returncode}",
            )

        try:
            data = json.loads(result.stdout)

            # Claude CLI returns a JSON array with multiple event objects.
            # Find the result event (type='result') to extract output.
            if isinstance(data, list):
                result_event = next(
                    (item for item in data if item.get("type") == "result"),
                    None,
                )
                if result_event is None:
                    return RunResult(
                        success=False,
                        output="",
                        error="No result event in CLI output",
                    )
                output = result_event.get("result", "")
                usage = result_event.get("usage")
                is_error = result_event.get("is_error", False)
                if is_error:
                    return RunResult(
                        success=False,
                        output=output,
                        error=output or "Agent returned error",
                    )
            else:
                # Fallback for dict format (legacy or future changes)
                output = data.get("result", "")
                usage = data.get("usage")

            # Try to parse agent output as JSON for validation
            parsed_data = None
            if output:
                # First try direct JSON parse
                try:
                    parsed_data = json.loads(output)
                except json.JSONDecodeError:
                    # Try extracting JSON from markdown code blocks
                    extracted = _extract_json_from_markdown(output)
                    if extracted:
                        try:
                            parsed_data = json.loads(extracted)
                        except json.JSONDecodeError:
                            pass

                # Validate expected fields if specified
                if parsed_data and expected_fields and isinstance(parsed_data, dict):
                    missing = [f for f in expected_fields if f not in parsed_data]
                    if missing:
                        logger.warning(
                            "Agent response missing expected fields: %s",
                            ", ".join(missing),
                        )

            return RunResult(
                success=True,
                output=output,
                usage=usage,
                parsed_data=parsed_data,
            )
        except json.JSONDecodeError as e:
            # Sometimes output isn't JSON (error messages, etc.)
            return RunResult(
                success=False,
                output=result.stdout,
                error=f"JSON parse error: {e}",
            )
