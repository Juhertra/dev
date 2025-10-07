#!/usr/bin/env python3
"""
AI-Assisted Validation Summary Generator

This module parses the validation report and generates intelligent summaries
with categorized warnings, frequency analysis, and suggested actions.
"""

import os
import re
import yaml
from datetime import datetime
from typing import Dict, List, Tuple, Any
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REVIEW_DIR = os.path.join(ROOT, "docs", "review")
VALIDATION_REPORT = os.path.join(REVIEW_DIR, "validation_report.md")
VALIDATION_SUMMARY = os.path.join(REVIEW_DIR, "VALIDATION_SUMMARY.md")
REVIEW_STATUS = os.path.join(REVIEW_DIR, "REVIEW_STATUS.md")

class ValidationSummaryGenerator:
    """Generates intelligent validation summaries with AI-assisted categorization."""
    
    def __init__(self):
        self.warnings_by_category = defaultdict(list)
        self.issue_frequency = Counter()
        self.document_stats = defaultdict(lambda: {"warnings": 0, "criticals": 0})
        
    def parse_validation_report(self) -> Dict[str, Any]:
        """Parse the validation report and extract structured data."""
        if not os.path.exists(VALIDATION_REPORT):
            raise FileNotFoundError(f"Validation report not found: {VALIDATION_REPORT}")
        
        with open(VALIDATION_REPORT, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract summary statistics
        critical_match = re.search(r'- \*\*Criticals\*\*: (\d+)', content)
        warning_match = re.search(r'- \*\*Warnings\*\*: (\d+)', content)
        
        criticals = int(critical_match.group(1)) if critical_match else 0
        warnings = int(warning_match.group(1)) if warning_match else 0
        
        # Extract DQI information
        dqi_match = re.search(r'- \*\*Score\*\*: ([\d.]+)/100', content)
        trend_match = re.search(r'- \*\*Trend\*\*: ([↑↓→—])', content)
        
        dqi = float(dqi_match.group(1)) if dqi_match else None
        trend = trend_match.group(1) if trend_match else "—"
        
        # Extract document statistics
        doc_stats_pattern = r'\| ([^|]+) \| (\d+) \| (\d+) \|'
        doc_matches = re.findall(doc_stats_pattern, content)
        
        for doc_name, criticals_count, warnings_count in doc_matches:
            self.document_stats[doc_name] = {
                "warnings": int(warnings_count),
                "criticals": int(criticals_count)
            }
        
        # Extract individual warnings and criticals
        self._extract_issues(content)
        
        return {
            "criticals": criticals,
            "warnings": warnings,
            "dqi": dqi,
            "trend": trend,
            "total_documents": len(self.document_stats),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    def _extract_issues(self, content: str):
        """Extract and categorize individual issues from the report."""
        # Find all document sections
        doc_sections = re.split(r'## ([^\n]+)', content)[1:]  # Skip first empty element
        
        for i in range(0, len(doc_sections), 2):
            if i + 1 >= len(doc_sections):
                break
                
            doc_name = doc_sections[i].strip()
            doc_content = doc_sections[i + 1]
            
            # Extract criticals
            criticals_section = re.search(r'\*\*❌ Criticals\*\*\n\n(.*?)\n\n', doc_content, re.DOTALL)
            if criticals_section:
                criticals_text = criticals_section.group(1)
                for line in criticals_text.split('\n'):
                    if line.strip().startswith('- '):
                        issue = line.strip()[2:]  # Remove '- '
                        self._categorize_issue(issue, "critical")
            
            # Extract warnings
            warnings_section = re.search(r'\*\*⚠️ Warnings\*\*\n\n(.*?)(?:\n\n|$)', doc_content, re.DOTALL)
            if warnings_section:
                warnings_text = warnings_section.group(1)
                for line in warnings_text.split('\n'):
                    if line.strip().startswith('- '):
                        issue = line.strip()[2:]  # Remove '- '
                        self._categorize_issue(issue, "warning")
    
    def _categorize_issue(self, issue: str, severity: str):
        """Categorize an issue into appropriate groups."""
        issue_lower = issue.lower()
        
        # Categorization rules
        if any(keyword in issue_lower for keyword in ['placeholder', 'todo', 'tbd', 'fixme', '...']):
            category = "Placeholder / Missing Content"
        elif any(keyword in issue_lower for keyword in ['code block', 'code fence', 'language', 'syntax']):
            category = "Code Block Issues"
        elif any(keyword in issue_lower for keyword in ['forbidden term', 'terminology', 'glossary', 'consistency']):
            category = "Terminology / Glossary Inconsistencies"
        elif any(keyword in issue_lower for keyword in ['frontmatter', 'link', 'broken', 'missing']):
            category = "Frontmatter or Link Issues"
        elif any(keyword in issue_lower for keyword in ['ascii', 'diagram']):
            category = "Diagram / Visual Issues"
        else:
            category = "Other Issues"
        
        self.warnings_by_category[category].append(issue)
        self.issue_frequency[issue] += 1
    
    def generate_summary(self) -> str:
        """Generate the validation summary markdown."""
        stats = self.parse_validation_report()
        
        summary_lines = [
            "# AI-Assisted Validation Summary",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Source**: {os.path.relpath(VALIDATION_REPORT, ROOT)}",
            "",
            "## 📊 Overview",
            f"- **Total Documents**: {stats['total_documents']}",
            f"- **Critical Issues**: {stats['criticals']}",
            f"- **Warnings**: {stats['warnings']}",
            f"- **Categories**: {len(self.warnings_by_category)}",
            ""
        ]
        
        # Add DQI section if available
        if stats.get('dqi') is not None:
            dqi = stats['dqi']
            trend = stats.get('trend', '—')
            
            summary_lines.extend([
                "## 📈 Documentation Quality Index (DQI)",
                f"- **Score**: {dqi:.1f}/100",
                f"- **Trend**: {trend}",
                ""
            ])
            
            # Add DQI interpretation
            if dqi >= 90:
                summary_lines.append("**Quality Level**: 🟢 Excellent")
            elif dqi >= 80:
                summary_lines.append("**Quality Level**: 🟡 Good")
            elif dqi >= 70:
                summary_lines.append("**Quality Level**: 🟠 Fair")
            else:
                summary_lines.append("**Quality Level**: 🔴 Needs Improvement")
            
            summary_lines.extend(["", ""])
        
        summary_lines.extend([
            "## 🏷️ Warnings by Category",
            ""
        ])
        
        # Add category breakdown
        for category, issues in sorted(self.warnings_by_category.items(), 
                                    key=lambda x: len(x[1]), reverse=True):
            summary_lines.extend([
                f"### {category}",
                f"**Count**: {len(issues)}",
                "",
                "**Issues**:",
                ""
            ])
            
            # Show unique issues in this category
            unique_issues = list(set(issues))
            for issue in unique_issues[:5]:  # Show top 5 unique issues
                summary_lines.append(f"- {issue}")
            
            if len(unique_issues) > 5:
                summary_lines.append(f"- ... and {len(unique_issues) - 5} more")
            
            summary_lines.append("")
        
        # Add top 10 most frequent issues
        summary_lines.extend([
            "## 🔥 Top 10 Most Frequent Issues",
            ""
        ])
        
        for i, (issue, count) in enumerate(self.issue_frequency.most_common(10), 1):
            summary_lines.append(f"{i}. **{count}x** - {issue}")
        
        summary_lines.extend([
            "",
            "## 💡 Suggested Actions",
            ""
        ])
        
        # Generate suggested actions based on categories
        suggestions = self._generate_suggestions()
        for suggestion in suggestions:
            summary_lines.append(f"- {suggestion}")
        
        summary_lines.extend([
            "",
            "## 📈 Document Health Score",
            ""
        ])
        
        # Calculate and display document health scores
        health_scores = self._calculate_health_scores()
        summary_lines.extend([
            "| Document | Warnings | Criticals | Health Score |",
            "|----------|----------|-----------|--------------|"
        ])
        
        for doc_name, score_info in sorted(health_scores.items(), 
                                         key=lambda x: x[1]['score'], reverse=True):
            warnings = score_info['warnings']
            criticals = score_info['criticals']
            score = score_info['score']
            status = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
            
            summary_lines.append(f"| {doc_name} | {warnings} | {criticals} | {status} {score}% |")
        
        summary_lines.extend([
            "",
            "## 🎯 Priority Recommendations",
            ""
        ])
        
        # Generate priority recommendations
        priorities = self._generate_priorities()
        for priority in priorities:
            summary_lines.append(f"- {priority}")
        
        summary_lines.extend([
            "",
            "---",
            f"*Generated by AI-Assisted Validation Summary Generator*",
            f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])
        
        return "\n".join(summary_lines)
    
    def _generate_suggestions(self) -> List[str]:
        """Generate actionable suggestions based on issue categories."""
        suggestions = []
        
        if "Placeholder / Missing Content" in self.warnings_by_category:
            count = len(self.warnings_by_category["Placeholder / Missing Content"])
            suggestions.append(f"**Complete placeholder content** ({count} issues): Replace `...`, `TODO`, `TBD` with actual implementation details")
        
        if "Code Block Issues" in self.warnings_by_category:
            count = len(self.warnings_by_category["Code Block Issues"])
            suggestions.append(f"**Add language hints to code blocks** ({count} issues): Specify `python`, `yaml`, `json` etc. for better syntax highlighting")
        
        if "Terminology / Glossary Inconsistencies" in self.warnings_by_category:
            count = len(self.warnings_by_category["Terminology / Glossary Inconsistencies"])
            suggestions.append(f"**Standardize terminology** ({count} issues): Use consistent capitalization (e.g., 'SecFlow' not 'secflow')")
        
        if "Frontmatter or Link Issues" in self.warnings_by_category:
            count = len(self.warnings_by_category["Frontmatter or Link Issues"])
            suggestions.append(f"**Fix frontmatter and links** ({count} issues): Ensure all documents have proper YAML metadata and valid internal links")
        
        if "Diagram / Visual Issues" in self.warnings_by_category:
            count = len(self.warnings_by_category["Diagram / Visual Issues"])
            suggestions.append(f"**Improve ASCII diagrams** ({count} issues): Simplify box drawing characters for better readability")
        
        # General suggestions
        suggestions.extend([
            "**Run validation regularly**: Use `make validate` before committing changes",
            "**Review validation summary**: Check `VALIDATION_SUMMARY.md` for detailed insights",
            "**Follow glossary standards**: Use `docs/review/glossary.yml` for terminology consistency",
            "**Complete code examples**: Replace placeholders with working code snippets"
        ])
        
        return suggestions
    
    def _calculate_health_scores(self) -> Dict[str, Dict[str, Any]]:
        """Calculate health scores for each document."""
        health_scores = {}
        
        for doc_name, stats in self.document_stats.items():
            warnings = stats['warnings']
            criticals = stats['criticals']
            
            # Calculate score (100 - warnings*2 - criticals*10)
            score = max(0, 100 - (warnings * 2) - (criticals * 10))
            
            health_scores[doc_name] = {
                'warnings': warnings,
                'criticals': criticals,
                'score': score
            }
        
        return health_scores
    
    def _generate_priorities(self) -> List[str]:
        """Generate priority recommendations based on analysis."""
        priorities = []
        
        # Find documents with highest warning counts
        high_warning_docs = sorted(self.document_stats.items(), 
                                 key=lambda x: x[1]['warnings'], reverse=True)[:3]
        
        if high_warning_docs:
            priorities.append(f"**Focus on high-warning documents**: {', '.join([doc[0] for doc in high_warning_docs])}")
        
        # Check for critical issues
        critical_docs = [doc for doc, stats in self.document_stats.items() if stats['criticals'] > 0]
        if critical_docs:
            priorities.append(f"**Address critical issues first**: {', '.join(critical_docs)}")
        
        # Category-based priorities
        if "Placeholder / Missing Content" in self.warnings_by_category:
            priorities.append("**Complete placeholder content**: High impact on documentation quality")
        
        if "Terminology / Glossary Inconsistencies" in self.warnings_by_category:
            priorities.append("**Standardize terminology**: Important for professional presentation")
        
        priorities.extend([
            "**Regular validation**: Run `make validate` before each commit",
            "**Team review**: Use structured review process for major changes",
            "**Continuous improvement**: Monitor validation trends over time"
        ])
        
        return priorities
    
    def update_review_status(self, stats: Dict[str, Any]):
        """Update REVIEW_STATUS.md with a one-line summary."""
        if not os.path.exists(REVIEW_STATUS):
            return
        
        # Read current content
        with open(REVIEW_STATUS, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add or update the auto-generated summary
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        summary_line = f"[Auto] Validation Summary updated — {stats['warnings']} warnings, {stats['criticals']} criticals ({timestamp})"
        
        # Check if auto summary already exists and replace it
        auto_pattern = r'\[Auto\] Validation Summary updated.*\n'
        if re.search(auto_pattern, content):
            content = re.sub(auto_pattern, f"{summary_line}\n", content)
        else:
            # Add at the end
            content = content.rstrip() + f"\n\n{summary_line}\n"
        
        # Write back
        with open(REVIEW_STATUS, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def run(self):
        """Main execution method."""
        try:
            print("🤖 Generating AI-Assisted Validation Summary...")
            
            # Generate summary
            summary_content = self.generate_summary()
            
            # Write summary file
            with open(VALIDATION_SUMMARY, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            
            # Update review status
            stats = self.parse_validation_report()
            self.update_review_status(stats)
            
            print(f"✅ Validation summary generated: {os.path.relpath(VALIDATION_SUMMARY, ROOT)}")
            print(f"📊 Categories: {len(self.warnings_by_category)}")
            print(f"🔍 Top issues: {len(self.issue_frequency)} unique issues")
            
        except Exception as e:
            print(f"❌ Error generating validation summary: {e}")
            raise

def main():
    """Main entry point."""
    generator = ValidationSummaryGenerator()
    generator.run()

if __name__ == "__main__":
    main()
