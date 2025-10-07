#!/usr/bin/env python3
"""
Pattern Engine CLI - Management and testing utilities for the pattern engine.
"""
import sys
import os
import json
import argparse
from typing import Dict, Any, List

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from detectors.pattern_engine import PatternEngine

def print_stats(engine: PatternEngine):
    """Print comprehensive pattern statistics."""
    stats = engine.get_pattern_stats()
    
    print("Pattern Engine Statistics")
    print("=" * 50)
    print(f"Total Rules: {stats['total_rules']}")
    print(f"Enabled: {stats['enabled_rules']}")
    print(f"Disabled: {stats['disabled_rules']}")
    print(f"Packs Loaded: {stats['packs_loaded']}")
    print(f"Cache Size: {stats['cache_size']}")
    print(f"Last Reload: {stats['last_reload']}")
    
    print("\nPack Breakdown:")
    print("-" * 30)
    for pack_name, pack_stats in stats['pack_breakdown'].items():
        print(f"  {pack_name}: {pack_stats['enabled']}/{pack_stats['total']} enabled")
    
    print("\nSeverity Breakdown:")
    print("-" * 30)
    for severity, count in sorted(stats['severity_breakdown'].items()):
        print(f"  {severity}: {count}")
    
    print("\nCWE Breakdown:")
    print("-" * 30)
    for cwe, count in sorted(stats['cwe_breakdown'].items()):
        print(f"  {cwe}: {count}")

def list_patterns(engine: PatternEngine, pack_filter: str = None, enabled_only: bool = False):
    """List all patterns with optional filtering."""
    patterns = engine.list_patterns()
    
    if pack_filter:
        patterns = [p for p in patterns if pack_filter.lower() in p['pack'].lower()]
    
    if enabled_only:
        patterns = [p for p in patterns if p['enabled']]
    
    print(f"Patterns ({len(patterns)} total)")
    print("=" * 80)
    print(f"{'ID':<20} {'Title':<30} {'Pack':<15} {'Severity':<8} {'CWE':<8} {'Enabled'}")
    print("-" * 80)
    
    for p in patterns:
        enabled_str = "✓" if p['enabled'] else "✗"
        cwe_str = p['cwe'] or "-"
        print(f"{p['id']:<20} {p['title'][:29]:<30} {p['pack'][:14]:<15} {p['severity']:<8} {cwe_str:<8} {enabled_str}")

def test_patterns(engine: PatternEngine, test_text: str, rule_id: str = None):
    """Test patterns against given text."""
    if rule_id:
        # Test specific pattern
        result = engine.test_pattern(rule_id, test_text)
        pattern = engine.get_pattern_by_id(rule_id)
        if pattern:
            print(f"Testing pattern: {pattern['title']} ({rule_id})")
            print(f"Text: {test_text}")
            print(f"Result: {'MATCH' if result else 'NO MATCH'}")
        else:
            print(f"Pattern not found: {rule_id}")
    else:
        # Test all patterns
        matches = engine.test_all_patterns(test_text)
        print(f"Testing text: {test_text}")
        print(f"Found {len(matches)} matches:")
        print("-" * 50)
        
        for match in matches:
            print(f"  {match['rule_id']}: {match['title']}")
            print(f"    Pack: {match['pack']}")
            print(f"    Severity: {match['severity']}")
            print(f"    CWE: {match['cwe'] or 'N/A'}")
            print(f"    Match: {match['match']}")
            print()

def toggle_pattern(engine: PatternEngine, rule_id: str, enabled: bool):
    """Enable/disable a pattern."""
    success = engine.toggle_pattern(rule_id, enabled)
    if success:
        status = "enabled" if enabled else "disabled"
        print(f"Pattern {rule_id} {status}")
    else:
        print(f"Pattern not found: {rule_id}")

def reload_patterns(engine: PatternEngine):
    """Reload all pattern files."""
    print("Reloading patterns...")
    engine.reload()
    stats = engine.get_pattern_stats()
    print(f"Reloaded {stats['total_rules']} rules from {stats['packs_loaded']} packs")

def main():
    parser = argparse.ArgumentParser(description="Pattern Engine CLI")
    parser.add_argument("--pattern-dir", default="detectors/patterns", 
                       help="Pattern directory (default: detectors/patterns)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Stats command
    subparsers.add_parser("stats", help="Show pattern statistics")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List patterns")
    list_parser.add_argument("--pack", help="Filter by pack name")
    list_parser.add_argument("--enabled-only", action="store_true", help="Show only enabled patterns")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test patterns")
    test_parser.add_argument("text", help="Text to test against")
    test_parser.add_argument("--rule-id", help="Test specific rule ID")
    
    # Toggle command
    toggle_parser = subparsers.add_parser("toggle", help="Enable/disable pattern")
    toggle_parser.add_argument("rule_id", help="Rule ID to toggle")
    toggle_parser.add_argument("--enable", action="store_true", help="Enable pattern")
    toggle_parser.add_argument("--disable", action="store_true", help="Disable pattern")
    
    # Reload command
    subparsers.add_parser("reload", help="Reload pattern files")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize pattern engine
    pattern_dir = os.path.abspath(args.pattern_dir)
    if not os.path.exists(pattern_dir):
        print(f"Pattern directory not found: {pattern_dir}")
        return
    
    engine = PatternEngine(pattern_dir)
    engine.reload()
    
    # Execute command
    if args.command == "stats":
        print_stats(engine)
    elif args.command == "list":
        list_patterns(engine, args.pack, args.enabled_only)
    elif args.command == "test":
        test_patterns(engine, args.text, args.rule_id)
    elif args.command == "toggle":
        if args.enable and args.disable:
            print("Cannot both enable and disable")
            return
        if not args.enable and not args.disable:
            print("Must specify --enable or --disable")
            return
        toggle_pattern(engine, args.rule_id, args.enable)
    elif args.command == "reload":
        reload_patterns(engine)

if __name__ == "__main__":
    main()
