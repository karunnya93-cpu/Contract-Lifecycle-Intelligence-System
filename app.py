from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_login import LoginManager

# Load the project-root .env file before importing configuration values.
load_dotenv(Path(__file__).resolve().parent / ".env")

from config import Config
from models import db
from models.contract import Contract
from models.user import User
from routes.auth import auth_bp
from routes.modules import modules_bp
from utils.security import generate_csrf_token


login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to access that page."
login_manager.login_message_category = "warning"


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")

    _ensure_runtime_directories(app)
    _configure_logging(app)

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(modules_bp)
    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    @app.route("/")
    def index():
        return render_template("index.html")

    with app.app_context():
        db.create_all()
        Contract.ensure_analysis_columns()

    return app


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    if not user_id.isdigit():
        return None
    return db.session.get(User, int(user_id))


def _ensure_runtime_directories(app: Flask) -> None:
    for key in ("UPLOAD_FOLDER", "DATABASE_DIR", "LOG_DIR"):
        Path(app.config[key]).mkdir(parents=True, exist_ok=True)


def _configure_logging(app: Flask) -> None:
    if app.debug or app.testing:
        return

    log_file = Path(app.config["LOG_DIR"]) / "application.log"
    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(module)s:%(lineno)d - %(message)s"
        )
    )
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("AI-Based Contract Intelligence System started")


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
