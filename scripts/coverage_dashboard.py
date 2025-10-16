#!/usr/bin/env python3
"""
Coverage Dashboard for M1 Test Coverage Tracking

This script generates a comprehensive coverage dashboard showing:
- Current coverage status
- Progress toward M1 80% target
- Coverage by module
- Coverage trends
- Coverage gaps analysis
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import subprocess
import datetime

class CoverageDashboard:
    """Coverage dashboard generator."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.coverage_file = self.project_root / "coverage.xml"
        self.html_report_dir = self.project_root / "htmlcov"
        self.reports_dir = self.project_root / "reports" / "coverage"
        
    def run_coverage_analysis(self) -> Dict:
        """Run coverage analysis and return results."""
        print("🔍 Running coverage analysis...")
        
        # Run pytest with coverage
        cmd = [
            "pytest", 
            "--cov=.", 
            "--cov-report=xml", 
            "--cov-report=html",
            "--cov-report=term-missing",
            "-q"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            if result.returncode != 0:
                print(f"⚠️  Coverage analysis had issues: {result.stderr}")
        except Exception as e:
            print(f"❌ Failed to run coverage analysis: {e}")
            return {}
        
        # Parse coverage results
        return self._parse_coverage_results()
    
    def _parse_coverage_results(self) -> Dict:
        """Parse coverage results from XML and terminal output."""
        coverage_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_statements": 0,
            "covered_statements": 0,
            "missing_statements": 0,
            "coverage_percentage": 0.0,
            "modules": [],
            "target_coverage": 80.0,
            "coverage_gap": 0
        }
        
        # Parse XML coverage file if it exists
        if self.coverage_file.exists():
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(self.coverage_file)
                root = tree.getroot()
                
                # Get overall coverage
                coverage_data["total_statements"] = int(root.get("lines-valid", 0))
                coverage_data["covered_statements"] = int(root.get("lines-covered", 0))
                coverage_data["missing_statements"] = coverage_data["total_statements"] - coverage_data["covered_statements"]
                coverage_data["coverage_percentage"] = float(root.get("line-rate", 0)) * 100
                
                # Parse module coverage
                for package in root.findall(".//package"):
                    package_name = package.get("name", "unknown")
                    package_statements = int(package.get("lines-valid", 0))
                    package_covered = int(package.get("lines-covered", 0))
                    package_missing = package_statements - package_covered
                    package_coverage = (package_covered / package_statements * 100) if package_statements > 0 else 0
                    
                    coverage_data["modules"].append({
                        "name": package_name,
                        "statements": package_statements,
                        "covered": package_covered,
                        "missing": package_missing,
                        "coverage": package_coverage,
                        "priority": self._get_module_priority(package_name, package_coverage)
                    })
                
            except Exception as e:
                print(f"⚠️  Failed to parse XML coverage: {e}")
        
        # Calculate coverage gap
        target_statements = int(coverage_data["total_statements"] * coverage_data["target_coverage"] / 100)
        coverage_data["coverage_gap"] = target_statements - coverage_data["covered_statements"]
        
        return coverage_data
    
    def _get_module_priority(self, module_name: str, coverage: float) -> str:
        """Determine module priority based on name and coverage."""
        # Critical M1 components
        critical_modules = [
            "packages/workflow_engine",
            "packages/plugins/loader",
            "findings",
            "security/signing",
            "security/sandbox"
        ]
        
        # High-impact, low-coverage modules
        if any(critical in module_name for critical in critical_modules):
            if coverage < 80:
                return "HIGH"
            else:
                return "MEDIUM"
        
        # Core system components
        core_modules = ["web_routes", "store", "packages/runtime_core"]
        if any(core in module_name for core in core_modules):
            if coverage < 70:
                return "HIGH"
            else:
                return "MEDIUM"
        
        # Supporting components
        if coverage < 60:
            return "MEDIUM"
        else:
            return "LOW"
    
    def generate_dashboard(self, coverage_data: Dict) -> str:
        """Generate HTML dashboard."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SecFlow M1 Coverage Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric {{ background: #ecf0f1; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ color: #7f8c8d; margin-top: 5px; }}
        .progress-bar {{ background: #bdc3c7; height: 20px; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ background: #27ae60; height: 100%; transition: width 0.3s; }}
        .modules {{ margin: 20px 0; }}
        .module {{ background: white; border: 1px solid #bdc3c7; margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .module-header {{ display: flex; justify-content: space-between; align-items: center; }}
        .module-name {{ font-weight: bold; }}
        .module-coverage {{ font-size: 1.2em; }}
        .priority-high {{ border-left: 5px solid #e74c3c; }}
        .priority-medium {{ border-left: 5px solid #f39c12; }}
        .priority-low {{ border-left: 5px solid #27ae60; }}
        .coverage-low {{ color: #e74c3c; }}
        .coverage-medium {{ color: #f39c12; }}
        .coverage-high {{ color: #27ae60; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 SecFlow M1 Coverage Dashboard</h1>
        <p>Target: 80% Coverage | Generated: {coverage_data.get('timestamp', 'Unknown')}</p>
    </div>
    
    <div class="metrics">
        <div class="metric">
            <div class="metric-value">{coverage_data.get('coverage_percentage', 0):.1f}%</div>
            <div class="metric-label">Current Coverage</div>
        </div>
        <div class="metric">
            <div class="metric-value">{coverage_data.get('target_coverage', 80)}%</div>
            <div class="metric-label">Target Coverage</div>
        </div>
        <div class="metric">
            <div class="metric-value">{coverage_data.get('coverage_gap', 0):,}</div>
            <div class="metric-label">Statements to Cover</div>
        </div>
        <div class="metric">
            <div class="metric-value">{coverage_data.get('total_statements', 0):,}</div>
            <div class="metric-label">Total Statements</div>
        </div>
    </div>
    
    <div class="progress-bar">
        <div class="progress-fill" style="width: {coverage_data.get('coverage_percentage', 0)}%"></div>
    </div>
    
    <div class="modules">
        <h2>📊 Module Coverage Analysis</h2>
        {self._generate_module_html(coverage_data.get('modules', []))}
    </div>
</body>
</html>
        """
        
        return html_content
    
    def _generate_module_html(self, modules: List[Dict]) -> str:
        """Generate HTML for module coverage."""
        if not modules:
            return "<p>No module data available.</p>"
        
        # Sort modules by priority and coverage
        modules.sort(key=lambda x: (x.get('priority', 'LOW'), -x.get('coverage', 0)))
        
        html = ""
        for module in modules:
            priority = module.get('priority', 'LOW').lower()
            coverage = module.get('coverage', 0)
            coverage_class = 'coverage-low' if coverage < 60 else 'coverage-medium' if coverage < 80 else 'coverage-high'
            
            html += f"""
            <div class="module priority-{priority}">
                <div class="module-header">
                    <div class="module-name">{module.get('name', 'Unknown')}</div>
                    <div class="module-coverage {coverage_class}">{coverage:.1f}%</div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {coverage}%"></div>
                </div>
                <p>Covered: {module.get('covered', 0):,} / {module.get('statements', 0):,} statements</p>
            </div>
            """
        
        return html
    
    def save_dashboard(self, coverage_data: Dict):
        """Save dashboard to file."""
        # Ensure reports directory exists
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate HTML dashboard
        html_content = self.generate_dashboard(coverage_data)
        
        # Save HTML dashboard
        dashboard_file = self.reports_dir / f"coverage-dashboard-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
        with open(dashboard_file, 'w') as f:
            f.write(html_content)
        
        # Save JSON data
        json_file = self.reports_dir / f"coverage-data-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json.dump(coverage_data, f, indent=2)
        
        print(f"📊 Dashboard saved: {dashboard_file}")
        print(f"📊 Data saved: {json_file}")
        
        return dashboard_file, json_file
    
    def print_summary(self, coverage_data: Dict):
        """Print coverage summary to console."""
        print("\n" + "="*60)
        print("🎯 M1 COVERAGE DASHBOARD SUMMARY")
        print("="*60)
        
        current = coverage_data.get('coverage_percentage', 0)
        target = coverage_data.get('target_coverage', 80)
        gap = coverage_data.get('coverage_gap', 0)
        
        print(f"📊 Current Coverage: {current:.1f}%")
        print(f"🎯 Target Coverage: {target}%")
        print(f"📈 Coverage Gap: {gap:,} statements")
        print(f"📋 Total Statements: {coverage_data.get('total_statements', 0):,}")
        
        # Progress calculation
        progress = (current / target) * 100 if target > 0 else 0
        print(f"🚀 Progress to Target: {progress:.1f}%")
        
        # Priority modules
        high_priority = [m for m in coverage_data.get('modules', []) if m.get('priority') == 'HIGH']
        if high_priority:
            print(f"\n🔴 High Priority Modules ({len(high_priority)}):")
            for module in high_priority[:5]:  # Show top 5
                print(f"   • {module.get('name', 'Unknown')}: {module.get('coverage', 0):.1f}%")
        
        print("\n" + "="*60)

def main():
    """Main function."""
    dashboard = CoverageDashboard()
    
    # Run coverage analysis
    coverage_data = dashboard.run_coverage_analysis()
    
    if not coverage_data:
        print("❌ Failed to generate coverage data")
        sys.exit(1)
    
    # Print summary
    dashboard.print_summary(coverage_data)
    
    # Save dashboard
    dashboard.save_dashboard(coverage_data)
    
    print("\n✅ Coverage dashboard generated successfully!")

if __name__ == "__main__":
    main()
