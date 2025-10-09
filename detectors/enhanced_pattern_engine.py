#!/usr/bin/env python3
"""
Enhanced Pattern Engine - Advanced pattern detection with external integrations.
"""
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .modsecurity_integration import ModSecurityIntegration
from .nuclei_integration import NucleiIntegration
from .pattern_engine import PatternEngine
from .pattern_manager import PatternManager


class EnhancedPatternEngine(PatternEngine):
    """
    Enhanced pattern engine with:
    - Per-project pattern directories
    - Community pattern pack support
    - Nuclei template integration
    - ModSecurity CRS integration
    - Advanced filtering and statistics
    - Pattern management UI support
    """
    
    def __init__(self, base_dir: str, project_id: Optional[str] = None):
        super().__init__(os.path.join(base_dir, "patterns"))
        
        self.base_dir = Path(base_dir)
        self.project_id = project_id
        self.pattern_manager = PatternManager(base_dir)
        
        # Initialize external integrations
        self.nuclei_integration = None
        self.modsecurity_integration = None
        
        # Load all available patterns
        self._load_all_patterns()
    
    def _load_all_patterns(self):
        """Load patterns from all sources with deduplication."""
        # Clear existing patterns to prevent memory leaks
        self._compiled = []
        self.rule_sets = []
        
        # Load built-in patterns (from parent class)
        super().reload()
        
        # Track loaded pattern IDs to prevent duplicates
        loaded_ids = set()
        for pattern in self._compiled:
            if pattern.get("id"):
                loaded_ids.add(pattern["id"])
        
        # Load project-specific patterns
        if self.project_id:
            project_patterns = self.pattern_manager.get_project_patterns(self.project_id)
            self._add_patterns_to_engine(project_patterns, "project", loaded_ids)
        
        # Load community patterns
        community_patterns = self.pattern_manager.get_all_patterns()
        self._add_patterns_to_engine(community_patterns, "community", loaded_ids)
    
    def _add_patterns_to_engine(self, patterns: List[Dict[str, Any]], source_type: str, loaded_ids: set = None):
        """Add patterns from external sources to the engine with deduplication."""
        if loaded_ids is None:
            loaded_ids = set()
            
        for pattern in patterns:
            if not pattern.get("enabled", True):
                continue
            
            # Skip if pattern ID already loaded
            pattern_id = pattern.get("id")
            if pattern_id and pattern_id in loaded_ids:
                continue
            
            # Convert to our internal format
            regex = pattern.get("regex", "")
            if not regex:
                continue
            
            compiled_regex = self._compile(regex)
            if not compiled_regex:
                continue
            
            where = pattern.get("where", ["response.body"])
            if isinstance(where, str):
                where = [where]
            
            item = {
                "id": pattern.get("id", ""),
                "title": pattern.get("title", "Pattern match"),
                "where": list(where),
                "regex": regex,
                "re": compiled_regex,
                "cwe": pattern.get("cwe"),
                "cvss": pattern.get("cvss"),
                "severity": pattern.get("severity"),
                "confidence": int(pattern.get("confidence", 60)),
                "tags": pattern.get("tags", []),
                "enabled": True,
                "pack_name": pattern.get("pack_name", "Unknown"),
                "pack_type": source_type,
                "pack_version": pattern.get("pack_version"),
                "pack_path": pattern.get("pack_path", ""),
            }
            
            self._compiled.append(item)
            if pattern_id:
                loaded_ids.add(pattern_id)
    
    def setup_nuclei_integration(self, nuclei_templates_dir: str):
        """Setup Nuclei templates integration."""
        self.nuclei_integration = NucleiIntegration(nuclei_templates_dir)
    
    def setup_modsecurity_integration(self, crs_dir: str):
        """Setup ModSecurity CRS integration."""
        self.modsecurity_integration = ModSecurityIntegration(crs_dir)
    
    def convert_nuclei_templates(self, output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """Convert Nuclei templates to our pattern format."""
        if not self.nuclei_integration:
            raise ValueError("Nuclei integration not setup. Call setup_nuclei_integration() first.")
        
        return self.nuclei_integration.convert_templates(output_file)
    
    def convert_modsecurity_crs(self, output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """Convert ModSecurity CRS rules to our pattern format."""
        if not self.modsecurity_integration:
            raise ValueError("ModSecurity integration not setup. Call setup_modsecurity_integration() first.")
        
        return self.modsecurity_integration.convert_crs_rules(output_file)
    
    def update_community_packs(self, force: bool = False) -> Dict[str, Any]:
        """Update community pattern packs."""
        return self.pattern_manager.update_community_packs(force)
    
    def create_project_patterns(self, project_id: str) -> bool:
        """Create pattern directory for a project."""
        return self.pattern_manager.create_project_patterns(project_id)
    
    def get_patterns_by_filter(self, 
                              severity: Optional[str] = None,
                              cwe: Optional[str] = None,
                              confidence_min: Optional[int] = None,
                              confidence_max: Optional[int] = None,
                              tags: Optional[List[str]] = None,
                              pack_type: Optional[str] = None,
                              pack_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get patterns filtered by various criteria."""
        filtered_patterns = []
        
        for pattern in self._compiled:
            # Severity filter
            if severity and pattern.get("severity") != severity:
                continue
            
            # CWE filter
            if cwe and pattern.get("cwe") != cwe:
                continue
            
            # Confidence range filter
            pattern_confidence = pattern.get("confidence", 50)
            if confidence_min is not None and pattern_confidence < confidence_min:
                continue
            if confidence_max is not None and pattern_confidence > confidence_max:
                continue
            
            # Tags filter
            if tags:
                pattern_tags = pattern.get("tags", [])
                if not any(tag in pattern_tags for tag in tags):
                    continue
            
            # Pack type filter
            if pack_type and pattern.get("pack_type") != pack_type:
                continue
            
            # Pack name filter
            if pack_name and pack_name.lower() not in pattern.get("pack_name", "").lower():
                continue
            
            filtered_patterns.append(pattern)
        
        return filtered_patterns
    
    def get_advanced_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pattern statistics."""
        stats = super().get_pattern_stats()
        
        # Add enhanced statistics
        stats.update({
            "by_pack_type": {},
            "by_confidence_range": {},
            "by_tags": {},
            "project_patterns": 0,
            "community_patterns": 0,
            "builtin_patterns": 0
        })
        
        for pattern in self._compiled:
            # Pack type breakdown
            pack_type = pattern.get("pack_type", "unknown")
            stats["by_pack_type"][pack_type] = stats["by_pack_type"].get(pack_type, 0) + 1
            
            # Confidence range breakdown
            confidence = pattern.get("confidence", 50)
            if confidence >= 90:
                conf_range = "90-100"
            elif confidence >= 70:
                conf_range = "70-89"
            elif confidence >= 50:
                conf_range = "50-69"
            else:
                conf_range = "0-49"
            stats["by_confidence_range"][conf_range] = stats["by_confidence_range"].get(conf_range, 0) + 1
            
            # Tags breakdown
            tags = pattern.get("tags", [])
            for tag in tags:
                stats["by_tags"][tag] = stats["by_tags"].get(tag, 0) + 1
            
            # Source breakdown
            if pack_type == "project":
                stats["project_patterns"] += 1
            elif pack_type == "community":
                stats["community_patterns"] += 1
            else:
                stats["builtin_patterns"] += 1
        
        return stats
    
    def test_pattern_against_text(self, pattern_id: str, text: str) -> Dict[str, Any]:
        """Test a specific pattern against text and return detailed results."""
        pattern = self.get_pattern_by_id(pattern_id)
        if not pattern:
            return {"error": "Pattern not found"}
        
        matches = []
        for where in pattern["where"]:
            if where == "response.body":
                test_text = text
            elif where == "response.headers":
                test_text = text  # Simplified for testing
            else:
                test_text = text
            
            match = pattern["re"].search(test_text)
            if match:
                matches.append({
                    "where": where,
                    "match": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "groups": match.groups()
                })
        
        return {
            "pattern_id": pattern_id,
            "pattern_title": pattern["title"],
            "matches": matches,
            "total_matches": len(matches)
        }
    
    def export_patterns(self, output_file: str, format: str = "json") -> bool:
        """Export patterns to various formats."""
        try:
            if format == "json":
                self._export_json(output_file)
            elif format == "csv":
                self._export_csv(output_file)
            elif format == "yaml":
                self._export_yaml(output_file)
            else:
                raise ValueError(f"Unsupported format: {format}")
            return True
        except Exception as e:
            print(f"Error exporting patterns: {e}")
            return False
    
    def _export_json(self, output_file: str):
        """Export patterns to JSON format."""
        export_data = {
            "export_info": {
                "timestamp": time.time(),
                "total_patterns": len(self._compiled),
                "project_id": self.project_id
            },
            "patterns": []
        }
        
        for pattern in self._compiled:
            export_data["patterns"].append({
                "id": pattern["id"],
                "title": pattern["title"],
                "regex": pattern["regex"],
                "severity": pattern.get("severity"),
                "confidence": pattern["confidence"],
                "cwe": pattern.get("cwe"),
                "cvss": pattern.get("cvss"),
                "tags": pattern.get("tags", []),
                "where": pattern["where"],
                "pack_name": pattern.get("pack_name"),
                "pack_type": pattern.get("pack_type"),
                "enabled": pattern.get("enabled", True)
            })
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def _export_csv(self, output_file: str):
        """Export patterns to CSV format."""
        import csv
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Title", "Regex", "Severity", "Confidence", "CWE", "CVSS",
                "Tags", "Where", "Pack Name", "Pack Type", "Enabled"
            ])
            
            for pattern in self._compiled:
                writer.writerow([
                    pattern["id"],
                    pattern["title"],
                    pattern["regex"],
                    pattern.get("severity", ""),
                    pattern["confidence"],
                    pattern.get("cwe", ""),
                    pattern.get("cvss", ""),
                    ",".join(pattern.get("tags", [])),
                    ",".join(pattern["where"]),
                    pattern.get("pack_name", ""),
                    pattern.get("pack_type", ""),
                    pattern.get("enabled", True)
                ])
    
    def _export_yaml(self, output_file: str):
        """Export patterns to YAML format."""
        import yaml
        
        export_data = {
            "export_info": {
                "timestamp": time.time(),
                "total_patterns": len(self._compiled),
                "project_id": self.project_id
            },
            "patterns": []
        }
        
        for pattern in self._compiled:
            export_data["patterns"].append({
                "id": pattern["id"],
                "title": pattern["title"],
                "regex": pattern["regex"],
                "severity": pattern.get("severity"),
                "confidence": pattern["confidence"],
                "cwe": pattern.get("cwe"),
                "cvss": pattern.get("cvss"),
                "tags": pattern.get("tags", []),
                "where": pattern["where"],
                "pack_name": pattern.get("pack_name"),
                "pack_type": pattern.get("pack_type"),
                "enabled": pattern.get("enabled", True)
            })
        
        with open(output_file, 'w') as f:
            yaml.dump(export_data, f, default_flow_style=False)
    
    def import_patterns(self, import_file: str, format: str = "json") -> Tuple[bool, List[str]]:
        """Import patterns from various formats."""
        errors = []
        
        try:
            if format == "json":
                patterns = self._import_json(import_file)
            elif format == "csv":
                patterns = self._import_csv(import_file)
            elif format == "yaml":
                patterns = self._import_yaml(import_file)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            # Validate and add patterns
            for pattern in patterns:
                is_valid, pattern_errors = self.pattern_manager.validate_pattern(pattern)
                if is_valid:
                    # Add to engine
                    self._add_patterns_to_engine([pattern], "imported")
                else:
                    errors.extend(pattern_errors)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(str(e))
            return False, errors
    
    def _import_json(self, import_file: str) -> List[Dict[str, Any]]:
        """Import patterns from JSON format."""
        with open(import_file, 'r') as f:
            data = json.load(f)
        
        if "patterns" in data:
            return data["patterns"]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("Invalid JSON format")
    
    def _import_csv(self, import_file: str) -> List[Dict[str, Any]]:
        """Import patterns from CSV format."""
        import csv
        
        patterns = []
        with open(import_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pattern = {
                    "id": row.get("ID", ""),
                    "title": row.get("Title", ""),
                    "regex": row.get("Regex", ""),
                    "severity": row.get("Severity"),
                    "confidence": int(row.get("Confidence", 50)),
                    "cwe": row.get("CWE"),
                    "cvss": row.get("CVSS"),
                    "tags": row.get("Tags", "").split(",") if row.get("Tags") else [],
                    "where": row.get("Where", "").split(",") if row.get("Where") else ["response.body"],
                    "pack_name": row.get("Pack Name", "Imported"),
                    "pack_type": "imported",
                    "enabled": row.get("Enabled", "True").lower() == "true"
                }
                patterns.append(pattern)
        
        return patterns
    
    def _import_yaml(self, import_file: str) -> List[Dict[str, Any]]:
        """Import patterns from YAML format."""
        import yaml
        
        with open(import_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if "patterns" in data:
            return data["patterns"]
        elif isinstance(data, list):
            return data
        else:
            raise ValueError("Invalid YAML format")
