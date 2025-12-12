from flask_sqlalchemy import SQLAlchemy
import math

db = SQLAlchemy()

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    professor = db.Column(db.String(100))
    schedule = db.Column(db.String(100))
    attended = db.Column(db.Integer, default=0)
    total_classes = db.Column(db.Integer, default=0)
    
    # Resources
    syllabus_link = db.Column(db.String(500))
    zoom_link = db.Column(db.String(500))
    professor_email = db.Column(db.String(100))
    notes = db.Column(db.Text)
    
    assignments = db.relationship('Assignment', backref='subject', lazy=True, cascade="all, delete-orphan")

    @property
    def attendance_percentage(self):
        if self.total_classes == 0:
            return 100.0
        return round((self.attended / self.total_classes) * 100, 1)

    @property
    def bunk_status(self):
        if self.total_classes == 0:
            return "No classes yet."
        current_pct = self.attendance_percentage
        if current_pct >= 75:
            bunks_possible = math.floor((self.attended / 0.75) - self.total_classes)
            if bunks_possible > 0:
                return f"✅ Safe to bunk {bunks_possible}"
            else:
                return "⚠️ Don't miss next!"
        else:
            needed = (3 * self.total_classes) - (4 * self.attended)
            return f"🚨 Attend next {needed}!"

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    is_exam = db.Column(db.Boolean, default=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

# --- NEW: Event Model for Calendar ---
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    # Tag stores the color category: 'primary' (Blue), 'danger' (Red), 'success' (Green), etc.
    tag = db.Column(db.String(20), default='primary')
    description = db.Column(db.String(500))