from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app import db
from app.models import (
    Enrollment, MasterClass, TeacherAvailability, TeacherSkill, 
    StudentSchedule, User, TimeSlot, ClassEnrollment
)

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
    
    # Get class_enrollments for this enrollment
    class_enrollments = ClassEnrollment.query.filter_by(enrollment_id=enrollment.id).all()
    
    # Get master_class_ids from the program's classes
    required_class_ids = []
    for ce in class_enrollments:
        if ce.program_class and ce.program_class.master_class_id:
            required_class_ids.append({
                'class_enrollment_id': ce.id,
                'master_class_id': ce.program_class.master_class_id,
                'class_name': ce.program_class.display_name
            })
    
    # Get already scheduled class_enrollment_ids
    scheduled_class_enrollment_ids = [s.class_enrollment_id for s in enrollment.schedules if s.class_enrollment_id]
    
    # Find the first class that hasn't been scheduled
    todo_class = next(
        (c for c in required_class_ids if c['class_enrollment_id'] not in scheduled_class_enrollment_ids), 
        None
    )
    
    if todo_class is None:
        # All classes have been scheduled
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
    
    # Get the MasterClass object
    master_class_obj = MasterClass.query.get(todo_class['master_class_id'])
    
    # --- FIND ELIGIBLE TEACHERS & AVAILABILITY ---
    # 1. Find teachers who can teach this master_class
    eligible_teachers = db.session.query(User.id).join(TeacherSkill).filter(
        TeacherSkill.master_class_id == todo_class['master_class_id']
    ).all()
    teacher_ids = [t[0] for t in eligible_teachers]
    
    # 2. Find availability of these teachers for this master_class
    availabilities = TeacherAvailability.query.filter(
        TeacherAvailability.teacher_id.in_(teacher_ids),
        TeacherAvailability.master_class_id == todo_class['master_class_id']
    ).all()
    
    # 3. Format for Frontend (Calendar Events)
    timeslots = {ts.id: ts for ts in TimeSlot.query.all()}
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    
    events = []
    for av in availabilities:
        ts = timeslots.get(av.timeslot_id)
        if ts:
            events.append({
                'title': f"{av.teacher.name} - {ts.name}",
                'start': '2024-01-01',  # Dummy date, we use repeating days
                'daysOfWeek': [av.day_of_week], 
                'startTime': ts.start_time.strftime('%H:%M'),
                'endTime': ts.end_time.strftime('%H:%M'),
                'color': '#28a745',
                'extendedProps': {
                    'teacher_id': av.teacher.id,
                    'teacher_name': av.teacher.name,
                    'timeslot_id': av.timeslot_id,
                    'timeslot_name': ts.name,
                    'day': av.day_of_week,
                    'day_name': days[av.day_of_week]
                }
            })
    
    # Build simple slot list for table display
    available_slots = []
    for av in availabilities:
        ts = timeslots.get(av.timeslot_id)
        if ts:
            available_slots.append({
                'teacher_id': av.teacher.id,
                'teacher_name': av.teacher.name,
                'day_of_week': av.day_of_week,
                'day_name': days[av.day_of_week],
                'timeslot_id': av.timeslot_id,
                'timeslot_name': ts.name,
                'time_range': f"{ts.start_time.strftime('%H:%M')} - {ts.end_time.strftime('%H:%M')}"
            })
        
    if request.method == 'POST':
        # Save the schedule
        new_sched = StudentSchedule(
            enrollment_id=enrollment.id,
            class_enrollment_id=todo_class['class_enrollment_id'],
            teacher_id=request.form['teacher_id'],
            day_of_week=int(request.form['day']),
            timeslot_id=int(request.form['timeslot_id'])
        )
        db.session.add(new_sched)
        db.session.commit()
        flash(f'Jadwal untuk {todo_class["class_name"]} berhasil disimpan!')
        return redirect(url_for('onboarding.schedule_wizard', enrollment_id=enrollment.id))

    return render_template('onboarding.html', 
                           master_class=master_class_obj,
                           class_name=todo_class['class_name'],
                           class_enrollment_id=todo_class['class_enrollment_id'],
                           events=events,
                           available_slots=available_slots,
                           enrollment=enrollment,
                           program_name=enrollment.program.name,
                           total_classes=len(required_class_ids),
                           scheduled_count=len(scheduled_class_enrollment_ids))