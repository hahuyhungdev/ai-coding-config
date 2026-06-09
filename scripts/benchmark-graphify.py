#!/usr/bin/env python3
"""
Graphify Performance Benchmark Script

Tests:
1. Graph loading time
2. Query execution time
3. Memory usage
4. Cache hit rates
5. Large codebase performance
"""

import json
import os
import sys
import time
import psutil
from pathlib import Path
from typing import Dict, List, Tuple
import statistics

class GraphifyBenchmark:
    """Benchmark graphify performance."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.graph_path = self.project_path / "graphify-out" / "graph.json"
        self.results: Dict[str, List[float]] = {
            "load_time": [],
            "query_time": [],
            "memory_usage": [],
            "file_count": [],
            "graph_size": []
        }

    def get_file_count(self) -> int:
        """Count files in project."""
        count = 0
        for _ in self.project_path.rglob("*"):
            if _.is_file():
                count += 1
        return count

    def get_graph_size(self) -> int:
        """Get graph.json size in bytes."""
        if self.graph_path.exists():
            return self.graph_path.stat().st_size
        return 0

    def measure_load_time(self, iterations: int = 5) -> float:
        """Measure graph loading time."""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            with open(self.graph_path, 'r') as f:
                data = json.load(f)
            end = time.perf_counter()
            times.append(end - start)
        return statistics.mean(times)

    def measure_memory_usage(self) -> float:
        """Measure memory usage during graph loading."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        with open(self.graph_path, 'r') as f:
            data = json.load(f)

        final_memory = process.memory_info().rss
        return (final_memory - initial_memory) / 1024 / 1024  # MB

    def measure_query_time(self, query: str, iterations: int = 3) -> float:
        """Measure query execution time."""
        # This would integrate with actual graphify query
        # For now, return placeholder
        return 0.0

    def run_benchmark(self) -> Dict:
        """Run complete benchmark."""
        print(f"🔍 Benchmarking: {self.project_path}")
        print(f"   Files: {self.get_file_count()}")
        print(f"   Graph size: {self.get_graph_size() / 1024:.2f} KB")

        # Measure load time
        load_time = self.measure_load_time()
        self.results["load_time"].append(load_time)
        print(f"   Load time: {load_time*1000:.2f} ms")

        # Measure memory usage
        memory = self.measure_memory_usage()
        self.results["memory_usage"].append(memory)
        print(f"   Memory usage: {memory:.2f} MB")

        # Store metrics
        self.results["file_count"].append(self.get_file_count())
        self.results["graph_size"].append(self.get_graph_size())

        return {
            "project": str(self.project_path),
            "file_count": self.get_file_count(),
            "graph_size_kb": self.get_graph_size() / 1024,
            "load_time_ms": load_time * 1000,
            "memory_mb": memory
        }

def benchmark_multiple_projects(projects: List[str]) -> List[Dict]:
    """Benchmark multiple projects."""
    results = []
    for project in projects:
        if Path(project).exists():
            benchmark = GraphifyBenchmark(project)
            result = benchmark.run_benchmark()
            results.append(result)
            print()
    return results

def analyze_results(results: List[Dict]) -> Dict:
    """Analyze benchmark results."""
    if not results:
        return {}

    file_counts = [r["file_count"] for r in results]
    load_times = [r["load_time_ms"] for r in results]
    memory_usages = [r["memory_mb"] for r in results]

    analysis = {
        "total_projects": len(results),
        "avg_file_count": statistics.mean(file_counts),
        "avg_load_time_ms": statistics.mean(load_times),
        "avg_memory_mb": statistics.mean(memory_usages),
        "max_file_count": max(file_counts),
        "max_load_time_ms": max(load_times),
        "max_memory_mb": max(memory_usages),
        "min_load_time_ms": min(load_times),
        "min_memory_mb": min(memory_usages)
    }

    return analysis

def print_report(results: List[Dict], analysis: Dict):
    """Print benchmark report."""
    print("\n" + "=" * 80)
    print("📊 GRAPHIFY PERFORMANCE BENCHMARK REPORT")
    print("=" * 80)

    print(f"\n📈 Summary:")
    print(f"   Total projects: {analysis.get('total_projects', 0)}")
    print(f"   Average file count: {analysis.get('avg_file_count', 0):.0f}")
    print(f"   Average load time: {analysis.get('avg_load_time_ms', 0):.2f} ms")
    print(f"   Average memory: {analysis.get('avg_memory_mb', 0):.2f} MB")

    print(f"\n📊 Ranges:")
    print(f"   File count: {analysis.get('min_file_count', 0)} - {analysis.get('max_file_count', 0)}")
    print(f"   Load time: {analysis.get('min_load_time_ms', 0):.2f} - {analysis.get('max_load_time_ms', 0):.2f} ms")
    print(f"   Memory: {analysis.get('min_memory_mb', 0):.2f} - {analysis.get('max_memory_mb', 0):.2f} MB")

    print(f"\n📋 Detailed Results:")
    for i, result in enumerate(results, 1):
        print(f"\n   Project {i}: {result['project']}")
        print(f"      Files: {result['file_count']}")
        print(f"      Graph size: {result['graph_size_kb']:.2f} KB")
        print(f"      Load time: {result['load_time_ms']:.2f} ms")
        print(f"      Memory: {result['memory_mb']:.2f} MB")

    print("\n" + "=" * 80)

def main():
    """Main function."""
    # Find projects with graphify
    projects = []
    for path in Path.home().glob("projects/personals/*"):
        if (path / "graphify-out" / "graph.json").exists():
            projects.append(str(path))

    if not projects:
        print("❌ No projects with graphify found")
        return 1

    print(f"🚀 Found {len(projects)} projects with graphify\n")

    # Run benchmarks
    results = benchmark_multiple_projects(projects)

    # Analyze results
    analysis = analyze_results(results)

    # Print report
    print_report(results, analysis)

    # Save results
    output_path = Path("benchmark-results.json")
    with open(output_path, 'w') as f:
        json.dump({
            "timestamp": time.time(),
            "results": results,
            "analysis": analysis
        }, f, indent=2)

    print(f"\n💾 Results saved to: {output_path}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
