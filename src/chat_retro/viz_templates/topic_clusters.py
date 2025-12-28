"""Topic clusters visualization: force-directed topic graph."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class TopicClusterViz:
    """D3.js force-directed graph showing topic clusters.

    Expected data format:
    {
        "nodes": [{"id": "python", "group": 1, "count": 50}, ...],
        "links": [{"source": "python", "target": "debugging", "value": 10}, ...]
    }
    """

    @staticmethod
    def prepare_data(patterns: list[dict[str, Any]]) -> dict[str, Any]:
        """Convert patterns to topic cluster data.

        Args:
            patterns: List of pattern dicts with 'label', 'type', and 'conversation_ids'

        Returns:
            Data dict with 'nodes' and 'links' for force-directed graph
        """
        if not patterns:
            return {"nodes": [], "links": []}

        # Group patterns by type for coloring
        type_to_group: dict[str, int] = {}
        group_counter = 0

        nodes = []
        for pattern in patterns:
            label = pattern.get("label", "")
            if not label:
                continue

            pattern_type = pattern.get("type", "unknown")
            if pattern_type not in type_to_group:
                type_to_group[pattern_type] = group_counter
                group_counter += 1

            # Count is based on number of conversations
            conv_ids = pattern.get("conversation_ids", [])
            count = len(conv_ids) if isinstance(conv_ids, list) else 1

            nodes.append({
                "id": label,
                "group": type_to_group[pattern_type],
                "count": count,
                "type": pattern_type,
            })

        # Build links based on shared conversations
        # Patterns that appear in the same conversations are linked
        conv_to_patterns: dict[str, list[str]] = defaultdict(list)
        for pattern in patterns:
            label = pattern.get("label", "")
            if not label:
                continue
            for conv_id in pattern.get("conversation_ids", []):
                conv_to_patterns[conv_id].append(label)

        # Count co-occurrences
        link_counts: dict[tuple[str, str], int] = defaultdict(int)
        for labels in conv_to_patterns.values():
            if len(labels) < 2:
                continue
            # All pairs of patterns in this conversation
            for i, label1 in enumerate(labels):
                for label2 in labels[i + 1:]:
                    key = tuple(sorted([label1, label2]))
                    link_counts[key] += 1

        # Convert to links (only include significant links)
        links = [
            {"source": src, "target": tgt, "value": count}
            for (src, tgt), count in link_counts.items()
            if count >= 1  # Minimum co-occurrence threshold
        ]

        return {"nodes": nodes, "links": links}

    @staticmethod
    def get_js_code() -> str:
        """Return D3.js code for topic cluster visualization.

        The code expects DATA.nodes and DATA.links arrays.
        """
        return """
(function() {
    const nodes = DATA.nodes || [];
    const links = DATA.links || [];

    if (nodes.length === 0) {
        document.getElementById('visualization').innerHTML = '<p>No topic data available.</p>';
        return;
    }

    // Set up dimensions
    const container = document.getElementById('visualization');
    const width = Math.min(container.clientWidth || 800, 1000);
    const height = 500;

    // Clear and create SVG
    container.innerHTML = '';
    const svg = d3.select('#visualization')
        .append('svg')
        .attr('width', width)
        .attr('height', height);

    // Color scale for groups
    const color = d3.scaleOrdinal(d3.schemeCategory10);

    // Size scale for node radius
    const maxCount = d3.max(nodes, d => d.count) || 1;
    const radiusScale = d3.scaleSqrt()
        .domain([1, maxCount])
        .range([8, 30]);

    // Create simulation
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => radiusScale(d.count) + 5));

    // Draw links
    const link = svg.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(links)
        .enter()
        .append('line')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', d => Math.sqrt(d.value));

    // Draw nodes
    const node = svg.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(nodes)
        .enter()
        .append('g')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    // Node circles
    node.append('circle')
        .attr('r', d => radiusScale(d.count))
        .attr('fill', d => color(d.group))
        .attr('stroke', '#fff')
        .attr('stroke-width', 2);

    // Node labels
    node.append('text')
        .text(d => d.id)
        .attr('x', 0)
        .attr('y', d => radiusScale(d.count) + 12)
        .attr('text-anchor', 'middle')
        .style('font-size', '11px')
        .style('fill', '#333');

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

    node.on('mouseover', function(event, d) {
        tooltip.transition().duration(200).style('opacity', 1);
        tooltip.html(`<strong>${d.id}</strong><br/>Type: ${d.type}<br/>Conversations: ${d.count}`)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 28) + 'px');
    }).on('mouseout', function() {
        tooltip.transition().duration(200).style('opacity', 0);
    });

    // Title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', 20)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('font-weight', 'bold')
        .text('Topic Clusters');

    // Simulation tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }

    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }

    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }

    // Legend
    const types = [...new Set(nodes.map(d => d.type))];
    const legend = svg.append('g')
        .attr('transform', `translate(20, 40)`);

    types.forEach((type, i) => {
        const g = legend.append('g')
            .attr('transform', `translate(0, ${i * 20})`);

        g.append('circle')
            .attr('r', 6)
            .attr('fill', color(nodes.find(n => n.type === type)?.group || 0));

        g.append('text')
            .attr('x', 12)
            .attr('y', 4)
            .style('font-size', '11px')
            .text(type);
    });
})();
"""
