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
from plyer import notification 

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///planner.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    if not Settings.query.first():
        db.session.add(Settings(student_name="Future Coder", university="CodeChef Univ"))
        db.session.commit()

# --- 1. NOTIFICATION SYSTEM ---
def check_notifications():
    with app.app_context():
        while True:
            now = datetime.now()
            current_day = now.strftime("%a").upper()
            current_hour = now.hour
            subjects = Subject.query.all()
            for sub in subjects:
                if sub.schedule:
                    # Simple check: assumes format "MON 14-16"
                    slots = sub.schedule.split(',')
                    for slot in slots:
                        slot = slot.strip().upper()
                        if current_day in slot:
                            match = re.search(r'(\d+)', slot)
                            if match:
                                class_hour = int(match.group(1))
                                if class_hour == current_hour and now.minute < 2:
                                    try: notification.notify(title='Class Alert 🎓', message=f"{sub.code} starting!", app_name='CampusOS', timeout=10)
                                    except: pass
            time.sleep(60)

# --- 2. DASHBOARD & GAP FINDER ---
@app.route('/')
def dashboard():
    subjects = Subject.query.all()
    pending = Assignment.query.filter(Assignment.due_date >= date.today(), Assignment.status == 'Pending').order_by(Assignment.is_exam.desc(), Assignment.due_date).all()
    
    # Gap Finder
    today_name = date.today().strftime("%a").upper()
    today_classes = []
    
    for sub in subjects:
        if sub.schedule:
            slots = sub.schedule.split(',')
            for slot in slots:
                if today_name in slot.upper():
                    match = re.search(r'(\d+)-(\d+)', slot)
                    if match:
                        # Trust the DB has correct 24h format (e.g., 14-16)
                        start, end = int(match.group(1)), int(match.group(2))
                        today_classes.append({'name': sub.code, 'start': start, 'end': end})
    
    today_classes.sort(key=lambda x: x['start'])
    gaps = []
    if today_classes:
        for i in range(len(today_classes) - 1):
            if today_classes[i+1]['start'] > today_classes[i]['end']:
                gaps.append({'start': today_classes[i]['end'], 'end': today_classes[i+1]['start']})

    dates = [t.due_date for t in pending]
    bottlenecks = [{'date': d, 'count': c} for d, c in Counter(dates).items() if c >= 3]

    return render_template('dashboard.html', subjects=subjects, assignments=pending, exams=[a for a in pending if a.is_exam], notes=Note.query.all(), today=date.today(), settings=Settings.query.first(), bottlenecks=bottlenecks, gaps=gaps, quote=random.choice(["Focus on progress.", "Code is poetry."]))

# --- 3. TIMETABLE VIEW (FIXED) ---
@app.route('/timetable')
def timetable_view():
    s = Subject.query.all()
    h = [8,9,10,11,12,14,15,16,17,18,19] 
    t = {x:{d:None for d in ['MON','TUE','WED','THU','FRI']} for x in h}
    
    for sub in s:
        if sub.schedule:
            slots = sub.schedule.split(',')
            for slot in slots:
                slot = slot.strip().upper()
                # Parse "MON 14-16"
                match = re.search(r'([A-Z]+)\s+(\d+)-(\d+)', slot)
                if match:
                    d, st, en = match.groups()
                    st, en = int(st), int(en)
                    
                    # DIRECT MAPPING (No PM guessing)
                    for day_key in ['MON','TUE','WED','THU','FRI']:
                        if d in day_key:
                            for hr in range(st, en):
                                if hr in t: t[hr][day_key] = sub

    return render_template('timetable.html', timetable=t, days=['MON','TUE','WED','THU','FRI'], hours=h)

# --- 4. ADD SUBJECT (STRICT FORMAT) ---
@app.route('/add_subject', methods=['POST'])
def add_subject():
    days = request.form.getlist('days')
    starts = request.form.getlist('start_times')
    ends = request.form.getlist('end_times')
    
    # Save as "MON 14-16"
    schedule_parts = []
    for i in range(len(days)):
        if days[i] and starts[i] and ends[i]:
            part = f"{days[i]} {starts[i]}-{ends[i]}"
            schedule_parts.append(part)
    
    final_schedule = ", ".join(schedule_parts)
    
    db.session.add(Subject(name=request.form.get('name'), code=request.form.get('code'), professor=request.form.get('prof'), schedule=final_schedule))
    db.session.commit()
    return redirect(url_for('dashboard'))

# ... [REST OF ROUTES: Keep your standard CRUD routes below] ...
@app.route('/update_attendance/<int:subject_id>/<action>')
def update_attendance(subject_id, action): 
    sub = Subject.query.get_or_404(subject_id)
    if action == 'present': sub.attended += 1; sub.total_classes += 1; db.session.add(AttendanceLog(subject_id=sub.id, status='Present', date=date.today()))
    elif action == 'absent': sub.total_classes += 1; db.session.add(AttendanceLog(subject_id=sub.id, status='Absent', date=date.today()))
    db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/undo_attendance/<int:subject_id>')
def undo_attendance(subject_id):
    sub = Subject.query.get_or_404(subject_id)
    last_log = AttendanceLog.query.filter_by(subject_id=subject_id).order_by(AttendanceLog.id.desc()).first()
    if last_log:
        if last_log.status == 'Present': sub.attended = max(0, sub.attended - 1); sub.total_classes = max(0, sub.total_classes - 1)
        elif last_log.status == 'Absent': sub.total_classes = max(0, sub.total_classes - 1)
        db.session.delete(last_log); db.session.commit()
    return redirect(url_for('dashboard'))
@app.route('/delete_subject/<int:id>')
def delete_subject(id): db.session.delete(Subject.query.get_or_404(id)); db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/history/<int:subject_id>')
def attendance_history(subject_id): return render_template('attendance_history.html', subject=Subject.query.get(subject_id), logs=AttendanceLog.query.filter_by(subject_id=subject_id).order_by(AttendanceLog.date.desc()).all())
@app.route('/search')
def search():
    q = request.args.get('q', '')
    if not q: return redirect(url_for('dashboard'))
    return render_template('search_results.html', query=q, subjects=Subject.query.filter(Subject.name.contains(q)|Subject.code.contains(q)).all(), tasks=Assignment.query.filter(Assignment.title.contains(q)).all(), notes=Note.query.filter(Note.content.contains(q)).all())
@app.route('/forecast', methods=['POST'])
def forecast_attendance(): return render_template('forecast_result.html', alerts=[], start=date.today(), end=date.today())
@app.route('/career')
def career_view(): return render_template('career.html', items=CareerItem.query.order_by(CareerItem.date.desc()).all())
@app.route('/add_career_item', methods=['POST'])
def add_career_item(): db.session.add(CareerItem(title=request.form.get('title'), category=request.form.get('category'), tech_stack=request.form.get('tech_stack'), link=request.form.get('link'), date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date())); db.session.commit(); return redirect(url_for('career_view'))
@app.route('/delete_career_item/<int:id>')
def delete_career_item(id): db.session.delete(CareerItem.query.get(id)); db.session.commit(); return redirect(url_for('career_view'))
@app.route('/add_assignment', methods=['POST'])
def add_assignment(): db.session.add(Assignment(title=request.form.get('title'), due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date(), subject_id=request.form.get('subject_id'), is_exam=(True if request.form.get('is_exam') else False), status='Pending', color_tag=(request.form.get('color_tag') or 'emerald'), estimated_hours=(float(request.form.get('hours')) if request.form.get('hours') else 1.0))); db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/mark_done/<int:id>')
def mark_done(id): t=Assignment.query.get(id); t.status='Done'; db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/delete_assignment/<int:id>')
def delete_assignment(id): db.session.delete(Assignment.query.get(id)); db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/matrix')
def matrix_view(): t = Assignment.query.filter_by(status='Pending').all(); return render_template('matrix.html', matrix={'q1':[x for x in t if x.matrix_quadrant=='q1'], 'q2':[x for x in t if x.matrix_quadrant=='q2'], 'q3':[x for x in t if x.matrix_quadrant=='q3'], 'q4':[x for x in t if x.matrix_quadrant=='q4']})
@app.route('/update_quadrant/<int:id>/<string:quadrant>')
def update_quadrant(id, quadrant): t=Assignment.query.get(id); t.matrix_quadrant=quadrant; db.session.commit(); return jsonify({'success': True})
@app.route('/calendar')
def calendar_view(): return render_template('calendar.html', month_days=cal_module.Calendar(0).monthdatescalendar(datetime.now().year, datetime.now().month), events_by_date={}, current_year=datetime.now().year, current_month=datetime.now().month, month_name=cal_module.month_name[datetime.now().month], prev_year=2024, prev_month=1, next_year=2026, next_month=1)
@app.route('/add_event', methods=['POST'])
def add_event(): db.session.add(Event(title=request.form.get('title'), date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(), tag=request.form.get('tag'))); db.session.commit(); return redirect(url_for('calendar_view'))
@app.route('/delete_event/<int:id>')
def delete_event(id): db.session.delete(Event.query.get(id)); db.session.commit(); return redirect(url_for('calendar_view'))
@app.route('/add_note', methods=['POST'])
def add_note(): db.session.add(Note(content=request.form.get('content'))); db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/delete_note/<int:id>')
def delete_note(id): db.session.delete(Note.query.get(id)); db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/update_profile', methods=['POST'])
def update_profile(): s=Settings.query.first(); s.student_name=request.form.get('student_name'); s.university=request.form.get('university'); db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/subject/<int:id>')
def subject_details(id): return render_template('subject_details.html', subject=Subject.query.get(id))
@app.route('/update_resources/<int:id>', methods=['POST'])
def update_resources(id): s=Subject.query.get(id); s.syllabus_link=request.form.get('syllabus_link'); s.zoom_link=request.form.get('zoom_link'); s.notes=request.form.get('notes'); s.total_modules=int(request.form.get('total_modules') or 5); s.completed_student=float(request.form.get('completed_student') or 0); s.completed_teacher=float(request.form.get('completed_teacher') or 0); db.session.commit(); return redirect(url_for('subject_details', id=id))
@app.route('/export_data')
def export_data(): return redirect(url_for('dashboard'))

def start_server(): app.run(port=5000, threaded=True)

if __name__ == '__main__':
    t1 = threading.Thread(target=check_notifications); t1.daemon=True; t1.start()
    t2 = threading.Thread(target=start_server); t2.daemon=True; t2.start()
    time.sleep(2)
    webview.create_window("CampusOS", "http://127.0.0.1:5000", width=1200, height=800, resizable=True)
    webview.start()