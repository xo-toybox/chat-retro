"""Length distribution visualization: conversation length histogram."""


from typing import Any


class LengthDistributionViz:
    """D3.js histogram showing distribution of conversation lengths.

    Expected data format:
    {
        "distribution": [
            {"bin": "1-5", "min": 1, "max": 5, "count": 20},
            {"bin": "6-10", "min": 6, "max": 10, "count": 35},
            ...
        ],
        "stats": {
            "total": 100,
            "min": 1,
            "max": 50,
            "mean": 12.5,
            "median": 10
        }
    }
    """

    @staticmethod
    def prepare_data(
        conversations: list[dict[str, Any]],
        bin_size: int = 5,
    ) -> dict[str, Any]:
        """Convert conversations to length distribution data.

        Args:
            conversations: List of conversation dicts with 'mapping' (messages)
            bin_size: Size of each histogram bin

        Returns:
            Data dict with 'distribution' and 'stats'
        """
        # Extract conversation lengths (number of messages)
        lengths: list[int] = []

        for conv in conversations:
            # Try different structures for message count
            if "mapping" in conv and isinstance(conv["mapping"], dict):
                # ChatGPT format: mapping is dict of message nodes
                length = len(conv["mapping"]) or 1
            elif "messages" in conv and isinstance(conv["messages"], list):
                # Alternative format with messages list
                length = len(conv["messages"]) or 1
            else:
                # Fallback: count any list-like content
                length = 1

            lengths.append(length)

        if not lengths:
            return {"distribution": [], "stats": {}}

        # Calculate statistics
        sorted_lengths = sorted(lengths)
        total = len(lengths)
        min_len = min(lengths)
        max_len = max(lengths)
        mean = sum(lengths) / total
        median = sorted_lengths[total // 2] if total % 2 == 1 else (
            sorted_lengths[total // 2 - 1] + sorted_lengths[total // 2]
        ) / 2

        # Create bins
        bins: dict[int, int] = {}  # bin_start -> count
        for length in lengths:
            bin_start = ((length - 1) // bin_size) * bin_size + 1
            bins[bin_start] = bins.get(bin_start, 0) + 1

        # Convert to list format
        distribution = []
        for bin_start in sorted(bins.keys()):
            bin_end = bin_start + bin_size - 1
            distribution.append({
                "bin": f"{bin_start}-{bin_end}",
                "min": bin_start,
                "max": bin_end,
                "count": bins[bin_start],
            })

        return {
            "distribution": distribution,
            "stats": {
                "total": total,
                "min": min_len,
                "max": max_len,
                "mean": round(mean, 1),
                "median": median,
            },
        }

    @staticmethod
    def get_js_code() -> str:
        """Return D3.js code for length distribution visualization.

        The code expects DATA.distribution and DATA.stats.
        """
        return """
(function() {
    const data = DATA.distribution || [];
    const stats = DATA.stats || {};
    const container = document.getElementById('visualization');

    if (data.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:80px 20px;color:#6b7280;font-family:system-ui"><p style="font-size:16px;margin:0">No length data available</p></div>';
        return;
    }

    // Dimensions
    const margin = {top: 70, right: 40, bottom: 70, left: 60};
    const width = Math.min(container.clientWidth || 800, 900) - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;

    container.innerHTML = '';
    const svg = d3.select('#visualization')
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .style('font-family', 'system-ui, -apple-system, sans-serif')
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Scales
    const x = d3.scaleBand().domain(data.map(d => d.bin)).range([0, width]).padding(0.2);
    const y = d3.scaleLinear().domain([0, d3.max(data, d => d.count) * 1.1]).nice().range([height, 0]);

    // Grid
    svg.append('g').selectAll('line').data(y.ticks(5)).enter().append('line')
        .attr('x1', 0).attr('x2', width).attr('y1', d => y(d)).attr('y2', d => y(d))
        .attr('stroke', '#f3f4f6').attr('stroke-width', 1);

    // Gradient
    const defs = svg.append('defs');
    const grad = defs.append('linearGradient').attr('id', 'barGrad').attr('x1', '0%').attr('y1', '0%').attr('x2', '0%').attr('y2', '100%');
    grad.append('stop').attr('offset', '0%').attr('stop-color', '#8b5cf6');
    grad.append('stop').attr('offset', '100%').attr('stop-color', '#6366f1');

    // Bars
    svg.selectAll('.bar').data(data).enter().append('rect').attr('class', 'bar')
        .attr('x', d => x(d.bin)).attr('y', d => y(d.count)).attr('width', x.bandwidth()).attr('height', d => height - y(d.count))
        .attr('fill', 'url(#barGrad)').attr('rx', 4).style('cursor', 'pointer').style('transition', 'opacity 0.1s');

    // Axes
    svg.append('g').attr('transform', `translate(0,${height})`).call(d3.axisBottom(x).tickSize(0).tickPadding(12))
        .call(g => g.select('.domain').attr('stroke', '#e5e7eb'))
        .call(g => g.selectAll('text').attr('fill', '#6b7280').style('font-size', '11px').attr('transform', data.length > 8 ? 'rotate(-45)' : '').style('text-anchor', data.length > 8 ? 'end' : 'middle'));
    svg.append('g').call(d3.axisLeft(y).ticks(5).tickSize(-width).tickPadding(10))
        .call(g => g.select('.domain').remove())
        .call(g => g.selectAll('.tick line').attr('stroke', '#f3f4f6'))
        .call(g => g.selectAll('text').attr('fill', '#6b7280').style('font-size', '11px'));

    // Labels
    svg.append('text').attr('x', width / 2).attr('y', height + 55).attr('text-anchor', 'middle').attr('fill', '#9ca3af').style('font-size', '12px').text('Messages per Conversation');
    svg.append('text').attr('transform', 'rotate(-90)').attr('x', -height / 2).attr('y', -45).attr('text-anchor', 'middle').attr('fill', '#9ca3af').style('font-size', '12px').text('Conversations');

    // Title
    svg.append('text').attr('x', 0).attr('y', -45).attr('fill', '#111827').style('font-size', '18px').style('font-weight', '600').text('Conversation Length Distribution');
    svg.append('text').attr('x', 0).attr('y', -25).attr('fill', '#6b7280').style('font-size', '13px').text(`${stats.total} conversations · avg ${stats.mean} messages`);

    // Stats card
    const card = svg.append('g').attr('transform', `translate(${width - 130}, 0)`);
    card.append('rect').attr('width', 130).attr('height', 90).attr('fill', '#f9fafb').attr('rx', 8);
    const items = [{l: 'Min', v: stats.min}, {l: 'Max', v: stats.max}, {l: 'Mean', v: stats.mean}, {l: 'Median', v: stats.median}];
    items.forEach((item, i) => {
        card.append('text').attr('x', 12).attr('y', 22 + i * 18).attr('fill', '#6b7280').style('font-size', '11px').text(item.l);
        card.append('text').attr('x', 118).attr('y', 22 + i * 18).attr('text-anchor', 'end').attr('fill', '#111827').style('font-size', '12px').style('font-weight', '600').text(item.v);
    });

    // Tooltip
    const tooltip = d3.select('#visualization').append('div')
        .style('position', 'absolute').style('background', '#1f2937').style('color', '#fff').style('padding', '12px 16px')
        .style('border-radius', '8px').style('font-size', '13px').style('font-family', 'system-ui').style('box-shadow', '0 10px 25px -5px rgba(0,0,0,0.2)')
        .style('pointer-events', 'none').style('opacity', 0).style('transition', 'opacity 0.15s');

    svg.selectAll('.bar')
        .on('mouseover', function(event, d) {
            d3.select(this).style('opacity', 0.85);
            tooltip.style('opacity', 1).html(`<div style="font-weight:600;margin-bottom:4px">${d.bin} messages</div><div style="color:#c4b5fd">${d.count} conversation${d.count !== 1 ? 's' : ''}</div>`)
                .style('left', (event.pageX + 15) + 'px').style('top', (event.pageY - 50) + 'px');
        })
        .on('mouseout', function() {
            d3.select(this).style('opacity', 1);
            tooltip.style('opacity', 0);
        });
})();
"""
