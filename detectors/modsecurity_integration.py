#!/usr/bin/env python3
"""
ModSecurity CRS Integration - Convert OWASP ModSecurity Core Rule Set to pattern engine format.
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class ModSecurityIntegration:
    """
    Integration with OWASP ModSecurity Core Rule Set.
    Converts ModSecurity rules to our JSON pattern format.
    """
    
    def __init__(self, crs_dir: str):
        self.crs_dir = Path(crs_dir)
        self.converted_patterns = []
    
    def convert_crs_rules(self, output_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """Convert all ModSecurity CRS rules to our pattern format."""
        converted = []
        
        # Walk through all .conf files in the CRS directory
        for conf_file in self.crs_dir.rglob("*.conf"):
            try:
                rule_patterns = self._convert_conf_file(conf_file)
                converted.extend(rule_patterns)
            except Exception as e:
                print(f"Warning: Could not convert {conf_file}: {e}")
        
        self.converted_patterns = converted
        
        if output_file:
            self._save_converted_patterns(output_file)
        
        return converted
    
    def _convert_conf_file(self, conf_file: Path) -> List[Dict[str, Any]]:
        """Convert a single ModSecurity configuration file."""
        patterns = []
        
        with open(conf_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Split into individual rules
            rules = self._split_modsecurity_rules(content)
            
            for rule in rules:
                pattern = self._convert_single_rule(rule, conf_file)
                if pattern:
                    patterns.append(pattern)
        
        return patterns
    
    def _split_modsecurity_rules(self, content: str) -> List[str]:
        """Split ModSecurity content into individual rules."""
        # Remove comments and empty lines
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                lines.append(line)
        
        # Group lines into rules (SecRule directives)
        rules = []
        current_rule = []
        
        for line in lines:
            if line.startswith('SecRule'):
                if current_rule:
                    rules.append('\n'.join(current_rule))
                current_rule = [line]
            elif current_rule:
                current_rule.append(line)
        
        if current_rule:
            rules.append('\n'.join(current_rule))
        
        return rules
    
    def _convert_single_rule(self, rule_text: str, source_file: Path) -> Optional[Dict[str, Any]]:
        """Convert a single ModSecurity rule to our pattern format."""
        try:
            # Parse the SecRule directive
            parsed = self._parse_secrule(rule_text)
            if not parsed:
                return None
            
            # Extract information
            rule_id = parsed.get('id', 'unknown')
            title = self._generate_title(parsed, source_file)
            severity = self._map_crs_severity(parsed.get('severity', 'info'))
            cwe = self._extract_cwe_from_rule(rule_text)
            tags = self._extract_tags_from_rule(rule_text)
            
            # Convert ModSecurity regex to standard regex
            regex_pattern = self._convert_modsecurity_regex(parsed.get('pattern', ''))
            if not regex_pattern:
                return None
            
            pattern = {
                "id": f"crs_{rule_id}",
                "title": title,
                "description": self._generate_description(parsed, source_file),
                "severity": severity,
                "confidence": self._calculate_confidence(parsed),
                "cwe": cwe,
                "tags": tags,
                "where": self._determine_where_clauses(parsed),
                "regex": regex_pattern,
                "enabled": True,
                "pack_name": "OWASP CRS",
                "pack_type": "modsecurity",
                "source_file": str(source_file.relative_to(self.crs_dir))
            }
            
            return pattern
            
        except Exception as e:
            print(f"Error converting rule from {source_file}: {e}")
            return None
    
    def _parse_secrule(self, rule_text: str) -> Optional[Dict[str, Any]]:
        """Parse a ModSecurity SecRule directive."""
        # Basic regex to match SecRule pattern
        pattern = r'SecRule\s+([^\s]+)\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"'
        match = re.search(pattern, rule_text)
        
        if not match:
            return None
        
        return {
            'variable': match.group(1),
            'pattern': match.group(2),
            'operator': match.group(3),
            'action': match.group(4)
        }
    
    def _generate_title(self, parsed: Dict[str, Any], source_file: Path) -> str:
        """Generate a human-readable title for the rule."""
        # Extract rule ID from action
        action = parsed.get('action', '')
        id_match = re.search(r'id:(\d+)', action)
        if id_match:
            rule_id = id_match.group(1)
        else:
            rule_id = "unknown"
        
        # Generate title based on file and rule ID
        file_name = source_file.stem
        if 'sql' in file_name.lower():
            return f"SQL Injection Detection (Rule {rule_id})"
        elif 'xss' in file_name.lower():
            return f"Cross-Site Scripting Detection (Rule {rule_id})"
        elif 'rce' in file_name.lower():
            return f"Remote Code Execution Detection (Rule {rule_id})"
        elif 'lfi' in file_name.lower():
            return f"Local File Inclusion Detection (Rule {rule_id})"
        elif 'rfi' in file_name.lower():
            return f"Remote File Inclusion Detection (Rule {rule_id})"
        else:
            return f"Security Rule {rule_id} ({file_name})"
    
    def _map_crs_severity(self, severity: str) -> str:
        """Map CRS severity to our severity levels."""
        mapping = {
            "CRITICAL": "critical",
            "ERROR": "high",
            "WARNING": "medium",
            "NOTICE": "low",
            "INFO": "info"
        }
        return mapping.get(severity.upper(), "info")
    
    def _extract_cwe_from_rule(self, rule_text: str) -> Optional[str]:
        """Extract CWE from rule text."""
        # Look for CWE references in comments or metadata
        cwe_match = re.search(r'CWE-(\d+)', rule_text, re.IGNORECASE)
        if cwe_match:
            return f"CWE-{cwe_match.group(1)}"
        
        return None
    
    def _extract_tags_from_rule(self, rule_text: str) -> List[str]:
        """Extract tags from rule text."""
        tags = []
        
        # Common ModSecurity rule categories
        if 'SQL' in rule_text.upper():
            tags.append('sql-injection')
        if 'XSS' in rule_text.upper():
            tags.append('xss')
        if 'RCE' in rule_text.upper():
            tags.append('rce')
        if 'LFI' in rule_text.upper():
            tags.append('lfi')
        if 'RFI' in rule_text.upper():
            tags.append('rfi')
        if 'INJECTION' in rule_text.upper():
            tags.append('injection')
        if 'AUTH' in rule_text.upper():
            tags.append('authentication')
        if 'SESSION' in rule_text.upper():
            tags.append('session')
        
        # Add generic CRS tag
        tags.append('modsecurity-crs')
        
        return tags
    
    def _convert_modsecurity_regex(self, pattern: str) -> Optional[str]:
        """Convert ModSecurity regex to standard regex."""
        if not pattern:
            return None
        
        # Remove ModSecurity-specific syntax
        # Convert @rx: prefix
        if pattern.startswith('@rx:'):
            pattern = pattern[4:]
        
        # Convert @pm: prefix (parameter match)
        if pattern.startswith('@pm:'):
            # Convert space-separated words to alternation
            words = pattern[4:].split()
            if words:
                escaped_words = [re.escape(word) for word in words]
                pattern = f"({'|'.join(escaped_words)})"
        
        # Convert @pmf: prefix (parameter match from file)
        if pattern.startswith('@pmf:'):
            # This would require reading the file, for now return None
            return None
        
        # Convert @streq: prefix (string equality)
        if pattern.startswith('@streq:'):
            escaped = re.escape(pattern[7:])
            pattern = f"^{escaped}$"
        
        # Convert @contains: prefix
        if pattern.startswith('@contains:'):
            escaped = re.escape(pattern[10:])
            pattern = escaped
        
        # Convert @beginswith: prefix
        if pattern.startswith('@beginswith:'):
            escaped = re.escape(pattern[12:])
            pattern = f"^{escaped}"
        
        # Convert @endsWith: prefix
        if pattern.startswith('@endsWith:'):
            escaped = re.escape(pattern[10:])
            pattern = f"{escaped}$"
        
        # Convert @detectSQLi: prefix
        if pattern.startswith('@detectSQLi'):
            # This is a complex operator, return a basic SQL injection pattern
            pattern = r"(?i)(union\s+select|insert\s+into|delete\s+from|drop\s+table|exec\s*\(|sp_executesql)"
        
        # Convert @detectXSS: prefix
        if pattern.startswith('@detectXSS'):
            # This is a complex operator, return a basic XSS pattern
            pattern = r"(?i)(<script[^>]*>|javascript:|on\w+\s*=)"
        
        # Validate the resulting regex
        try:
            re.compile(pattern)
            return pattern
        except re.error:
            return None
    
    def _determine_where_clauses(self, parsed: Dict[str, Any]) -> List[str]:
        """Determine where clauses based on ModSecurity variable."""
        variable = parsed.get('variable', '')
        where_clauses = []
        
        # Map ModSecurity variables to our where clauses
        if 'ARGS' in variable:
            where_clauses.append('request.body')
            where_clauses.append('request.query')
        elif 'REQUEST_HEADERS' in variable:
            where_clauses.append('request.headers')
        elif 'RESPONSE_HEADERS' in variable:
            where_clauses.append('response.headers')
        elif 'RESPONSE_BODY' in variable:
            where_clauses.append('response.body')
        elif 'REQUEST_BODY' in variable:
            where_clauses.append('request.body')
        elif 'REQUEST_URI' in variable:
            where_clauses.append('request.url')
        else:
            # Default to checking both request and response
            where_clauses.extend(['request.body', 'request.query', 'response.body'])
        
        return where_clauses
    
    def _calculate_confidence(self, parsed: Dict[str, Any]) -> int:
        """Calculate confidence based on rule characteristics."""
        base_confidence = 70  # ModSecurity rules are generally reliable
        
        # Increase confidence for specific operators
        operator = parsed.get('operator', '')
        if '@detectSQLi' in operator or '@detectXSS' in operator:
            base_confidence += 15
        elif '@rx:' in operator:
            base_confidence += 10
        elif '@pm:' in operator:
            base_confidence += 5
        
        return min(base_confidence, 95)
    
    def _generate_description(self, parsed: Dict[str, Any], source_file: Path) -> str:
        """Generate a description for the rule."""
        file_name = source_file.stem
        variable = parsed.get('variable', '')
        
        description = f"ModSecurity rule from {file_name}"
        
        if 'ARGS' in variable:
            description += " - Monitors request arguments"
        elif 'REQUEST_HEADERS' in variable:
            description += " - Monitors request headers"
        elif 'RESPONSE_HEADERS' in variable:
            description += " - Monitors response headers"
        elif 'RESPONSE_BODY' in variable:
            description += " - Monitors response body"
        
        return description
    
    def _save_converted_patterns(self, output_file: str):
        """Save converted patterns to JSON file."""
        output_data = {
            "name": "OWASP ModSecurity CRS",
            "version": "4.0",
            "description": "Converted OWASP ModSecurity Core Rule Set patterns",
            "rules": self.converted_patterns
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
    
    def get_rule_categories(self) -> Dict[str, List[str]]:
        """Get available rule categories and their files."""
        categories = {}
        
        for conf_file in self.crs_dir.rglob("*.conf"):
            try:
                with open(conf_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Categorize by file name
                    file_name = conf_file.stem.lower()
                    if 'sql' in file_name:
                        category = 'sql-injection'
                    elif 'xss' in file_name:
                        category = 'xss'
                    elif 'rce' in file_name:
                        category = 'rce'
                    elif 'lfi' in file_name:
                        category = 'lfi'
                    elif 'rfi' in file_name:
                        category = 'rfi'
                    elif 'auth' in file_name:
                        category = 'authentication'
                    elif 'session' in file_name:
                        category = 'session'
                    else:
                        category = 'general'
                    
                    if category not in categories:
                        categories[category] = []
                    
                    relative_path = str(conf_file.relative_to(self.crs_dir))
                    categories[category].append(relative_path)
            except Exception as e:
                print(f"Warning: Could not process {conf_file}: {e}")
        
        return categories
