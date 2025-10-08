#!/usr/bin/env python3
"""
Mermaid Block Fix Script
Fixes common formatting and syntax issues in Mermaid blocks
"""
import re
import pathlib
import sys
from typing import List, Tuple

ROOT = pathlib.Path("docs")
MERMAID_OPEN = re.compile(r'^```mermaid\s*$')
MERMAID_CLOSE = re.compile(r'^```\s*$')
INIT_PATTERN = re.compile(r'%%\{init:')

def fix_file(file_path: pathlib.Path) -> bool:
    """Fix Mermaid blocks in a single file"""
    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    changed = False
    
    i = 0
    while i < len(lines):
        if MERMAID_OPEN.match(lines[i]):
            # Fix opening fence (remove trailing spaces)
            if lines[i].rstrip() != '```mermaid':
                lines[i] = '```mermaid'
                changed = True
            
            # Find the closing fence
            j = i + 1
            while j < len(lines) and not MERMAID_CLOSE.match(lines[j]):
                j += 1
            
            if j < len(lines):
                # Fix closing fence (remove trailing spaces)
                if lines[j].rstrip() != '```':
                    lines[j] = '```'
                    changed = True
                
                # Fix content between fences
                content_lines = lines[i+1:j]
                content_text = '\n'.join(content_lines)
                
                # Fix %%{init: directives
                if INIT_PATTERN.search(content_text):
                    # Move %%{init: to the first line of content
                    init_match = INIT_PATTERN.search(content_text)
                    if init_match:
                        init_line = content_text[init_match.start():content_text.find('\n', init_match.start())]
                        # Remove the init line from its current position
                        content_text = INIT_PATTERN.sub('', content_text).strip()
                        # Add it to the beginning
                        content_text = init_line + '\n' + content_text
                        
                        # Update the lines
                        new_content_lines = content_text.split('\n')
                        lines[i+1:j] = new_content_lines
                        changed = True
                
                # Fix nested code fences
                if '```' in content_text:
                    # Replace nested fences with escaped versions
                    content_text = content_text.replace('```', '\\`\\`\\`')
                    lines[i+1:j] = content_text.split('\n')
                    changed = True
                
                # Fix sequence diagram arrow syntax
                if content_text.startswith('sequenceDiagram'):
                    # Fix invalid arrow syntax
                    content_text = re.sub(r'(\w+)\s*->>\s*(\w+)', r'\1->>\2', content_text)
                    content_text = re.sub(r'(\w+)\s*-->>\s*(\w+)', r'\1-->>\2', content_text)
                    content_text = re.sub(r'(\w+)\s*-\s*>\s*(\w+)', r'\1->\2', content_text)
                    
                    lines[i+1:j] = content_text.split('\n')
                    changed = True
                
                i = j + 1
            else:
                # Unclosed block - add closing fence
                lines.append('```')
                changed = True
                break
        else:
            i += 1
    
    if changed:
        file_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    
    return changed

def main():
    print("🔧 Fixing Mermaid blocks in documentation...")
    print("=" * 60)
    
    fixed_files = []
    
    # Find all files with Mermaid blocks
    for file_path in ROOT.rglob("*.md"):
        if file_path.is_file():
            if fix_file(file_path):
                fixed_files.append(file_path)
                print(f"✅ Fixed: {file_path}")
    
    print("=" * 60)
    if fixed_files:
        print(f"🔧 Fixed {len(fixed_files)} files")
        return 0
    else:
        print("✅ No files needed fixing")
        return 0

if __name__ == "__main__":
    sys.exit(main())
