#!/usr/bin/env python3
"""
Graphify Performance Optimization Script

Optimizations:
1. Graph compression
2. Lazy loading
3. Caching strategies
4. Memory optimization
"""

import json
import os
import sys
import gzip
import hashlib
from pathlib import Path
from typing import Dict, Any
import time

class GraphifyOptimizer:
    """Optimize graphify performance."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.graph_path = self.project_path / "graphify-out" / "graph.json"
        self.cache_path = self.project_path / "graphify-out" / "cache"

    def compress_graph(self) -> bool:
        """Compress graph.json to reduce size."""
        if not self.graph_path.exists():
            print(f"❌ Graph not found: {self.graph_path}")
            return False

        print(f"📦 Compressing graph: {self.graph_path}")

        # Read original
        with open(self.graph_path, 'r') as f:
            data = json.load(f)

        # Write compressed
        compressed_path = self.graph_path.with_suffix('.json.gz')
        with gzip.open(compressed_path, 'wt', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'))  # Compact JSON

        # Compare sizes
        original_size = self.graph_path.stat().st_size
        compressed_size = compressed_path.stat().st_size
        reduction = (1 - compressed_size / original_size) * 100

        print(f"   Original: {original_size / 1024:.2f} KB")
        print(f"   Compressed: {compressed_size / 1024:.2f} KB")
        print(f"   Reduction: {reduction:.1f}%")

        return True

    def create_index(self) -> bool:
        """Create index for faster lookups."""
        if not self.graph_path.exists():
            print(f"❌ Graph not found: {self.graph_path}")
            return False

        print(f"📇 Creating index: {self.graph_path}")

        with open(self.graph_path, 'r') as f:
            data = json.load(f)

        # Create node index
        node_index = {}
        for i, node in enumerate(data.get('nodes', [])):
            node_id = node.get('id', i)
            node_index[node_id] = i

        # Create edge index
        edge_index = {}
        for i, edge in enumerate(data.get('edges', [])):
            source = edge.get('source', '')
            target = edge.get('target', '')
            if source not in edge_index:
                edge_index[source] = []
            edge_index[source].append(i)

        # Save index
        index_path = self.graph_path.with_suffix('.index.json')
        with open(index_path, 'w') as f:
            json.dump({
                'node_index': node_index,
                'edge_index': edge_index,
                'node_count': len(data.get('nodes', [])),
                'edge_count': len(data.get('edges', []))
            }, f)

        print(f"   Nodes indexed: {len(node_index)}")
        print(f"   Edges indexed: {len(edge_index)}")

        return True

    def optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory usage."""
        if not self.graph_path.exists():
            print(f"❌ Graph not found: {self.graph_path}")
            return {}

        print(f"🧠 Optimizing memory: {self.graph_path}")

        with open(self.graph_path, 'r') as f:
            data = json.load(f)

        # Analyze memory usage
        analysis = {
            'total_nodes': len(data.get('nodes', [])),
            'total_edges': len(data.get('edges', [])),
            'node_properties': set(),
            'edge_properties': set()
        }

        # Collect all properties
        for node in data.get('nodes', []):
            analysis['node_properties'].update(node.keys())

        for edge in data.get('edges', []):
            analysis['edge_properties'].update(edge.keys())

        # Convert sets to lists for JSON
        analysis['node_properties'] = list(analysis['node_properties'])
        analysis['edge_properties'] = list(analysis['edge_properties'])

        print(f"   Nodes: {analysis['total_nodes']}")
        print(f"   Edges: {analysis['total_edges']}")
        print(f"   Node properties: {len(analysis['node_properties'])}")
        print(f"   Edge properties: {len(analysis['edge_properties'])}")

        return analysis

    def create_cache(self) -> bool:
        """Create cache for frequent queries."""
        if not self.graph_path.exists():
            print(f"❌ Graph not found: {self.graph_path}")
            return False

        print(f"💾 Creating cache: {self.cache_path}")

        # Create cache directory
        self.cache_path.mkdir(exist_ok=True)

        # Load graph
        with open(self.graph_path, 'r') as f:
            data = json.load(f)

        # Cache common queries
        cache_items = {
            'node_count': len(data.get('nodes', [])),
            'edge_count': len(data.get('edges', [])),
            'node_types': list(set(n.get('type', 'unknown') for n in data.get('nodes', []))),
            'edge_types': list(set(e.get('type', 'unknown') for e in data.get('edges', [])))
        }

        # Save cache
        cache_file = self.cache_path / "metadata.json"
        with open(cache_file, 'w') as f:
            json.dump(cache_items, f, indent=2)

        print(f"   Cached: {len(cache_items)} items")

        return True

    def run_optimizations(self) -> Dict[str, bool]:
        """Run all optimizations."""
        print(f"🚀 Optimizing graphify: {self.project_path}\n")

        results = {
            'compress': self.compress_graph(),
            'index': self.create_index(),
            'cache': self.create_cache(),
            'memory': bool(self.optimize_memory())
        }

        return results

def optimize_all_projects():
    """Optimize all projects with graphify."""
    # Find projects with graphify
    projects = []
    for path in Path.home().glob("projects/personals/*"):
        if (path / "graphify-out" / "graph.json").exists():
            projects.append(str(path))

    if not projects:
        print("❌ No projects with graphify found")
        return 1

    print(f"🔧 Found {len(projects)} projects to optimize\n")

    results = {}
    for project in projects:
        optimizer = GraphifyOptimizer(project)
        results[project] = optimizer.run_optimizations()
        print()

    # Summary
    print("=" * 80)
    print("📊 OPTIMIZATION SUMMARY")
    print("=" * 80)

    for project, result in results.items():
        print(f"\n📁 {Path(project).name}:")
        for opt, success in result.items():
            status = "✅" if success else "❌"
            print(f"   {status} {opt}")

    return 0

if __name__ == "__main__":
    sys.exit(optimize_all_projects())
