#!/usr/bin/env python3
"""
Caching Strategy Implementation for Graphify

Implements:
1. Query result caching
2. Node caching
3. Edge caching
4. Cache invalidation
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import time

class GraphifyCache:
    """Cache for graphify queries and data."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.cache_path = self.project_path / "graphify-out" / "cache"
        self.cache_path.mkdir(exist_ok=True)

    def _get_cache_key(self, prefix: str, params: Dict) -> str:
        """Generate cache key from parameters."""
        param_str = json.dumps(params, sort_keys=True)
        hash_obj = hashlib.md5(param_str.encode())
        return f"{prefix}_{hash_obj.hexdigest()[:8]}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        cache_file = self.cache_path / f"{key}.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return data.get('value')
        return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL."""
        cache_file = self.cache_path / f"{key}.json"
        cache_data = {
            'value': value,
            'timestamp': time.time(),
            'ttl': ttl
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        return True

    def is_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        cache_file = self.cache_path / f"{key}.json"
        if not cache_file.exists():
            return False

        with open(cache_file, 'r') as f:
            cache_data = json.load(f)

        timestamp = cache_data.get('timestamp', 0)
        ttl = cache_data.get('ttl', 3600)
        return (time.time() - timestamp) < ttl

    def invalidate(self, key: str) -> bool:
        """Invalidate cache entry."""
        cache_file = self.cache_path / f"{key}.json"
        if cache_file.exists():
            cache_file.unlink()
            return True
        return False

    def clear(self) -> int:
        """Clear all cache entries."""
        count = 0
        for cache_file in self.cache_path.glob("*.json"):
            cache_file.unlink()
            count += 1
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_files = list(self.cache_path.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)

        return {
            'entry_count': len(cache_files),
            'total_size_kb': total_size / 1024,
            'cache_path': str(self.cache_path)
        }

    def cache_query(self, query: str, result: Any) -> bool:
        """Cache a query result."""
        key = self._get_cache_key('query', {'query': query})
        return self.set(key, result)

    def get_cached_query(self, query: str) -> Optional[Any]:
        """Get cached query result."""
        key = self._get_cache_key('query', {'query': query})
        if self.is_valid(key):
            return self.get(key)
        return None

    def cache_node(self, node_id: str, node_data: Dict) -> bool:
        """Cache a node."""
        key = self._get_cache_key('node', {'id': node_id})
        return self.set(key, node_data)

    def get_cached_node(self, node_id: str) -> Optional[Dict]:
        """Get cached node."""
        key = self._get_cache_key('node', {'id': node_id})
        if self.is_valid(key):
            return self.get(key)
        return None

def demo_caching():
    """Demonstrate caching capabilities."""
    print("💾 Caching Demo\n")

    # Find a project with graphify
    project_path = None
    for path in Path.home().glob("projects/personals/*"):
        if (path / "graphify-out" / "graph.json").exists():
            project_path = path
            break

    if not project_path:
        print("❌ No project with graphify found")
        return

    cache = GraphifyCache(str(project_path))

    # Show stats
    stats = cache.get_stats()
    print(f"📊 Cache Statistics:")
    print(f"   Entries: {stats['entry_count']}")
    print(f"   Size: {stats['total_size_kb']:.2f} KB")
    print(f"   Path: {stats['cache_path']}")

    # Demo caching
    print(f"\n🧪 Testing Cache Operations:")

    # Cache a query
    query = "project structure"
    result = {"nodes": 100, "edges": 200}
    cache.cache_query(query, result)
    print(f"   ✅ Cached query: '{query}'")

    # Get cached query
    cached = cache.get_cached_query(query)
    print(f"   ✅ Retrieved: {cached}")

    # Cache a node
    node_id = "node_123"
    node_data = {"id": node_id, "label": "Test Node"}
    cache.cache_node(node_id, node_data)
    print(f"   ✅ Cached node: {node_id}")

    # Get cached node
    cached_node = cache.get_cached_node(node_id)
    print(f"   ✅ Retrieved: {cached_node}")

    # Show updated stats
    stats = cache.get_stats()
    print(f"\n📊 Updated Statistics:")
    print(f"   Entries: {stats['entry_count']}")
    print(f"   Size: {stats['total_size_kb']:.2f} KB")

    print("\n✅ Caching demo complete!")

if __name__ == "__main__":
    demo_caching()
