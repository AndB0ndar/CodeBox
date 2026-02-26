from flask import Flask

from app.core.config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    from app.routes.site import site_bp
    from app.routes.api import api_bp
    app.register_blueprint(site_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app

