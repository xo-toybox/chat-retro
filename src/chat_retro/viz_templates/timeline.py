"""Timeline visualization: conversation frequency over time."""


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
    const container = document.getElementById('visualization');

    if (data.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:80px 20px;color:#6b7280;font-family:system-ui,-apple-system,sans-serif"><p style="font-size:16px;margin:0">No timeline data available</p></div>';
        return;
    }

    // Parse dates
    const parseDate = d3.timeParse("%Y-%m-%d");
    const parsedData = data.map(d => ({date: parseDate(d.date), count: d.count})).filter(d => d.date !== null);
    if (parsedData.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:80px 20px;color:#6b7280;font-family:system-ui">Could not parse dates</div>';
        return;
    }

    // Dimensions
    const margin = {top: 60, right: 40, bottom: 60, left: 60};
    const width = Math.min(container.clientWidth || 800, 960) - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    container.innerHTML = '';
    const svg = d3.select('#visualization')
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Gradient
    const defs = svg.append('defs');
    const grad = defs.append('linearGradient').attr('id', 'areaGrad').attr('x1', '0%').attr('y1', '0%').attr('x2', '0%').attr('y2', '100%');
    grad.append('stop').attr('offset', '0%').attr('stop-color', '#8b5cf6').attr('stop-opacity', 0.4);
    grad.append('stop').attr('offset', '100%').attr('stop-color', '#8b5cf6').attr('stop-opacity', 0.05);

    // Scales
    const x = d3.scaleTime().domain(d3.extent(parsedData, d => d.date)).range([0, width]);
    const y = d3.scaleLinear().domain([0, d3.max(parsedData, d => d.count) * 1.1]).nice().range([height, 0]);

    // Grid
    svg.append('g').attr('class', 'grid').selectAll('line').data(y.ticks(5)).enter().append('line')
        .attr('x1', 0).attr('x2', width).attr('y1', d => y(d)).attr('y2', d => y(d))
        .attr('stroke', '#f3f4f6').attr('stroke-width', 1);

    // Area + Line
    const area = d3.area().x(d => x(d.date)).y0(height).y1(d => y(d.count)).curve(d3.curveMonotoneX);
    const line = d3.line().x(d => x(d.date)).y(d => y(d.count)).curve(d3.curveMonotoneX);
    svg.append('path').datum(parsedData).attr('fill', 'url(#areaGrad)').attr('d', area);
    svg.append('path').datum(parsedData).attr('fill', 'none').attr('stroke', '#8b5cf6').attr('stroke-width', 2.5).attr('stroke-linejoin', 'round').attr('d', line);

    // Axes
    svg.append('g').attr('transform', `translate(0,${height})`).call(d3.axisBottom(x).ticks(6).tickFormat(d3.timeFormat('%b %d')).tickSize(0).tickPadding(10))
        .call(g => g.select('.domain').attr('stroke', '#e5e7eb'))
        .call(g => g.selectAll('text').attr('fill', '#6b7280').style('font-size', '11px'));
    svg.append('g').call(d3.axisLeft(y).ticks(5).tickSize(-width).tickPadding(10))
        .call(g => g.select('.domain').remove())
        .call(g => g.selectAll('.tick line').attr('stroke', '#f3f4f6'))
        .call(g => g.selectAll('text').attr('fill', '#6b7280').style('font-size', '11px'));

    // Labels
    svg.append('text').attr('x', width / 2).attr('y', height + 45).attr('text-anchor', 'middle').attr('fill', '#9ca3af').style('font-size', '12px').text('Date');
    svg.append('text').attr('transform', 'rotate(-90)').attr('x', -height / 2).attr('y', -45).attr('text-anchor', 'middle').attr('fill', '#9ca3af').style('font-size', '12px').text('Conversations');

    // Title + Summary
    const total = d3.sum(parsedData, d => d.count);
    const avg = (total / parsedData.length).toFixed(1);
    svg.append('text').attr('x', 0).attr('y', -35).attr('fill', '#111827').style('font-size', '18px').style('font-weight', '600').text('Conversation Activity');
    svg.append('text').attr('x', 0).attr('y', -15).attr('fill', '#6b7280').style('font-size', '13px').text(`${total} total conversations · ${avg} avg per day`);

    // Tooltip
    const tooltip = d3.select('#visualization').append('div')
        .style('position', 'absolute').style('background', '#1f2937').style('color', '#fff').style('padding', '12px 16px')
        .style('border-radius', '8px').style('font-size', '13px').style('font-family', 'system-ui').style('box-shadow', '0 10px 25px -5px rgba(0,0,0,0.2)')
        .style('pointer-events', 'none').style('opacity', 0).style('transition', 'opacity 0.15s');

    // Dots
    svg.selectAll('.dot').data(parsedData).enter().append('circle').attr('class', 'dot')
        .attr('cx', d => x(d.date)).attr('cy', d => y(d.count)).attr('r', 5)
        .attr('fill', '#8b5cf6').attr('stroke', '#fff').attr('stroke-width', 2).style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            d3.select(this).transition().duration(100).attr('r', 8);
            tooltip.style('opacity', 1).html(`<div style="font-weight:600;margin-bottom:4px">${d3.timeFormat('%B %d, %Y')(d.date)}</div><div style="color:#c4b5fd">${d.count} conversation${d.count !== 1 ? 's' : ''}</div>`)
                .style('left', (event.pageX + 15) + 'px').style('top', (event.pageY - 50) + 'px');
        })
        .on('mouseout', function() {
            d3.select(this).transition().duration(100).attr('r', 5);
            tooltip.style('opacity', 0);
        });
})();
"""
