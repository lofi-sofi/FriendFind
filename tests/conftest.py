import pytest

from friendfind import create_app
from friendfind.emailer import outbox
from friendfind.models import Invite, User, db
from friendfind.security import hash_password


@pytest.fixture()
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "test-key",
        "SERVER_NAME": "localhost",
        "SMTP_HOST": None,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    outbox.clear()


@pytest.fixture()
def client(app):
    return app.test_client()


def make_user(email, name, password="supersecret123", verified=True):
    user = User(email=email, display_name=name,
                password_hash=hash_password(password),
                email_verified=verified)
    if verified:
        user.check_in()
    db.session.add(user)
    db.session.commit()
    return user


def make_invite():
    invite = Invite()
    db.session.add(invite)
    db.session.commit()
    return invite


def login(client, email, password="supersecret123"):
    return client.post("/login", data={"email": email, "password": password},
                       follow_redirects=True)


@pytest.fixture()
def alice(app):
    return make_user("alice@example.com", "Alice")


@pytest.fixture()
def bob(app):
    return make_user("bob@example.com", "Bob")
