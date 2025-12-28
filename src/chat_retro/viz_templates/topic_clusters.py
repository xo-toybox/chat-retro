"""Topic clusters visualization: force-directed topic graph."""


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
    const container = document.getElementById('visualization');

    if (nodes.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:80px 20px;color:#6b7280;font-family:system-ui"><p style="font-size:16px;margin:0">No topic data available</p></div>';
        return;
    }

    const width = Math.min(container.clientWidth || 800, 960);
    const height = 520;

    container.innerHTML = '';
    const svg = d3.select('#visualization')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .style('font-family', 'system-ui, -apple-system, sans-serif');

    // Modern color palette
    const colors = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#6366f1', '#14b8a6'];
    const color = d3.scaleOrdinal(colors);

    const maxCount = d3.max(nodes, d => d.count) || 1;
    const radiusScale = d3.scaleSqrt().domain([1, maxCount]).range([12, 40]);

    // Simulation
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(120))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2 + 20))
        .force('collision', d3.forceCollide().radius(d => radiusScale(d.count) + 8));

    // Links
    const link = svg.append('g').selectAll('line').data(links).enter().append('line')
        .attr('stroke', '#e5e7eb').attr('stroke-width', d => Math.sqrt(d.value) * 1.5);

    // Nodes
    const node = svg.append('g').selectAll('g').data(nodes).enter().append('g')
        .style('cursor', 'grab')
        .call(d3.drag().on('start', dragstarted).on('drag', dragged).on('end', dragended));

    // Node circles with shadow
    node.append('circle')
        .attr('r', d => radiusScale(d.count))
        .attr('fill', d => color(d.group))
        .attr('stroke', '#fff')
        .attr('stroke-width', 3)
        .style('filter', 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))');

    // Node labels
    node.append('text')
        .text(d => d.id.length > 12 ? d.id.slice(0, 11) + '…' : d.id)
        .attr('x', 0)
        .attr('y', d => radiusScale(d.count) + 16)
        .attr('text-anchor', 'middle')
        .attr('fill', '#374151')
        .style('font-size', '12px')
        .style('font-weight', '500');

    // Tooltip
    const tooltip = d3.select('#visualization').append('div')
        .style('position', 'absolute').style('background', '#1f2937').style('color', '#fff').style('padding', '12px 16px')
        .style('border-radius', '8px').style('font-size', '13px').style('font-family', 'system-ui').style('box-shadow', '0 10px 25px -5px rgba(0,0,0,0.2)')
        .style('pointer-events', 'none').style('opacity', 0).style('transition', 'opacity 0.15s').style('max-width', '200px');

    node.on('mouseover', function(event, d) {
        d3.select(this).select('circle').transition().duration(100).attr('stroke-width', 4);
        tooltip.style('opacity', 1)
            .html(`<div style="font-weight:600;margin-bottom:6px">${d.id}</div><div style="color:#9ca3af;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px">${d.type}</div><div style="color:#c4b5fd">${d.count} conversation${d.count !== 1 ? 's' : ''}</div>`)
            .style('left', (event.pageX + 15) + 'px').style('top', (event.pageY - 60) + 'px');
    }).on('mouseout', function() {
        d3.select(this).select('circle').transition().duration(100).attr('stroke-width', 3);
        tooltip.style('opacity', 0);
    });

    // Title
    svg.append('text').attr('x', 24).attr('y', 32).attr('fill', '#111827').style('font-size', '18px').style('font-weight', '600').text('Topic Clusters');
    svg.append('text').attr('x', 24).attr('y', 52).attr('fill', '#6b7280').style('font-size', '13px').text(`${nodes.length} topics · ${links.length} connections`);

    // Legend
    const types = [...new Set(nodes.map(d => d.type))];
    const legend = svg.append('g').attr('transform', `translate(${width - 140}, 28)`);
    legend.append('rect').attr('x', -12).attr('y', -12).attr('width', 130).attr('height', types.length * 24 + 16).attr('fill', '#f9fafb').attr('rx', 8);
    types.forEach((type, i) => {
        const g = legend.append('g').attr('transform', `translate(0, ${i * 24})`);
        g.append('circle').attr('r', 6).attr('fill', color(nodes.find(n => n.type === type)?.group || 0));
        g.append('text').attr('x', 14).attr('y', 4).attr('fill', '#374151').style('font-size', '12px').text(type);
    });

    // Tick
    simulation.on('tick', () => {
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('transform', d => `translate(${Math.max(50, Math.min(width - 50, d.x))},${Math.max(70, Math.min(height - 30, d.y))})`);
    });

    function dragstarted(event) { if (!event.active) simulation.alphaTarget(0.3).restart(); event.subject.fx = event.subject.x; event.subject.fy = event.subject.y; d3.select(this).style('cursor', 'grabbing'); }
    function dragged(event) { event.subject.fx = event.x; event.subject.fy = event.y; }
    function dragended(event) { if (!event.active) simulation.alphaTarget(0); event.subject.fx = null; event.subject.fy = null; d3.select(this).style('cursor', 'grab'); }
})();
"""
