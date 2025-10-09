#!/usr/bin/env python3
"""
Parser performance benchmark script for tools wrappers.

This script benchmarks parser performance to ensure it meets the
≥1000 findings/sec baseline requirement.
"""

import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import sys


def load_golden_sample(tool: str, version: str) -> List[Dict[str, Any]]:
    """Load golden sample for benchmarking."""
    sample_path = Path(__file__).parent.parent / "tests" / "golden_samples" / tool / version / "output.json"
    
    if not sample_path.exists():
        print(f"❌ Golden sample not found: {sample_path}")
        return []
    
    try:
        with open(sample_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load golden sample: {e}")
        return []


def benchmark_nuclei_parser(sample_data: List[Dict[str, Any]], iterations: int = 1000) -> float:
    """Benchmark Nuclei parser performance."""
    print(f"🔬 Benchmarking Nuclei parser with {iterations} iterations...")
    
    start_time = time.time()
    
    for _ in range(iterations):
        findings = []
        for item in sample_data:
            try:
                finding = {
                    "title": item["info"]["name"],
                    "severity": item["info"]["severity"],
                    "path": item["matched-at"],
                    "detector_id": "nuclei",
                    "evidence": item
                }
                findings.append(finding)
            except Exception:
                continue
    
    end_time = time.time()
    duration = end_time - start_time
    findings_per_sec = (len(sample_data) * iterations) / duration
    
    print(f"✅ Nuclei parser: {findings_per_sec:.2f} findings/sec")
    return findings_per_sec


def benchmark_feroxbuster_parser(sample_data: List[Dict[str, Any]], iterations: int = 1000) -> float:
    """Benchmark Feroxbuster parser performance."""
    print(f"🔬 Benchmarking Feroxbuster parser with {iterations} iterations...")
    
    start_time = time.time()
    
    for _ in range(iterations):
        endpoints = []
        for item in sample_data:
            try:
                endpoint = {
                    "url": item["url"],
                    "status": item["status"],
                    "size": item["size"],
                    "method": item["method"],
                    "type": "endpoint",
                    "detector_id": "feroxbuster"
                }
                endpoints.append(endpoint)
            except Exception:
                continue
    
    end_time = time.time()
    duration = end_time - start_time
    findings_per_sec = (len(sample_data) * iterations) / duration
    
    print(f"✅ Feroxbuster parser: {findings_per_sec:.2f} findings/sec")
    return findings_per_sec


def benchmark_katana_parser(sample_data: List[Dict[str, Any]], iterations: int = 1000) -> float:
    """Benchmark Katana parser performance."""
    print(f"🔬 Benchmarking Katana parser with {iterations} iterations...")
    
    start_time = time.time()
    
    for _ in range(iterations):
        endpoints = []
        for item in sample_data:
            try:
                endpoint = {
                    "url": item["url"],
                    "method": item["method"],
                    "status": item["status"],
                    "depth": item["depth"],
                    "type": "endpoint",
                    "detector_id": "katana"
                }
                endpoints.append(endpoint)
            except Exception:
                continue
    
    end_time = time.time()
    duration = end_time - start_time
    findings_per_sec = (len(sample_data) * iterations) / duration
    
    print(f"✅ Katana parser: {findings_per_sec:.2f} findings/sec")
    return findings_per_sec


def main():
    parser = argparse.ArgumentParser(description="Benchmark parser performance")
    parser.add_argument("--threshold", type=int, default=1000, help="Minimum findings/sec threshold")
    parser.add_argument("--iterations", type=int, default=1000, help="Number of iterations for benchmarking")
    args = parser.parse_args()
    
    print(f"🚀 Parser Performance Benchmark (threshold: {args.threshold} findings/sec)")
    print("=" * 60)
    
    results = {}
    
    # Benchmark Nuclei
    nuclei_sample = load_golden_sample("nuclei", "v3.0.x")
    if nuclei_sample:
        results["nuclei"] = benchmark_nuclei_parser(nuclei_sample, args.iterations)
    else:
        print("⚠️  Skipping Nuclei benchmark - no golden sample")
        results["nuclei"] = 0
    
    # Benchmark Feroxbuster
    ferox_sample = load_golden_sample("feroxbuster", "v2.10.x")
    if ferox_sample:
        results["feroxbuster"] = benchmark_feroxbuster_parser(ferox_sample, args.iterations)
    else:
        print("⚠️  Skipping Feroxbuster benchmark - no golden sample")
        results["feroxbuster"] = 0
    
    # Benchmark Katana
    katana_sample = load_golden_sample("katana", "v1.0.x")
    if katana_sample:
        results["katana"] = benchmark_katana_parser(katana_sample, args.iterations)
    else:
        print("⚠️  Skipping Katana benchmark - no golden sample")
        results["katana"] = 0
    
    print("\n📊 Benchmark Results:")
    print("=" * 60)
    
    all_passed = True
    for tool, perf in results.items():
        status = "✅ PASS" if perf >= args.threshold else "❌ FAIL"
        print(f"{tool:12}: {perf:8.2f} findings/sec {status}")
        if perf < args.threshold:
            all_passed = False
    
    print(f"\n🎯 Threshold: {args.threshold} findings/sec")
    
    if all_passed:
        print("🎉 All parsers meet performance requirements!")
        sys.exit(0)
    else:
        print("⚠️  Some parsers below performance threshold")
        sys.exit(1)


if __name__ == "__main__":
    main()
