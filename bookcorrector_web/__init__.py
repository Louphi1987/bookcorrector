from __future__ import annotations

from flask import Flask

from .routes import main_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        JSON_SORT_KEYS=False,
    )
    app.register_blueprint(main_bp)
    return app
