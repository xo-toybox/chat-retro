"""Heatmap visualization: usage by hour and weekday."""

from __future__ import annotations

from datetime import datetime
from typing import Any


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
    def prepare_data(conversations: list[dict[str, Any]]) -> dict[str, Any]:
        """Convert raw conversations to heatmap data.

        Args:
            conversations: List of conversation dicts with 'create_time' or 'created_at'

        Returns:
            Data dict with 'heatmap' key containing day/hour/count entries
        """
        # Initialize 7x24 grid
        counts: dict[tuple[int, int], int] = {}

        for conv in conversations:
            timestamp = conv.get("create_time") or conv.get("created_at")
            if timestamp is None:
                continue

            # Convert timestamp to datetime
            if isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    continue
            else:
                continue

            # Get weekday (0=Monday in Python, we want 0=Sunday)
            weekday = (dt.weekday() + 1) % 7
            hour = dt.hour

            key = (weekday, hour)
            counts[key] = counts.get(key, 0) + 1

        # Convert to list format
        heatmap = [
            {"day": day, "hour": hour, "count": count}
            for (day, hour), count in sorted(counts.items())
        ]

        return {"heatmap": heatmap}

    @staticmethod
    def get_js_code() -> str:
        """Return D3.js code for heatmap visualization.

        The code expects DATA.heatmap to be an array of {day, hour, count} objects.
        """
        return """
(function() {
    const data = DATA.heatmap || [];
    const container = document.getElementById('visualization');
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

    // Dimensions
    const margin = {top: 80, right: 40, bottom: 60, left: 70};
    const cellSize = 28;
    const width = 24 * cellSize;
    const height = 7 * cellSize;

    // Build lookup
    const countMap = new Map();
    data.forEach(d => countMap.set(`${d.day}-${d.hour}`, d.count));
    const maxCount = d3.max(data, d => d.count) || 1;
    const totalCount = d3.sum(data, d => d.count);

    container.innerHTML = '';
    const svg = d3.select('#visualization')
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Color scale - purple theme
    const colorScale = d3.scaleSequential(t => d3.interpolate('#f3e8ff', '#7c3aed')(t)).domain([0, maxCount]);

    // Scales
    const x = d3.scaleBand().domain(d3.range(24)).range([0, width]).padding(0.08);
    const y = d3.scaleBand().domain(d3.range(7)).range([0, height]).padding(0.08);

    // Draw cells
    for (let day = 0; day < 7; day++) {
        for (let hour = 0; hour < 24; hour++) {
            const count = countMap.get(`${day}-${hour}`) || 0;
            svg.append('rect')
                .attr('x', x(hour)).attr('y', y(day)).attr('width', x.bandwidth()).attr('height', y.bandwidth())
                .attr('fill', count > 0 ? colorScale(count) : '#f9fafb')
                .attr('stroke', '#fff').attr('stroke-width', 2).attr('rx', 4)
                .attr('data-day', day).attr('data-hour', hour).attr('data-count', count)
                .style('cursor', 'pointer').style('transition', 'opacity 0.1s');
        }
    }

    // X axis (hours)
    svg.append('g').attr('transform', `translate(0,${height + 8})`)
        .selectAll('text').data([0, 6, 12, 18, 23]).enter().append('text')
        .attr('x', d => x(d) + x.bandwidth() / 2).attr('y', 0).attr('text-anchor', 'middle')
        .attr('fill', '#6b7280').style('font-size', '11px')
        .text(d => d === 0 ? '12am' : d === 6 ? '6am' : d === 12 ? '12pm' : d === 18 ? '6pm' : '11pm');

    // Y axis (days)
    svg.append('g').attr('transform', 'translate(-12, 0)')
        .selectAll('text').data(d3.range(7)).enter().append('text')
        .attr('x', 0).attr('y', d => y(d) + y.bandwidth() / 2).attr('dy', '0.35em').attr('text-anchor', 'end')
        .attr('fill', '#6b7280').style('font-size', '11px').text(d => days[d]);

    // Title
    svg.append('text').attr('x', 0).attr('y', -55).attr('fill', '#111827').style('font-size', '18px').style('font-weight', '600').text('Usage by Day & Hour');
    svg.append('text').attr('x', 0).attr('y', -35).attr('fill', '#6b7280').style('font-size', '13px').text(`${totalCount} total conversations`);

    // Legend
    const legendW = 120, legendH = 8, legendX = width - legendW;
    const defs = svg.append('defs');
    const grad = defs.append('linearGradient').attr('id', 'heatLegend');
    [0, 0.5, 1].forEach(t => grad.append('stop').attr('offset', t * 100 + '%').attr('stop-color', colorScale(t * maxCount)));
    svg.append('rect').attr('x', legendX).attr('y', -55).attr('width', legendW).attr('height', legendH).attr('rx', 4).style('fill', 'url(#heatLegend)');
    svg.append('text').attr('x', legendX - 5).attr('y', -49).attr('text-anchor', 'end').attr('fill', '#9ca3af').style('font-size', '10px').text('0');
    svg.append('text').attr('x', legendX + legendW + 5).attr('y', -49).attr('text-anchor', 'start').attr('fill', '#9ca3af').style('font-size', '10px').text(maxCount);

    // Tooltip
    const tooltip = d3.select('#visualization').append('div')
        .style('position', 'absolute').style('background', '#1f2937').style('color', '#fff').style('padding', '12px 16px')
        .style('border-radius', '8px').style('font-size', '13px').style('font-family', 'system-ui').style('box-shadow', '0 10px 25px -5px rgba(0,0,0,0.2)')
        .style('pointer-events', 'none').style('opacity', 0).style('transition', 'opacity 0.15s');

    svg.selectAll('rect')
        .on('mouseover', function(event) {
            const day = +this.getAttribute('data-day');
            const hour = +this.getAttribute('data-hour');
            const count = +this.getAttribute('data-count');
            const hourStr = hour === 0 ? '12am' : hour < 12 ? hour + 'am' : hour === 12 ? '12pm' : (hour - 12) + 'pm';
            d3.select(this).style('opacity', 0.8);
            tooltip.style('opacity', 1).html(`<div style="font-weight:600;margin-bottom:4px">${days[day]} at ${hourStr}</div><div style="color:#c4b5fd">${count} conversation${count !== 1 ? 's' : ''}</div>`)
                .style('left', (event.pageX + 15) + 'px').style('top', (event.pageY - 50) + 'px');
        })
        .on('mouseout', function() {
            d3.select(this).style('opacity', 1);
            tooltip.style('opacity', 0);
        });
})();
"""
