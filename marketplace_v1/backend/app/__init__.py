from flask import Flask
from flask_cors import CORS

from .config import Config
from .extensions import db, jwt, migrate


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    register_blueprints(app)

    @app.get("/health")
    def health_check() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    @app.get("/")
    def landing_page() -> str:
        return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Marketplace API</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 40px; line-height: 1.5; }
      h1 { margin-bottom: 8px; }
      code { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; }
      ul { padding-left: 20px; }
    </style>
  </head>
  <body>
    <h1>Marketplace API is running</h1>
    <p>Use these endpoints to verify service health and auth:</p>
    <ul>
      <li><code>GET /health</code></li>
      <li><code>POST /api/v1/auth/bootstrap-admin</code></li>
      <li><code>POST /api/v1/auth/register</code></li>
      <li><code>POST /api/v1/auth/login</code></li>
      <li><code>GET /api/v1/orders/ping</code></li>
    </ul>
  </body>
</html>
"""

    return app


def register_blueprints(app: Flask) -> None:
    from .api.v1.admin_routes import admin_bp
    from .api.v1.auth_routes import auth_bp
    from .api.v1.order_routes import order_bp

    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(order_bp, url_prefix="/api/v1/orders")
    app.register_blueprint(admin_bp, url_prefix="/api/v1/admin")
