from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app import db
from app.models import Enrollment, Subject, TeacherAvailability, TeacherSkill, StudentSchedule, User, TimeSlot

bp = Blueprint('onboarding', __name__, url_prefix='/onboarding')

@bp.route('/schedule', methods=['GET', 'POST'])
@bp.route('/schedule/<int:enrollment_id>', methods=['GET', 'POST'])
@login_required
def schedule_wizard(enrollment_id=None):
    # If enrollment_id is provided, use it; otherwise find pending enrollment
    if enrollment_id:
        enrollment = Enrollment.query.filter_by(
            id=enrollment_id, 
            student_id=current_user.id
        ).first()
        if not enrollment:
            flash('Enrollment tidak ditemukan.')
            return redirect(url_for('main.dashboard'))
    else:
        # Find first enrollment that needs scheduling (pending_schedule status)
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            status='pending_schedule'
        ).first()
        
        # If no pending, check if there's any enrollment
        if not enrollment:
            enrollment = Enrollment.query.filter_by(student_id=current_user.id).first()
    
    if not enrollment:
        flash('Anda belum terdaftar di program manapun.')
        return redirect(url_for('main.dashboard'))
    
    # Ambil semua subject yang WAJIB diambil di program ini
    required_subjects = [ps.subject_id for ps in enrollment.program.subjects]
    
    # Ambil subject yang SUDAH dijadwalkan oleh siswa ini
    scheduled_subjects = [s.subject_id for s in enrollment.schedules]
    
    # Cari subject mana yang BELUM dijadwalkan
    todo_subject_id = next((sid for sid in required_subjects if sid not in scheduled_subjects), None)
    
    if todo_subject_id is None:
        # Jika semua sudah dipilih
        enrollment.status = 'active'
        db.session.commit()
        flash(f'Jadwal untuk program {enrollment.program.name} berhasil diatur! Selamat belajar.')
        
        # Check if there are other enrollments needing scheduling
        next_pending = Enrollment.query.filter_by(
            student_id=current_user.id,
            status='pending_schedule'
        ).first()
        
        if next_pending:
            flash(f'Anda masih perlu mengatur jadwal untuk program {next_pending.program.name}.')
            return redirect(url_for('onboarding.schedule_wizard', enrollment_id=next_pending.id))
        
        return redirect(url_for('main.dashboard'))
        
    # Ambil object Subject
    subject_obj = Subject.query.get(todo_subject_id)
    
    # --- LOGIKA CARI TEACHER & AVAILABILITY ---
    # 1. Cari Guru yang bisa subject ini
    eligible_teachers = db.session.query(User.id).join(TeacherSkill).filter(
        TeacherSkill.subject_id == todo_subject_id
    ).all()
    teacher_ids = [t[0] for t in eligible_teachers]
    
    # 2. Cari Availability Guru-guru tersebut
    availabilities = TeacherAvailability.query.filter(
        TeacherAvailability.teacher_id.in_(teacher_ids)
    ).all()
    
    # 3. Format untuk Frontend (Calendar Events)
    events = []
    for av in availabilities:
        events.append({
            'title': f"Available: {av.teacher.name}",
            'start': '2024-01-01', # Dummy date, we use repeating days
            'daysOfWeek': [av.day_of_week], 
            'startTime': av.timeslot.start_time.strftime('%H:%M'),
            'endTime': av.timeslot.end_time.strftime('%H:%M'),
            'color': '#28a745',
            'extendedProps': {
                'teacher_id': av.teacher.id,
                'timeslot_id': av.timeslot.id,
                'day': av.day_of_week
            }
        })
        
    if request.method == 'POST':
        # Simpan Pilihan
        new_sched = StudentSchedule(
            enrollment_id=enrollment.id,
            subject_id=todo_subject_id,
            teacher_id=request.form['teacher_id'],
            day_of_week=request.form['day'],
            timeslot_id=request.form['timeslot_id']
        )
        db.session.add(new_sched)
        db.session.commit()
        return redirect(url_for('onboarding.schedule_wizard', enrollment_id=enrollment.id))

    return render_template('onboarding.html', 
                           subject=subject_obj, 
                           events=events,
                           enrollment=enrollment,
                           program_name=enrollment.program.name)