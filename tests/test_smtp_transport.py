from unittest.mock import MagicMock, patch

from friendfind import create_app


def send_one(app):
    with app.app_context():
        from friendfind.emailer import send_email
        send_email("to@example.com", "subj", "body")


def make_app(**cfg):
    base = {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SECRET_KEY": "t", "SERVER_NAME": "localhost",
            "SMTP_HOST": "smtp.example.com", "SMTP_USER": "u",
            "SMTP_PASSWORD": "p"}
    base.update(cfg)
    return create_app(base)


def test_default_is_465_implicit_ssl(monkeypatch):
    import os
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.delenv("SMTP_SSL", raising=False)
    app = make_app()
    assert app.config["SMTP_PORT"] == 465
    assert app.config["SMTP_SSL"] is True

    with patch("friendfind.emailer.smtplib.SMTP_SSL") as ssl_cls, \
         patch("friendfind.emailer.smtplib.SMTP") as plain_cls:
        smtp = ssl_cls.return_value.__enter__.return_value
        send_one(app)
        ssl_cls.assert_called_once_with("smtp.example.com", 465, timeout=20)
        plain_cls.assert_not_called()
        smtp.starttls.assert_not_called()  # implicit SSL, no STARTTLS upgrade
        smtp.login.assert_called_once_with("u", "p")
        smtp.send_message.assert_called_once()


def test_explicit_starttls_opt_out(monkeypatch):
    app = make_app(SMTP_PORT=587, SMTP_SSL=False)
    with patch("friendfind.emailer.smtplib.SMTP") as plain_cls, \
         patch("friendfind.emailer.smtplib.SMTP_SSL") as ssl_cls:
        smtp = plain_cls.return_value.__enter__.return_value
        send_one(app)
        plain_cls.assert_called_once_with("smtp.example.com", 587, timeout=20)
        ssl_cls.assert_not_called()
        smtp.starttls.assert_called_once()
        smtp.send_message.assert_called_once()
