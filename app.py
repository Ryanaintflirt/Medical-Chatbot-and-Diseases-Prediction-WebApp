from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_migrate import Migrate
import click
import requests
import os
import uuid
import logging
from dotenv import load_dotenv
import json
from datetime import datetime
from models import db, User, MedicalInfofuser, Doctor, Appointment, Conversation, Message, Hospital
from loadModels import load_models
from sqlalchemy.exc import OperationalError
from src import rag
import numpy as np

logger = logging.getLogger(__name__)

# Load environment variables (.env then SECRET.env so either file works; latter overrides)
_app_root = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_app_root, '.env'))

def get_env_value(name, default=None):
    value = os.getenv(name, default)
    if isinstance(value, str):
        return value.strip()
    return value

def strip_key_prefix(value, prefix):
    if not value:
        return value
    if value.startswith(prefix):
        return value[len(prefix):]
    return value

app = Flask(__name__)

# Load models at startup
ML_MODELS = load_models()

# Environment / debug detection (used for secret key + app.run below)
_flask_env = (get_env_value('FLASK_ENV', '') or '').lower()
_flask_debug = (get_env_value('FLASK_DEBUG', '') or '').lower()
IS_PRODUCTION = _flask_env == 'production'
DEBUG_MODE = _flask_debug in ('1', 'true', 'yes') or (not IS_PRODUCTION and _flask_debug != 'false')

# Secret key: required in production, dev-only fallback otherwise.
app.secret_key = get_env_value('SECRET_KEY')
if not app.secret_key:
    if IS_PRODUCTION:
        raise RuntimeError(
            'SECRET_KEY environment variable must be set in production. '
            'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    logger.warning('SECRET_KEY not set; using an insecure development key. Do NOT use in production.')
    app.secret_key = 'dev-only-insecure-secret-key-change-me'

# Database configuration.
# Prefer DATABASE_URL (e.g. a managed Postgres on Render) so data survives
# redeploys; fall back to a local SQLite file under instance/ for development.
_database_url = get_env_value('DATABASE_URL')
if _database_url:
    # SQLAlchemy needs the 'postgresql://' scheme, but Render/Heroku hand out
    # the legacy 'postgres://' — normalise it so the driver is selected.
    if _database_url.startswith('postgres://'):
        _database_url = _database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = _database_url
else:
    os.makedirs(app.instance_path, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        'sqlite:///' + os.path.join(app.instance_path, 'healthcare_users.db')
    )
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Profile picture uploads
PROFILE_PIC_DIR = os.path.join(_app_root, 'static', 'uploads', 'profile_pictures')
os.makedirs(PROFILE_PIC_DIR, exist_ok=True)
app.config['PROFILE_PIC_FOLDER'] = PROFILE_PIC_DIR
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_PROFILE_PIC_BYTES = 5 * 1024 * 1024  # 5 MB

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)  # `flask db migrate/upgrade` for future schema changes


def _ensure_sqlite_columns():
    """Add columns introduced after the initial release to an existing SQLite DB.

    db.create_all() creates missing *tables* but never alters existing ones, so a
    database created before these columns existed would be missing them. This runs
    an idempotent, non-destructive `ALTER TABLE ADD COLUMN` for each and is a no-op
    once the column is present. Only applies to SQLite (the configured backend).
    """
    from sqlalchemy import text

    if not app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
        return

    # (table, column, column definition) — definitions must include a DEFAULT if NOT NULL.
    pending = [
        ('users', 'role', "VARCHAR(20) NOT NULL DEFAULT 'user'"),
        ('doctor', 'hospital_id', 'INTEGER'),
    ]
    for table, column, coldef in pending:
        existing = [row[1] for row in db.session.execute(text(f'PRAGMA table_info({table})'))]
        if not existing:
            continue  # table doesn't exist yet; create_all handles fresh installs
        if column not in existing:
            db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {coldef}'))
            logger.info('Auto-added missing column %s.%s', table, column)
    db.session.commit()


# Create tables if missing (avoids "no such table" when /init-db was never run),
# then backfill any columns added in later releases.
with app.app_context():
    try:
        db.create_all()
    except OperationalError as exc:
        # With multiple gunicorn workers, each imports this module and calls
        # create_all() concurrently against the same fresh SQLite file. They
        # race between checkfirst's reflection and the CREATE TABLE, so the
        # loser sees "table ... already exists". The winning worker creates the
        # full schema, so the loser can safely roll back and carry on.
        if 'already exists' not in str(exc).lower():
            raise
        db.session.rollback()
        logger.warning('create_all() raced with another worker; schema already present: %s', exc)
    _ensure_sqlite_columns()
CORS(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore[attr-defined]
login_manager.login_message = 'Please log in to access this page.'

@login_manager.unauthorized_handler
def unauthorized():
    if request.method == 'DELETE':
        return jsonify({'error': 'Authentication required'}), 401
    return redirect(url_for('login', next=request.path))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------------------------------------------------------------
# Admin dashboard (Flask-Admin) — back-office CRUD for staff only
# ---------------------------------------------------------------------------
def _current_user_is_admin():
    return current_user.is_authenticated and getattr(current_user, 'role', 'user') == 'admin'


# Emails that should always have the admin role, from the ADMIN_EMAILS env var
# (comma-separated, case-insensitive). Applied on every login so admin access
# survives the database being recreated (e.g. Render's ephemeral disk), where a
# one-off `flask make-admin` would be lost on the next deploy.
ADMIN_EMAILS = {
    e.strip().lower()
    for e in (get_env_value('ADMIN_EMAILS', '') or '').split(',')
    if e.strip()
}


def _apply_configured_admin_role(user):
    """Promote `user` to admin if their email is listed in ADMIN_EMAILS."""
    if user and user.email and user.email.strip().lower() in ADMIN_EMAILS:
        if user.role != 'admin':
            user.role = 'admin'
            logger.info('Granted admin role to %s via ADMIN_EMAILS', user.email)


class SecureModelView(ModelView):
    """Base admin view: only reachable by logged-in admins."""
    def is_accessible(self):
        return _current_user_is_admin()

    def inaccessible_callback(self, name, **kwargs):
        # Non-admins are sent to login (or bounced if already logged in as a user).
        if current_user.is_authenticated:
            abort(403)
        return redirect(url_for('login', next=request.path))


class SecureAdminIndexView(AdminIndexView):
    """Admin landing page: a stats overview. Same access rule as the model views."""
    def is_accessible(self):
        return _current_user_is_admin()

    def inaccessible_callback(self, name, **kwargs):
        if current_user.is_authenticated:
            abort(403)
        return redirect(url_for('login', next=request.path))

    @expose('/')
    def index(self):
        # Access is enforced by Flask-Admin via is_accessible/inaccessible_callback.
        from datetime import date
        stats = {
            'users': User.query.count(),
            'doctors': Doctor.query.count(),
            'hospitals': Hospital.query.count(),
            'appointments': Appointment.query.count(),
        }
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        upcoming = (
            Appointment.query
            .filter(Appointment.appointment_date >= date.today())
            .order_by(Appointment.appointment_date, Appointment.appointment_time)
            .limit(5)
            .all()
        )
        return self.render(
            'admin/dashboard.html',
            stats=stats,
            recent_users=recent_users,
            upcoming=upcoming,
        )


class UserAdmin(SecureModelView):
    # Never expose the password hash in the list or edit form.
    column_exclude_list = ['password_hash']
    form_excluded_columns = ['password_hash', 'conversations', 'linked_accounts']
    column_searchable_list = ['username', 'email', 'full_name']
    column_filters = ['role', 'auth_method', 'is_active']
    column_editable_list = ['role', 'is_active']


class DoctorAdmin(SecureModelView):
    # Show the affiliated hospital in the list table (relationships aren't listed
    # by default) so assignments are visible at a glance.
    column_list = ['full_name', 'specialty', 'gender', 'email', 'hospital', 'years_experience']
    column_labels = {'hospital': 'Hospital', 'years_experience': 'Experience (yrs)'}
    column_searchable_list = ['full_name', 'specialty', 'email']
    column_filters = ['specialty', 'gender', 'hospital']
    # The 'hospital' relationship field renders as a dropdown in the create/edit
    # form (populate the Hospitals table first so it has options to choose from).
    form_excluded_columns = ['appointments']


class HospitalAdmin(SecureModelView):
    column_searchable_list = ['name', 'city']
    form_excluded_columns = ['doctors']

    def on_model_delete(self, model):
        # Don't orphan doctors: block deleting a hospital that still has affiliations.
        if model.doctors:
            raise ValueError(
                f'Cannot delete "{model.name}": {len(model.doctors)} doctor(s) are still '
                'assigned. Reassign or remove them first.'
            )


class AppointmentAdmin(SecureModelView):
    column_filters = ['status', 'appointment_date']


admin = Admin(
    app,
    name='HealthCare Admin',
    index_view=SecureAdminIndexView(name='Dashboard', url='/admin'),
    template_mode='bootstrap4',
)
admin.add_view(UserAdmin(User, db.session, name='Users'))
admin.add_view(DoctorAdmin(Doctor, db.session, name='Doctors'))
admin.add_view(HospitalAdmin(Hospital, db.session, name='Hospitals'))
admin.add_view(AppointmentAdmin(Appointment, db.session, name='Appointments'))


@app.cli.command('make-admin')
@click.argument('email')
def make_admin(email):
    """Promote the user with EMAIL to the admin role: `flask make-admin you@example.com`."""
    user = User.query.filter_by(email=email).first()
    if not user:
        click.echo(f'No user found with email: {email}')
        return
    user.role = 'admin'
    db.session.commit()
    click.echo(f'{email} is now an admin.')


# Firebase Configuration
FIREBASE_CONFIG = {
    "apiKey": get_env_value('FIREBASE_API_KEY'),
    "authDomain": get_env_value('FIREBASE_AUTH_DOMAIN'),
    "projectId": get_env_value('FIREBASE_PROJECT_ID'),
    "storageBucket": get_env_value('FIREBASE_STORAGE_BUCKET'),
    "messagingSenderId": get_env_value('FIREBASE_MESSAGING_SENDER_ID'),
    "appId": get_env_value('FIREBASE_APP_ID'),
    "measurementId": get_env_value('FIREBASE_MEASUREMENT_ID'),
    "databaseURL": get_env_value('FIREBASE_DATABASE_URL')
}

# AI Chatbot Configuration (Gemini)
GEMINI_API_KEY = get_env_value('GEMINI_API_KEY') or get_env_value('AiApi_Key')
GEMINI_MODEL = get_env_value('GEMINI_MODEL', 'gemini-3-flash-preview')
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# Send the API key as a header instead of a URL query param (avoids leaking it in logs/proxies)
GEMINI_HEADERS = {'x-goog-api-key': GEMINI_API_KEY or '', 'Content-Type': 'application/json'}


@app.route('/')
def index():
    username = current_user.username if current_user.is_authenticated else None
    full_name = current_user.full_name if current_user.is_authenticated else None
    return render_template("index.html", username=username, full_name=full_name)


@app.route('/terms')
def terms():
    """Terms and Conditions (public)."""
    return render_template("terms.html")

def _require_admin_token():
    """Guard for maintenance routes. Returns an error response tuple if unauthorized, else None.

    Set ADMIN_TOKEN in the environment and pass it as ?token=... or an
    'X-Admin-Token' header. If ADMIN_TOKEN is unset, the routes are disabled.
    """
    admin_token = get_env_value('ADMIN_TOKEN')
    if not admin_token:
        return jsonify({'error': 'This endpoint is disabled. Set ADMIN_TOKEN to enable it.'}), 403
    provided = request.headers.get('X-Admin-Token') or request.args.get('token')
    if not provided or provided != admin_token:
        return jsonify({'error': 'Unauthorized'}), 401
    return None

@app.route('/init-db')
def init_db():
    """Initialize the database with tables"""
    denied = _require_admin_token()
    if denied:
        return denied
    try:
        with app.app_context():
            db.create_all()
        return jsonify({'message': 'Database initialized successfully!'})
    except Exception as e:
        return jsonify({'error': f'Database initialization failed: {str(e)}'}), 500

def verify_firebase_token(id_token):
    """Verify Firebase ID token using REST API"""
    try:
        # Firebase REST API endpoint for token verification
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={FIREBASE_CONFIG['apiKey']}"
        
        payload = {"idToken": id_token}
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if 'users' in data and len(data['users']) > 0:
                user = data['users'][0]
                provider_ids = []
                for p in user.get('providerUserInfo') or []:
                    pid = p.get('providerId')
                    if pid:
                        provider_ids.append(pid)
                return {
                    'uid': user.get('localId'),
                    'email': user.get('email', ''),
                    'name': user.get('displayName', ''),
                    'email_verified': user.get('emailVerified', False),
                    'photoURL': user.get('photoUrl'),
                    'provider_ids': provider_ids,
                    'has_google_provider': 'google.com' in provider_ids,
                }
        return None
    except Exception as e:
        logger.warning("Token verification error: %s", e)
        return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            auth_type = data.get('authType', 'firebase')  # 'firebase' or 'custom'
            
            if auth_type == 'firebase':
                id_token = data.get('idToken')
                
                if not id_token:
                    return jsonify({'error': 'No ID token provided'}), 400
                
                user_data = verify_firebase_token(id_token)
                
                if not user_data:
                    return jsonify({'error': 'Invalid token'}), 401
                
                user = User.query.filter_by(firebase_uid=user_data['uid']).first()

                if not user:
                    # No account for this Firebase UID yet. Before creating a new
                    # one, check whether the (Firebase-verified) email is already
                    # registered — if so, link this sign-in identity to that
                    # account instead of inserting a duplicate email (which would
                    # violate the UNIQUE constraint on users.email).
                    existing_email = User.query.filter_by(email=user_data['email']).first()
                    if existing_email:
                        existing_email.firebase_uid = user_data['uid']
                        if user_data.get('has_google_provider'):
                            existing_email.auth_method = 'google'
                            if not existing_email.profile_picture:
                                existing_email.profile_picture = user_data.get('photoURL')
                        user = existing_email
                    elif user_data.get('has_google_provider'):
                        user = User.create_google_user(
                            firebase_uid=user_data['uid'],
                            email=user_data['email'],
                            full_name=user_data['name'],
                            profile_picture=user_data.get('photoURL'),
                        )
                    else:
                        user = User.create_firebase_password_user(
                            firebase_uid=user_data['uid'],
                            email=user_data['email'],
                            full_name=user_data['name'] or None,
                        )
                
                # Update last login
                user.last_login = datetime.utcnow()
                _apply_configured_admin_role(user)
                db.session.commit()

                # Login user with Flask-Login
                login_user(user, remember=True)

                return jsonify({
                    'success': True,
                    'message': 'Login successful!',
                    'user': user.to_dict()
                })

            elif auth_type == 'custom':
                # Custom email/password authentication
                email = data.get('email')
                password = data.get('password')
                
                if not email or not password:
                    return jsonify({'error': 'Email and password are required'}), 400
                
                # Find user by email
                user = User.query.filter_by(email=email, auth_method='custom').first()
                
                if not user or not user.check_password(password):
                    return jsonify({'error': 'Invalid email or password'}), 401
                
                if not user.is_active:
                    return jsonify({'error': 'Account is deactivated'}), 401
                
                # Update last login
                user.last_login = datetime.utcnow()
                _apply_configured_admin_role(user)
                db.session.commit()

                # Login user with Flask-Login
                login_user(user, remember=True)

                return jsonify({
                    'success': True,
                    'message': 'Login successful!',
                    'user': user.to_dict()
                })

            else:
                return jsonify({'error': 'Invalid authentication type'}), 400
                
        except Exception as e:
            return jsonify({'error': f'Authentication failed: {str(e)}'}), 500
    
    return render_template("login.html", firebase_config=FIREBASE_CONFIG)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            logger.debug("Registration POST received (keys=%s)", list(data.keys()))
            auth_type = data.get('authType', 'firebase')  # 'firebase' or 'custom'
            logger.debug("Registration auth_type=%s", auth_type)
            
            if auth_type == 'firebase':
                id_token = data.get('idToken')
                fullname = data.get('fullname', '')
                preferred_username = (data.get('username') or '').strip()
                
                if not id_token:
                    return jsonify({'error': 'No ID token provided'}), 400
                
                user_data = verify_firebase_token(id_token)
                
                if not user_data:
                    return jsonify({'error': 'Invalid token'}), 401
                
                existing_user = User.query.filter_by(firebase_uid=user_data['uid']).first()
                if existing_user:
                    return jsonify({'error': 'An account with this sign-in method already exists.'}), 400
                
                existing_email = User.query.filter_by(email=user_data['email']).first()
                if existing_email:
                    return jsonify({'error': 'Email already registered. Please log in instead.'}), 400
                
                display = user_data['name'] or fullname
                if user_data.get('has_google_provider'):
                    user = User.create_google_user(
                        firebase_uid=user_data['uid'],
                        email=user_data['email'],
                        full_name=display,
                        profile_picture=user_data.get('photoURL'),
                    )
                else:
                    user = User.create_firebase_password_user(
                        firebase_uid=user_data['uid'],
                        email=user_data['email'],
                        full_name=display or None,
                        username=preferred_username or None,
                    )
                
                login_user(user, remember=True)
                
                return jsonify({
                    'success': True,
                    'message': 'Registration successful!',
                    'user': user.to_dict()
                })
                
            elif auth_type == 'custom':
                # Custom email/password registration
                username = data.get('username')
                email = data.get('email')
                password = data.get('password')
                fullname = data.get('fullname', '')
                
                logger.debug("Custom registration attempt username=%s email=%s", username, email)
                
                if not all([username, email, password]):
                    logger.debug("Registration rejected: missing username/email/password flags")
                    return jsonify({'error': 'Username, email, and password are required'}), 400
                
                # Check if username already exists
                existing_username = User.query.filter_by(username=username).first()
                if existing_username:
                    logger.debug("Registration rejected: username taken username=%s", username)
                    return jsonify({'error': 'Username already exists'}), 400
                
                # Check if email already exists
                existing_email = User.query.filter_by(email=email).first()
                if existing_email:
                    logger.debug("Registration rejected: email already registered")
                    return jsonify({'error': 'Email already registered'}), 400
                
                logger.debug("Creating custom user username=%s", username)
                
                # Create new custom user
                user = User.create_custom_user(
                    username=username,
                    email=email,
                    password=password,
                    full_name=fullname
                )
                
                logger.info("User registered: id=%s username=%s", user.id, user.username)
                
                # Login user with Flask-Login
                login_user(user, remember=True)
                
                return jsonify({
                    'success': True,
                    'message': 'Registration successful!',
                    'user': user.to_dict()
                })
            
            else:
                return jsonify({'error': 'Invalid authentication type'}), 400
                
        except Exception as e:
            logger.exception("Registration failed: %s", e)
            return jsonify({'error': f'Registration failed: {str(e)}'}), 500
    
    return render_template("register.html", firebase_config=FIREBASE_CONFIG)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("index.html", username=current_user.username)

@app.route('/home')
@login_required
def home():
    return render_template("home.html", username=current_user.username)

@app.route('/test-ai')
@login_required
def test_ai():
    """Test route to check AI API connection"""
    
    try:
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": "Hello, are you working?"}]
                }
            ]
        }

        api_url = f"{GEMINI_API_BASE}/{GEMINI_MODEL}:generateContent"
        print("Testing Gemini API connection...")
        response = requests.post(api_url, json=payload, headers=GEMINI_HEADERS, timeout=10)
        
        return jsonify({
            'status': response.status_code,
            'response': response.text[:500] if response.text else 'No response text',
            'headers': dict(response.headers)
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'type': type(e).__name__
        })

def _get_owned_conversation(conversation_id):
    """Return the conversation if it exists and belongs to the current user, else None."""
    conversation = Conversation.query.get(conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        return None
    return conversation


@app.route('/conversations', methods=['GET'])
@login_required
def list_conversations():
    """List the current user's conversations for the sidebar (most recent first)."""
    conversations = (
        Conversation.query
        .filter_by(user_id=current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return jsonify({'conversations': [c.to_dict() for c in conversations]})


@app.route('/conversations', methods=['POST'])
@login_required
def create_conversation():
    """Create a new (empty) conversation and return it."""
    conversation = Conversation(user_id=current_user.id, title='New Chat')
    db.session.add(conversation)
    db.session.commit()
    return jsonify({'conversation': conversation.to_dict()}), 201


@app.route('/conversations/<int:conversation_id>', methods=['GET'])
@login_required
def get_conversation(conversation_id):
    """Return a single conversation with all of its messages."""
    conversation = _get_owned_conversation(conversation_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    return jsonify({'conversation': conversation.to_dict(include_messages=True)})


@app.route('/conversations/<int:conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """Delete a conversation (and its messages via cascade)."""
    conversation = _get_owned_conversation(conversation_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/ask', methods=['POST'])
@login_required
def ask():

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        prompt = data.get('prompt', '')

        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400

        # Resolve the conversation: use the one provided (if owned) or start a new one.
        conversation = None
        conversation_id = data.get('conversation_id')
        if conversation_id:
            conversation = _get_owned_conversation(conversation_id)
            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404
        if conversation is None:
            conversation = Conversation(user_id=current_user.id, title='New Chat')
            db.session.add(conversation)
            db.session.flush()  # assign an id without committing yet

        print(f"User {current_user.username} asked: {prompt}")

        # Build the request contents from prior messages so the AI has context,
        # then append the new prompt. (Cap history to keep the payload reasonable.)
        HISTORY_LIMIT = 20
        contents = []
        for m in conversation.messages[-HISTORY_LIMIT:]:
            contents.append({
                "role": "model" if m.role == "ai" else "user",
                "parts": [{"text": m.content}],
            })
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        # Retrieval-Augmented Generation: pull relevant passages from the medical
        # reference book and ground the model's answer in them. Degrades silently
        # to a normal (non-grounded) answer if the index/embeddings are unavailable.
        base_instruction = (
            "You are a helpful AI Health Assistant. Provide accurate, helpful health "
            "information and advice. Always remind users to consult with healthcare "
            "professionals for serious medical concerns. If user ask other question "
            "except medical question, say that you don't know. Use five sentences "
            "maximum and keep the answer concise."
        )
        rag_context = rag.build_context(prompt)
        if rag_context:
            instruction_text = (
                base_instruction
                + "\n\nUse the following context from a trusted medical reference to "
                "inform your answer when relevant. If the context does not help, rely "
                "on your general medical knowledge.\n\nContext:\n" + rag_context
            )
            print(f"RAG: grounded answer using retrieved medical context ({len(rag_context)} chars)")
        else:
            instruction_text = base_instruction

        # Prepare the payload for the Gemini API
        payload = {
            "systemInstruction": {
                "parts": [{"text": instruction_text}]
            },
            "contents": contents
        }

        print(f"Sending request to AI API...")
        
        api_url = f"{GEMINI_API_BASE}/{GEMINI_MODEL}:generateContent"
        response = requests.post(api_url, json=payload, headers=GEMINI_HEADERS, timeout=30)
        
        print(f"API Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"API Error Response: {response.text}")
            return jsonify({'error': f'AI service error: {response.status_code}'}), 503
        
        ai_data = response.json()
        print(f"API Response Data: {ai_data}")
        
        # Check if response has expected structure
        if "candidates" not in ai_data or not ai_data["candidates"]:
            print(f"Unexpected API response structure: {ai_data}")
            return jsonify({'error': 'AI service returned unexpected response format'}), 500

        reply = ai_data["candidates"][0]["content"]["parts"][0]["text"]
        print(f"AI Reply: {reply[:100]}...")

        # Persist the exchange. Title the conversation from its first user message.
        is_first_message = len(conversation.messages) == 0
        db.session.add(Message(conversation_id=conversation.id, role='user', content=prompt))
        db.session.add(Message(conversation_id=conversation.id, role='ai', content=reply))
        if is_first_message:
            title = ' '.join(prompt.split())[:60]
            conversation.title = title + ('...' if len(prompt) > 60 else '')
        conversation.updated_at = datetime.utcnow()  # bump so it sorts to top of the sidebar
        db.session.commit()

        return jsonify({
            "reply": reply,
            "conversation_id": conversation.id,
            "title": conversation.title,
        })

    except requests.exceptions.Timeout:
        print("API request timed out")
        return jsonify({'error': 'AI service request timed out. Please try again.'}), 503
    except requests.exceptions.ConnectionError:
        print("API connection error")
        return jsonify({'error': 'Cannot connect to AI service. Please check your internet connection.'}), 503
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return jsonify({'error': f'AI service error: {str(e)}'}), 503
    except KeyError as e:
        print(f"Unexpected API response format: {e}")
        return jsonify({'error': 'AI service returned unexpected response format'}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/predict-diseases')
@login_required
def predict_diseases():
    """Route to display the disease prediction page"""
    return render_template("predit.html", username=current_user.username)

@app.route('/predict-heart')
@login_required
def predict_heart():
    """Route for heart disease prediction"""
    return render_template("preditHeart.html", username=current_user.username)

@app.route('/predict-diabetes')
@login_required
def predict_diabetes():
    """Route for diabetes prediction"""
    return render_template("preditDiabetes.html", username=current_user.username)

@app.route('/predict-parkinsons')
@login_required
def predict_parkinsons():
    """Route for Parkinson's disease prediction"""
    return render_template("preditParkinsons.html", username=current_user.username)

@app.route('/symptoms-check')
@login_required
def symptoms_check():
    """Route for symptom check page"""
    return render_template("symptomsCheck.html", username=current_user.username)

@app.route('/check-symptoms', methods=['POST'])
@login_required
def check_symptoms():
    """Route to handle symptom checking using external API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract form data
        age = data.get('age')
        gender = data.get('gender')
        main_symptoms = data.get('mainSymptoms')
        onset_time = data.get('onsetTime')
        severity = data.get('severity')
        medical_history = data.get('medicalHistory', '')
        additional_info = data.get('additionalInfo', '')
        
        # Validate required fields
        if not all([age, gender, main_symptoms, onset_time, severity]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Build comprehensive description for the API
        description_parts = [
            f"Patient: {age}-year-old {gender}",
            f"Main symptoms: {main_symptoms}",
            f"Symptoms started: {onset_time}",
            f"Severity: {severity}"
        ]
        
        if medical_history:
            description_parts.append(f"Medical history: {medical_history}")
        
        if additional_info:
            description_parts.append(f"Additional information: {additional_info}")
        
        # Create comprehensive description (200-2000 characters as recommended)
        description = ". ".join(description_parts) + "."
        
        # Ensure description is within recommended length
        if len(description) > 2000:
            description = description[:1997] + "..."
        
        # Prepare API request payload (using the same structure as symptomCheck.py)
        import uuid
        myuuid = str(uuid.uuid4())
        
        api_url = get_env_value('DUrl')
        DapiKey = strip_key_prefix(get_env_value('DapiKey'), 'Ocp-Apim-Subscription-Key-')
        headers = {
            "Ocp-Apim-Subscription-Key": DapiKey,
            "Content-Type": "application/json"
        }
        
        if not api_url:
            return jsonify({'error': 'Symptom analysis API URL is not configured'}), 500
        if not DapiKey:
            return jsonify({'error': 'Symptom analysis API key is not configured'}), 500
        
        payload = {
            "description": description,
            "lang": "en",
            "myuuid": myuuid,
            "model": "gpt4o",
            "response_mode": "direct",
            "timezone": "America/New_York"
        }
        
        # Make API request
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            api_data = response.json()
            
            if "data" in api_data and api_data["data"]:
                # Format the response for the frontend
                diagnoses = []
                for item in api_data["data"]:
                    diagnoses.append({
                        "diagnosis": item.get('diagnosis', 'Unknown'),
                        "description": item.get('description', 'No description available'),
                    })
                
                return jsonify({
                    "success": True,
                    "diagnoses": diagnoses,
                    "total_found": len(diagnoses)
                })
            else:
                return jsonify({
                    "success": True,
                    "diagnoses": [],
                    "message": "No specific diagnoses found based on the provided symptoms."
                })
        else:
            print(f"Symptom check API error: {response.status_code} - {response.text}")
            return jsonify({'error': 'External symptom analysis service is currently unavailable'}), 503
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Symptom analysis request timed out. Please try again.'}), 503
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Cannot connect to symptom analysis service. Please check your internet connection.'}), 503
    except Exception as e:
        print(f"Error in symptom checking: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An error occurred during symptom analysis. Please try again.'}), 500

@app.route('/doctors')
@login_required
def doctors():
    """Route for doctors page"""
    # Fetch all doctors from database
    doctors = Doctor.query.all()
    return render_template("Doctors.html", username=current_user.username, doctors=doctors)

@app.route('/predict-heart-disease', methods=['POST'])
@login_required
def predict_heart_disease():
    """Route to handle heart disease prediction"""
    try:
        if not ML_MODELS['heart']:
            return jsonify({'error': 'Heart disease prediction model is not available'}), 503
        
        # Get form data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract and validate input parameters
        required_fields = ['age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg', 
                          'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal']
        
        # Check if all required fields are present
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Convert to numpy array in the correct order
        try:
            input_data = np.array([
                float(data['age']),
                float(data['sex']),
                float(data['cp']),
                float(data['trestbps']),
                float(data['chol']),
                float(data['fbs']),
                float(data['restecg']),
                float(data['thalach']),
                float(data['exang']),
                float(data['oldpeak']),
                float(data['slope']),
                float(data['ca']),
                float(data['thal'])
            ]).reshape(1, -1)
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid input data: {str(e)}'}), 400
        
        # Make prediction
        prediction = ML_MODELS['heart'].predict(input_data)[0]
        
        # Get prediction probability if available
        confidence = None
        try:
            if hasattr(ML_MODELS['heart'], 'predict_proba'):
                probabilities = ML_MODELS['heart'].predict_proba(input_data)[0]
                confidence = round(max(probabilities) * 100, 2)
        except Exception as e:
            logger.debug("Heart model predict_proba skipped: %s", e, exc_info=True)
        
        # Prepare response
        result = {
            'prediction': int(prediction),
            'confidence': confidence,
            'message': 'Heart disease risk detected' if prediction == 1 else 'Low heart disease risk'
        }
        
        logger.debug("Heart prediction user_id=%s prediction=%s confidence=%s", current_user.id, result['prediction'], confidence)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in heart disease prediction: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An error occurred during prediction. Please try again.'}), 500

@app.route('/predict-diabetes-disease', methods=['POST'])
@login_required
def predict_diabetes_disease():
    """Route to handle diabetes prediction"""
    try:
        if not ML_MODELS['diabetes']:
            return jsonify({'error': 'Diabetes prediction model is not available'}), 503
        
        # Get form data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract and validate input parameters for diabetes
        required_fields = ['pregnancies', 'glucose', 'bloodpressure', 'skinthickness', 
                          'insulin', 'bmi', 'diabetespedigreefunction', 'age']
        
        # Check if all required fields are present
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Convert to numpy array in the correct order (matching the diabetes dataset)
        try:
            input_data = np.array([
                float(data['pregnancies']),
                float(data['glucose']),
                float(data['bloodpressure']),
                float(data['skinthickness']),
                float(data['insulin']),
                float(data['bmi']),
                float(data['diabetespedigreefunction']),
                float(data['age'])
            ]).reshape(1, -1)
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid input data: {str(e)}'}), 400
        
        # Make prediction
        prediction = ML_MODELS['diabetes'].predict(input_data)[0]
        
        # Get prediction probability if available
        confidence = None
        try:
            if hasattr(ML_MODELS['diabetes'], 'predict_proba'):
                probabilities = ML_MODELS['diabetes'].predict_proba(input_data)[0]
                confidence = round(max(probabilities) * 100, 2)
        except Exception as e:
            logger.debug("Diabetes model predict_proba skipped: %s", e, exc_info=True)
        
        # Prepare response
        result = {
            'prediction': int(prediction),
            'confidence': confidence,
            'message': 'Diabetes risk detected' if prediction == 1 else 'Low diabetes risk'
        }
        
        logger.debug("Diabetes prediction user_id=%s prediction=%s confidence=%s", current_user.id, result['prediction'], confidence)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in diabetes prediction: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An error occurred during prediction. Please try again.'}), 500

@app.route('/predict-parkinsons-disease', methods=['POST'])
@login_required
def predict_parkinsons_disease():
    """Route to handle Parkinson's disease prediction"""
    try:
        if not ML_MODELS['parkinsons']:
            return jsonify({'error': 'Parkinson\'s disease prediction model is not available'}), 503
        
        # Get form data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Extract and validate input parameters for Parkinson's (matching preditEg.py)
        required_fields = ['fo', 'fhi', 'flo', 'Jitter_percent', 'Jitter_Abs', 
                          'RAP', 'PPQ', 'DDP', 'Shimmer', 'Shimmer_dB', 'APQ3', 'APQ5', 
                          'APQ', 'DDA', 'NHR', 'HNR', 'RPDE', 'DFA', 
                          'spread1', 'spread2', 'D2', 'PPE']
        
        # Check if all required fields are present
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Convert to numpy array in the correct order (matching preditEg.py)
        try:
            input_data = np.array([
                float(data['fo']),
                float(data['fhi']),
                float(data['flo']),
                float(data['Jitter_percent']),
                float(data['Jitter_Abs']),
                float(data['RAP']),
                float(data['PPQ']),
                float(data['DDP']),
                float(data['Shimmer']),
                float(data['Shimmer_dB']),
                float(data['APQ3']),
                float(data['APQ5']),
                float(data['APQ']),
                float(data['DDA']),
                float(data['NHR']),
                float(data['HNR']),
                float(data['RPDE']),
                float(data['DFA']),
                float(data['spread1']),
                float(data['spread2']),
                float(data['D2']),
                float(data['PPE'])
            ]).reshape(1, -1)
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid input data: {str(e)}'}), 400
        
        # Make prediction
        prediction = ML_MODELS['parkinsons'].predict(input_data)[0]
        
        # Get prediction probability if available
        confidence = None
        try:
            if hasattr(ML_MODELS['parkinsons'], 'predict_proba'):
                probabilities = ML_MODELS['parkinsons'].predict_proba(input_data)[0]
                confidence = round(max(probabilities) * 100, 2)
        except Exception as e:
            logger.debug("Parkinsons model predict_proba skipped: %s", e, exc_info=True)
        
        # Prepare response
        result = {
            'prediction': int(prediction),
            'confidence': confidence,
            'message': 'Parkinson\'s disease risk detected' if prediction == 1 else 'Low Parkinson\'s disease risk'
        }
        
        logger.debug("Parkinsons prediction user_id=%s prediction=%s confidence=%s", current_user.id, result['prediction'], confidence)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in Parkinson's disease prediction: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An error occurred during prediction. Please try again.'}), 500

@app.route('/view-profile')
@login_required
def view_profile():
    """Route to display user profile page"""
    # Load user's medical info if available
    medical = MedicalInfofuser.query.filter_by(user_id=current_user.id).first()
    logger.debug(
        "view_profile: user_id=%s medical_record_id=%s",
        current_user.id,
        medical.id if medical else None,
    )
    return render_template("viewProfile.html", user=current_user, medical=medical, username=current_user.username)

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Route to handle profile updates"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get current user
        user = current_user
        
        # Validate and update username
        if 'username' in data and data['username']:
            new_username = data['username'].strip()
            if len(new_username) < 3:
                return jsonify({'error': 'Username must be at least 3 characters'}), 400
            
            # Check if username is already taken by another user
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Username already taken'}), 400
            
            user.username = new_username
        
        # Update email (only for custom accounts)
        if 'email' in data and user.auth_method not in ('google', 'firebase'):
            new_email = data['email'].strip()
            if not new_email or '@' not in new_email:
                return jsonify({'error': 'Invalid email address'}), 400
            
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Email already registered'}), 400
            
            user.email = new_email
        
        # Update other profile fields
        if 'full_name' in data:
            user.full_name = data['full_name'].strip() if data['full_name'] else None
        
        if 'phone_number' in data:
            user.phone_number = data['phone_number'].strip() if data['phone_number'] else None
        
        if 'date_of_birth' in data and data['date_of_birth']:
            try:
                from datetime import datetime
                user.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format'}), 400
        
        # Update password (only for custom accounts)
        if 'password' in data and data['password'] and user.auth_method not in ('google', 'firebase'):
            password = data['password']
            confirm_password = data.get('confirm_password', '')
            
            if len(password) < 8:
                return jsonify({'error': 'Password must be at least 8 characters'}), 400
            
            if password != confirm_password:
                return jsonify({'error': 'Passwords do not match'}), 400
            
            # Check password strength
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            
            if not (has_upper and has_lower and has_digit):
                return jsonify({'error': 'Password must contain uppercase, lowercase, and number'}), 400
            
            user.set_password(password)
        
        # Save changes to database
        db.session.commit()
        
        print(f"Profile updated for user {user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        })
        
    except Exception as e:
        print(f"Error updating profile: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'error': 'An error occurred while updating profile'}), 500

@app.route('/upload-profile-picture', methods=['POST'])
@login_required
def upload_profile_picture():
    """Upload or replace the current user's profile picture."""
    try:
        if 'profile_picture' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['profile_picture']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return jsonify({'error': 'Invalid file type. Use PNG, JPG, GIF, or WEBP.'}), 400

        # Validate size without trusting the client-declared length.
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_PROFILE_PIC_BYTES:
            return jsonify({'error': 'File too large. Maximum size is 5 MB.'}), 400

        filename = f"user_{current_user.id}_{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(app.config['PROFILE_PIC_FOLDER'], filename))

        old_picture = current_user.profile_picture
        new_url = url_for('static', filename=f'uploads/profile_pictures/{filename}')
        current_user.profile_picture = new_url
        db.session.commit()

        # Clean up the previous file, but only if it was one we stored locally
        # (never touch external URLs such as Google-hosted avatars).
        if old_picture and '/static/uploads/profile_pictures/' in old_picture:
            old_path = os.path.join(_app_root, old_picture.lstrip('/'))
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
            except OSError:
                pass

        return jsonify({
            'success': True,
            'message': 'Profile picture updated',
            'profile_picture': new_url,
        })

    except Exception as e:
        print(f"Error uploading profile picture: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'error': 'An error occurred while uploading the picture'}), 500

@app.route('/update-medical-info', methods=['POST'])
@login_required
def update_medical_info():
    """Route to handle medical info update"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get current user
        user = current_user
        
        # Update medical info in database
        medical = MedicalInfofuser.query.filter_by(user_id=user.id).first()
    
        if not medical:
            logger.debug("Creating medical record for user_id=%s", user.id)
            medical = MedicalInfofuser(user_id=user.id)
            db.session.add(medical)
            db.session.flush()  # Flush to get the ID
        else:
            logger.debug("Updating medical record id=%s user_id=%s", medical.id, user.id)
            # Don't add existing record to session - it's already tracked
        # Update fields
        if 'full_name' in data:
            medical.full_name = data['full_name'].strip() if data['full_name'] else None
        if 'date_of_birth' in data:
            dob_str = (data['date_of_birth'] or '').strip()
            if dob_str:
                try:
                    from datetime import datetime
                    # Expecting YYYY-MM-DD from <input type="date">
                    medical.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Invalid date_of_birth format. Use YYYY-MM-DD'}), 400
            else:
                medical.date_of_birth = None
        if 'gender' in data:
            medical.gender = data['gender'].strip() if data['gender'] else None
        if 'phone_number' in data:
            medical.phone_number = data['phone_number'].strip() if data['phone_number'] else None
        if 'symptoms' in data:
            medical.symptoms = data['symptoms'].strip() if data['symptoms'] else None
        if 'started_time' in data:
            started_str = (data['started_time'] or '').strip()
            if started_str:
                try:
                    from datetime import datetime
                    # Expecting YYYY-MM-DDTHH:MM from <input type="datetime-local">
                    medical.started_time = datetime.strptime(started_str, '%Y-%m-%dT%H:%M')
                except ValueError:
                    # Try fallback without minutes/with seconds
                    try:
                        import datetime as _dt
                        medical.started_time = _dt.datetime.fromisoformat(started_str)
                    except Exception:
                        return jsonify({'error': 'Invalid started_time format. Use YYYY-MM-DDTHH:MM'}), 400
            else:
                medical.started_time = None
        if 'current_medication' in data:
            medical.current_medication = data['current_medication'].strip() if data['current_medication'] else None
        if 'allergies' in data:
            medical.allergies = data['allergies'].strip() if data['allergies'] else None
            
        db.session.commit()     
        
        print(f"Medical info updated for user {user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Medical info updated successfully',
            'medical': medical.to_dict()
        })
        
    except Exception as e:
        print(f"Error updating medical info: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        # Return detailed error to help with debugging on frontend
        return jsonify({'error': f'Update failed: {str(e)}'}), 500
@app.route('/delete-profile', methods=['DELETE'])
@login_required
def delete_profile():
    """Route to handle profile deletion"""
    try:
        user_id = current_user.id
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        username = user.username

        # Delete user from database using the mapped SQLAlchemy instance
        db.session.delete(user)
        db.session.commit()

        # End session after successful deletion
        logout_user()
        
        print(f"Profile deleted for user {username}")
        
        return jsonify({
            'success': True,
            'message': 'Account deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting profile: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'error': 'An error occurred while deleting account'}), 500

@app.route('/appointment')
@login_required
def appointment():
    # Get doctor_id from query parameters if provided
    doctor_id = request.args.get('doctor_id')
    doctor = None
    
    if doctor_id:
        doctor = Doctor.query.get(doctor_id)
    
    # Get all appointments for the current user
    appointments = Appointment.query.filter_by(user_id=current_user.id).all()
    
    # Get today's date for date picker minimum
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Calculate max date (6 months from today)
    from datetime import timedelta
    max_date = (datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d')
    
    return render_template("appointment.html", 
                         username=current_user.username, 
                         doctor=doctor,
                         appointments=appointments,
                         today=today,
                         max_date=max_date)

@app.route('/appointments', methods=['POST'])
@login_required
def create_appointment():
    """Create a new appointment"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('doctor_id') or not data.get('appointment_date') or not data.get('appointment_time'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Validate doctor exists
        doctor = Doctor.query.get(data['doctor_id'])
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        # Parse date and time
        appointment_date = datetime.strptime(data['appointment_date'], '%Y-%m-%d').date()
        appointment_time = datetime.strptime(data['appointment_time'], '%H:%M').time()
        
        # Check for conflicting appointments (same doctor, date, and time)
        existing_appointment = Appointment.query.filter_by(
            doctor_id=data['doctor_id'],
            appointment_date=appointment_date,
            appointment_time=appointment_time
        ).filter(Appointment.status != 'Cancelled').first()
        
        if existing_appointment:
            return jsonify({'error': 'This time slot is already booked. Please choose another time.'}), 400
        
        # Create new appointment
        appointment = Appointment(
            doctor_id=data['doctor_id'],
            user_id=current_user.id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status='Scheduled'
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        return jsonify({'message': 'Appointment booked successfully', 'appointment_id': appointment.id}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500




if __name__ == '__main__':
    port = int(get_env_value('PORT', '8080'))
    app.run(host="0.0.0.0", port=port, debug=DEBUG_MODE)