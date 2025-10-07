from flask import Blueprint

# Create a blueprint to mirror the existing one so app.py stays unchanged.
web_bp = Blueprint("web", __name__)

# Register feature routes onto this blueprint
from .sitemap import register_sitemap_routes  # noqa: E402
from .queue import register_queue_routes  # noqa: E402
from .findings import register_findings_routes  # noqa: E402
from .explorer import register_explorer_routes  # noqa: E402
from .history import register_history_routes  # noqa: E402
from .nuclei import register_nuclei_routes  # noqa: E402
from .patterns import register_patterns_routes  # noqa: E402
from .reports import register_reports_routes  # noqa: E402
from .tools import register_tools_routes  # noqa: E402
from .vulns import register_vulns_routes  # noqa: E402
from .triage import register_triage_routes  # noqa: E402
from .metrics import register_metrics_routes  # noqa: E402
from .dashboard import dashboard_bp  # noqa: E402

register_sitemap_routes(web_bp)
register_queue_routes(web_bp)
register_findings_routes(web_bp)
register_explorer_routes(web_bp)
register_history_routes(web_bp)
register_nuclei_routes(web_bp)
register_patterns_routes(web_bp)
register_reports_routes(web_bp)
register_tools_routes(web_bp)
register_vulns_routes(web_bp)
register_triage_routes(web_bp)
register_metrics_routes(web_bp)

# Register dashboard blueprint
web_bp.register_blueprint(dashboard_bp, url_prefix='')

__all__ = ["web_bp"]


