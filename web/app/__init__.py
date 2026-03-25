from flask import Flask

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.core.config import Config
from app.error_handlers import register_error_handlers


limiter = Limiter(key_func=get_remote_address)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    register_error_handlers(app)

    limiter.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.site import site_bp
    from app.routes.api import api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(site_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app

