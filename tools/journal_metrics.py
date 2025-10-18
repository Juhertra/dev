#!/usr/bin/env python3
"""
SecFlow Journal Metrics Collection

This script collects basic metrics from journal entries to track trends over time.
Processes journal files and generates JSON metrics for reporting and analysis.

Usage:
    python tools/journal_metrics.py [period]
    
If no period is provided, uses current UTC date.
"""

import json
import pathlib
import datetime
import collections
import sys
import argparse


def get_root_path():
    """Get the project root path."""
    return pathlib.Path(__file__).resolve().parents[1]


def collect_metrics(period, journal_path, output_path):
    """
    Collect metrics from journal entries for a given period.
    
    Args:
        period: Period to collect metrics for (YYYY-MM-DD)
        journal_path: Path to journal directory
        output_path: Path to output directory
        
    Returns:
        Dictionary containing collected metrics
    """
    counts = collections.Counter()
    per_role = collections.defaultdict(lambda: collections.Counter())
    total_entries = 0
    processed_files = 0
    
    # Find all journal files that might contain entries for the period
    # Handle different file naming patterns:
    # 1. {role}-{period}.ndjson
    # 2. {role}-{YYYY-MM}.ndjson (monthly files)
    # 3. {period}.ndjson (simple format)
    journal_files = []
    
    # Pattern 1: Direct period files
    journal_files.extend(journal_path.rglob(f"*-{period}.ndjson"))
    
    # Pattern 2: Monthly files that might contain the period
    year, month, day = period.split('-')
    monthly_pattern = f"*-{year}-{month}.ndjson"
    journal_files.extend(journal_path.rglob(monthly_pattern))
    
    # Pattern 3: Simple period files
    journal_files.extend(journal_path.rglob(f"{period}.ndjson"))
    
    # Remove duplicates
    journal_files = list(set(journal_files))
    
    for journal_file in journal_files:
        if not journal_file.exists():
            continue
            
        try:
            # Extract role from file path
            role = journal_file.parent.parent.name
            processed_files += 1
            
            # Read and process each line
            for line in journal_file.read_text().splitlines():
                if not line.strip():
                    continue
                    
                try:
                    entry = json.loads(line)
                    total_entries += 1
                    
                    # Only process entries for the specified period
                    if entry.get("period") != period:
                        continue
                    
                    # Count event types
                    event_type = entry.get("event", "note")
                    counts[event_type] += 1
                    per_role[role][event_type] += 1
                    
                except json.JSONDecodeError:
                    # Skip malformed JSON lines
                    continue
                    
        except Exception as e:
            print(f"Error processing {journal_file}: {e}", file=sys.stderr)
            continue
    
    # Build metrics summary
    metrics = {
        "period": period,
        "summary": {
            "total_entries": total_entries,
            "processed_files": processed_files,
            "event_types": len(counts),
            "roles": len(per_role)
        },
        "events": dict(counts),
        "by_role": {role: dict(events) for role, events in per_role.items()},
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    return metrics


def write_metrics(period, data, output_path):
    """
    Write metrics data to the appropriate output directory.
    
    Args:
        period: Period for the metrics (YYYY-MM-DD)
        data: Metrics data to write
        output_path: Base output path
    """
    # Create directory structure: reports/daily/YYYY/MM/DD/
    year, month, day = period.split('-')
    output_dir = output_path / year / month / day
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write metrics file
    metrics_file = output_dir / "metrics.json"
    metrics_file.write_text(json.dumps(data, indent=2))
    
    print(f"Metrics written to: {metrics_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Collect journal metrics")
    parser.add_argument(
        "period", 
        nargs="?", 
        help="Period to collect metrics for (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--journal-path",
        default="control/journal/agents",
        help="Path to journal directory"
    )
    parser.add_argument(
        "--output-path", 
        default="reports/daily",
        help="Path to output directory"
    )
    
    args = parser.parse_args()
    
    # Get project root
    root = get_root_path()
    
    # Set up paths
    journal_path = root / args.journal_path
    output_path = root / args.output_path
    
    # Determine period
    if args.period:
        period = args.period
    else:
        period = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    
    print(f"Collecting metrics for period: {period}")
    print(f"Journal path: {journal_path}")
    print(f"Output path: {output_path}")
    
    # Collect metrics
    try:
        metrics = collect_metrics(period, journal_path, output_path)
        
        # Write metrics
        write_metrics(period, metrics, output_path)
        
        # Print summary
        print(f"\nMetrics Summary:")
        print(f"  Total entries: {metrics['summary']['total_entries']}")
        print(f"  Processed files: {metrics['summary']['processed_files']}")
        print(f"  Event types: {metrics['summary']['event_types']}")
        print(f"  Roles: {metrics['summary']['roles']}")
        
        print(f"\nEvent counts:")
        for event, count in metrics['events'].items():
            print(f"  {event}: {count}")
        
        print(f"\nBy role:")
        for role, events in metrics['by_role'].items():
            print(f"  {role}: {dict(events)}")
            
    except Exception as e:
        print(f"Error collecting metrics: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
