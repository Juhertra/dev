#!/usr/bin/env python3
"""
P5 - Triage API Routes

REST endpoints for findings triage workflow:
- Update triage status, owner, tags
- Add/remove notes
- Suppress findings
"""

import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app

from store import _bust_vulns_cache
from utils.schema_validation import validate_json


def register_triage_routes(web_bp: Blueprint):
    """Register triage API routes."""
    
    @web_bp.route('/p/<pid>/findings/<int:idx>/triage', methods=['POST'])
    def update_finding_triage(pid: str, idx: int):
        """Update triage fields for a specific finding."""
        try:
            # Load findings file
            findings_file = f"ui_projects/{pid}.findings.json"
            
            try:
                with open(findings_file, 'r') as f:
                    findings = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                return jsonify({"error": f"Failed to load findings: {e}"}), 400
            
            # Validate index
            if idx < 0 or idx >= len(findings):
                return jsonify({"error": "Invalid finding index"}), 400
            
            # Get request data
            data = request.get_json() or {}
            
            # Validate triage data against schema
            triage_data = data.get('triage', {})
            if triage_data:
                # Load schema for validation
                try:
                    with open('findings.schema.json', 'r') as f:
                        schema = json.load(f)
                    
                    # Validate triage object
                    triage_schema = schema['items']['properties']['triage']
                    validate_json(triage_data, triage_schema)
                except Exception as e:
                    return jsonify({"error": f"Schema validation failed: {e}"}), 400
            
            # Update finding
            finding = findings[idx]
            
            # Initialize triage if not exists
            if 'triage' not in finding:
                finding['triage'] = {"status": "open", "tags": [], "notes": []}
            
            # Update triage fields
            if 'status' in data:
                finding['triage']['status'] = data['status']
            
            if 'owner' in data:
                finding['triage']['owner'] = data['owner']
            
            if 'tags' in data:
                finding['triage']['tags'] = data['tags']
            
            if 'suppress' in data:
                finding['triage']['suppress'] = data['suppress']
            
            # Save findings
            with open(findings_file, 'w') as f:
                json.dump(findings, f, indent=2)
            
            # Bust cache
            try:
                _bust_vulns_cache(pid)
            except Exception as e:
                current_app.logger.warning(f"Cache bust failed for {pid}: {e}")
            
            return jsonify({
                "success": True,
                "finding_index": idx,
                "triage": finding['triage']
            })
            
        except Exception as e:
            current_app.logger.error(f"Triage update failed: {e}")
            return jsonify({"error": str(e)}), 500
    
    @web_bp.route('/p/<pid>/findings/<int:idx>/note', methods=['POST'])
    def add_finding_note(pid: str, idx: int):
        """Add a note to a finding's triage thread."""
        try:
            # Load findings file
            findings_file = f"ui_projects/{pid}.findings.json"
            
            try:
                with open(findings_file, 'r') as f:
                    findings = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                return jsonify({"error": f"Failed to load findings: {e}"}), 400
            
            # Validate index
            if idx < 0 or idx >= len(findings):
                return jsonify({"error": "Invalid finding index"}), 400
            
            # Get request data
            data = request.get_json() or {}
            note_text = data.get('text', '').strip()
            note_by = data.get('by', 'unknown')
            
            if not note_text:
                return jsonify({"error": "Note text is required"}), 400
            
            # Update finding
            finding = findings[idx]
            
            # Initialize triage if not exists
            if 'triage' not in finding:
                finding['triage'] = {"status": "open", "tags": [], "notes": []}
            
            # Add note
            note = {
                "at": datetime.now(timezone.utc).isoformat(),
                "by": note_by,
                "text": note_text
            }
            
            if 'notes' not in finding['triage']:
                finding['triage']['notes'] = []
            
            finding['triage']['notes'].append(note)
            
            # Save findings
            with open(findings_file, 'w') as f:
                json.dump(findings, f, indent=2)
            
            # Bust cache
            try:
                _bust_vulns_cache(pid)
            except Exception as e:
                current_app.logger.warning(f"Cache bust failed for {pid}: {e}")
            
            return jsonify({
                "success": True,
                "finding_index": idx,
                "note": note,
                "total_notes": len(finding['triage']['notes'])
            })
            
        except Exception as e:
            current_app.logger.error(f"Note addition failed: {e}")
            return jsonify({"error": str(e)}), 500
    
    @web_bp.route('/p/<pid>/findings/<int:idx>/tag', methods=['POST'])
    def manage_finding_tag(pid: str, idx: int):
        """Add or remove a tag from a finding."""
        try:
            # Load findings file
            findings_file = f"ui_projects/{pid}.findings.json"
            
            try:
                with open(findings_file, 'r') as f:
                    findings = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                return jsonify({"error": f"Failed to load findings: {e}"}), 400
            
            # Validate index
            if idx < 0 or idx >= len(findings):
                return jsonify({"error": "Invalid finding index"}), 400
            
            # Get request data
            data = request.get_json() or {}
            tag = data.get('tag', '').strip()
            action = data.get('action', 'add')  # 'add' or 'remove'
            
            if not tag:
                return jsonify({"error": "Tag is required"}), 400
            
            # Update finding
            finding = findings[idx]
            
            # Initialize triage if not exists
            if 'triage' not in finding:
                finding['triage'] = {"status": "open", "tags": [], "notes": []}
            
            if 'tags' not in finding['triage']:
                finding['triage']['tags'] = []
            
            # Add or remove tag
            if action == 'add':
                if tag not in finding['triage']['tags']:
                    finding['triage']['tags'].append(tag)
            elif action == 'remove':
                if tag in finding['triage']['tags']:
                    finding['triage']['tags'].remove(tag)
            else:
                return jsonify({"error": "Invalid action. Use 'add' or 'remove'"}), 400
            
            # Save findings
            with open(findings_file, 'w') as f:
                json.dump(findings, f, indent=2)
            
            # Bust cache
            try:
                _bust_vulns_cache(pid)
            except Exception as e:
                current_app.logger.warning(f"Cache bust failed for {pid}: {e}")
            
            return jsonify({
                "success": True,
                "finding_index": idx,
                "action": action,
                "tag": tag,
                "tags": finding['triage']['tags']
            })
            
        except Exception as e:
            current_app.logger.error(f"Tag management failed: {e}")
            return jsonify({"error": str(e)}), 500
    
    @web_bp.route('/p/<pid>/findings/<int:idx>/suppress', methods=['POST'])
    def suppress_finding(pid: str, idx: int):
        """Suppress a finding with optional scope and duration."""
        try:
            # Load findings file
            findings_file = f"ui_projects/{pid}.findings.json"
            
            try:
                with open(findings_file, 'r') as f:
                    findings = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                return jsonify({"error": f"Failed to load findings: {e}"}), 400
            
            # Validate index
            if idx < 0 or idx >= len(findings):
                return jsonify({"error": "Invalid finding index"}), 400
            
            # Get request data
            data = request.get_json() or {}
            reason = data.get('reason', '').strip()
            until = data.get('until')  # ISO timestamp
            scope = data.get('scope', 'this')
            
            if not reason:
                return jsonify({"error": "Suppression reason is required"}), 400
            
            # Update finding
            finding = findings[idx]
            
            # Initialize triage if not exists
            if 'triage' not in finding:
                finding['triage'] = {"status": "open", "tags": [], "notes": []}
            
            # Set suppression
            finding['triage']['suppress'] = {
                "reason": reason,
                "scope": scope
            }
            
            if until:
                finding['triage']['suppress']['until'] = until
            
            # Save findings
            with open(findings_file, 'w') as f:
                json.dump(findings, f, indent=2)
            
            # Bust cache
            try:
                _bust_vulns_cache(pid)
            except Exception as e:
                current_app.logger.warning(f"Cache bust failed for {pid}: {e}")
            
            return jsonify({
                "success": True,
                "finding_index": idx,
                "suppress": finding['triage']['suppress']
            })
            
        except Exception as e:
            current_app.logger.error(f"Suppression failed: {e}")
            return jsonify({"error": str(e)}), 500
