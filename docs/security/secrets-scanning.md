# Secrets Scanning Integration

## Overview
This document outlines the integration of secrets scanning into the SecFlow security framework using TruffleHog.

## Secrets Scanning Implementation

### Tool Selection
- **Primary Tool**: TruffleHog (Python-based)
- **Alternative**: Gitleaks (Go-based, requires binary installation)
- **Integration**: CI/CD pipeline and local development

### Secrets Scanning Configuration

#### TruffleHog Configuration
```python
# tools/secrets_scanner.py
import subprocess
import json
import pathlib
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class SecretFinding:
    """Represents a detected secret."""
    file_path: str
    line_number: int
    secret_type: str
    confidence: str
    description: str
    severity: str

class SecretsScanner:
    """Secrets scanning using TruffleHog."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = pathlib.Path(repo_path)
        self.exclude_patterns = [
            "*.pyc",
            "__pycache__/*",
            "venv/*",
            "node_modules/*",
            ".git/*",
            "*.log",
            "*.tmp"
        ]
    
    def scan_repository(self) -> List[SecretFinding]:
        """Scan repository for secrets."""
        try:
            # Run TruffleHog scan
            cmd = [
                "trufflehog",
                str(self.repo_path),
                "--json",
                "--entropy",
                "True",
                "--regex",
                "True"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"TruffleHog scan failed: {result.stderr}")
                return []
            
            # Parse results
            findings = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        finding_data = json.loads(line)
                        finding = SecretFinding(
                            file_path=finding_data.get('path', ''),
                            line_number=finding_data.get('line', 0),
                            secret_type=finding_data.get('reason', ''),
                            confidence=finding_data.get('confidence', 'medium'),
                            description=finding_data.get('description', ''),
                            severity=self._determine_severity(finding_data)
                        )
                        findings.append(finding)
                    except json.JSONDecodeError:
                        continue
            
            return findings
            
        except subprocess.TimeoutExpired:
            print("TruffleHog scan timed out")
            return []
        except Exception as e:
            print(f"Secrets scan failed: {e}")
            return []
    
    def _determine_severity(self, finding_data: Dict[str, Any]) -> str:
        """Determine severity of secret finding."""
        reason = finding_data.get('reason', '').lower()
        
        # High severity patterns
        high_severity = ['password', 'secret', 'key', 'token', 'api_key', 'private_key']
        if any(pattern in reason for pattern in high_severity):
            return 'high'
        
        # Medium severity patterns
        medium_severity = ['credential', 'auth', 'access', 'bearer']
        if any(pattern in reason for pattern in medium_severity):
            return 'medium'
        
        return 'low'
    
    def generate_report(self, findings: List[SecretFinding]) -> str:
        """Generate secrets scan report."""
        report = []
        report.append("# Secrets Scan Report")
        report.append(f"**Total Findings:** {len(findings)}")
        report.append("")
        
        # Group by severity
        high_findings = [f for f in findings if f.severity == 'high']
        medium_findings = [f for f in findings if f.severity == 'medium']
        low_findings = [f for f in findings if f.severity == 'low']
        
        if high_findings:
            report.append("## High Severity Findings")
            for finding in high_findings:
                report.append(f"- **{finding.file_path}:{finding.line_number}** - {finding.secret_type}")
                report.append(f"  - Description: {finding.description}")
            report.append("")
        
        if medium_findings:
            report.append("## Medium Severity Findings")
            for finding in medium_findings:
                report.append(f"- **{finding.file_path}:{finding.line_number}** - {finding.secret_type}")
                report.append(f"  - Description: {finding.description}")
            report.append("")
        
        if low_findings:
            report.append("## Low Severity Findings")
            for finding in low_findings:
                report.append(f"- **{finding.file_path}:{finding.line_number}** - {finding.secret_type}")
                report.append(f"  - Description: {finding.description}")
        
        return '\n'.join(report)
```

### CI/CD Integration

#### GitHub Actions Workflow
```yaml
secrets-scan:
  runs-on: ubuntu-latest
  steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0
        
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install TruffleHog
      run: |
        pip install trufflehog
        
    - name: Run secrets scan
      run: |
        mkdir -p reports/security
        python tools/secrets_scanner.py > reports/security/secrets-scan-$(date +%Y%m%d).json
        
    - name: Upload secrets scan results
      uses: actions/upload-artifact@v3
      with:
        name: secrets-scan-${{ github.run_number }}
        path: reports/security/secrets-scan-*.json
      if: always()
```

### Secrets Detection Patterns

#### Common Secret Types
- **API Keys**: AWS, Google Cloud, Azure, GitHub, etc.
- **Passwords**: Database passwords, service passwords
- **Tokens**: JWT tokens, OAuth tokens, access tokens
- **Private Keys**: SSH keys, SSL certificates, GPG keys
- **Credentials**: Username/password combinations
- **Database URLs**: Connection strings with embedded credentials

#### Custom Detection Rules
```json
{
  "rules": [
    {
      "name": "AWS Access Key",
      "pattern": "AKIA[0-9A-Z]{16}",
      "severity": "high",
      "description": "AWS Access Key ID"
    },
    {
      "name": "GitHub Token",
      "pattern": "ghp_[0-9A-Za-z]{36}",
      "severity": "high",
      "description": "GitHub Personal Access Token"
    },
    {
      "name": "JWT Token",
      "pattern": "eyJ[A-Za-z0-9+/=]+",
      "severity": "medium",
      "description": "JSON Web Token"
    }
  ]
}
```

### Security Best Practices

#### Prevention
- **Pre-commit Hooks**: Scan for secrets before commits
- **IDE Integration**: Real-time secrets detection in editors
- **Developer Training**: Security awareness for developers
- **Code Review**: Manual review for sensitive code

#### Detection
- **Automated Scanning**: Regular scans in CI/CD pipeline
- **Historical Scanning**: Scan git history for leaked secrets
- **Entropy Analysis**: Detect high-entropy strings
- **Pattern Matching**: Use regex patterns for known secret formats

#### Response
- **Immediate Rotation**: Rotate compromised secrets immediately
- **Incident Response**: Follow security incident procedures
- **Notification**: Alert security team and stakeholders
- **Documentation**: Document findings and remediation steps

### Integration with Security Framework

#### Security Monitoring
- **Daily Scans**: Automated daily secrets scanning
- **PR Integration**: Scan pull requests for secrets
- **Alert System**: Real-time alerts for high-severity findings
- **Reporting**: Regular security reports including secrets findings

#### Compliance Integration
- **NIST SP 800-53**: SI-4 (Information System Monitoring)
- **ISO 27001**: A.12.4 (Logging and Monitoring)
- **SOC 2**: CC6.1 (Logical and Physical Access Controls)
- **OWASP**: A07 (Identification and Authentication Failures)

### Tools and Technologies

#### Primary Tools
- **TruffleHog**: Python-based secrets scanner
- **Gitleaks**: Go-based secrets scanner
- **GitGuardian**: Commercial secrets detection
- **GitHub Secret Scanning**: Native GitHub feature

#### Integration Tools
- **Pre-commit**: Git hooks for pre-commit scanning
- **GitHub Actions**: CI/CD integration
- **Jenkins**: CI/CD integration
- **GitLab CI**: CI/CD integration

### Monitoring and Alerting

#### Alert Thresholds
- **High Severity**: Immediate alert for any high-severity finding
- **Medium Severity**: Daily summary of medium-severity findings
- **Low Severity**: Weekly summary of low-severity findings

#### Notification Channels
- **Email**: Security team notifications
- **Slack**: Real-time alerts in security channel
- **JIRA**: Automatic ticket creation for findings
- **Dashboard**: Security metrics dashboard

### Remediation Procedures

#### Immediate Response
1. **Assess Impact**: Determine scope of secret exposure
2. **Rotate Secrets**: Immediately rotate compromised secrets
3. **Notify Stakeholders**: Alert relevant teams and users
4. **Document Incident**: Record details for future reference

#### Long-term Remediation
1. **Root Cause Analysis**: Identify how secret was exposed
2. **Process Improvement**: Update development processes
3. **Training**: Provide additional security training
4. **Tool Enhancement**: Improve detection and prevention tools

### Metrics and KPIs

#### Security Metrics
- **Secrets Found**: Number of secrets detected per scan
- **False Positive Rate**: Percentage of false positives
- **Mean Time to Detection**: Time to detect secret exposure
- **Mean Time to Remediation**: Time to fix secret exposure

#### Operational Metrics
- **Scan Performance**: Duration and success rate of scans
- **Coverage**: Percentage of codebase scanned
- **Integration**: Success rate of CI/CD integration
- **User Adoption**: Developer usage of prevention tools

## References

- [TruffleHog Documentation](https://github.com/trufflesecurity/trufflehog)
- [OWASP Secrets Management](https://owasp.org/www-project-top-ten/2017/A2_2017-Broken_Authentication)
- [NIST SP 800-53 SI-4](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
