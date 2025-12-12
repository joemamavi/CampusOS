from flask_sqlalchemy import SQLAlchemy
import math
from datetime import date, datetime

db = SQLAlchemy()

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    professor = db.Column(db.String(100))
    schedule = db.Column(db.String(100))
    attended = db.Column(db.Integer, default=0)
    total_classes = db.Column(db.Integer, default=0)
    syllabus_link = db.Column(db.String(500))
    zoom_link = db.Column(db.String(500))
    professor_email = db.Column(db.String(100))
    notes = db.Column(db.Text)
    total_modules = db.Column(db.Integer, default=5)
    completed_student = db.Column(db.Float, default=0.0)
    completed_teacher = db.Column(db.Float, default=0.0)
    assignments = db.relationship('Assignment', backref='subject', lazy=True, cascade="all, delete-orphan")
    attendance_logs = db.relationship('AttendanceLog', backref='subject', lazy=True, cascade="all, delete-orphan")

    @property
    def student_progress_percent(self):
        if self.total_modules == 0: return 0
        pct = (self.completed_student / self.total_modules) * 100
        return min(round(pct), 100)

    @property
    def teacher_progress_percent(self):
        if self.total_modules == 0: return 0
        pct = (self.completed_teacher / self.total_modules) * 100
        return min(round(pct), 100)

    @property
    def attendance_percentage(self):
        if self.total_classes == 0: return 100.0
        return round((self.attended / self.total_classes) * 100, 1)

    @property
    def bunk_status(self):
        if self.total_classes == 0: return "No classes yet."
        current_pct = self.attendance_percentage
        if current_pct >= 75:
            bunks_possible = math.floor((self.attended / 0.75) - self.total_classes)
            if bunks_possible > 0: return f"✅ Safe to bunk {bunks_possible}"
            else: return "⚠️ Don't miss next!"
        else:
            needed = (3 * self.total_classes) - (4 * self.attended)
            return f"🚨 Attend next {needed}!"

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    is_exam = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='Pending')
    matrix_quadrant = db.Column(db.String(10), default='q2') 
    # NEW: Color Tag (Stores values like 'emerald', 'blue', 'rose')
    color_tag = db.Column(db.String(20), default='emerald') 
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    tag = db.Column(db.String(20), default='emerald')
    description = db.Column(db.String(500))

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

class AttendanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(10), nullable=False)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), default="Student")
    university = db.Column(db.String(100), default="My University")

class CareerItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    tech_stack = db.Column(db.String(200))
    date = db.Column(db.Date, default=date.today)
    link = db.Column(db.String(500))