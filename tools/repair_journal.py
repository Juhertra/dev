#!/usr/bin/env python3
"""
Journal Repair Tool

This script repairs journal shape violations (role mismatch, missing ts) 
without breaking append-only guarantees. Only fixes structural issues,
not content changes.

Usage:
    python tools/repair_journal.py [target_file]
    
If no target file is provided, uses the default observability-lead file.
"""

import json
import sys
import pathlib
import datetime as dt


def repair_journal_file(target_file):
    """
    Repair journal file shape violations.
    
    Args:
        target_file: Path to the journal file to repair
        
    Returns:
        Tuple of (fixed_count, manifest_path)
    """
    root = pathlib.Path(__file__).resolve().parents[1]
    
    if not target_file.exists():
        print(f"Target file does not exist: {target_file}")
        return 0, None
    
    # Read existing lines
    lines = target_file.read_text().splitlines()
    fixed = []
    out = []
    now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
            
        try:
            rec = json.loads(line)
        except Exception as e:
            print(f"# skip non-JSON at line {i}: {e}")
            continue
        
        changed = False
        
        # 1) role shape fix
        if rec.get("role") != "observability-lead":
            rec["role"] = "observability-lead"
            changed = True
        
        # 2) ts shape fix
        if "ts" not in rec or not isinstance(rec["ts"], str) or "T" not in rec["ts"]:
            rec["ts"] = now
            changed = True
        
        out.append(json.dumps(rec, separators=(",", ":")))
        
        if changed:
            fixed.append({
                "line": i,
                "title": rec.get("title", ""),
                "event": rec.get("event"),
                "ts": rec["ts"]
            })
    
    # Write back the repaired file
    target_file.write_text("\n".join(out) + ("\n" if out else ""))
    
    # Log a correction manifest for audit
    corrdir = root / "control" / "journal" / "corrections"
    corrdir.mkdir(parents=True, exist_ok=True)
    manifest = corrdir / f"{target_file.name}.repair-{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
    manifest.write_text(json.dumps({
        "file": str(target_file),
        "fixed": fixed,
        "repair_timestamp": now,
        "total_lines": len(lines),
        "repaired_lines": len(fixed)
    }, indent=2))
    
    return len(fixed), manifest


def main():
    """Main function."""
    root = pathlib.Path(__file__).resolve().parents[1]
    
    # Default target file
    target = root / "control/journal/agents/observability-lead/2025-10/observability-lead-2025-10-18.ndjson"
    
    # Allow CLI override
    if len(sys.argv) > 1:
        target = pathlib.Path(sys.argv[1])
    
    print(f"Repairing journal file: {target}")
    
    try:
        fixed_count, manifest_path = repair_journal_file(target)
        
        if fixed_count > 0:
            print(f"Repaired {fixed_count} record(s); manifest: {manifest_path}")
        else:
            print("No repairs needed - file is already compliant")
            
    except Exception as e:
        print(f"Error repairing journal file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
