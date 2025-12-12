from flask_sqlalchemy import SQLAlchemy
import math

db = SQLAlchemy()

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    professor = db.Column(db.String(100))
    schedule = db.Column(db.String(100)) # New: Stores "Mon 9AM, Wed 2PM"
    attended = db.Column(db.Integer, default=0)
    total_classes = db.Column(db.Integer, default=0)
    
    assignments = db.relationship('Assignment', backref='subject', lazy=True, cascade="all, delete-orphan")

    @property
    def attendance_percentage(self):
        if self.total_classes == 0:
            return 100.0
        return round((self.attended / self.total_classes) * 100, 1)

    @property
    def bunk_status(self):
        """Calculates how many classes you can skip or must attend."""
        if self.total_classes == 0:
            return "No classes yet."
        
        current_pct = self.attendance_percentage
        
        if current_pct >= 75:
            # Formula: How many more classes (x) can I miss?
            # (Attended) / (Total + x) >= 0.75
            # x <= (Attended / 0.75) - Total
            bunks_possible = math.floor((self.attended / 0.75) - self.total_classes)
            if bunks_possible > 0:
                return f"✅ Safe to bunk {bunks_possible} classes."
            else:
                return "⚠️ Don't miss the next class!"
        else:
            # Formula: How many (x) must I attend?
            # (Attended + x) / (Total + x) >= 0.75
            # x >= 3 * Total - 4 * Attended
            needed = (3 * self.total_classes) - (4 * self.attended)
            return f"🚨 Attend next {needed} classes!"

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)