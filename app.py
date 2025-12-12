from flask import Flask, render_template, request, redirect, url_for, Response
from models import db, Subject, Assignment, Event, Note, AttendanceLog, Settings
from datetime import datetime, date, timedelta
import calendar as cal_module
import re
import random
import csv
import io
from collections import Counter

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///planner.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    if not Settings.query.first():
        db.session.add(Settings(student_name="Future Coder", university="CodeChef Univ"))
        db.session.commit()

@app.route('/')
def dashboard():
    subjects = Subject.query.all()
    
    # 1. Assignments Logic
    pending_assignments = Assignment.query.filter(
        Assignment.due_date >= date.today(),
        Assignment.status == 'Pending'
    ).order_by(Assignment.is_exam.desc(), Assignment.due_date).all()
    
    completed_assignments = Assignment.query.filter_by(status='Done').order_by(Assignment.due_date.desc()).all()
    exams = [a for a in pending_assignments if a.is_exam]
    notes = Note.query.all()
    settings = Settings.query.first()
    
    # 2. WORKLOAD HEATMAP LOGIC (Problem 3)
    # Count assignments per due date
    all_dates = [task.due_date for task in pending_assignments]
    date_counts = Counter(all_dates)
    
    # Filter days with >= 3 tasks (Bottlenecks)
    bottlenecks = []
    for d, count in date_counts.items():
        if count >= 3:
            bottlenecks.append({'date': d, 'count': count})
    
    # Sort by date
    bottlenecks.sort(key=lambda x: x['date'])

    # Quotes
    quotes = [
        "The code you write today is the documentation for tomorrow.",
        "First, solve the problem. Then, write the code.",
        "Talk is cheap. Show me the code."
    ]
    daily_quote = random.choice(quotes)

    return render_template('dashboard.html', 
                           subjects=subjects, 
                           assignments=pending_assignments, 
                           completed_assignments=completed_assignments,
                           exams=exams, 
                           notes=notes,
                           today=date.today(),
                           quote=daily_quote,
                           settings=settings,
                           bottlenecks=bottlenecks) # Pass bottlenecks to template

# --- NEW: HOLIDAY PLANNER LOGIC (Problem 1) ---
@app.route('/forecast', methods=['POST'])
def forecast_attendance():
    start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
    end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
    
    subjects = Subject.query.all()
    alerts = []
    
    # Helper to map day names to integers (0=Mon, 6=Sun)
    day_map = {'MON': 0, 'TUE': 1, 'WED': 2, 'THU': 3, 'FRI': 4, 'SAT': 5, 'SUN': 6}
    
    # Iterate through every day in the holiday range
    delta = end_date - start_date
    for i in range(delta.days + 1):
        current_day = start_date + timedelta(days=i)
        current_weekday = current_day.weekday() # 0-6
        
        # Check every subject to see if it has a class on this day
        for sub in subjects:
            if sub.schedule:
                # Schedule string: "Mon 9AM, Wed 2PM"
                # Normalize to uppercase and check if day matches
                schedule_parts = sub.schedule.upper().split(',')
                for part in schedule_parts:
                    # Check if any day abbreviation matches current weekday
                    for day_name, day_idx in day_map.items():
                        if day_name in part and day_idx == current_weekday:
                            # We found a class that will be missed!
                            # Temporarily increment total_classes (simulate missing it)
                            # Note: We do NOT increment 'attended'
                            sub.total_classes += 1
    
    # Calculate Impact
    for sub in subjects:
        # Check if the simulated attendance drops below 75%
        if sub.attendance_percentage < 75:
            alerts.append({
                'code': sub.code,
                'name': sub.name,
                'new_percent': sub.attendance_percentage
            })
    
    # IMPORTANT: Rollback changes so we don't actually save this simulation to DB
    db.session.rollback()
    
    return render_template('forecast_result.html', alerts=alerts, start=start_date, end=end_date)

# --- EXISTING ROUTES (No Changes) ---
@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query: return redirect(url_for('dashboard'))
    found_subjects = Subject.query.filter(Subject.name.contains(query) | Subject.code.contains(query)).all()
    found_tasks = Assignment.query.filter(Assignment.title.contains(query)).all()
    found_notes = Note.query.filter(Note.content.contains(query)).all()
    return render_template('search_results.html', query=query, subjects=found_subjects, tasks=found_tasks, notes=found_notes)

@app.route('/history/<int:subject_id>')
def attendance_history(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    logs = AttendanceLog.query.filter_by(subject_id=subject_id).order_by(AttendanceLog.date.desc()).all()
    return render_template('attendance_history.html', subject=subject, logs=logs)

@app.route('/update_attendance/<int:subject_id>/<action>')
def update_attendance(subject_id, action):
    subject = Subject.query.get_or_404(subject_id)
    if action == 'present':
        subject.attended += 1
        subject.total_classes += 1
        db.session.add(AttendanceLog(subject_id=subject.id, status='Present', date=date.today()))
    elif action == 'absent':
        subject.total_classes += 1
        db.session.add(AttendanceLog(subject_id=subject.id, status='Absent', date=date.today()))
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/export_data')
def export_data():
    subjects = Subject.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Subject Code', 'Name', 'Attended', 'Total Classes', 'Percentage', 'Bunk Status'])
    for sub in subjects:
        writer.writerow([sub.code, sub.name, sub.attended, sub.total_classes, f"{sub.attendance_percentage}%", sub.bunk_status])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=my_academic_report.csv"})

@app.route('/update_profile', methods=['POST'])
def update_profile():
    settings = Settings.query.first()
    settings.student_name = request.form.get('student_name')
    settings.university = request.form.get('university')
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/update_resources/<int:id>', methods=['POST'])
def update_resources(id):
    subject = Subject.query.get_or_404(id)
    subject.syllabus_link = request.form.get('syllabus_link')
    subject.zoom_link = request.form.get('zoom_link')
    subject.professor_email = request.form.get('professor_email')
    subject.notes = request.form.get('notes')
    try:
        subject.total_modules = int(request.form.get('total_modules'))
        subject.completed_student = float(request.form.get('completed_student'))
        subject.completed_teacher = float(request.form.get('completed_teacher'))
    except: pass
    db.session.commit()
    return redirect(url_for('subject_details', id=id))

@app.route('/mark_done/<int:id>')
def mark_done(id):
    task = Assignment.query.get_or_404(id)
    task.status = 'Done'
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/add_note', methods=['POST'])
def add_note():
    if request.form.get('content'):
        db.session.add(Note(content=request.form.get('content')))
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_note/<int:id>')
def delete_note(id):
    note = Note.query.get_or_404(id)
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/calendar')
@app.route('/calendar/<int:year>/<int:month>')
def calendar_view(year=None, month=None):
    if year is None: now = datetime.now(); year, month = now.year, now.month
    cal = cal_module.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(year, month)
    db_events = Event.query.all()
    db_assignments = Assignment.query.filter_by(status='Pending').all()
    events_by_date = {}
    for e in db_events:
        d_str = e.date.strftime('%Y-%m-%d')
        if d_str not in events_by_date: events_by_date[d_str] = []
        events_by_date[d_str].append({'title': e.title, 'tag': e.tag, 'is_assignment': False, 'id': e.id})
    for a in db_assignments:
        d_str = a.due_date.strftime('%Y-%m-%d')
        if d_str not in events_by_date: events_by_date[d_str] = []
        tag = 'danger' if a.is_exam else 'warning'
        events_by_date[d_str].append({'title': f"{a.subject.code}: {a.title}", 'tag': tag, 'is_assignment': True, 'id': a.id})
    prev_month = month - 1 if month > 1 else 12; prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1; next_year = year if month < 12 else year + 1
    return render_template('calendar.html', month_days=month_days, events_by_date=events_by_date, current_year=year, current_month=month, month_name=cal_module.month_name[month], prev_year=prev_year, prev_month=prev_month, next_year=next_year, next_month=next_month)

@app.route('/timetable')
def timetable_view():
    subjects = Subject.query.all()
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    hours = range(8, 19)
    timetable = {h: {d: None for d in days} for h in hours}
    for sub in subjects:
        if sub.schedule:
            parts = sub.schedule.split(',')
            for part in parts:
                part = part.upper().strip()
                found_day = None
                for d in days:
                    if d.upper() in part: found_day = d; break
                match = re.search(r'(\d+)', part)
                if found_day and match:
                    hour = int(match.group(1)); 
                    if 'PM' in part and hour != 12: hour += 12
                    if hour in timetable: timetable[hour][found_day] = sub
    return render_template('timetable.html', timetable=timetable, days=days, hours=hours)

@app.route('/add_event', methods=['POST'])
def add_event():
    db.session.add(Event(title=request.form.get('title'), date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(), tag=request.form.get('tag')))
    db.session.commit()
    year, month = int(request.form.get('date').split('-')[0]), int(request.form.get('date').split('-')[1])
    return redirect(url_for('calendar_view', year=year, month=month))

@app.route('/delete_event/<int:id>')
def delete_event(id):
    event = Event.query.get_or_404(id); db.session.delete(event); db.session.commit()
    return redirect(url_for('calendar_view'))

@app.route('/subject/<int:id>')
def subject_details(id):
    subject = Subject.query.get_or_404(id); return render_template('subject_details.html', subject=subject)

@app.route('/add_subject', methods=['POST'])
def add_subject():
    db.session.add(Subject(name=request.form.get('name'), code=request.form.get('code'), professor=request.form.get('prof'), schedule=request.form.get('schedule')))
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/add_assignment', methods=['POST'])
def add_assignment():
    is_exam = True if request.form.get('is_exam') else False
    db.session.add(Assignment(title=request.form.get('title'), due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date(), subject_id=request.form.get('subject_id'), is_exam=is_exam, status='Pending'))
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_subject/<int:id>')
def delete_subject(id):
    subject = Subject.query.get_or_404(id); db.session.delete(subject); db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_assignment/<int:id>')
def delete_assignment(id):
    task = Assignment.query.get_or_404(id); db.session.delete(task); db.session.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)