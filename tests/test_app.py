"""Tests for the healthcare web application.

Covers three areas the assessment cares about: that public pages render, that
authentication/authorisation are actually enforced, and that the core
domain logic (user creation, admin promotion, model loading) behaves.
"""
import app as app_module
from models import db, User


# --- Public pages -----------------------------------------------------------

def test_index_page_ok(client):
    resp = client.get('/')
    assert resp.status_code == 200


def test_terms_page_ok(client):
    resp = client.get('/terms')
    assert resp.status_code == 200


def test_login_page_ok(client):
    resp = client.get('/login')
    assert resp.status_code == 200


# --- Authentication / authorisation -----------------------------------------

def test_protected_route_redirects_when_anonymous(client):
    """A login-required page bounces anonymous users to the login screen."""
    resp = client.get('/view-profile')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']


def test_admin_forbidden_for_anonymous(client):
    """The admin dashboard is not reachable without an admin session."""
    resp = client.get('/admin/')
    # Flask-Admin redirects anonymous users to the login page.
    assert resp.status_code in (302, 403)


# --- Registration / login flow ----------------------------------------------

def test_custom_register_then_login(client):
    payload = {
        'authType': 'custom',
        'username': 'alice',
        'email': 'alice@example.com',
        'password': 'sup3rsecret',
        'fullname': 'Alice Example',
    }
    reg = client.post('/register', json=payload)
    assert reg.status_code == 200
    assert reg.get_json()['success'] is True

    login = client.post('/login', json={
        'authType': 'custom',
        'email': 'alice@example.com',
        'password': 'sup3rsecret',
    })
    assert login.status_code == 200
    assert login.get_json()['success'] is True


def test_login_rejects_bad_password(client):
    client.post('/register', json={
        'authType': 'custom', 'username': 'bob',
        'email': 'bob@example.com', 'password': 'correct-horse',
    })
    resp = client.post('/login', json={
        'authType': 'custom', 'email': 'bob@example.com', 'password': 'wrong',
    })
    assert resp.status_code == 401


def test_duplicate_email_registration_rejected(client):
    payload = {
        'authType': 'custom', 'username': 'carol',
        'email': 'carol@example.com', 'password': 'passw0rd',
    }
    assert client.post('/register', json=payload).status_code == 200
    payload['username'] = 'carol2'
    dup = client.post('/register', json=payload)
    assert dup.status_code == 400


# --- Domain logic -----------------------------------------------------------

def test_password_is_hashed_not_plaintext(app):
    user = User.create_custom_user('dave', 'dave@example.com', 'my-password')
    assert user.password_hash != 'my-password'
    assert user.check_password('my-password') is True
    assert user.check_password('nope') is False


def test_new_user_defaults_to_non_admin(app):
    user = User.create_custom_user('erin', 'erin@example.com', 'pw123456')
    assert user.role == 'user'
    assert user.is_admin is False


def test_admin_email_promotion(app, monkeypatch):
    """Users whose email is in ADMIN_EMAILS are promoted on login."""
    monkeypatch.setattr(app_module, 'ADMIN_EMAILS', {'boss@example.com'})
    user = User(username='boss', email='boss@example.com', auth_method='custom')
    db.session.add(user)
    db.session.commit()

    app_module._apply_configured_admin_role(user)
    assert user.role == 'admin'
    assert user.is_admin is True


def test_non_listed_email_not_promoted(app, monkeypatch):
    monkeypatch.setattr(app_module, 'ADMIN_EMAILS', {'boss@example.com'})
    user = User.create_custom_user('frank', 'frank@example.com', 'pw123456')
    app_module._apply_configured_admin_role(user)
    assert user.role == 'user'


def test_load_models_returns_all_keys():
    """load_models always returns the three model slots, even if unavailable."""
    from loadModels import load_models
    models = load_models()
    assert set(models.keys()) == {'heart', 'diabetes', 'parkinsons'}
