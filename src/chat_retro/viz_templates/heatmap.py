"""Heatmap visualization: usage by hour and weekday."""

from __future__ import annotations


class HeatmapViz:
    """D3.js heatmap showing usage patterns by hour and weekday.

    Expected data format:
    {
        "heatmap": [
            {"day": 0, "hour": 9, "count": 5},  # Sunday 9am
            ...
        ]
    }

    Day: 0=Sunday, 6=Saturday
    Hour: 0-23
    """

    @staticmethod
    def prepare_data(conversations: list[dict]) -> dict:
        """Convert raw conversations to heatmap data."""
        # TODO: Implement in viz-heatmap feature
        return {"heatmap": []}

    @staticmethod
    def get_js_code() -> str:
        """Return D3.js code for heatmap visualization."""
        return "document.getElementById('visualization').innerHTML = '<p>Heatmap visualization not yet implemented.</p>';"
