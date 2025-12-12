from flask import Flask, render_template, request, redirect, url_for
from models import db, Subject, Assignment
from datetime import datetime, date

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///planner.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def dashboard():
    subjects = Subject.query.all()
    upcoming_assignments = Assignment.query.filter(
        Assignment.due_date >= date.today()
    ).order_by(Assignment.due_date).all()

    return render_template('dashboard.html', subjects=subjects, assignments=upcoming_assignments, today=date.today())

@app.route('/add_subject', methods=['POST'])
def add_subject():
    name = request.form.get('name')
    code = request.form.get('code')
    prof = request.form.get('prof')
    schedule = request.form.get('schedule') # Capture schedule
    
    new_subject = Subject(name=name, code=code, professor=prof, schedule=schedule)
    db.session.add(new_subject)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_subject/<int:id>')
def delete_subject(id):
    subject = Subject.query.get_or_404(id)
    db.session.delete(subject)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_assignment/<int:id>')
def delete_assignment(id):
    task = Assignment.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/update_attendance/<int:subject_id>/<action>')
def update_attendance(subject_id, action):
    subject = Subject.query.get_or_404(subject_id)
    if action == 'present':
        subject.attended += 1
        subject.total_classes += 1
    elif action == 'absent':
        subject.total_classes += 1
    elif action == 'reset': 
        subject.attended = 0
        subject.total_classes = 0
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/add_assignment', methods=['POST'])
def add_assignment():
    subject_id = request.form.get('subject_id')
    title = request.form.get('title')
    due_date_str = request.form.get('due_date')
    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
    
    new_task = Assignment(title=title, due_date=due_date, subject_id=subject_id)
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)