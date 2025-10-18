"""
Quality Gate Enforcement Configuration for SecFlow

This module provides configuration and utilities for enforcing quality gates
across the SecFlow project.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Quality gate thresholds
QUALITY_GATES = {
    "coverage": {
        "minimum": 80.0,
        "target": 90.0,
        "critical": 75.0
    },
    "linting": {
        "ruff_errors": 0,
        "ruff_warnings": 10
    },
    "type_checking": {
        "pyright_errors": 0,
        "pyright_warnings": 5
    },
    "security": {
        "critical_vulnerabilities": 0,
        "high_vulnerabilities": 0,
        "medium_vulnerabilities": 5
    },
    "performance": {
        "workflow_execution_time": 30.0,  # seconds
        "memory_usage_mb": 500.0,
        "test_execution_time": 300.0  # seconds
    },
    "build": {
        "build_size_mb": 400.0,
        "build_time": 600.0  # seconds
    }
}

class QualityGateStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

@dataclass
class QualityGateResult:
    """Result of a quality gate check."""
    name: str
    status: QualityGateStatus
    value: Any
    threshold: Any
    message: str
    details: Optional[Dict[str, Any]] = None

class QualityGateEnforcer:
    """Enforces quality gates across the project."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[QualityGateResult] = []
    
    def run_all_gates(self) -> List[QualityGateResult]:
        """Run all quality gates and return results."""
        self.results = []
        
        # Coverage gate
        self._check_coverage()
        
        # Linting gate
        self._check_linting()
        
        # Type checking gate
        self._check_type_checking()
        
        # Security gate
        self._check_security()
        
        # Performance gate
        self._check_performance()
        
        # Build gate
        self._check_build()
        
        return self.results
    
    def _check_coverage(self):
        """Check test coverage."""
        try:
            # Run coverage
            result = subprocess.run([
                "coverage", "run", "-m", "pytest", "-q"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                self.results.append(QualityGateResult(
                    name="coverage",
                    status=QualityGateStatus.FAILED,
                    value=0.0,
                    threshold=QUALITY_GATES["coverage"]["minimum"],
                    message="Coverage collection failed",
                    details={"error": result.stderr}
                ))
                return
            
            # Get coverage report
            coverage_result = subprocess.run([
                "coverage", "report", "--show-missing"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if coverage_result.returncode != 0:
                self.results.append(QualityGateResult(
                    name="coverage",
                    status=QualityGateStatus.FAILED,
                    value=0.0,
                    threshold=QUALITY_GATES["coverage"]["minimum"],
                    message="Coverage reporting failed",
                    details={"error": coverage_result.stderr}
                ))
                return
            
            # Parse coverage percentage
            coverage_lines = coverage_result.stdout.split('\n')
            total_line = None
            for line in coverage_lines:
                if line.strip().startswith('TOTAL'):
                    total_line = line
                    break
            
            if not total_line:
                self.results.append(QualityGateResult(
                    name="coverage",
                    status=QualityGateStatus.FAILED,
                    value=0.0,
                    threshold=QUALITY_GATES["coverage"]["minimum"],
                    message="Could not parse coverage total"
                ))
                return
            
            # Extract percentage
            parts = total_line.split()
            percentage_str = parts[-1].replace('%', '')
            try:
                coverage_percentage = float(percentage_str)
            except ValueError:
                self.results.append(QualityGateResult(
                    name="coverage",
                    status=QualityGateStatus.FAILED,
                    value=0.0,
                    threshold=QUALITY_GATES["coverage"]["minimum"],
                    message="Could not parse coverage percentage"
                ))
                return
            
            # Determine status
            if coverage_percentage >= QUALITY_GATES["coverage"]["target"]:
                status = QualityGateStatus.PASSED
                message = f"Coverage {coverage_percentage:.1f}% exceeds target"
            elif coverage_percentage >= QUALITY_GATES["coverage"]["minimum"]:
                status = QualityGateStatus.WARNING
                message = f"Coverage {coverage_percentage:.1f}% meets minimum but below target"
            elif coverage_percentage >= QUALITY_GATES["coverage"]["critical"]:
                status = QualityGateStatus.WARNING
                message = f"Coverage {coverage_percentage:.1f}% below minimum threshold"
            else:
                status = QualityGateStatus.FAILED
                message = f"Coverage {coverage_percentage:.1f}% below critical threshold"
            
            self.results.append(QualityGateResult(
                name="coverage",
                status=status,
                value=coverage_percentage,
                threshold=QUALITY_GATES["coverage"]["minimum"],
                message=message,
                details={"coverage_report": coverage_result.stdout}
            ))
            
        except Exception as e:
            self.results.append(QualityGateResult(
                name="coverage",
                status=QualityGateStatus.FAILED,
                value=0.0,
                threshold=QUALITY_GATES["coverage"]["minimum"],
                message=f"Coverage check failed: {str(e)}"
            ))
    
    def _check_linting(self):
        """Check code linting."""
        try:
            # Run ruff
            result = subprocess.run([
                "ruff", "check", "."
            ], capture_output=True, text=True, cwd=self.project_root)
            
            # Parse ruff output
            error_count = 0
            warning_count = 0
            
            for line in result.stdout.split('\n'):
                if line.strip():
                    if 'error' in line.lower():
                        error_count += 1
                    elif 'warning' in line.lower():
                        warning_count += 1
            
            # Determine status
            if error_count == 0 and warning_count <= QUALITY_GATES["linting"]["ruff_warnings"]:
                status = QualityGateStatus.PASSED
                message = f"Linting passed: {error_count} errors, {warning_count} warnings"
            elif error_count == 0:
                status = QualityGateStatus.WARNING
                message = f"Linting warning: {warning_count} warnings exceed threshold"
            else:
                status = QualityGateStatus.FAILED
                message = f"Linting failed: {error_count} errors, {warning_count} warnings"
            
            self.results.append(QualityGateResult(
                name="linting",
                status=status,
                value={"errors": error_count, "warnings": warning_count},
                threshold={"errors": QUALITY_GATES["linting"]["ruff_errors"], "warnings": QUALITY_GATES["linting"]["ruff_warnings"]},
                message=message,
                details={"ruff_output": result.stdout}
            ))
            
        except Exception as e:
            self.results.append(QualityGateResult(
                name="linting",
                status=QualityGateStatus.FAILED,
                value={"errors": -1, "warnings": -1},
                threshold={"errors": QUALITY_GATES["linting"]["ruff_errors"], "warnings": QUALITY_GATES["linting"]["ruff_warnings"]},
                message=f"Linting check failed: {str(e)}"
            ))
    
    def _check_type_checking(self):
        """Check type checking."""
        try:
            # Run pyright
            result = subprocess.run([
                "pyright", "."
            ], capture_output=True, text=True, cwd=self.project_root)
            
            # Parse pyright output
            error_count = 0
            warning_count = 0
            
            for line in result.stdout.split('\n'):
                if line.strip():
                    if 'error' in line.lower():
                        error_count += 1
                    elif 'warning' in line.lower():
                        warning_count += 1
            
            # Determine status
            if error_count == 0 and warning_count <= QUALITY_GATES["type_checking"]["pyright_warnings"]:
                status = QualityGateStatus.PASSED
                message = f"Type checking passed: {error_count} errors, {warning_count} warnings"
            elif error_count == 0:
                status = QualityGateStatus.WARNING
                message = f"Type checking warning: {warning_count} warnings exceed threshold"
            else:
                status = QualityGateStatus.FAILED
                message = f"Type checking failed: {error_count} errors, {warning_count} warnings"
            
            self.results.append(QualityGateResult(
                name="type_checking",
                status=status,
                value={"errors": error_count, "warnings": warning_count},
                threshold={"errors": QUALITY_GATES["type_checking"]["pyright_errors"], "warnings": QUALITY_GATES["type_checking"]["pyright_warnings"]},
                message=message,
                details={"pyright_output": result.stdout}
            ))
            
        except Exception as e:
            self.results.append(QualityGateResult(
                name="type_checking",
                status=QualityGateStatus.FAILED,
                value={"errors": -1, "warnings": -1},
                threshold={"errors": QUALITY_GATES["type_checking"]["pyright_errors"], "warnings": QUALITY_GATES["type_checking"]["pyright_warnings"]},
                message=f"Type checking failed: {str(e)}"
            ))
    
    def _check_security(self):
        """Check security vulnerabilities."""
        try:
            # Run pip-audit
            result = subprocess.run([
                "pip-audit", "--format=json"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                self.results.append(QualityGateResult(
                    name="security",
                    status=QualityGateStatus.FAILED,
                    value={"critical": -1, "high": -1, "medium": -1},
                    threshold={"critical": QUALITY_GATES["security"]["critical_vulnerabilities"], "high": QUALITY_GATES["security"]["high_vulnerabilities"], "medium": QUALITY_GATES["security"]["medium_vulnerabilities"]},
                    message="Security scan failed",
                    details={"error": result.stderr}
                ))
                return
            
            # Parse pip-audit output
            try:
                audit_data = json.loads(result.stdout)
                vulnerabilities = audit_data.get("vulnerabilities", [])
                
                critical_count = 0
                high_count = 0
                medium_count = 0
                
                for vuln in vulnerabilities:
                    severity = vuln.get("severity", "").lower()
                    if severity == "critical":
                        critical_count += 1
                    elif severity == "high":
                        high_count += 1
                    elif severity == "medium":
                        medium_count += 1
                
                # Determine status
                if (critical_count == 0 and 
                    high_count == 0 and 
                    medium_count <= QUALITY_GATES["security"]["medium_vulnerabilities"]):
                    status = QualityGateStatus.PASSED
                    message = f"Security scan passed: {critical_count} critical, {high_count} high, {medium_count} medium"
                elif critical_count == 0 and high_count == 0:
                    status = QualityGateStatus.WARNING
                    message = f"Security warning: {medium_count} medium vulnerabilities exceed threshold"
                else:
                    status = QualityGateStatus.FAILED
                    message = f"Security scan failed: {critical_count} critical, {high_count} high, {medium_count} medium"
                
                self.results.append(QualityGateResult(
                    name="security",
                    status=status,
                    value={"critical": critical_count, "high": high_count, "medium": medium_count},
                    threshold={"critical": QUALITY_GATES["security"]["critical_vulnerabilities"], "high": QUALITY_GATES["security"]["high_vulnerabilities"], "medium": QUALITY_GATES["security"]["medium_vulnerabilities"]},
                    message=message,
                    details={"vulnerabilities": vulnerabilities}
                ))
                
            except json.JSONDecodeError:
                self.results.append(QualityGateResult(
                    name="security",
                    status=QualityGateStatus.FAILED,
                    value={"critical": -1, "high": -1, "medium": -1},
                    threshold={"critical": QUALITY_GATES["security"]["critical_vulnerabilities"], "high": QUALITY_GATES["security"]["high_vulnerabilities"], "medium": QUALITY_GATES["security"]["medium_vulnerabilities"]},
                    message="Could not parse security scan results"
                ))
                
        except Exception as e:
            self.results.append(QualityGateResult(
                name="security",
                status=QualityGateStatus.FAILED,
                value={"critical": -1, "high": -1, "medium": -1},
                threshold={"critical": QUALITY_GATES["security"]["critical_vulnerabilities"], "high": QUALITY_GATES["security"]["high_vulnerabilities"], "medium": QUALITY_GATES["security"]["medium_vulnerabilities"]},
                message=f"Security check failed: {str(e)}"
            ))
    
    def _check_performance(self):
        """Check performance metrics."""
        try:
            # Run performance tests
            start_time = time.time()
            result = subprocess.run([
                "pytest", "tests/integration/test_performance.py", "-v"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=QUALITY_GATES["performance"]["test_execution_time"])
            
            execution_time = time.time() - start_time
            
            # Parse performance results
            if result.returncode != 0:
                self.results.append(QualityGateResult(
                    name="performance",
                    status=QualityGateStatus.FAILED,
                    value={"execution_time": execution_time, "test_status": "failed"},
                    threshold={"execution_time": QUALITY_GATES["performance"]["test_execution_time"]},
                    message="Performance tests failed",
                    details={"error": result.stderr}
                ))
                return
            
            # Check execution time
            if execution_time <= QUALITY_GATES["performance"]["test_execution_time"]:
                status = QualityGateStatus.PASSED
                message = f"Performance tests passed in {execution_time:.1f}s"
            else:
                status = QualityGateStatus.WARNING
                message = f"Performance tests slow: {execution_time:.1f}s exceeds threshold"
            
            self.results.append(QualityGateResult(
                name="performance",
                status=status,
                value={"execution_time": execution_time, "test_status": "passed"},
                threshold={"execution_time": QUALITY_GATES["performance"]["test_execution_time"]},
                message=message,
                details={"test_output": result.stdout}
            ))
            
        except subprocess.TimeoutExpired:
            self.results.append(QualityGateResult(
                name="performance",
                status=QualityGateStatus.FAILED,
                value={"execution_time": QUALITY_GATES["performance"]["test_execution_time"], "test_status": "timeout"},
                threshold={"execution_time": QUALITY_GATES["performance"]["test_execution_time"]},
                message="Performance tests timed out"
            ))
        except Exception as e:
            self.results.append(QualityGateResult(
                name="performance",
                status=QualityGateStatus.FAILED,
                value={"execution_time": -1, "test_status": "error"},
                threshold={"execution_time": QUALITY_GATES["performance"]["test_execution_time"]},
                message=f"Performance check failed: {str(e)}"
            ))
    
    def _check_build(self):
        """Check build metrics."""
        try:
            # Run build
            start_time = time.time()
            result = subprocess.run([
                "python", "-m", "build"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=QUALITY_GATES["build"]["build_time"])
            
            build_time = time.time() - start_time
            
            if result.returncode != 0:
                self.results.append(QualityGateResult(
                    name="build",
                    status=QualityGateStatus.FAILED,
                    value={"build_time": build_time, "build_status": "failed"},
                    threshold={"build_time": QUALITY_GATES["build"]["build_time"]},
                    message="Build failed",
                    details={"error": result.stderr}
                ))
                return
            
            # Check build time
            if build_time <= QUALITY_GATES["build"]["build_time"]:
                status = QualityGateStatus.PASSED
                message = f"Build passed in {build_time:.1f}s"
            else:
                status = QualityGateStatus.WARNING
                message = f"Build slow: {build_time:.1f}s exceeds threshold"
            
            self.results.append(QualityGateResult(
                name="build",
                status=status,
                value={"build_time": build_time, "build_status": "passed"},
                threshold={"build_time": QUALITY_GATES["build"]["build_time"]},
                message=message,
                details={"build_output": result.stdout}
            ))
            
        except subprocess.TimeoutExpired:
            self.results.append(QualityGateResult(
                name="build",
                status=QualityGateStatus.FAILED,
                value={"build_time": QUALITY_GATES["build"]["build_time"], "build_status": "timeout"},
                threshold={"build_time": QUALITY_GATES["build"]["build_time"]},
                message="Build timed out"
            ))
        except Exception as e:
            self.results.append(QualityGateResult(
                name="build",
                status=QualityGateStatus.FAILED,
                value={"build_time": -1, "build_status": "error"},
                threshold={"build_time": QUALITY_GATES["build"]["build_time"]},
                message=f"Build check failed: {str(e)}"
            ))
    
    def generate_report(self) -> str:
        """Generate a quality gate report."""
        report = []
        report.append("# Quality Gate Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Summary
        passed = sum(1 for r in self.results if r.status == QualityGateStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == QualityGateStatus.FAILED)
        warnings = sum(1 for r in self.results if r.status == QualityGateStatus.WARNING)
        
        report.append("## Summary")
        report.append(f"- **Passed:** {passed}")
        report.append(f"- **Failed:** {failed}")
        report.append(f"- **Warnings:** {warnings}")
        report.append(f"- **Total:** {len(self.results)}")
        report.append("")
        
        # Detailed results
        report.append("## Detailed Results")
        for result in self.results:
            status_emoji = {
                QualityGateStatus.PASSED: "✅",
                QualityGateStatus.FAILED: "❌",
                QualityGateStatus.WARNING: "⚠️",
                QualityGateStatus.SKIPPED: "⏭️"
            }
            
            report.append(f"### {status_emoji[result.status]} {result.name.title()}")
            report.append(f"**Status:** {result.status.value}")
            report.append(f"**Value:** {result.value}")
            report.append(f"**Threshold:** {result.threshold}")
            report.append(f"**Message:** {result.message}")
            
            if result.details:
                report.append("**Details:**")
                for key, value in result.details.items():
                    report.append(f"- {key}: {value}")
            
            report.append("")
        
        return "\n".join(report)
    
    def save_report(self, output_file: Path):
        """Save quality gate report to file."""
        report = self.generate_report()
        output_file.write_text(report)

# CLI interface
def main():
    """Main CLI interface for quality gate enforcement."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SecFlow Quality Gate Enforcer")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Project root directory")
    parser.add_argument("--output", type=Path, help="Output file for report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    enforcer = QualityGateEnforcer(args.project_root)
    results = enforcer.run_all_gates()
    
    if args.verbose:
        print(enforcer.generate_report())
    
    if args.output:
        enforcer.save_report(args.output)
    
    # Exit with appropriate code
    failed_gates = [r for r in results if r.status == QualityGateStatus.FAILED]
    if failed_gates:
        print(f"Quality gates failed: {len(failed_gates)}")
        sys.exit(1)
    else:
        print("All quality gates passed")
        sys.exit(0)

if __name__ == "__main__":
    main()
