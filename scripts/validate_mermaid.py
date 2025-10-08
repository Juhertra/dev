#!/usr/bin/env python3
"""
Mermaid Block Validation Script
Validates syntax and formatting of all Mermaid blocks in Markdown files
"""
import re
import pathlib
import sys
from typing import List, Tuple, Dict

ROOT = pathlib.Path("docs")
MERMAID_OPEN = re.compile(r'^```mermaid\s*$')
MERMAID_CLOSE = re.compile(r'^```\s*$')
INIT_PATTERN = re.compile(r'%%\{init:')

class MermaidBlock:
    def __init__(self, file_path: pathlib.Path, start_line: int, end_line: int, content: str):
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.issues = []

def find_mermaid_blocks(file_path: pathlib.Path) -> List[MermaidBlock]:
    """Find all Mermaid blocks in a file"""
    blocks = []
    lines = file_path.read_text(encoding="utf-8").splitlines()
    
    i = 0
    while i < len(lines):
        if MERMAID_OPEN.match(lines[i]):
            start_line = i + 1
            # Find the closing fence
            j = i + 1
            while j < len(lines) and not MERMAID_CLOSE.match(lines[j]):
                j += 1
            
            if j < len(lines):
                # Extract content between fences
                content_lines = lines[i+1:j]
                content = '\n'.join(content_lines)
                blocks.append(MermaidBlock(file_path, start_line, j+1, content))
                i = j + 1
            else:
                # Unclosed block
                content_lines = lines[i+1:]
                content = '\n'.join(content_lines)
                blocks.append(MermaidBlock(file_path, start_line, len(lines), content))
                break
        else:
            i += 1
    
    return blocks

def validate_mermaid_block(block: MermaidBlock) -> List[str]:
    """Validate a single Mermaid block"""
    issues = []
    
    # Check for %%{init: outside of fence
    if INIT_PATTERN.search(block.content):
        issues.append("Contains %%{init: directive - should be inside fence")
    
    # Check for nested code fences
    if '```' in block.content:
        issues.append("Contains nested code fences")
    
    # Check for trailing spaces on opening fence
    opening_line = block.file_path.read_text(encoding="utf-8").splitlines()[block.start_line - 2]
    if opening_line.rstrip() != '```mermaid':
        issues.append("Opening fence has trailing spaces")
    
    # Basic syntax validation
    content = block.content.strip()
    if not content:
        issues.append("Empty Mermaid block")
        return issues
    
    # Check for common syntax issues
    lines = content.split('\n')
    
    # Check for flowchart syntax
    if content.startswith('flowchart'):
        if not re.search(r'flowchart\s+(TD|LR|TB|RL|BT)', content):
            issues.append("Invalid flowchart direction")
    
    # Check for graph syntax
    if content.startswith('graph'):
        if not re.search(r'graph\s+(TD|LR|TB|RL|BT)', content):
            issues.append("Invalid graph direction")
    
    # Check for sequence diagram syntax
    if content.startswith('sequenceDiagram'):
        if not re.search(r'participant\s+\w+', content):
            issues.append("Sequence diagram missing participants")
    
    # Check for class diagram syntax
    if content.startswith('classDiagram'):
        if not re.search(r'class\s+\w+', content):
            issues.append("Class diagram missing class definitions")
    
    # Check for state diagram syntax
    if content.startswith('stateDiagram'):
        if not re.search(r'\[\*\]', content):
            issues.append("State diagram missing initial state")
    
    # Check for common syntax errors
    if '-->' in content and not re.search(r'\w+\s*-->\s*\w+', content):
        issues.append("Invalid arrow syntax")
    
    if '->>' in content and not re.search(r'\w+\s*->>\s*\w+', content):
        issues.append("Invalid sequence arrow syntax")
    
    return issues

def main():
    print("🔍 Validating Mermaid blocks in documentation...")
    print("=" * 60)
    
    all_blocks = []
    total_files = 0
    
    # Find all Mermaid blocks
    for file_path in ROOT.rglob("*.md"):
        if file_path.is_file():
            blocks = find_mermaid_blocks(file_path)
            if blocks:
                all_blocks.extend(blocks)
                total_files += 1
    
    print(f"Found {len(all_blocks)} Mermaid blocks in {total_files} files")
    print()
    
    # Validate each block
    issues_found = 0
    files_with_issues = set()
    
    for block in all_blocks:
        issues = validate_mermaid_block(block)
        if issues:
            issues_found += len(issues)
            files_with_issues.add(block.file_path)
            
            print(f"❌ {block.file_path}:{block.start_line}")
            for issue in issues:
                print(f"   - {issue}")
            print()
    
    # Summary
    print("=" * 60)
    if issues_found == 0:
        print("✅ All Mermaid blocks are valid!")
        return 0
    else:
        print(f"❌ Found {issues_found} issues in {len(files_with_issues)} files")
        print("\nFiles with issues:")
        for file_path in sorted(files_with_issues):
            print(f"  - {file_path}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
