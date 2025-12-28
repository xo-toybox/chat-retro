"""Timeline visualization: conversation frequency over time."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TimelineDataPoint:
    """Single data point for timeline visualization."""

    date: str  # ISO date string (YYYY-MM-DD)
    count: int  # Number of conversations on this date


class TimelineViz:
    """D3.js timeline showing conversation frequency over time.

    Expected data format:
    {
        "timeline": [
            {"date": "2024-01-15", "count": 5},
            {"date": "2024-01-16", "count": 3},
            ...
        ]
    }
    """

    @staticmethod
    def prepare_data(conversations: list[dict[str, Any]]) -> dict[str, Any]:
        """Convert raw conversations to timeline data.

        Args:
            conversations: List of conversation dicts with 'create_time' or 'created_at'

        Returns:
            Data dict with 'timeline' key containing date/count pairs
        """
        date_counts: dict[str, int] = {}

        for conv in conversations:
            # Handle different export formats
            timestamp = conv.get("create_time") or conv.get("created_at")
            if timestamp is None:
                continue

            # Convert timestamp to date string
            if isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
            elif isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    continue
            else:
                continue

            date_str = dt.strftime("%Y-%m-%d")
            date_counts[date_str] = date_counts.get(date_str, 0) + 1

        # Sort by date
        timeline = [
            {"date": date, "count": count}
            for date, count in sorted(date_counts.items())
        ]

        return {"timeline": timeline}

    @staticmethod
    def get_js_code() -> str:
        """Return D3.js code for timeline visualization.

        The code expects DATA.timeline to be an array of {date, count} objects.
        """
        return """
(function() {
    const data = DATA.timeline || [];
    if (data.length === 0) {
        document.getElementById('visualization').innerHTML = '<p>No timeline data available.</p>';
        return;
    }

    // Parse dates and find ranges
    const parseDate = d3.timeParse("%Y-%m-%d");
    const parsedData = data.map(d => ({
        date: parseDate(d.date),
        count: d.count
    })).filter(d => d.date !== null);

    if (parsedData.length === 0) {
        document.getElementById('visualization').innerHTML = '<p>Could not parse timeline dates.</p>';
        return;
    }

    // Set up dimensions
    const container = document.getElementById('visualization');
    const margin = {top: 20, right: 30, bottom: 50, left: 50};
    const width = Math.min(container.clientWidth || 800, 1000) - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    // Clear and create SVG
    container.innerHTML = '';
    const svg = d3.select('#visualization')
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // X scale (time)
    const x = d3.scaleTime()
        .domain(d3.extent(parsedData, d => d.date))
        .range([0, width]);

    // Y scale (count)
    const y = d3.scaleLinear()
        .domain([0, d3.max(parsedData, d => d.count)])
        .nice()
        .range([height, 0]);

    // Area generator
    const area = d3.area()
        .x(d => x(d.date))
        .y0(height)
        .y1(d => y(d.count))
        .curve(d3.curveMonotoneX);

    // Line generator
    const line = d3.line()
        .x(d => x(d.date))
        .y(d => y(d.count))
        .curve(d3.curveMonotoneX);

    // Draw area
    svg.append('path')
        .datum(parsedData)
        .attr('fill', 'rgba(66, 133, 244, 0.3)')
        .attr('d', area);

    // Draw line
    svg.append('path')
        .datum(parsedData)
        .attr('fill', 'none')
        .attr('stroke', '#4285f4')
        .attr('stroke-width', 2)
        .attr('d', line);

    // Draw dots
    svg.selectAll('.dot')
        .data(parsedData)
        .enter()
        .append('circle')
        .attr('class', 'dot')
        .attr('cx', d => x(d.date))
        .attr('cy', d => y(d.count))
        .attr('r', 4)
        .attr('fill', '#4285f4')
        .attr('stroke', 'white')
        .attr('stroke-width', 2);

    // X axis
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x)
            .ticks(Math.min(parsedData.length, 10))
            .tickFormat(d3.timeFormat("%b %d")))
        .selectAll('text')
        .attr('transform', 'rotate(-45)')
        .style('text-anchor', 'end');

    // Y axis
    svg.append('g')
        .call(d3.axisLeft(y).ticks(5));

    // Y axis label
    svg.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', -40)
        .attr('x', -height / 2)
        .attr('text-anchor', 'middle')
        .style('font-size', '12px')
        .text('Conversations');

    // Title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', -5)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('font-weight', 'bold')
        .text('Conversation Frequency Over Time');

    // Tooltip
    const tooltip = d3.select('#visualization')
        .append('div')
        .style('position', 'absolute')
        .style('background', 'rgba(0,0,0,0.8)')
        .style('color', 'white')
        .style('padding', '8px 12px')
        .style('border-radius', '4px')
        .style('font-size', '12px')
        .style('pointer-events', 'none')
        .style('opacity', 0);

    svg.selectAll('.dot')
        .on('mouseover', function(event, d) {
            tooltip.transition().duration(200).style('opacity', 1);
            tooltip.html(`<strong>${d3.timeFormat("%B %d, %Y")(d.date)}</strong><br/>${d.count} conversation${d.count !== 1 ? 's' : ''}`)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
            tooltip.transition().duration(200).style('opacity', 0);
        });
})();
"""
