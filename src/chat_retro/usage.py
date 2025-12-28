"""Usage tracking for chat-retro sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from claude_code_sdk import ResultMessage


@dataclass
class UsageReport:
    """Track costs and tokens across session."""

    session_id: str = ""
    total_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    turns: int = 0
    _processed_ids: set[str] = field(default_factory=set, repr=False)

    def update_from_result(self, msg: ResultMessage) -> None:
        """Update from ResultMessage (contains cumulative totals).

        Note: Multiple messages with same session_id report identical usage,
        so we track processed IDs to avoid double-counting in edge cases.
        """
        # ResultMessage contains cumulative values, so just overwrite
        self.session_id = msg.session_id
        self.total_cost_usd = msg.total_cost_usd or 0.0
        self.turns = msg.num_turns

        if msg.usage:
            self.input_tokens = msg.usage.get("input_tokens", 0)
            self.output_tokens = msg.usage.get("output_tokens", 0)
            self.cache_read_tokens = msg.usage.get("cache_read_input_tokens", 0)

    def summary(self) -> str:
        """Return formatted usage summary."""
        total_tokens = self.input_tokens + self.output_tokens
        return (
            f"Session {self.session_id[:8] if self.session_id else 'unknown'}... | "
            f"${self.total_cost_usd:.4f} | "
            f"{total_tokens:,} tokens | "
            f"{self.turns} turns"
        )
