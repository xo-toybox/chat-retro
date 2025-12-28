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

    // Set up dimensions
    const container = document.getElementById('visualization');
    const margin = {top: 50, right: 30, bottom: 50, left: 80};
    const cellSize = 30;
    const width = 24 * cellSize;
    const height = 7 * cellSize;

    // Days and hours
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const hours = Array.from({length: 24}, (_, i) => i);

    // Build lookup for counts
    const countMap = new Map();
    data.forEach(d => countMap.set(`${d.day}-${d.hour}`, d.count));
    const maxCount = d3.max(data, d => d.count) || 1;

    // Clear and create SVG
    container.innerHTML = '';
    const svg = d3.select('#visualization')
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Color scale
    const colorScale = d3.scaleSequential(d3.interpolateBlues)
        .domain([0, maxCount]);

    // X scale (hours)
    const x = d3.scaleBand()
        .domain(hours)
        .range([0, width])
        .padding(0.05);

    // Y scale (days)
    const y = d3.scaleBand()
        .domain(d3.range(7))
        .range([0, height])
        .padding(0.05);

    // Draw cells
    for (let day = 0; day < 7; day++) {
        for (let hour = 0; hour < 24; hour++) {
            const count = countMap.get(`${day}-${hour}`) || 0;
            svg.append('rect')
                .attr('x', x(hour))
                .attr('y', y(day))
                .attr('width', x.bandwidth())
                .attr('height', y.bandwidth())
                .attr('fill', count > 0 ? colorScale(count) : '#f0f0f0')
                .attr('stroke', '#fff')
                .attr('stroke-width', 1)
                .attr('rx', 2)
                .attr('data-day', day)
                .attr('data-hour', hour)
                .attr('data-count', count);
        }
    }

    // X axis (hours)
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).tickValues([0, 6, 12, 18, 23]).tickFormat(d => {
            if (d === 0) return '12am';
            if (d === 6) return '6am';
            if (d === 12) return '12pm';
            if (d === 18) return '6pm';
            return '11pm';
        }));

    // Y axis (days)
    svg.append('g')
        .call(d3.axisLeft(y).tickFormat(d => days[d]));

    // Title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', -25)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('font-weight', 'bold')
        .text('Conversations by Day and Hour');

    // Subtitle
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', -10)
        .attr('text-anchor', 'middle')
        .style('font-size', '11px')
        .style('fill', '#666')
        .text('Darker = more conversations');

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

    svg.selectAll('rect')
        .on('mouseover', function(event) {
            const day = +this.getAttribute('data-day');
            const hour = +this.getAttribute('data-hour');
            const count = +this.getAttribute('data-count');
            const hourStr = hour === 0 ? '12am' : hour < 12 ? hour + 'am' : hour === 12 ? '12pm' : (hour - 12) + 'pm';

            tooltip.transition().duration(200).style('opacity', 1);
            tooltip.html(`<strong>${days[day]} ${hourStr}</strong><br/>${count} conversation${count !== 1 ? 's' : ''}`)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
            tooltip.transition().duration(200).style('opacity', 0);
        });

    // Add legend
    const legendWidth = 150;
    const legendHeight = 10;
    const legendX = width - legendWidth;
    const legendY = -35;

    const legendScale = d3.scaleLinear()
        .domain([0, maxCount])
        .range([0, legendWidth]);

    const legendAxis = d3.axisBottom(legendScale)
        .ticks(3)
        .tickSize(legendHeight + 3);

    // Legend gradient
    const defs = svg.append('defs');
    const gradient = defs.append('linearGradient')
        .attr('id', 'legend-gradient');

    gradient.selectAll('stop')
        .data([0, 0.25, 0.5, 0.75, 1])
        .enter()
        .append('stop')
        .attr('offset', d => d * 100 + '%')
        .attr('stop-color', d => colorScale(d * maxCount));

    svg.append('rect')
        .attr('x', legendX)
        .attr('y', legendY)
        .attr('width', legendWidth)
        .attr('height', legendHeight)
        .style('fill', 'url(#legend-gradient)');
})();
"""
