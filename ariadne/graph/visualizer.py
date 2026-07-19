"""GraphVisualizer formatting entity graphs into Rich trees, ASCII tables, and Mermaid markdown diagrams."""

from typing import List
from rich.tree import Tree
from ariadne.graph.models import GraphSnapshot


class GraphVisualizer:
    """Visualizes intelligence graph topology as rich console trees and Mermaid diagrams."""

    @staticmethod
    def to_rich_tree(snapshot: GraphSnapshot) -> Tree:
        """Render snapshot graph topology as a Rich Tree hierarchy for terminal display."""
        nodes_map = {n.canonical_id: n for n in snapshot.nodes}
        root_nodes = [n for n in snapshot.nodes if n.entity_type == "target"]
        if not root_nodes and snapshot.nodes:
            root_nodes = [snapshot.nodes[0]]

        tree = Tree(f"[bold cyan]Graph Snapshot v{snapshot.version}[/bold cyan] ([green]{snapshot.target_id}[/green])")
        for root in root_nodes:
            root_branch = tree.add(f"[bold yellow]🎯 {root.label}[/bold yellow] (`{root.canonical_id}`)")
            edges = [e for e in snapshot.edges if e.source_id == root.canonical_id]
            for edge in edges:
                dst = nodes_map.get(edge.target_id)
                dst_label = dst.label if dst else edge.target_id
                color = "green" if edge.weight >= 0.75 else ("yellow" if edge.weight >= 0.45 else "red")
                root_branch.add(
                    f"[{color}]──({edge.relation_type}: {edge.weight:.2f})──>[/{color}] [bold white]{dst_label}[/bold white] (`{edge.target_id}`)"
                )
        return tree

    @staticmethod
    def to_mermaid(snapshot: GraphSnapshot) -> str:
        """Generate a Mermaid flowchart diagram string suitable for Obsidian knowledge notes."""
        lines = ["flowchart TD"]
        for node in snapshot.nodes:
            label_clean = node.label.replace('"', "'")
            shape_start = "([" if node.entity_type == "target" else "["
            shape_end = "])" if node.entity_type == "target" else "]"
            lines.append(f'    {node.canonical_id.replace(":", "_")}{shape_start}"{label_clean}"{shape_end}')

        for edge in snapshot.edges:
            src = edge.source_id.replace(":", "_")
            dst = edge.target_id.replace(":", "_")
            lines.append(f'    {src} -->|"{edge.relation_type} ({edge.weight:.2f})"| {dst}')

        return "\n".join(lines)
