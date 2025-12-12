from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    professor = db.Column(db.String(100))
    attended = db.Column(db.Integer, default=0)
    total_classes = db.Column(db.Integer, default=0)
    
    # Relationship to assignments
    assignments = db.relationship('Assignment', backref='subject', lazy=True)

    @property
    def attendance_percentage(self):
        if self.total_classes == 0:
            return 100.0
        return round((self.attended / self.total_classes) * 100, 1)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)