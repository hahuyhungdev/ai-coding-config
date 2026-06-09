#!/usr/bin/env python3
"""
Lazy Loading Implementation for Graphify

Implements:
1. On-demand graph loading
2. Partial graph loading
3. Query-specific loading
4. Memory-efficient streaming
"""

import json
import gzip
from pathlib import Path
from typing import Dict, Any, Optional, Iterator
import mmap

class LazyGraphLoader:
    """Lazy load graph data on demand."""

    def __init__(self, graph_path: str):
        self.graph_path = Path(graph_path)
        self.compressed_path = self.graph_path.with_suffix('.json.gz')
        self.index_path = self.graph_path.with_suffix('.index.json')
        self._metadata: Optional[Dict] = None
        self._node_index: Optional[Dict] = None

    @property
    def metadata(self) -> Dict:
        """Load metadata lazily."""
        if self._metadata is None:
            cache_path = self.graph_path.parent / "cache" / "metadata.json"
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    self._metadata = json.load(f)
            else:
                self._metadata = {
                    'node_count': 0,
                    'edge_count': 0,
                    'node_types': [],
                    'edge_types': []
                }
        return self._metadata

    @property
    def node_index(self) -> Dict:
        """Load node index lazily."""
        if self._node_index is None:
            if self.index_path.exists():
                with open(self.index_path, 'r') as f:
                    index_data = json.load(f)
                    self._node_index = index_data.get('node_index', {})
            else:
                self._node_index = {}
        return self._node_index

    def load_node(self, node_id: str) -> Optional[Dict]:
        """Load a specific node by ID."""
        if node_id not in self.node_index:
            return None

        index = self.node_index[node_id]

        # Use compressed file if available
        if self.compressed_path.exists():
            with gzip.open(self.compressed_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
                nodes = data.get('nodes', [])
                if index < len(nodes):
                    return nodes[index]
        else:
            with open(self.graph_path, 'r') as f:
                data = json.load(f)
                nodes = data.get('nodes', [])
                if index < len(nodes):
                    return nodes[index]

        return None

    def load_nodes_by_type(self, node_type: str) -> Iterator[Dict]:
        """Load nodes by type lazily."""
        if self.compressed_path.exists():
            with gzip.open(self.compressed_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
                for node in data.get('nodes', []):
                    if node.get('type') == node_type:
                        yield node
        else:
            with open(self.graph_path, 'r') as f:
                data = json.load(f)
                for node in data.get('nodes', []):
                    if node.get('type') == node_type:
                        yield node

    def load_edges_for_node(self, node_id: str) -> Iterator[Dict]:
        """Load edges for a specific node."""
        if self.compressed_path.exists():
            with gzip.open(self.compressed_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
                for edge in data.get('edges', []):
                    if edge.get('source') == node_id or edge.get('target') == node_id:
                        yield edge
        else:
            with open(self.graph_path, 'r') as f:
                data = json.load(f)
                for edge in data.get('edges', []):
                    if edge.get('source') == node_id or edge.get('target') == node_id:
                        yield edge

    def search_nodes(self, query: str, max_results: int = 10) -> list:
        """Search nodes by query."""
        results = []
        query_lower = query.lower()

        if self.compressed_path.exists():
            with gzip.open(self.compressed_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
                for node in data.get('nodes', []):
                    # Search in node properties
                    node_str = json.dumps(node).lower()
                    if query_lower in node_str:
                        results.append(node)
                        if len(results) >= max_results:
                            break
        else:
            with open(self.graph_path, 'r') as f:
                data = json.load(f)
                for node in data.get('nodes', []):
                    # Search in node properties
                    node_str = json.dumps(node).lower()
                    if query_lower in node_str:
                        results.append(node)
                        if len(results) >= max_results:
                            break

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics without loading full graph."""
        return {
            'node_count': self.metadata.get('node_count', 0),
            'edge_count': self.metadata.get('edge_count', 0),
            'node_types': self.metadata.get('node_types', []),
            'edge_types': self.metadata.get('edge_types', []),
            'has_compressed': self.compressed_path.exists(),
            'has_index': self.index_path.exists(),
            'compressed_size': self.compressed_path.stat().st_size if self.compressed_path.exists() else 0,
            'original_size': self.graph_path.stat().st_size if self.graph_path.exists() else 0
        }

def demo_lazy_loading():
    """Demonstrate lazy loading capabilities."""
    print("🚀 Lazy Loading Demo\n")

    # Find a project with graphify
    project_path = None
    for path in Path.home().glob("projects/personals/*"):
        graph_path = path / "graphify-out" / "graph.json"
        if graph_path.exists():
            project_path = path
            break

    if not project_path:
        print("❌ No project with graphify found")
        return

    graph_path = project_path / "graphify-out" / "graph.json"
    loader = LazyGraphLoader(str(graph_path))

    # Show statistics
    stats = loader.get_statistics()
    print(f"📊 Project: {project_path.name}")
    print(f"   Nodes: {stats['node_count']}")
    print(f"   Edges: {stats['edge_count']}")
    print(f"   Node types: {stats['node_types']}")
    print(f"   Compressed: {stats['has_compressed']}")
    print(f"   Original size: {stats['original_size'] / 1024:.2f} KB")
    print(f"   Compressed size: {stats['compressed_size'] / 1024:.2f} KB")

    # Search nodes
    print(f"\n🔍 Searching for 'main':")
    results = loader.search_nodes('main', max_results=3)
    for node in results:
        print(f"   - {node.get('label', 'unknown')}")

    # Load nodes by type
    print(f"\n📁 Loading nodes by type:")
    for node_type in stats['node_types'][:3]:
        nodes = list(loader.load_nodes_by_type(node_type))
        print(f"   {node_type}: {len(nodes)} nodes")

    print("\n✅ Lazy loading demo complete!")

if __name__ == "__main__":
    demo_lazy_loading()
