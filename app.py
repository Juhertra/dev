import os

from flask import Flask

from api_endpoints import api_bp
from core import write_json
from store import PROJECTS_INDEX, create_project, list_projects, set_current_project_id
from web_routes import bp as web_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)
    
    # Configure API keys from environment only; no hardcoded fallback.
    raw_api_keys = os.environ.get("API_KEYS", "")
    api_keys = [k.strip() for k in raw_api_keys.split(",") if k.strip()]
    if not api_keys:
        app.logger.warning(
            "API_KEYS is not set; API key-protected endpoints will reject all keys."
        )
    app.config["API_KEYS"] = api_keys
    
    return app

app = create_app()

if __name__ == "__main__":
    if not os.path.exists(PROJECTS_INDEX):
        write_json(PROJECTS_INDEX, {"projects": [], "current": None})
    if not list_projects():
        pid = create_project("Default")
        set_current_project_id(pid)
    app.run(debug=True, port=5001)
