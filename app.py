import sys
import threading
import time
import webview
from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
from models import db, Subject, Assignment, Event, Note, AttendanceLog, Settings, CareerItem
from datetime import datetime, date, timedelta
import calendar as cal_module
import re
import random
import csv
import io
from collections import Counter

# 1. INITIALIZE FLASK
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///planner.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    if not Settings.query.first():
        db.session.add(Settings(student_name="Future Coder", university="CodeChef Univ"))
        db.session.commit()

# --- ROUTES (Same as before) ---
@app.route('/')
def dashboard():
    subjects = Subject.query.all()
    pending_assignments = Assignment.query.filter(
        Assignment.due_date >= date.today(),
        Assignment.status == 'Pending'
    ).order_by(Assignment.is_exam.desc(), Assignment.due_date).all()
    completed_assignments = Assignment.query.filter_by(status='Done').order_by(Assignment.due_date.desc()).all()
    exams = [a for a in pending_assignments if a.is_exam]
    notes = Note.query.all()
    settings = Settings.query.first()
    
    all_dates = [task.due_date for task in pending_assignments]
    date_counts = Counter(all_dates)
    bottlenecks = [{'date': d, 'count': c} for d, c in date_counts.items() if c >= 3]
    bottlenecks.sort(key=lambda x: x['date'])

    today_name = date.today().strftime("%a").upper()
    today_classes = []
    for sub in subjects:
        if sub.schedule:
            parts = sub.schedule.upper().split(',')
            for part in parts:
                if today_name in part:
                    match = re.search(r'(\d+)', part)
                    if match:
                        hour = int(match.group(1))
                        if 'PM' in part and hour != 12: hour += 12
                        today_classes.append({'name': sub.code, 'time': hour})
    
    today_classes.sort(key=lambda x: x['time'])
    gaps = []
    if today_classes:
        for i in range(len(today_classes) - 1):
            current_end = today_classes[i]['time'] + 1
            next_start = today_classes[i+1]['time']
            if next_start > current_end:
                gaps.append({'start': current_end, 'end': next_start})

    quotes = ["The best way to predict your future is to create it.", "Code is poetry."]
    daily_quote = random.choice(quotes)

    return render_template('dashboard.html', 
                           subjects=subjects, assignments=pending_assignments, 
                           completed_assignments=completed_assignments, exams=exams, 
                           notes=notes, today=date.today(), quote=daily_quote, 
                           settings=settings, bottlenecks=bottlenecks, gaps=gaps)

@app.route('/career')
def career_view():
    items = CareerItem.query.order_by(CareerItem.date.desc()).all()
    return render_template('career.html', items=items)

@app.route('/add_career_item', methods=['POST'])
def add_career_item():
    item = CareerItem(title=request.form.get('title'), category=request.form.get('category'), tech_stack=request.form.get('tech_stack'), link=request.form.get('link'), date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date())
    db.session.add(item); db.session.commit()
    return redirect(url_for('career_view'))

@app.route('/delete_career_item/<int:id>')
def delete_career_item(id):
    db.session.delete(CareerItem.query.get(id)); db.session.commit()
    return redirect(url_for('career_view'))

@app.route('/add_assignment', methods=['POST'])
def add_assignment():
    is_exam = True if request.form.get('is_exam') else False
    color = request.form.get('color_tag') if request.form.get('color_tag') else 'emerald'
    db.session.add(Assignment(title=request.form.get('title'), due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date(), subject_id=request.form.get('subject_id'), is_exam=is_exam, status='Pending', color_tag=color))
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/mark_done/<int:id>')
def mark_done(id):
    task = Assignment.query.get_or_404(id); task.status = 'Done'; db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/matrix')
def matrix_view():
    tasks = Assignment.query.filter_by(status='Pending').all()
    matrix = {'q1': [t for t in tasks if t.matrix_quadrant == 'q1'], 'q2': [t for t in tasks if t.matrix_quadrant == 'q2'], 'q3': [t for t in tasks if t.matrix_quadrant == 'q3'], 'q4': [t for t in tasks if t.matrix_quadrant == 'q4']}
    return render_template('matrix.html', matrix=matrix)

@app.route('/update_quadrant/<int:id>/<string:quadrant>')
def update_quadrant(id, quadrant):
    task = Assignment.query.get_or_404(id); task.matrix_quadrant = quadrant; db.session.commit()
    return jsonify({'success': True})

@app.route('/calendar')
@app.route('/calendar/<int:year>/<int:month>')
def calendar_view(year=None, month=None):
    if year is None: now = datetime.now(); year, month = now.year, now.month
    cal = cal_module.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(year, month)
    db_events = Event.query.all()
    events_by_date = {}
    for e in db_events:
        d_str = e.date.strftime('%Y-%m-%d')
        if d_str not in events_by_date: events_by_date[d_str] = []
        events_by_date[d_str].append({'title': e.title, 'tag': e.tag, 'id': e.id})
    prev_month = month - 1 if month > 1 else 12; prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1; next_year = year if month < 12 else year + 1
    return render_template('calendar.html', month_days=month_days, events_by_date=events_by_date, current_year=year, current_month=month, month_name=cal_module.month_name[month], prev_year=prev_year, prev_month=prev_month, next_year=next_year, next_month=next_month)

@app.route('/add_event', methods=['POST'])
def add_event():
    db.session.add(Event(title=request.form.get('title'), date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(), tag=request.form.get('tag')))
    db.session.commit()
    return redirect(url_for('calendar_view', year=int(request.form.get('date').split('-')[0]), month=int(request.form.get('date').split('-')[1])))

@app.route('/delete_event/<int:id>')
def delete_event(id):
    db.session.delete(Event.query.get(id)); db.session.commit()
    return redirect(url_for('calendar_view'))

@app.route('/timetable')
def timetable_view():
    subjects = Subject.query.all()
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    hours = [8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19]
    timetable = {h: {d: None for d in days} for h in hours}
    for sub in subjects:
        if sub.schedule:
            parts = sub.schedule.upper().split(',')
            for part in parts:
                part = part.strip()
                found_day = None
                for d in days:
                    if d.upper() in part: found_day = d; break
                match = re.search(r'(\d+)', part)
                if found_day and match:
                    hour = int(match.group(1)); 
                    if 'PM' in part and hour != 12: hour += 12
                    if hour in timetable: timetable[hour][found_day] = sub
    return render_template('timetable.html', timetable=timetable, days=days, hours=hours)

@app.route('/forecast', methods=['POST'])
def forecast_attendance(): return render_template('forecast_result.html', alerts=[], start=date.today(), end=date.today())
@app.route('/search')
def search(): return redirect(url_for('dashboard'))
@app.route('/history/<int:subject_id>')
def attendance_history(subject_id): return render_template('attendance_history.html', subject=Subject.query.get(subject_id), logs=[])
@app.route('/update_attendance/<int:subject_id>/<action>')
def update_attendance(subject_id, action): 
    sub = Subject.query.get(subject_id); 
    if action == 'present': sub.attended += 1
    sub.total_classes += 1; db.session.commit()
    return redirect(url_for('dashboard'))
@app.route('/add_subject', methods=['POST'])
def add_subject():
    db.session.add(Subject(name=request.form.get('name'), code=request.form.get('code'), professor=request.form.get('prof'), schedule=request.form.get('schedule')))
    db.session.commit()
    return redirect(url_for('dashboard'))
@app.route('/add_note', methods=['POST'])
def add_note():
    db.session.add(Note(content=request.form.get('content'))); db.session.commit()
    return redirect(url_for('dashboard'))
@app.route('/delete_note/<int:id>')
def delete_note(id):
    db.session.delete(Note.query.get(id)); db.session.commit()
    return redirect(url_for('dashboard'))
@app.route('/delete_assignment/<int:id>')
def delete_assignment(id):
    db.session.delete(Assignment.query.get(id)); db.session.commit()
    return redirect(url_for('dashboard'))
@app.route('/update_profile', methods=['POST'])
def update_profile():
    s = Settings.query.first(); s.student_name = request.form.get('student_name'); s.university = request.form.get('university'); db.session.commit()
    return redirect(url_for('dashboard'))
@app.route('/subject/<int:id>')
def subject_details(id): return render_template('subject_details.html', subject=Subject.query.get(id))
@app.route('/update_resources/<int:id>', methods=['POST'])
def update_resources(id):
    s = Subject.query.get(id); s.syllabus_link=request.form.get('syllabus_link'); s.zoom_link=request.form.get('zoom_link'); s.notes=request.form.get('notes')
    try: s.total_modules=int(request.form.get('total_modules')); s.completed_student=float(request.form.get('completed_student')); s.completed_teacher=float(request.form.get('completed_teacher'))
    except: pass
    db.session.commit(); return redirect(url_for('subject_details', id=id))
@app.route('/delete_subject/<int:id>')
def delete_subject(id):
    db.session.delete(Subject.query.get(id)); db.session.commit()
    return redirect(url_for('dashboard'))
@app.route('/export_data')
def export_data(): return redirect(url_for('dashboard'))

# --- DESKTOP APP LOGIC ---
def start_server():
    app.run(port=5000, threaded=True)

if __name__ == '__main__':
    # 1. Start the Flask Server in a separate thread
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    # 2. Wait a split second to ensure server is up
    time.sleep(1)

    # 3. Open the "App Window" pointing to localhost
    webview.create_window("UniPlanner", "http://127.0.0.1:5000", width=1200, height=800, resizable=True)
    webview.start()