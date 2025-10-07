#!/usr/bin/env python3
"""
Nuclei Integration - Convert and integrate Nuclei templates with the pattern engine.
"""
import os
import yaml
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

class NucleiIntegration:
    """
    Integration with ProjectDiscovery Nuclei templates.
    Converts YAML Nuclei templates to our JSON pattern format.
    """
    
    def __init__(self, nuclei_templates_dir: str):
        self.templates_dir = Path(nuclei_templates_dir)
        self.converted_patterns = []
    
    def convert_templates(self, output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """Convert all Nuclei templates to our pattern format."""
        converted = []
        
        # Walk through all YAML files in the templates directory
        for yaml_file in self.templates_dir.rglob("*.yaml"):
            try:
                template_patterns = self._convert_template_file(yaml_file)
                converted.extend(template_patterns)
            except Exception as e:
                print(f"Warning: Could not convert {yaml_file}: {e}")
        
        self.converted_patterns = converted
        
        if output_file:
            self._save_converted_patterns(output_file)
        
        return converted
    
    def _convert_template_file(self, yaml_file: Path) -> List[Dict[str, Any]]:
        """Convert a single Nuclei template file."""
        patterns = []
        
        with open(yaml_file, 'r', encoding='utf-8') as f:
            try:
                templates = yaml.safe_load_all(f)
                for template in templates:
                    if not template or not isinstance(template, dict):
                        continue
                    
                    pattern = self._convert_single_template(template, yaml_file)
                    if pattern:
                        patterns.append(pattern)
            except yaml.YAMLError as e:
                print(f"YAML parsing error in {yaml_file}: {e}")
        
        return patterns
    
    def _convert_single_template(self, template: Dict[str, Any], source_file: Path) -> Optional[Dict[str, Any]]:
        """Convert a single Nuclei template to our pattern format."""
        try:
            # Extract basic information
            info = template.get("info", {})
            name = info.get("name", "Unknown")
            severity = self._map_nuclei_severity(info.get("severity", "info"))
            tags = info.get("tags", [])
            description = info.get("description", "")
            
            # Extract matchers
            matchers = template.get("matchers", [])
            if not matchers:
                return None
            
            # Convert to our pattern format
            pattern = {
                "id": f"nuclei_{self._sanitize_id(name)}",
                "title": name,
                "description": description,
                "severity": severity,
                "confidence": self._calculate_confidence(template),
                "cwe": self._extract_cwe(tags, description),
                "tags": self._extract_tags(tags),
                "where": self._determine_where_clauses(template),
                "regex": self._extract_regex_patterns(matchers),
                "enabled": True,
                "pack_name": "Nuclei Templates",
                "pack_type": "nuclei",
                "source_file": str(source_file.relative_to(self.templates_dir))
            }
            
            return pattern
            
        except Exception as e:
            print(f"Error converting template {source_file}: {e}")
            return None
    
    def _map_nuclei_severity(self, nuclei_severity: str) -> str:
        """Map Nuclei severity to our severity levels."""
        mapping = {
            "critical": "critical",
            "high": "high", 
            "medium": "medium",
            "low": "low",
            "info": "info"
        }
        return mapping.get(nuclei_severity.lower(), "info")
    
    def _sanitize_id(self, name: str) -> str:
        """Convert template name to a valid ID."""
        # Remove special characters and convert to lowercase
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name.lower())
        # Remove multiple underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading/trailing underscores
        return sanitized.strip('_')
    
    def _calculate_confidence(self, template: Dict[str, Any]) -> int:
        """Calculate confidence based on template complexity and matchers."""
        base_confidence = 60
        
        # Increase confidence for multiple matchers
        matchers = template.get("matchers", [])
        if len(matchers) > 1:
            base_confidence += 10
        
        # Increase confidence for specific matchers
        for matcher in matchers:
            if matcher.get("type") == "word":
                words = matcher.get("words", [])
                if len(words) > 1:
                    base_confidence += 5
            elif matcher.get("type") == "regex":
                base_confidence += 10
        
        # Increase confidence for status code matchers
        status_codes = template.get("matchers-status", [])
        if status_codes:
            base_confidence += 5
        
        return min(base_confidence, 95)
    
    def _extract_cwe(self, tags: List[str], description: str) -> Optional[str]:
        """Extract CWE from tags or description."""
        # Look for CWE in tags
        for tag in tags:
            if tag.startswith("cwe-"):
                return tag.upper()
        
        # Look for CWE in description
        cwe_match = re.search(r'CWE-(\d+)', description, re.IGNORECASE)
        if cwe_match:
            return f"CWE-{cwe_match.group(1)}"
        
        return None
    
    def _extract_tags(self, nuclei_tags: List[str]) -> List[str]:
        """Extract and clean tags from Nuclei template."""
        cleaned_tags = []
        
        for tag in nuclei_tags:
            # Skip CWE tags (handled separately)
            if tag.startswith("cwe-"):
                continue
            
            # Clean and add tag
            cleaned_tag = tag.lower().replace(' ', '-').replace('_', '-')
            cleaned_tags.append(cleaned_tag)
        
        return cleaned_tags
    
    def _determine_where_clauses(self, template: Dict[str, Any]) -> List[str]:
        """Determine where clauses based on template type and matchers."""
        where_clauses = []
        
        # Check if it's an HTTP template
        if "http" in template:
            where_clauses.append("response.body")
            where_clauses.append("response.headers")
        
        # Check matchers for specific locations
        matchers = template.get("matchers", [])
        for matcher in matchers:
            part = matcher.get("part", "body")
            if part == "header":
                if "response.headers" not in where_clauses:
                    where_clauses.append("response.headers")
            elif part == "body":
                if "response.body" not in where_clauses:
                    where_clauses.append("response.body")
            elif part == "all":
                where_clauses.extend(["response.body", "response.headers"])
        
        return where_clauses if where_clauses else ["response.body"]
    
    def _extract_regex_patterns(self, matchers: List[Dict[str, Any]]) -> str:
        """Extract regex patterns from Nuclei matchers."""
        patterns = []
        
        for matcher in matchers:
            matcher_type = matcher.get("type", "")
            
            if matcher_type == "regex":
                regex = matcher.get("regex", "")
                if regex:
                    patterns.append(regex)
            elif matcher_type == "word":
                words = matcher.get("words", [])
                if words:
                    # Convert word matchers to regex
                    word_patterns = []
                    for word in words:
                        # Escape special regex characters
                        escaped_word = re.escape(word)
                        word_patterns.append(escaped_word)
                    
                    if word_patterns:
                        # Join with alternation
                        patterns.append(f"({'|'.join(word_patterns)})")
            elif matcher_type == "status":
                # Status code matchers are handled separately
                continue
        
        if not patterns:
            return r".*"  # Default catch-all pattern
        
        # Combine patterns with alternation
        if len(patterns) == 1:
            return patterns[0]
        else:
            return f"({'|'.join(patterns)})"
    
    def _save_converted_patterns(self, output_file: str):
        """Save converted patterns to JSON file."""
        output_data = {
            "name": "Nuclei Templates",
            "version": "latest",
            "description": "Converted ProjectDiscovery Nuclei security templates",
            "rules": self.converted_patterns
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
    
    def get_template_categories(self) -> Dict[str, List[str]]:
        """Get available template categories and their files."""
        categories = {}
        
        for yaml_file in self.templates_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    templates = yaml.safe_load_all(f)
                    for template in templates:
                        if not template or not isinstance(template, dict):
                            continue
                        
                        info = template.get("info", {})
                        tags = info.get("tags", [])
                        
                        # Categorize by first tag
                        if tags:
                            category = tags[0].lower()
                            if category not in categories:
                                categories[category] = []
                            
                            relative_path = str(yaml_file.relative_to(self.templates_dir))
                            categories[category].append(relative_path)
            except Exception as e:
                print(f"Warning: Could not process {yaml_file}: {e}")
        
        return categories
    
    def validate_template(self, template: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate a Nuclei template."""
        errors = []
        
        # Check required fields
        if "info" not in template:
            errors.append("Missing required 'info' section")
        else:
            info = template["info"]
            if "name" not in info:
                errors.append("Missing required 'name' field in info")
        
        # Check for matchers
        if "matchers" not in template and "requests" not in template:
            errors.append("Template must have either 'matchers' or 'requests' section")
        
        return len(errors) == 0, errors
