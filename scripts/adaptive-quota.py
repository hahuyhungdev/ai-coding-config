#!/usr/bin/env python3
"""
Adaptive Quota System for Graphify

Implements:
1. Project-size-based quota adjustment
2. Usage analytics
3. Quota optimization recommendations
4. Cache warming strategies
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import time
import fcntl
import tempfile

class AdaptiveQuota:
    """Adaptive quota system based on project size."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.graph_path = self.project_path / "graphify-out" / "graph.json"
        self.cache_path = self.project_path / "graphify-out" / "cache"
        self.quota_file = self.cache_path / "quota.json"

    def get_project_size(self) -> Dict[str, int]:
        """Get project size metrics."""
        file_count = 0
        total_size = 0

        for file_path in self.project_path.rglob("*"):
            if file_path.is_file():
                file_count += 1
                total_size += file_path.stat().st_size

        return {
            'file_count': file_count,
            'total_size_mb': total_size / 1024 / 1024
        }

    def calculate_adaptive_quota(self) -> int:
        """Calculate quota based on project size."""
        size = self.get_project_size()
        file_count = size['file_count']

        # Base quota
        base_quota = 3

        # Adjust based on file count
        if file_count < 1000:
            quota = base_quota
        elif file_count < 10000:
            quota = base_quota + 1
        elif file_count < 50000:
            quota = base_quota + 2
        else:
            quota = base_quota + 3

        # Adjust based on graph size
        if self.graph_path.exists():
            graph_size = self.graph_path.stat().st_size
            if graph_size > 10 * 1024 * 1024:  # > 10 MB
                quota += 1

        return quota

    def get_current_usage(self, session_id: str) -> int:
        """Get current quota usage for session."""
        safe = "".join(ch for ch in session_id if ch.isalnum() or ch in "-_")[:120]
        state_file = Path(tempfile.gettempdir()) / f"ai-coding-config-graphify-{safe}.count"

        try:
            with state_file.open("a+") as handle:
                fcntl.flock(handle, fcntl.LOCK_EX)
                handle.seek(0)
                try:
                    count = int(handle.read().strip() or "0")
                except ValueError:
                    count = 0
                fcntl.flock(handle, fcntl.LOCK_UN)
                return count
        except Exception:
            return 0

    def get_quota_analytics(self, session_id: str) -> Dict[str, Any]:
        """Get quota usage analytics."""
        usage = self.get_current_usage(session_id)
        quota = self.calculate_adaptive_quota()

        return {
            'session_id': session_id,
            'current_usage': usage,
            'max_quota': quota,
            'remaining': max(0, quota - usage),
            'usage_percent': (usage / quota * 100) if quota > 0 else 0,
            'project_size': self.get_project_size()
        }

    def get_optimization_recommendations(self, session_id: str) -> list:
        """Get quota optimization recommendations."""
        analytics = self.get_quota_analytics(session_id)
        recommendations = []

        if analytics['usage_percent'] > 80:
            recommendations.append({
                'type': 'warning',
                'message': 'Quota usage high. Consider starting a new session.',
                'priority': 'high'
            })

        if analytics['project_size']['file_count'] > 50000:
            recommendations.append({
                'type': 'info',
                'message': 'Large project detected. Use scoped queries for better results.',
                'priority': 'medium'
            })

        if analytics['remaining'] == 0:
            recommendations.append({
                'type': 'critical',
                'message': 'Quota exhausted. Start new session or use bypass.',
                'priority': 'high'
            })

        return recommendations

    def warm_cache(self) -> Dict[str, Any]:
        """Warm cache with common queries."""
        if not self.graph_path.exists():
            return {'status': 'error', 'message': 'Graph not found'}

        print(f"🔥 Warming cache for: {self.project_path}")

        with open(self.graph_path, 'r') as f:
            data = json.load(f)

        # Cache common metadata
        cache_items = {
            'node_count': len(data.get('nodes', [])),
            'edge_count': len(data.get('edges', [])),
            'node_types': list(set(n.get('type', 'unknown') for n in data.get('nodes', []))),
            'edge_types': list(set(e.get('type', 'unknown') for e in data.get('edges', []))),
            'project_path': str(self.project_path),
            'timestamp': time.time()
        }

        # Save to cache
        cache_file = self.cache_path / "metadata.json"
        self.cache_path.mkdir(exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(cache_items, f, indent=2)

        print(f"   ✅ Cached: {len(cache_items)} items")

        return {
            'status': 'success',
            'cached_items': len(cache_items),
            'cache_path': str(cache_file)
        }

    def track_cache_hit(self, query: str, hit: bool) -> None:
        """Track cache hit/miss metrics."""
        metrics_file = self.cache_path / "metrics.json"

        # Load existing metrics
        metrics = {}
        if metrics_file.exists():
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)

        # Update metrics
        if 'cache_hits' not in metrics:
            metrics['cache_hits'] = 0
            metrics['cache_misses'] = 0

        if hit:
            metrics['cache_hits'] += 1
        else:
            metrics['cache_misses'] += 1

        metrics['hit_rate'] = metrics['cache_hits'] / (metrics['cache_hits'] + metrics['cache_misses'])
        metrics['last_updated'] = time.time()

        # Save metrics
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)

    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache hit/miss metrics."""
        metrics_file = self.cache_path / "metrics.json"

        if not metrics_file.exists():
            return {
                'cache_hits': 0,
                'cache_misses': 0,
                'hit_rate': 0.0
            }

        with open(metrics_file, 'r') as f:
            return json.load(f)

def demo_adaptive_quota():
    """Demonstrate adaptive quota system."""
    print("📊 Adaptive Quota Demo\n")

    # Find a project with graphify
    project_path = None
    for path in Path.home().glob("projects/personals/*"):
        if (path / "graphify-out" / "graph.json").exists():
            project_path = path
            break

    if not project_path:
        print("❌ No project with graphify found")
        return

    quota_system = AdaptiveQuota(str(project_path))

    # Show project size
    size = quota_system.get_project_size()
    print(f"📁 Project: {project_path.name}")
    print(f"   Files: {size['file_count']}")
    print(f"   Size: {size['total_size_mb']:.2f} MB")

    # Show adaptive quota
    quota = quota_system.calculate_adaptive_quota()
    print(f"\n📊 Adaptive Quota:")
    print(f"   Base quota: 3")
    print(f"   Adjusted quota: {quota}")
    print(f"   Reason: Project size-based adjustment")

    # Show usage analytics
    session_id = "test-session-123"
    analytics = quota_system.get_quota_analytics(session_id)
    print(f"\n📈 Usage Analytics:")
    print(f"   Current usage: {analytics['current_usage']}")
    print(f"   Max quota: {analytics['max_quota']}")
    print(f"   Remaining: {analytics['remaining']}")
    print(f"   Usage: {analytics['usage_percent']:.1f}%")

    # Show recommendations
    recommendations = quota_system.get_optimization_recommendations(session_id)
    print(f"\n💡 Recommendations:")
    for rec in recommendations:
        print(f"   [{rec['priority'].upper()}] {rec['message']}")

    # Warm cache
    print(f"\n🔥 Warming Cache:")
    result = quota_system.warm_cache()
    print(f"   Status: {result['status']}")
    print(f"   Cached items: {result.get('cached_items', 0)}")

    # Show cache metrics
    metrics = quota_system.get_cache_metrics()
    print(f"\n📊 Cache Metrics:")
    print(f"   Hits: {metrics['cache_hits']}")
    print(f"   Misses: {metrics['cache_misses']}")
    print(f"   Hit rate: {metrics['hit_rate']:.1%}")

    print("\n✅ Adaptive quota demo complete!")

if __name__ == "__main__":
    demo_adaptive_quota()
