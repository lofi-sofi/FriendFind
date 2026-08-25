import os
from functools import wraps

from flask import Flask, g, redirect, session, url_for
from markupsafe import Markup

from .models import db, User
from . import platforms


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///" + os.path.join(app.instance_path, "friendfind.db")
        ),
        MAIL_FROM=os.environ.get("MAIL_FROM", "friendfind@localhost"),
        SMTP_HOST=os.environ.get("SMTP_HOST"),
        SMTP_PORT=int(os.environ.get("SMTP_PORT", "587")),
        SMTP_USER=os.environ.get("SMTP_USER"),
        SMTP_PASSWORD=os.environ.get("SMTP_PASSWORD"),
        # Needed so CLI commands (create-invite, send-reminders) can build
        # absolute URLs, e.g. SERVER_NAME=friendfind.example.com
        SERVER_NAME=os.environ.get("SERVER_NAME"),
        PREFERRED_URL_SCHEME=os.environ.get("URL_SCHEME", "https" if os.environ.get("SERVER_NAME") else "http"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    with app.app_context():
        db.create_all()

    from .blueprints import account, auth, checkin, directory, handles
    app.register_blueprint(auth.bp)
    app.register_blueprint(handles.bp)
    app.register_blueprint(directory.bp)
    app.register_blueprint(checkin.bp)
    app.register_blueprint(account.bp)

    from . import cli
    cli.register(app)

    @app.before_request
    def load_user():
        uid = session.get("user_id")
        g.user = db.session.get(User, uid) if uid else None

    @app.context_processor
    def template_globals():
        return {
            "current_user": g.get("user"),
            "PLATFORMS": platforms.PLATFORMS,
            "platform_name": platforms.platform_name,
            "charm": lambda slug, size=24: Markup(platforms.charm_svg(slug, size)),
        }

    @app.route("/")
    def index():
        if g.user:
            return redirect(url_for("directory.home"))
        return redirect(url_for("auth.login"))

    return app
