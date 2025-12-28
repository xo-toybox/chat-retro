"""Usage tracking for chat-retro sessions."""


import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from claude_code_sdk import ResultMessage


@dataclass
class ErrorRecord:
    """Record of an error during session."""

    timestamp: str
    error_type: str
    message: str
    turn: int


@dataclass
class TurnTiming:
    """Timing data for a single turn."""

    turn_number: int
    latency_seconds: float
    timestamp: str


@dataclass
class UsageReport:
    """Track costs, tokens, latency, and errors across session."""

    session_id: str = ""
    total_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    turns: int = 0
    turn_timings: list[TurnTiming] = field(default_factory=list)
    errors: list[ErrorRecord] = field(default_factory=list)
    session_start: float = field(default_factory=time.time)
    _processed_ids: set[str] = field(default_factory=set, repr=False)
    _turn_start: float | None = field(default=None, repr=False)

    def update_from_result(self, msg: "ResultMessage") -> None:
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

    def start_turn(self) -> None:
        """Mark the start of a turn for timing."""
        self._turn_start = time.time()

    def end_turn(self) -> None:
        """Record turn completion and latency."""
        if self._turn_start is not None:
            latency = time.time() - self._turn_start
            timing = TurnTiming(
                turn_number=len(self.turn_timings) + 1,
                latency_seconds=latency,
                timestamp=datetime.now().isoformat(),
            )
            self.turn_timings.append(timing)
            self._turn_start = None

    def record_error(self, error: Exception) -> None:
        """Record an error that occurred during the session."""
        record = ErrorRecord(
            timestamp=datetime.now().isoformat(),
            error_type=type(error).__name__,
            message=str(error),
            turn=self.turns,
        )
        self.errors.append(record)

    @property
    def total_latency_seconds(self) -> float:
        """Total time spent waiting for agent responses."""
        return sum(t.latency_seconds for t in self.turn_timings)

    @property
    def avg_latency_seconds(self) -> float:
        """Average latency per turn."""
        if not self.turn_timings:
            return 0.0
        return self.total_latency_seconds / len(self.turn_timings)

    @property
    def session_duration_seconds(self) -> float:
        """Total session duration from start to now."""
        return time.time() - self.session_start

    def summary(self) -> str:
        """Return formatted usage summary."""
        total_tokens = self.input_tokens + self.output_tokens
        parts = [
            f"Session {self.session_id[:8] if self.session_id else 'unknown'}...",
            f"${self.total_cost_usd:.4f}",
            f"{total_tokens:,} tokens",
            f"{self.turns} turns",
        ]
        if self.turn_timings:
            parts.append(f"{self.avg_latency_seconds:.1f}s avg latency")
        if self.errors:
            parts.append(f"{len(self.errors)} errors")
        return " | ".join(parts)

    def detailed_summary(self) -> dict:
        """Return detailed metrics as a dictionary for logging/export."""
        return {
            "session_id": self.session_id,
            "cost_usd": self.total_cost_usd,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "cache_read": self.cache_read_tokens,
                "total": self.input_tokens + self.output_tokens,
            },
            "turns": self.turns,
            "timing": {
                "total_latency_seconds": self.total_latency_seconds,
                "avg_latency_seconds": self.avg_latency_seconds,
                "session_duration_seconds": self.session_duration_seconds,
                "per_turn": [
                    {
                        "turn": t.turn_number,
                        "latency_seconds": t.latency_seconds,
                        "timestamp": t.timestamp,
                    }
                    for t in self.turn_timings
                ],
            },
            "errors": [
                {
                    "timestamp": e.timestamp,
                    "type": e.error_type,
                    "message": e.message,
                    "turn": e.turn,
                }
                for e in self.errors
            ],
        }
