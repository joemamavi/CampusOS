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

# --- NOTIFICATION SYSTEM ---
def check_notifications():
    """Checks for upcoming classes every 60 seconds."""
    with app.app_context():
        while True:
            now = datetime.now()
            current_day = now.strftime("%a").upper()
            current_hour = now.hour
            
            subjects = Subject.query.all()
            for sub in subjects:
                if sub.schedule:
                    if current_day in sub.schedule.upper():
                        # Parse "MON 10-12" to get start hour
                        match = re.search(r'(\d+)', sub.schedule)
                        if match:
                            class_hour = int(match.group(1))
                            if 'PM' in sub.schedule.upper() and class_hour != 12: class_hour += 12
                            
                            # Notify if it's currently the hour of the class
                            if class_hour == current_hour and now.minute == 0:
                                try:
                                    notification.notify(
                                        title='Class Alert 🎓',
                                        message=f"{sub.code}: {sub.name} is starting now!",
                                        app_name='CampusOS',
                                        timeout=10
                                    )
                                except: pass
            time.sleep(60)

# --- DASHBOARD & GAP FINDER ---
@app.route('/')
def dashboard():
    subjects = Subject.query.all()
    pending = Assignment.query.filter(Assignment.due_date >= date.today(), Assignment.status == 'Pending').order_by(Assignment.is_exam.desc(), Assignment.due_date).all()
    
    # Gap Finder Logic
    today_name = date.today().strftime("%a").upper()
    today_classes = []
    for sub in subjects:
        if sub.schedule and today_name in sub.schedule.upper():
            match = re.search(r'(\d+)-(\d+)', sub.schedule)
            if match: 
                today_classes.append({'name': sub.code, 'start': int(match.group(1)), 'end': int(match.group(2))})
    
    today_classes.sort(key=lambda x: x['start'])
    gaps = []
    if today_classes:
        for i in range(len(today_classes) - 1):
            if today_classes[i+1]['start'] > today_classes[i]['end']:
                gaps.append({'start': today_classes[i]['end'], 'end': today_classes[i+1]['start']})

    # Bottlenecks
    dates = [t.due_date for t in pending]
    bottlenecks = [{'date': d, 'count': c} for d, c in Counter(dates).items() if c >= 3]

    return render_template('dashboard.html', 
                           subjects=subjects, assignments=pending, 
                           exams=[a for a in pending if a.is_exam], notes=Note.query.all(), 
                           today=date.today(), settings=Settings.query.first(), 
                           bottlenecks=bottlenecks, gaps=gaps, 
                           quote=random.choice(["Focus on progress, not perfection.", "Code is poetry."]))

# --- ATTENDANCE LOGIC (FIXED) ---
@app.route('/update_attendance/<int:subject_id>/<action>')
def update_attendance(subject_id, action): 
    sub = Subject.query.get_or_404(subject_id)
    if action == 'present':
        sub.attended += 1
        sub.total_classes += 1
        # Log for history/undo
        db.session.add(AttendanceLog(subject_id=sub.id, status='Present', date=date.today()))
    elif action == 'absent':
        sub.total_classes += 1
        db.session.add(AttendanceLog(subject_id=sub.id, status='Absent', date=date.today()))
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/undo_attendance/<int:subject_id>')
def undo_attendance(subject_id):
    sub = Subject.query.get_or_404(subject_id)
    # Find last log
    last_log = AttendanceLog.query.filter_by(subject_id=subject_id).order_by(AttendanceLog.id.desc()).first()
    
    if last_log:
        if last_log.status == 'Present':
            sub.attended = max(0, sub.attended - 1)
            sub.total_classes = max(0, sub.total_classes - 1)
        elif last_log.status == 'Absent':
            sub.total_classes = max(0, sub.total_classes - 1)
        
        db.session.delete(last_log)
        db.session.commit()
        
    return redirect(url_for('dashboard'))

@app.route('/history/<int:subject_id>')
def attendance_history(subject_id):
    # Fetch real logs
    logs = AttendanceLog.query.filter_by(subject_id=subject_id).order_by(AttendanceLog.date.desc()).all()
    return render_template('attendance_history.html', subject=Subject.query.get(subject_id), logs=logs)

# --- FORECAST LOGIC (FIXED) ---
@app.route('/forecast', methods=['POST'])
def forecast_attendance():
    start = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
    end = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
    subjects = Subject.query.all()
    alerts = []
    day_map = {0:'MON', 1:'TUE', 2:'WED', 3:'THU', 4:'FRI', 5:'SAT', 6:'SUN'}
    
    days_to_check = (end - start).days + 1
    
    for sub in subjects:
        if not sub.schedule: continue
        missed = 0
        for i in range(days_to_check):
            d = start + timedelta(days=i)
            if day_map[d.weekday()] in sub.schedule.upper():
                missed += 1
        
        if missed > 0:
            new_total = sub.total_classes + missed
            new_pct = (sub.attended / new_total) * 100 if new_total > 0 else 0
            if new_pct < 75:
                alerts.append({'code': sub.code, 'name': sub.name, 'new_percent': round(new_pct, 1)})
                
    return render_template('forecast_result.html', alerts=alerts, start=start, end=end)

# --- SEARCH LOGIC (FIXED) ---
@app.route('/search')
def search():
    q = request.args.get('q', '')
    if not q: return redirect(url_for('dashboard'))
    
    found_subs = Subject.query.filter(Subject.name.contains(q) | Subject.code.contains(q)).all()
    found_tasks = Assignment.query.filter(Assignment.title.contains(q)).all()
    found_notes = Note.query.filter(Note.content.contains(q)).all()
    
    return render_template('search_results.html', query=q, subjects=found_subs, tasks=found_tasks, notes=found_notes)

# --- STANDARD ROUTES (Career, Subject, Note, etc.) ---
@app.route('/add_subject', methods=['POST'])
def add_subject():
    s = f"{request.form.get('day')} {request.form.get('start_time')}-{request.form.get('end_time')}"
    db.session.add(Subject(name=request.form.get('name'), code=request.form.get('code'), professor=request.form.get('prof'), schedule=s))
    db.session.commit(); return redirect(url_for('dashboard'))

@app.route('/career')
def career_view(): return render_template('career.html', items=CareerItem.query.order_by(CareerItem.date.desc()).all())
@app.route('/add_career_item', methods=['POST'])
def add_career_item(): db.session.add(CareerItem(title=request.form.get('title'), category=request.form.get('category'), tech_stack=request.form.get('tech_stack'), link=request.form.get('link'), date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date())); db.session.commit(); return redirect(url_for('career_view'))
@app.route('/delete_career_item/<int:id>')
def delete_career_item(id): db.session.delete(CareerItem.query.get(id)); db.session.commit(); return redirect(url_for('career_view'))

@app.route('/add_assignment', methods=['POST'])
def add_assignment():
    est = float(request.form.get('hours')) if request.form.get('hours') else 1.0
    db.session.add(Assignment(title=request.form.get('title'), due_date=datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date(), subject_id=request.form.get('subject_id'), is_exam=(True if request.form.get('is_exam') else False), status='Pending', color_tag=(request.form.get('color_tag') or 'emerald'), estimated_hours=est))
    db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/mark_done/<int:id>')
def mark_done(id): t=Assignment.query.get(id); t.status='Done'; db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/delete_assignment/<int:id>')
def delete_assignment(id): db.session.delete(Assignment.query.get(id)); db.session.commit(); return redirect(url_for('dashboard'))

@app.route('/matrix')
def matrix_view(): t = Assignment.query.filter_by(status='Pending').all(); return render_template('matrix.html', matrix={'q1':[x for x in t if x.matrix_quadrant=='q1'], 'q2':[x for x in t if x.matrix_quadrant=='q2'], 'q3':[x for x in t if x.matrix_quadrant=='q3'], 'q4':[x for x in t if x.matrix_quadrant=='q4']})
@app.route('/update_quadrant/<int:id>/<string:quadrant>')
def update_quadrant(id, quadrant): t=Assignment.query.get(id); t.matrix_quadrant=quadrant; db.session.commit(); return jsonify({'success': True})

@app.route('/timetable')
def timetable_view():
    s = Subject.query.all(); h = [8,9,10,11,12,14,15,16,17,18,19]; t = {x:{d:None for d in ['MON','TUE','WED','THU','FRI']} for x in h}
    for sub in s:
        if sub.schedule:
            m = re.search(r'([A-Z]+)\s+(\d+)-(\d+)', sub.schedule.upper())
            if m:
                d, st, en = m.groups(); st, en = int(st), int(en)
                for hr in range(st, en): 
                    if hr in t: t[hr][d] = sub
    return render_template('timetable.html', timetable=t, days=['MON','TUE','WED','THU','FRI'], hours=h)

@app.route('/calendar')
@app.route('/calendar/<int:year>/<int:month>')
def calendar_view(year=None, month=None):
    if year is None: now = datetime.now(); year, month = now.year, now.month
    cal = cal_module.Calendar(0); month_days = cal.monthdatescalendar(year, month)
    events_by_date = {}
    for e in Event.query.all():
        d = e.date.strftime('%Y-%m-%d')
        if d not in events_by_date: events_by_date[d] = []
        events_by_date[d].append({'title': e.title, 'tag': e.tag, 'id': e.id})
    prev_m = month-1 if month>1 else 12; prev_y = year if month>1 else year-1
    next_m = month+1 if month<12 else 1; next_y = year if month<12 else year+1
    return render_template('calendar.html', month_days=month_days, events_by_date=events_by_date, current_year=year, current_month=month, month_name=cal_module.month_name[month], prev_year=prev_y, prev_month=prev_m, next_year=next_y, next_month=next_m)

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
@app.route('/delete_subject/<int:id>')
def delete_subject(id): db.session.delete(Subject.query.get(id)); db.session.commit(); return redirect(url_for('dashboard'))
@app.route('/export_data')
def export_data(): return redirect(url_for('dashboard'))

def start_server(): app.run(port=5000, threaded=True)

if __name__ == '__main__':
    t1 = threading.Thread(target=check_notifications); t1.daemon=True; t1.start()
    t2 = threading.Thread(target=start_server); t2.daemon=True; t2.start()
    time.sleep(2)
    webview.create_window("CampusOS", "http://127.0.0.1:5000", width=1200, height=800, resizable=True)
    webview.start()