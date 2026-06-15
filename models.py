from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    reminders = db.relationship('Reminder', backref='user', lazy=True)
    devices = db.relationship('Device', backref='user', lazy=True)
    notes = db.relationship('Note', backref='user', lazy=True)

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    note = db.Column(db.Text, nullable=True)
    reminder_text = db.Column(db.String(500), nullable=True)
    due = db.Column(db.DateTime, nullable=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)
    done = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    @property
    def display_text(self):
        if self.reminder_text:
            return self.reminder_text
        if self.note:
            return f'{self.title} - {self.note}'
        return self.title

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'reminder_text': self.display_text,
            'note': None,
            'due': self.due.isoformat() if self.due else None,
            'created': self.created.isoformat(),
            'done': self.done
        }

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_agent = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Device user_id={self.user_id} token={self.token[:8]}...>"

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Note id={self.id} user_id={self.user_id}>"
