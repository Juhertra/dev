#!/usr/bin/env python3
"""
Pattern Manager - Advanced pattern management with per-project directories,
community packs, and external integrations.
"""
import os
import json
import shutil
import requests
import zipfile
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

class PatternManager:
    """
    Advanced pattern management system supporting:
    - Per-project pattern directories
    - Community pattern packs with auto-update
    - External tool integrations (Nuclei, ModSecurity)
    - Pattern validation and testing
    - Pattern statistics and analytics
    """
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.patterns_dir = self.base_dir / "patterns"
        self.community_dir = self.patterns_dir / "community"
        self.projects_dir = self.patterns_dir / "projects"
        self.cache_dir = self.patterns_dir / "cache"
        self.temp_dir = self.patterns_dir / "temp"
        
        # Create directory structure
        for dir_path in [self.patterns_dir, self.community_dir, self.projects_dir, 
                        self.cache_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Community pack sources
        self.community_sources = {
            "owasp-crs": {
                "name": "OWASP Core Rule Set",
                "url": "https://github.com/coreruleset/coreruleset/archive/refs/heads/v4.0/master.zip",
                "description": "OWASP ModSecurity Core Rule Set patterns",
                "last_updated": None,
                "enabled": True
            },
            "nuclei-templates": {
                "name": "Nuclei Templates",
                "url": "https://github.com/projectdiscovery/nuclei-templates/archive/refs/heads/main.zip",
                "description": "ProjectDiscovery Nuclei security templates",
                "last_updated": None,
                "enabled": True
            },
            "security-patterns": {
                "name": "Security Patterns Collection",
                "url": "https://github.com/OWASP/security-patterns/archive/refs/heads/main.zip",
                "description": "OWASP security patterns and best practices",
                "last_updated": None,
                "enabled": False  # Disabled by default as it's more conceptual
            }
        }
        
        # Load community pack metadata
        self._load_community_metadata()
    
    def _load_community_metadata(self):
        """Load community pack update timestamps and status."""
        metadata_file = self.community_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    for pack_id, pack_data in metadata.items():
                        if pack_id in self.community_sources:
                            self.community_sources[pack_id].update(pack_data)
            except Exception as e:
                print(f"Warning: Could not load community metadata: {e}")
    
    def _save_community_metadata(self):
        """Save community pack metadata."""
        metadata_file = self.community_dir / "metadata.json"
        metadata = {}
        for pack_id, pack_data in self.community_sources.items():
            metadata[pack_id] = {
                "last_updated": pack_data.get("last_updated"),
                "enabled": pack_data.get("enabled", True)
            }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def create_project_patterns(self, project_id: str) -> bool:
        """Create a dedicated pattern directory for a project."""
        project_pattern_dir = self.projects_dir / project_id
        project_pattern_dir.mkdir(exist_ok=True)
        
        # Create default project patterns
        default_patterns = {
            "name": f"Project {project_id} Patterns",
            "version": "1.0.0",
            "description": f"Custom patterns for project {project_id}",
            "rules": [
                {
                    "id": f"{project_id}_custom_1",
                    "title": "Custom Pattern 1",
                    "regex": r"custom_pattern_example",
                    "severity": "medium",
                    "confidence": 80,
                    "cwe": "CWE-200",
                    "tags": ["custom", "project"],
                    "where": ["response.body"],
                    "enabled": True
                }
            ]
        }
        
        patterns_file = project_pattern_dir / "custom_patterns.json"
        with open(patterns_file, 'w') as f:
            json.dump(default_patterns, f, indent=2)
        
        return True
    
    def get_project_patterns(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all patterns for a specific project."""
        project_pattern_dir = self.projects_dir / project_id
        if not project_pattern_dir.exists():
            return []
        
        patterns = []
        for pattern_file in project_pattern_dir.glob("*.json"):
            try:
                with open(pattern_file, 'r') as f:
                    data = json.load(f)
                    if "rules" in data:
                        for rule in data["rules"]:
                            rule["project_id"] = project_id
                            rule["pack_name"] = data.get("name", "Project Patterns")
                            patterns.append(rule)
            except Exception as e:
                print(f"Warning: Could not load pattern file {pattern_file}: {e}")
        
        return patterns
    
    def update_community_packs(self, force: bool = False) -> Dict[str, Any]:
        """Update community pattern packs from remote sources."""
        results = {
            "updated": [],
            "failed": [],
            "skipped": []
        }
        
        for pack_id, pack_info in self.community_sources.items():
            if not pack_info.get("enabled", True):
                results["skipped"].append(pack_id)
                continue
            
            # Check if update is needed
            if not force and pack_info.get("last_updated"):
                last_update = datetime.fromisoformat(pack_info["last_updated"])
                if datetime.now() - last_update < timedelta(hours=24):
                    results["skipped"].append(pack_id)
                    continue
            
            try:
                success = self._download_community_pack(pack_id, pack_info)
                if success:
                    results["updated"].append(pack_id)
                    self.community_sources[pack_id]["last_updated"] = datetime.now().isoformat()
                else:
                    results["failed"].append(pack_id)
            except Exception as e:
                print(f"Error updating {pack_id}: {e}")
                results["failed"].append(pack_id)
        
        self._save_community_metadata()
        return results
    
    def _download_community_pack(self, pack_id: str, pack_info: Dict[str, Any]) -> bool:
        """Download and extract a community pattern pack."""
        try:
            # Download the pack
            response = requests.get(pack_info["url"], timeout=30)
            response.raise_for_status()
            
            # Save to temporary file
            temp_file = self.temp_dir / f"{pack_id}.zip"
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            # Extract to community directory
            pack_dir = self.community_dir / pack_id
            if pack_dir.exists():
                shutil.rmtree(pack_dir)
            pack_dir.mkdir()
            
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(pack_dir)
            
            # Convert to our format if needed
            self._convert_community_pack(pack_id, pack_dir)
            
            # Clean up
            temp_file.unlink()
            
            return True
            
        except Exception as e:
            print(f"Error downloading {pack_id}: {e}")
            return False
    
    def _convert_community_pack(self, pack_id: str, pack_dir: Path):
        """Convert community pack to our JSON format."""
        if pack_id == "owasp-crs":
            self._convert_owasp_crs(pack_dir)
        elif pack_id == "nuclei-templates":
            self._convert_nuclei_templates(pack_dir)
        elif pack_id == "security-patterns":
            self._convert_security_patterns(pack_dir)
    
    def _convert_owasp_crs(self, pack_dir: Path):
        """Convert OWASP CRS rules to our format."""
        # This would convert ModSecurity rules to our JSON format
        # For now, create a placeholder
        converted_rules = {
            "name": "OWASP Core Rule Set",
            "version": "4.0",
            "description": "Converted OWASP ModSecurity Core Rule Set patterns",
            "rules": [
                {
                    "id": "owasp_crs_sql_injection",
                    "title": "SQL Injection Attack",
                    "regex": r"(?i)(union\s+select|insert\s+into|delete\s+from|drop\s+table)",
                    "severity": "high",
                    "confidence": 90,
                    "cwe": "CWE-89",
                    "tags": ["injection", "sql", "owasp"],
                    "where": ["request.body", "request.query"],
                    "enabled": True
                },
                {
                    "id": "owasp_crs_xss",
                    "title": "Cross-Site Scripting Attack",
                    "regex": r"(?i)(<script[^>]*>|javascript:|on\w+\s*=)",
                    "severity": "high",
                    "confidence": 85,
                    "cwe": "CWE-79",
                    "tags": ["xss", "injection", "owasp"],
                    "where": ["request.body", "request.query"],
                    "enabled": True
                }
            ]
        }
        
        output_file = pack_dir / "converted_patterns.json"
        with open(output_file, 'w') as f:
            json.dump(converted_rules, f, indent=2)
    
    def _convert_nuclei_templates(self, pack_dir: Path):
        """Convert Nuclei templates to our format."""
        # This would convert YAML Nuclei templates to our JSON format
        # For now, create a placeholder
        converted_rules = {
            "name": "Nuclei Templates",
            "version": "latest",
            "description": "Converted ProjectDiscovery Nuclei security templates",
            "rules": [
                {
                    "id": "nuclei_http_headers",
                    "title": "Security Headers Missing",
                    "regex": r"(?i)(x-frame-options|x-content-type-options|strict-transport-security)",
                    "severity": "medium",
                    "confidence": 80,
                    "cwe": "CWE-693",
                    "tags": ["headers", "security", "nuclei"],
                    "where": ["response.headers"],
                    "enabled": True
                }
            ]
        }
        
        output_file = pack_dir / "converted_patterns.json"
        with open(output_file, 'w') as f:
            json.dump(converted_rules, f, indent=2)
    
    def _convert_security_patterns(self, pack_dir: Path):
        """Convert OWASP security patterns to our format."""
        # This would convert conceptual security patterns to detection rules
        # For now, create a placeholder
        converted_rules = {
            "name": "Security Patterns",
            "version": "latest",
            "description": "Converted OWASP security patterns",
            "rules": []
        }
        
        output_file = pack_dir / "converted_patterns.json"
        with open(output_file, 'w') as f:
            json.dump(converted_rules, f, indent=2)
    
    def get_all_patterns(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all available patterns, optionally filtered by project."""
        all_patterns = []
        
        # Add built-in patterns
        builtin_dir = self.patterns_dir.parent / "patterns"
        if builtin_dir.exists():
            for pattern_file in builtin_dir.glob("*.json"):
                try:
                    with open(pattern_file, 'r', encoding='utf-8') as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError as e:
                            print(f"Warning: Could not load built-in pattern {pattern_file}: line {e.lineno} col {e.colno} — {e.msg}")
                            continue
                        if "rules" in data:
                            for rule in data["rules"]:
                                rule["pack_name"] = data.get("name", "Built-in")
                                rule["pack_type"] = "builtin"
                                all_patterns.append(rule)
                except Exception as e:
                    print(f"Warning: Could not open built-in pattern {pattern_file}: {e}")
        
        # Add community patterns
        for pack_dir in self.community_dir.iterdir():
            if pack_dir.is_dir():
                for pattern_file in pack_dir.glob("*.json"):
                    try:
                        with open(pattern_file, 'r', encoding='utf-8') as f:
                            try:
                                data = json.load(f)
                            except json.JSONDecodeError as e:
                                print(f"Warning: Could not load community pattern {pattern_file}: line {e.lineno} col {e.colno} — {e.msg}")
                                continue
                            if "rules" in data:
                                for rule in data["rules"]:
                                    rule["pack_name"] = data.get("name", "Community")
                                    rule["pack_type"] = "community"
                                    all_patterns.append(rule)
                    except Exception as e:
                        print(f"Warning: Could not open community pattern {pattern_file}: {e}")
        
        # Add project-specific patterns if specified
        if project_id:
            project_patterns = self.get_project_patterns(project_id)
            for rule in project_patterns:
                rule["pack_type"] = "project"
                all_patterns.append(rule)
        
        return all_patterns
    
    def validate_pattern(self, pattern: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Enhanced pattern validation with comprehensive checks."""
        errors = []
        warnings = []
        
        # Required fields validation
        required_fields = ["id", "title", "regex"]
        for field in required_fields:
            if not pattern.get(field):
                errors.append(f"Missing required field: {field}")
        
        # ID validation
        pattern_id = pattern.get("id")
        if pattern_id:
            if not isinstance(pattern_id, str):
                errors.append("Pattern ID must be a string")
            elif len(pattern_id.strip()) == 0:
                errors.append("Pattern ID cannot be empty")
            elif not pattern_id.replace("-", "").replace("_", "").isalnum():
                warnings.append("Pattern ID should be alphanumeric with hyphens/underscores only")
        
        # Title validation
        title = pattern.get("title")
        if title:
            if not isinstance(title, str):
                errors.append("Title must be a string")
            elif len(title.strip()) < 3:
                warnings.append("Title should be at least 3 characters")
            elif len(title) > 200:
                warnings.append("Title should be less than 200 characters")
        
        # Regex validation with detailed error reporting
        regex = pattern.get("regex")
        if regex:
            if not isinstance(regex, str):
                errors.append("Regex must be a string")
            else:
                try:
                    import re
                    compiled_regex = re.compile(regex, re.IGNORECASE)
                    
                    # Check for common regex issues
                    if regex.count("(") != regex.count(")"):
                        warnings.append("Unmatched parentheses in regex")
                    
                    if ".*" in regex and len(regex) < 10:
                        warnings.append("Very broad regex pattern may cause false positives")
                    
                    if regex.startswith(".*") and regex.endswith(".*"):
                        warnings.append("Regex starts and ends with .* - consider anchoring")
                    
                    # Check for performance issues
                    if len(regex) > 500:
                        warnings.append("Very long regex may impact performance")
                        
                except re.error as e:
                    errors.append(f"Invalid regex: {e}")
        
        # CWE validation with format normalization
        cwe = pattern.get("cwe")
        if cwe:
            if isinstance(cwe, str):
                # Normalize CWE format
                cwe_normalized = cwe.upper().strip()
                if not cwe_normalized.startswith("CWE-"):
                    if cwe_normalized.isdigit():
                        cwe_normalized = f"CWE-{cwe_normalized}"
                    else:
                        errors.append("CWE must be in format CWE-XXX or just the number")
                
                # Validate CWE number
                cwe_num = cwe_normalized.replace("CWE-", "")
                if not cwe_num.isdigit():
                    errors.append("CWE number must be numeric")
                else:
                    cwe_int = int(cwe_num)
                    if cwe_int < 1 or cwe_int > 9999:
                        warnings.append("CWE number should be between 1 and 9999")
            else:
                errors.append("CWE must be a string")
        
        # CVSS validation
        cvss = pattern.get("cvss")
        if cvss is not None:
            try:
                cvss_val = float(cvss)
                if not 0.0 <= cvss_val <= 10.0:
                    errors.append("CVSS score must be between 0.0 and 10.0")
            except (ValueError, TypeError):
                errors.append("CVSS must be a number")
        
        # Confidence validation with enhanced checks
        confidence = pattern.get("confidence")
        if confidence is not None:
            try:
                conf_val = int(confidence)
                if not 0 <= conf_val <= 100:
                    errors.append("Confidence must be between 0 and 100")
                elif conf_val < 30:
                    warnings.append("Low confidence patterns may generate false positives")
                elif conf_val > 90:
                    warnings.append("Very high confidence patterns may miss variants")
            except (ValueError, TypeError):
                errors.append("Confidence must be a number")
        
        # Severity validation
        severity = pattern.get("severity")
        valid_severities = ["info", "low", "medium", "high", "critical"]
        if severity:
            if severity not in valid_severities:
                errors.append(f"Severity must be one of: {', '.join(valid_severities)}")
        
        # Where field validation
        where = pattern.get("where")
        if where:
            valid_where_values = [
                "request.body", "request.headers", "request.url", "request.params",
                "response.body", "response.headers", "response.status"
            ]
            if isinstance(where, str):
                where_list = [where]
            elif isinstance(where, list):
                where_list = where
            else:
                errors.append("Where field must be a string or list of strings")
                where_list = []
            
            for w in where_list:
                if w not in valid_where_values:
                    warnings.append(f"Unknown 'where' value: {w}. Valid values: {', '.join(valid_where_values)}")
        
        # Tags validation
        tags = pattern.get("tags")
        if tags:
            if not isinstance(tags, list):
                errors.append("Tags must be a list")
            else:
                for tag in tags:
                    if not isinstance(tag, str):
                        errors.append("All tags must be strings")
                    elif len(tag.strip()) == 0:
                        warnings.append("Empty tags should be removed")
        
        # Pack metadata validation
        pack_name = pattern.get("pack_name")
        if pack_name and not isinstance(pack_name, str):
            errors.append("Pack name must be a string")
        
        pack_version = pattern.get("pack_version")
        if pack_version and not isinstance(pack_version, str):
            errors.append("Pack version must be a string")
        
        # Return validation results
        all_issues = errors + warnings
        return len(errors) == 0, all_issues
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pattern statistics."""
        all_patterns = self.get_all_patterns()
        
        stats = {
            "total_patterns": len(all_patterns),
            "by_pack_type": {},
            "by_severity": {},
            "by_cwe": {},
            "by_confidence": {},
            "enabled_count": 0,
            "disabled_count": 0
        }
        
        for pattern in all_patterns:
            # Pack type
            pack_type = pattern.get("pack_type", "unknown")
            stats["by_pack_type"][pack_type] = stats["by_pack_type"].get(pack_type, 0) + 1
            
            # Severity
            severity = pattern.get("severity", "info")
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
            
            # CWE
            cwe = pattern.get("cwe")
            if cwe:
                stats["by_cwe"][cwe] = stats["by_cwe"].get(cwe, 0) + 1
            
            # Confidence ranges
            confidence = pattern.get("confidence", 50)
            if confidence >= 90:
                conf_range = "90-100"
            elif confidence >= 70:
                conf_range = "70-89"
            elif confidence >= 50:
                conf_range = "50-69"
            else:
                conf_range = "0-49"
            stats["by_confidence"][conf_range] = stats["by_confidence"].get(conf_range, 0) + 1
            
            # Enabled/disabled
            if pattern.get("enabled", True):
                stats["enabled_count"] += 1
            else:
                stats["disabled_count"] += 1
        
        return stats
