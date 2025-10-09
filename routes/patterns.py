from flask import render_template, request


def register_patterns_routes(bp):
    """Register pattern management routes on the given blueprint."""

    @bp.route("/p/<pid>/patterns")
    def patterns_page(pid: str):
        import os

        from detectors.enhanced_pattern_engine import EnhancedPatternEngine
        from store import get_project_name
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)  # project root for engine
            engine = EnhancedPatternEngine(base_dir, pid)
            stats = engine.get_advanced_statistics()
            all_patterns = engine.list_patterns()
            severity_filter = request.args.get('severity', '')
            cwe_filter = request.args.get('cwe', '')
            confidence_min = request.args.get('confidence_min', type=int)
            confidence_max = request.args.get('confidence_max', type=int)
            tags_filter = request.args.get('tags', '')
            pack_type_filter = request.args.get('pack_type', '')
            pack_name_filter = request.args.get('pack_name', '')
            filtered_patterns = engine.get_patterns_by_filter(
                severity=severity_filter or None,
                cwe=cwe_filter or None,
                confidence_min=confidence_min,
                confidence_max=confidence_max,
                tags=tags_filter.split(',') if tags_filter else None,
                pack_type=pack_type_filter or None,
                pack_name=pack_name_filter or None,
            )
            unique_severities = sorted(set(p.get('severity', 'info') for p in all_patterns))
            unique_cwes = sorted(set(p.get('cwe', '') for p in all_patterns if p.get('cwe')))
            unique_pack_types = sorted(set(p.get('pack_type', 'unknown') for p in all_patterns))
            unique_pack_names = sorted(set(p.get('pack_name', '') for p in all_patterns))
            unique_tags = sorted(set(tag for p in all_patterns for tag in p.get('tags', [])))
            return render_template("patterns.html",
                                  pid=pid,
                                  project_name=get_project_name(pid),
                                  patterns=filtered_patterns,
                                  stats=stats,
                                  unique_severities=unique_severities,
                                  unique_cwes=unique_cwes,
                                  unique_pack_types=unique_pack_types,
                                  unique_pack_names=unique_pack_names,
                                  unique_tags=unique_tags,
                                  current_filters={'severity': severity_filter,'cwe': cwe_filter,'confidence_min': confidence_min,'confidence_max': confidence_max,'tags': tags_filter,'pack_type': pack_type_filter,'pack_name': pack_name_filter})
        except Exception as e:
            return f"Error loading patterns: {str(e)}", 500

    @bp.route("/p/<pid>/patterns/test", methods=["POST"])
    def test_pattern(pid: str):
        import os

        from detectors.enhanced_pattern_engine import EnhancedPatternEngine
        try:
            pattern_id = request.form.get('pattern_id')
            test_text = request.form.get('test_text', '')
            if not pattern_id or not test_text:
                return {"error": "Missing pattern_id or test_text"}, 400
            base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
            engine = EnhancedPatternEngine(base_dir, pid)
            result = engine.test_pattern_against_text(pattern_id, test_text)
            return result
        except Exception as e:
            return {"error": str(e)}, 500

    @bp.route("/p/<pid>/patterns/toggle", methods=["POST"])
    def toggle_pattern(pid: str):
        import os

        from detectors.enhanced_pattern_engine import EnhancedPatternEngine
        try:
            pattern_id = request.form.get('pattern_id')
            enabled = request.form.get('enabled', '').lower() == 'true'
            if not pattern_id:
                return {"error": "Missing pattern_id"}, 400
            base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
            engine = EnhancedPatternEngine(base_dir, pid)
            success = engine.toggle_pattern(pattern_id, enabled)
            if success:
                return {"success": True, "enabled": enabled}
            else:
                return {"error": "Pattern not found"}, 404
        except Exception as e:
            return {"error": str(e)}, 500

    @bp.route("/p/<pid>/patterns/export")
    def export_patterns(pid: str):
        import os
        import tempfile

        from detectors.enhanced_pattern_engine import EnhancedPatternEngine
        try:
            format_type = request.args.get('format', 'json')
            if format_type not in ['json', 'csv', 'yaml']:
                return {"error": "Invalid format"}, 400
            base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
            engine = EnhancedPatternEngine(base_dir, pid)
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{format_type}', delete=False) as f:
                temp_file = f.name
            success = engine.export_patterns(temp_file, format_type)
            if not success:
                return {"error": "Export failed"}, 500
            with open(temp_file, 'r') as f:
                content = f.read()
            os.unlink(temp_file)
            from flask import Response
            return Response(content, mimetype={
                'json': 'application/json', 'csv': 'text/csv', 'yaml': 'application/x-yaml'
            }[format_type], headers={'Content-Disposition': f'attachment; filename=patterns_{pid}.{format_type}'})
        except Exception as e:
            return {"error": str(e)}, 500

    @bp.route("/p/<pid>/patterns/import", methods=["POST"])
    def import_patterns(pid: str):
        import os
        import tempfile

        from detectors.enhanced_pattern_engine import EnhancedPatternEngine
        try:
            if 'file' not in request.files:
                return {"error": "No file provided"}, 400
            file = request.files['file']
            if file.filename == '':
                return {"error": "No file selected"}, 400
            filename = file.filename.lower()
            if filename.endswith('.json'):
                format_type = 'json'
            elif filename.endswith('.csv'):
                format_type = 'csv'
            elif filename.endswith('.yaml') or filename.endswith('.yml'):
                format_type = 'yaml'
            else:
                return {"error": "Unsupported file format"}, 400
            with tempfile.NamedTemporaryFile(mode='w+b', suffix=f'.{format_type}', delete=False) as f:
                file.save(f.name)
                temp_file = f.name
            base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
            engine = EnhancedPatternEngine(base_dir, pid)
            success, errors = engine.import_patterns(temp_file, format_type)
            os.unlink(temp_file)
            if success:
                return {"success": True, "message": "Patterns imported successfully"}
            else:
                return {"error": "Import failed", "details": errors}, 400
        except Exception as e:
            return {"error": str(e)}, 500

    @bp.route("/p/<pid>/patterns/community/update", methods=["POST"])
    def update_community_packs(pid: str):
        import os

        from detectors.pattern_manager import PatternManager
        try:
            force = request.form.get('force', '').lower() == 'true'
            base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
            pattern_manager = PatternManager(base_dir)
            results = pattern_manager.update_community_packs(force)
            return {
                "success": True,
                "results": results,
                "message": f"Updated {len(results['updated'])} packs, {len(results['failed'])} failed, {len(results['skipped'])} skipped"
            }
        except Exception as e:
            return {"error": str(e)}, 500

    @bp.route("/p/<pid>/patterns/stats")
    def pattern_statistics(pid: str):
        import os

        from detectors.enhanced_pattern_engine import EnhancedPatternEngine
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
            engine = EnhancedPatternEngine(base_dir, pid)
            stats = engine.get_advanced_statistics()
            return stats
        except Exception as e:
            return {"error": str(e)}, 500


