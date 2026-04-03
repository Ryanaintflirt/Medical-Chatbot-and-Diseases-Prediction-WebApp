import re
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for hybrid authentication system"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for Google-only users
    full_name = db.Column(db.String(100), nullable=True)
    
    # Authentication method tracking
    auth_method = db.Column(db.String(20), nullable=False, default='custom')  # 'custom', 'google', or 'firebase'
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True)  # Firebase UID (Google or email/password)
    
    # Account linking
    linked_accounts = db.Column(db.JSON, nullable=True)  # Store linked account info
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Profile information
    profile_picture = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Hash and set password for custom authentication"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password for custom authentication"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary for JSON responses"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'auth_method': self.auth_method,
            'firebase_uid': self.firebase_uid,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'profile_picture': self.profile_picture
        }
    
    @staticmethod
    def create_google_user(firebase_uid, email, full_name=None, profile_picture=None):
        """Create a new user from Google authentication"""
        # Generate username from email if full_name not available
        username = full_name.lower().replace(' ', '_') if full_name else email.split('@')[0]
        
        # Ensure username is unique
        original_username = username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{original_username}_{counter}"
            counter += 1
        
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            auth_method='google',
            firebase_uid=firebase_uid,
            profile_picture=profile_picture
        )
        
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def create_firebase_password_user(firebase_uid, email, full_name=None, username=None):
        """Create a user signed up with Firebase Email/Password (not Google OAuth)."""
        if username and isinstance(username, str):
            username = username.strip()
            if not re.match(r'^[a-zA-Z0-9_]{3,80}$', username):
                username = None
        if not username:
            username = (
                full_name.lower().replace(' ', '_')
                if full_name
                else email.split('@')[0]
            )
        original_username = username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{original_username}_{counter}"
            counter += 1

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            auth_method='firebase',
            firebase_uid=firebase_uid,
            profile_picture=None,
        )
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def create_custom_user(username, email, password, full_name=None):
        """Create a new user with custom authentication"""
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            auth_method='custom'
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        return user
    
    def link_google_account(self, firebase_uid, profile_picture=None):
        """Link a Google account to an existing custom user"""
        if self.auth_method == 'custom' and not self.firebase_uid:
            self.firebase_uid = firebase_uid
            if profile_picture:
                self.profile_picture = profile_picture
            db.session.commit()
            return True
        return False
    
    def unlink_google_account(self):
        """Unlink Google account from user"""
        if self.auth_method == 'custom' and self.firebase_uid:
            self.firebase_uid = None
            self.profile_picture = None
            db.session.commit()
            return True
        return False


class MedicalInfofuser(db.Model):
    """Table to store user medical information"""
    __tablename__ = 'medical_Infofuser'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    full_name = db.Column(db.String(100), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    symptoms = db.Column(db.Text, nullable=True)
    started_time = db.Column(db.DateTime, nullable=True)
    current_medication = db.Column(db.Text, nullable=True)
    allergies = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MedicalInfofuser {self.id} - {self.full_name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'full_name': self.full_name,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'phone_number': self.phone_number,
            'symptoms': self.symptoms,
            'started_time': self.started_time.isoformat() if self.started_time else None,
            'current_medication': self.current_medication,
            'allergies': self.allergies,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Doctor(db.Model):
    """Doctor model for healthcare appointments"""
    __tablename__ = 'doctor'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    specialty = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    available_days = db.Column(db.String(100), nullable=True)
    available_time = db.Column(db.String(50), nullable=True)
    years_experience = db.Column(db.Integer, nullable=True)
    qualification = db.Column(db.String(150), nullable=True)
    profile_photo = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    
    # Relationship with appointments
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)
    
    def __repr__(self):
        return f'<Doctor {self.full_name} - {self.specialty}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'specialty': self.specialty,
            'phone_number': self.phone_number,
            'email': self.email,
            'available_days': self.available_days,
            'available_time': self.available_time,
            'years_experience': self.years_experience,
            'qualification': self.qualification,
            'profile_photo': self.profile_photo,
            'bio': self.bio
        }


class Appointment(db.Model):
    """Appointment model for doctor appointments"""
    __tablename__ = 'appointment'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    medical_Infofuser_id = db.Column(db.Integer, db.ForeignKey('medical_Infofuser.id'), nullable=True)
    appointment_date = db.Column(db.Date, nullable=True)
    appointment_time = db.Column(db.Time, nullable=True)
    status = db.Column(db.String(50), nullable=True)
    
    def __repr__(self):
        return f'<Appointment {self.id} - Doctor {self.doctor_id} - User {self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'doctor_id': self.doctor_id,
            'user_id': self.user_id,
            'appointment_date': self.appointment_date.isoformat() if self.appointment_date else None,
            'appointment_time': self.appointment_time.isoformat() if self.appointment_time else None,
            'status': self.status
        }