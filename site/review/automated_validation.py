#!/usr/bin/env python3
import ast
import glob
import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARCH_DIR = os.path.join(ROOT, "docs", "architecture")
REVIEW_DIR = os.path.join(ROOT, "docs", "review")
REPORT = os.path.join(REVIEW_DIR, "validation_report.md")
VALIDATION_STATE = os.path.join(REVIEW_DIR, "validation_state.json")
REVIEW_STATUS = os.path.join(REVIEW_DIR, "REVIEW_STATUS.md")

REQUIRED_FRONTMATTER_KEYS = ["title", "author", "version", "date"]

# Legacy → canonical filename alias map (add more as needed)
ALIASES = {
    "13-enrichment-layer.md": "13-cve-cwe-poc-enrichment-layer.md",
    "03-repo-layout.md": "03-repository-layout.md",
    "04-core-packages.md": "04-core-packages-and-responsibilities.md",
    "05-orchestration-workflow.md": "05-orchestration-and-workflow-engine.md",
    "07-tools-integration.md": "07-tools-integration-model.md",
    "08-tool-manager-ux.md": "08-tool-manager-and-ux-design.md",
    "10-wordlists-sharing.md": "10-wordlist-and-output-sharing.md",
    "11-project-isolation-and-sharing.md": "11-project-isolation-and-data-sharing.md",
    "21-cicd-and-testing.md": "21-ci-cd-and-testing-strategy.md",
    "22-developer-experience.md": "22-developer-experience-and-docs.md",
}

PLACEHOLDER_PATTERNS = [
    r"\bTODO\b",
    r"\bTBD\b",
    r"\bFIXME\b",
    r"\.\.\.(?!\s*\)|\s*\]|\s*\"|\s*'|\s*Field|\s*$|\s*\[|\s*description|\s*,)",  # ellipsis not followed by ), ], ", ', Field, end of line, [, description, or comma
    r"PLACEHOLDER",
    r"\(Full detailed content from chat",
]

FENCED_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_\-\+\.]*)\n(.*?)\n```", re.DOTALL)
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

def load_glossary(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def calculate_dqi(warnings: int, criticals: int) -> float:
    """Calculate Documentation Quality Index (DQI).
    
    Formula: DQI = 100 - (warnings * 0.2 + criticals * 5)
    
    Args:
        warnings: Number of warning issues
        criticals: Number of critical issues
        
    Returns:
        DQI score (0-100)
    """
    dqi = 100 - (warnings * 0.2 + criticals * 5)
    return max(0.0, min(100.0, dqi))  # Clamp between 0 and 100

def load_validation_state() -> Dict:
    """Load previous validation state from JSON file."""
    if os.path.exists(VALIDATION_STATE):
        try:
            with open(VALIDATION_STATE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"dqi": None, "timestamp": None, "warnings": None, "criticals": None}

def save_validation_state(dqi: float, warnings: int, criticals: int):
    """Save current validation state to JSON file."""
    state = {
        "dqi": dqi,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "warnings": warnings,
        "criticals": criticals
    }
    
    os.makedirs(os.path.dirname(VALIDATION_STATE), exist_ok=True)
    with open(VALIDATION_STATE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def get_dqi_trend(current_dqi: float, previous_state: Dict) -> str:
    """Determine trend direction based on previous DQI."""
    if previous_state.get("dqi") is None:
        return "—"  # No previous data
    
    previous_dqi = previous_state["dqi"]
    if current_dqi > previous_dqi:
        return "↑"
    elif current_dqi < previous_dqi:
        return "↓"
    else:
        return "→"

def update_review_status_dqi(dqi: float, trend: str, warnings: int, criticals: int):
    """Update REVIEW_STATUS.md with DQI information."""
    if not os.path.exists(REVIEW_STATUS):
        return
    
    # Read current content
    with open(REVIEW_STATUS, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add or update the DQI summary
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    dqi_line = f"[Auto] DQI recalculated — {dqi:.1f}/100 (Trend: {trend})"
    
    # Check if DQI summary already exists and replace it
    dqi_pattern = r'\[Auto\] DQI recalculated.*\n'
    if re.search(dqi_pattern, content):
        content = re.sub(dqi_pattern, f"{dqi_line}\n", content)
    else:
        # Add at the end
        content = content.rstrip() + f"\n{dqi_line}\n"
    
    # Write back
    with open(REVIEW_STATUS, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_file_terminology(file_path: str, glossary: Dict) -> int:
    """Fix terminology issues in a single file and return the number of fixes."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    fixes = 0
    
    # Apply terminology fixes
    for term, rule in glossary.get("terms", {}).items():
        preferred = rule.get("preferred")
        forbidden = rule.get("forbidden", [])
        
        for forbidden_term in forbidden:
            # Use word boundaries to avoid partial replacements
            pattern = rf'\b{re.escape(forbidden_term)}\b'
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, preferred, content)
                fixes += len(matches)
    
    # Write the fixed content back if changes were made
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {fixes} terminology issues in {os.path.basename(file_path)}")
    
    return fixes

def validate_python_syntax(code: str) -> Optional[str]:
    """Validate Python syntax by compiling the code."""
    try:
        # Try to compile the code
        ast.parse(code)
        return None  # No syntax errors
    except SyntaxError as e:
        return f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return f"Parse error: {str(e)}"

def validate_json_syntax(code: str) -> Optional[str]:
    """Validate JSON syntax."""
    try:
        json.loads(code)
        return None  # No syntax errors
    except json.JSONDecodeError as e:
        return f"JSON error at line {e.lineno}, column {e.colno}: {e.msg}"
    except Exception as e:
        return f"JSON parse error: {str(e)}"

def validate_yaml_syntax(code: str) -> Optional[str]:
    """Validate YAML syntax."""
    try:
        yaml.safe_load(code)
        return None  # No syntax errors
    except yaml.YAMLError as e:
        # Extract line number if available
        if hasattr(e, 'problem_mark') and e.problem_mark:
            line = e.problem_mark.line + 1
            column = e.problem_mark.column + 1
            return f"YAML error at line {line}, column {column}: {e.problem}"
        else:
            return f"YAML error: {str(e)}"
    except Exception as e:
        return f"YAML parse error: {str(e)}"

def validate_code_syntax(language: str, code: str) -> Optional[str]:
    """Validate syntax for the given language and code."""
    language = language.lower().strip()
    
    if language == "python":
        return validate_python_syntax(code)
    elif language in ("json", "jsonc"):
        return validate_json_syntax(code)
    elif language in ("yaml", "yml"):
        return validate_yaml_syntax(code)
    else:
        return None  # Unknown language, skip validation

def list_md_files() -> List[str]:
    files = sorted(glob.glob(os.path.join(ARCH_DIR, "*.md")))
    return files

def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except Exception:
        data = {}
    rest = content[m.end():]
    return data, rest

def check_frontmatter(path: str, fm: Dict) -> List[str]:
    issues = []
    for k in REQUIRED_FRONTMATTER_KEYS:
        if k not in fm or not fm[k]:
            issues.append(f"Missing frontmatter key `{k}` in {os.path.basename(path)}")
    # basic date format sanity
    if "date" in fm:
        try:
            datetime.fromisoformat(str(fm["date"]))
        except Exception:
            issues.append(f"Frontmatter `date` not ISO format in {os.path.basename(path)}")
    return issues

def canonicalize_link(href: str) -> str:
    # reject double .md.md
    href = href.replace(".md.md", ".md")
    # apply aliases
    base = os.path.basename(href)
    if base in ALIASES:
        href = href.replace(base, ALIASES[base])
    return href

def validate_links(path: str, content: str, all_files: List[str]) -> Tuple[List[str], List[str]]:
    warnings, criticals = [], []
    targets = {os.path.basename(p) for p in all_files}
    for _, href in LINK_RE.findall(content):
        if not href.endswith(".md"):
            continue
        href2 = canonicalize_link(href)
        base = os.path.basename(href2)
        if base not in targets:
            # maybe referenced with subdir prefix in mkdocs.yml; try to allow "docs/architecture/"
            if base not in targets:
                criticals.append(f"Broken link in {os.path.basename(path)} → `{href}` (resolved `{href2}`)")
        if ".md.md" in href or ".md.md" in href2:
            criticals.append(f"Double extension `.md.md` in {os.path.basename(path)} → `{href}`")
        if href != href2:
            warnings.append(f"Canonicalized link in {os.path.basename(path)}: `{href}` → `{href2}`")
    return warnings, criticals

def validate_placeholders(path: str, content: str) -> List[str]:
    issues = []
    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, content):
            issues.append(f"Placeholder content found in {os.path.basename(path)} (pattern `{pat}`)")
    return issues

def validate_code_blocks(path: str, content: str) -> Tuple[List[str], List[str]]:
    warnings, criticals = [], []
    for lang, body in FENCED_BLOCK_RE.findall(content):
        # language hint recommended
        if lang.strip() == "":
            warnings.append(f"Code fence missing language in {os.path.basename(path)}")
        # placeholder detection inside blocks
        if re.search(r"\bTODO\b|\bTBD\b|\bFIXME\b|\.\.\.", body):
            warnings.append(f"Code block in {os.path.basename(path)} contains placeholder(s)")
        
        # Syntax validation for supported languages
        if lang.strip():
            syntax_error = validate_code_syntax(lang.strip(), body)
            if syntax_error:
                warnings.append(f"Syntax check failed in {os.path.basename(path)}: {syntax_error}")
    
    return warnings, criticals

def validate_glossary(path: str, content: str, glossary: Dict) -> List[str]:
    issues = []
    text = content
    for term, rule in glossary.get("terms", {}).items():
        # check preferred capitalization occurrences
        preferred = rule.get("preferred")
        forbidden = rule.get("forbidden", [])
        # if any forbidden appears, warn
        for bad in forbidden:
            # word-boundary-ish check
            if re.search(rf"\b{re.escape(bad)}\b", text):
                issues.append(f"Forbidden term in {os.path.basename(path)}: `{bad}` (use `{preferred}`)")
    return issues

def summarize(results: Dict[str, Dict[str, List[str]]]) -> Tuple[int, int]:
    total_w, total_c = 0, 0
    for _, res in results.items():
        total_w += len(res["warnings"])
        total_c += len(res["criticals"])
    return total_w, total_c

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate documentation and optionally fix terminology issues')
    parser.add_argument('--fix', action='store_true', help='Fix terminology issues automatically')
    args = parser.parse_args()
    
    os.makedirs(REVIEW_DIR, exist_ok=True)
    glossary_path = os.path.join(REVIEW_DIR, "glossary.yml")
    glossary = {}
    if os.path.exists(glossary_path):
        glossary = load_glossary(glossary_path)
    
    # If --fix flag is provided, fix terminology issues
    if args.fix:
        print("🔧 Fixing terminology issues...")
        files = list_md_files()
        total_fixes = 0
        files_fixed = 0
        
        for file_path in files:
            fixes = fix_file_terminology(file_path, glossary)
            if fixes > 0:
                files_fixed += 1
                total_fixes += fixes
        
        print("\n✅ Terminology fixes complete:")
        print(f"Files processed: {len(files)}")
        print(f"Files fixed: {files_fixed}")
        print(f"Total terminology fixes: {total_fixes}")
        return

    files = list_md_files()
    if not files:
        print("No architecture files found.")
        sys.exit(2)

    results = {}
    for f in files:
        content = read(f)
        fm, body = parse_frontmatter(content)
        res = {"warnings": [], "criticals": []}

        # frontmatter
        res["warnings"].extend(check_frontmatter(f, fm))

        # links
        w1, c1 = validate_links(f, content, files)
        res["warnings"].extend(w1)
        res["criticals"].extend(c1)

        # placeholders
        res["warnings"].extend(validate_placeholders(f, content))

        # code blocks
        w2, c2 = validate_code_blocks(f, content)
        res["warnings"].extend(w2)
        res["criticals"].extend(c2)

        # glossary
        res["warnings"].extend(validate_glossary(f, content, glossary))

        results[os.path.basename(f)] = res

    total_w, total_c = summarize(results)
    
    # Calculate Documentation Quality Index (DQI)
    dqi = calculate_dqi(total_w, total_c)
    
    # Load previous state for trend analysis
    previous_state = load_validation_state()
    trend = get_dqi_trend(dqi, previous_state)
    
    # Save current state
    save_validation_state(dqi, total_w, total_c)
    
    # Update REVIEW_STATUS.md with DQI
    update_review_status_dqi(dqi, trend, total_w, total_c)

    # write markdown report
    with open(REPORT, "w", encoding="utf-8") as rpt:
        rpt.write(f"# Validation Report — {datetime.utcnow().isoformat()}Z\n\n")
        rpt.write(f"- **Criticals**: {total_c}\n")
        rpt.write(f"- **Warnings**: {total_w}\n\n")
        rpt.write("| Document | Criticals | Warnings |\n|---|---:|---:|\n")
        for fname, res in sorted(results.items()):
            rpt.write(f"| {fname} | {len(res['criticals'])} | {len(res['warnings'])} |\n")
        rpt.write("\n---\n")
        for fname, res in sorted(results.items()):
            if res["criticals"] or res["warnings"]:
                rpt.write(f"## {fname}\n\n")
                if res["criticals"]:
                    rpt.write("**❌ Criticals**\n\n")
                    for c in res["criticals"]:
                        rpt.write(f"- {c}\n")
                    rpt.write("\n")
                if res["warnings"]:
                    rpt.write("**⚠️ Warnings**\n\n")
                    for w in res["warnings"]:
                        rpt.write(f"- {w}\n")
                    rpt.write("\n")
        
        # Add Documentation Quality Index section
        rpt.write("\n## 📈 Documentation Quality Index\n\n")
        rpt.write(f"- **Score**: {dqi:.1f}/100\n")
        rpt.write(f"- **Criticals**: {total_c}\n")
        rpt.write(f"- **Warnings**: {total_w}\n")
        rpt.write(f"- **Trend**: {trend}\n\n")
        
        # Add DQI interpretation
        if dqi >= 90:
            rpt.write("**Quality Level**: 🟢 Excellent\n")
        elif dqi >= 80:
            rpt.write("**Quality Level**: 🟡 Good\n")
        elif dqi >= 70:
            rpt.write("**Quality Level**: 🟠 Fair\n")
        else:
            rpt.write("**Quality Level**: 🔴 Needs Improvement\n")
        
        # Add trend interpretation
        if trend == "↑":
            rpt.write("**Trend**: 📈 Improving\n")
        elif trend == "↓":
            rpt.write("**Trend**: 📉 Declining\n")
        elif trend == "→":
            rpt.write("**Trend**: ➡️ Stable\n")
        else:
            rpt.write("**Trend**: ➖ No previous data\n")

    # console summary
    print(f"[VALIDATION] Criticals={total_c} Warnings={total_w} DQI={dqi:.1f}/100 Trend={trend} → report: {os.path.relpath(REPORT, ROOT)}")
    sys.exit(1 if total_c > 0 else 0)

if __name__ == "__main__":
    main()