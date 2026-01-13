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
    
    # Build list of classes with scheduling requirements
    required_classes = []
    for ce in class_enrollments:
        if ce.program_class and ce.program_class.master_class_id:
            # Count how many schedules already exist for this class_enrollment
            existing_schedules = StudentSchedule.query.filter_by(
                enrollment_id=enrollment.id,
                class_enrollment_id=ce.id
            ).count()
            
            sessions_per_week = ce.program_class.sessions_per_week or 1
            remaining_to_schedule = sessions_per_week - existing_schedules
            
            required_classes.append({
                'class_enrollment_id': ce.id,
                'master_class_id': ce.program_class.master_class_id,
                'class_name': ce.program_class.display_name,
                'sessions_per_week': sessions_per_week,
                'scheduled_count': existing_schedules,
                'remaining': max(0, remaining_to_schedule)
            })
    
    # Find the first class that still needs more schedules
    todo_class = next(
        (c for c in required_classes if c['remaining'] > 0), 
        None
    )
    
    if todo_class is None:
        # All classes have been fully scheduled - now pick first class date
        enrollment.status = 'pending_first_class'
        db.session.commit()
        
        # Redirect to first class date selection
        return redirect(url_for('onboarding.first_class_date', enrollment_id=enrollment.id))
    
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
    
    # 3. Get ALL already selected slots for this enrollment (across ALL classes)
    # to prevent booking same day+timeslot for different classes
    existing_slots = StudentSchedule.query.filter_by(
        enrollment_id=enrollment.id
    ).all()
    existing_slot_keys = {(s.day_of_week, s.timeslot_id) for s in existing_slots}
    
    # 4. Format for Frontend
    timeslots = {ts.id: ts for ts in TimeSlot.query.all()}
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    
    events = []
    available_slots = []
    
    for av in availabilities:
        # Skip if this slot is already taken
        if (av.day_of_week, av.timeslot_id) in existing_slot_keys:
            continue
            
        ts = timeslots.get(av.timeslot_id)
        if ts:
            events.append({
                'title': f"{av.teacher.name} - {ts.name}",
                'start': '2024-01-01',
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
        
        # Check if more slots needed for this class
        new_count = todo_class['scheduled_count'] + 1
        if new_count < todo_class['sessions_per_week']:
            flash(f'Jadwal ke-{new_count} untuk {todo_class["class_name"]} tersimpan! Pilih jadwal ke-{new_count + 1}.')
        else:
            flash(f'Jadwal untuk {todo_class["class_name"]} lengkap!')
            
        return redirect(url_for('onboarding.schedule_wizard', enrollment_id=enrollment.id))

    # Calculate total progress
    total_slots_needed = sum(c['sessions_per_week'] for c in required_classes)
    total_slots_scheduled = sum(c['scheduled_count'] for c in required_classes)

    return render_template('onboarding.html', 
                           master_class=master_class_obj,
                           class_name=todo_class['class_name'],
                           class_enrollment_id=todo_class['class_enrollment_id'],
                           sessions_per_week=todo_class['sessions_per_week'],
                           current_slot=todo_class['scheduled_count'] + 1,
                           events=events,
                           available_slots=available_slots,
                           enrollment=enrollment,
                           program_name=enrollment.program.name,
                           total_slots_needed=total_slots_needed,
                           total_slots_scheduled=total_slots_scheduled,
                           required_classes=required_classes)


# --- FIRST CLASS DATE SELECTION ---
@bp.route('/first-class-date/<int:enrollment_id>', methods=['GET', 'POST'])
@login_required
def first_class_date(enrollment_id):
    from datetime import date, timedelta
    from app.models import Booking
    
    enrollment = Enrollment.query.filter_by(
        id=enrollment_id, 
        student_id=current_user.id
    ).first()
    
    if not enrollment:
        flash('Enrollment tidak ditemukan.')
        return redirect(url_for('main.dashboard'))
    
    # If first_class_date already set, student cannot change it
    if enrollment.first_class_date:
        flash('Tanggal mulai kelas sudah diatur dan tidak dapat diubah. Hubungi admin jika perlu perubahan.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    
    # Get all schedules for this enrollment
    schedules = StudentSchedule.query.filter_by(enrollment_id=enrollment.id).all()
    
    if not schedules:
        flash('Jadwal belum diatur. Silakan atur jadwal terlebih dahulu.')
        return redirect(url_for('onboarding.schedule_wizard', enrollment_id=enrollment.id))
    
    # Build schedule summary for display
    schedule_summary = []
    for sched in schedules:
        summary = {
            'day_name': days[sched.day_of_week],
            'day_of_week': sched.day_of_week,
            'timeslot_name': sched.timeslot.name,
            'timeslot_time': sched.timeslot.start_time.strftime('%H:%M'),
            'teacher_name': sched.teacher.name if sched.teacher else '-',
            'class_name': sched.class_enrollment.program_class.name if sched.class_enrollment else '-'
        }
        schedule_summary.append(summary)
    
    # Generate available start dates (next 4 weeks of valid dates based on schedule days)
    available_dates = []
    schedule_days = set(s.day_of_week for s in schedules)
    today = date.today()
    
    for i in range(28):  # Next 4 weeks
        check_date = today + timedelta(days=i)
        if check_date.weekday() in schedule_days:
            available_dates.append({
                'date': check_date,
                'date_str': check_date.strftime('%Y-%m-%d'),
                'display': f"{days[check_date.weekday()]}, {check_date.strftime('%d %b %Y')}"
            })
    
    if request.method == 'POST':
        selected_date_str = request.form.get('first_class_date')
        
        if not selected_date_str:
            flash('Pilih tanggal mulai kelas.')
            return redirect(url_for('onboarding.first_class_date', enrollment_id=enrollment.id))
        
        try:
            from datetime import datetime
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Format tanggal tidak valid.')
            return redirect(url_for('onboarding.first_class_date', enrollment_id=enrollment.id))
        
        # Validate that date has matching schedule
        if selected_date.weekday() not in schedule_days:
            flash('Tanggal yang dipilih tidak sesuai dengan jadwal.')
            return redirect(url_for('onboarding.first_class_date', enrollment_id=enrollment.id))
        
        # Save first class date
        enrollment.first_class_date = selected_date
        
        # Generate bookings for next 4 weeks
        bookings_created = 0
        end_date = selected_date + timedelta(weeks=4)
        
        for sched in schedules:
            current_date = selected_date
            while current_date <= end_date:
                if current_date.weekday() == sched.day_of_week:
                    # Check if booking already exists
                    existing = Booking.query.filter_by(
                        enrollment_id=enrollment.id,
                        date=current_date,
                        timeslot_id=sched.timeslot_id
                    ).first()
                    
                    if not existing:
                        new_booking = Booking(
                            enrollment_id=enrollment.id,
                            class_enrollment_id=sched.class_enrollment_id,
                            date=current_date,
                            timeslot_id=sched.timeslot_id,
                            teacher_id=sched.teacher_id,
                            status='booked'
                        )
                        db.session.add(new_booking)
                        bookings_created += 1
                
                current_date += timedelta(days=1)
        
        # Activate enrollment
        enrollment.status = 'active'
        db.session.commit()
        
        flash(f'Selamat! Jadwal berhasil diatur mulai {selected_date.strftime("%d %b %Y")}. {bookings_created} sesi terjadwal.')
        
        # Check if there are other enrollments needing scheduling
        next_pending = Enrollment.query.filter_by(
            student_id=current_user.id,
            status='pending_schedule'
        ).first()
        
        if next_pending:
            flash(f'Anda masih perlu mengatur jadwal untuk program {next_pending.program.name}.')
            return redirect(url_for('onboarding.schedule_wizard', enrollment_id=next_pending.id))
        
        return redirect(url_for('main.dashboard'))
    
    return render_template('first_class_date.html',
                           enrollment=enrollment,
                           program_name=enrollment.program.name,
                           schedule_summary=schedule_summary,
                           available_dates=available_dates,
                           days=days)