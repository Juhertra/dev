from flask import Flask
from web_routes import bp as web_bp
from api_endpoints import api_bp
from store import PROJECTS_INDEX, list_projects, create_project, set_current_project_id
from core import write_json
import os

def create_app():
    app = Flask(__name__)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)
    
    # Configure API keys (in production, use proper secret management)
    app.config['API_KEYS'] = os.environ.get('API_KEYS', 'test-key-123').split(',')
    
    return app

app = create_app()

if __name__ == "__main__":
    if not os.path.exists(PROJECTS_INDEX):
        write_json(PROJECTS_INDEX, {"projects": [], "current": None})
    if not list_projects():
        pid = create_project("Default")
        set_current_project_id(pid)
    app.run(debug=True, port=5001)
