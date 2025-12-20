from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import User, Enrollment, StudentSchedule, Subject, TimeSlot, TeacherAvailability, Program, Batch, ProgramSubject, TeacherSkill, Booking
from datetime import date

bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorator
def admin_required(func):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Akses ditolak!')
            return redirect(url_for('main.dashboard'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# --- SISWA (STUDENT) ---
@bp.route('/students')
@login_required
@admin_required
def student_list():
    students = db.session.query(User).filter(User.role == 'student').all()
    return render_template('admin/student_list.html', students=students)

@bp.route('/student/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def student_detail(user_id):
    student = User.query.get_or_404(user_id)
    enrollment = Enrollment.query.filter_by(student_id=student.id).first()
    
    if request.method == 'POST':
        if 'update_info' in request.form:
            enrollment.sessions_remaining = int(request.form['sessions_remaining'])
            enrollment.status = request.form['status']
            db.session.commit()
            flash('Info siswa diperbarui.')
        
        elif 'add_schedule' in request.form:
            new_sched = StudentSchedule(
                enrollment_id=enrollment.id,
                day_of_week=int(request.form['day']),
                timeslot_id=int(request.form['timeslot_id']),
                subject_id=int(request.form['subject_id']),
                teacher_id=int(request.form['teacher_id'])
            )
            db.session.add(new_sched)
            db.session.commit()
            flash('Jadwal manual ditambahkan.')
        
        elif 'add_manual_booking' in request.form:
            booking_date_str = request.form['date']
            booking_date = date.fromisoformat(booking_date_str)
            timeslot_id = int(request.form['timeslot_id'])
            
            # Additional fields for teacher/subject
            teacher_id = request.form.get('teacher_id')
            subject_id = request.form.get('subject_id')
            
            if teacher_id: teacher_id = int(teacher_id)
            if subject_id: subject_id = int(subject_id)
            
            # Check duplicate
            existing = Booking.query.filter_by(
                enrollment_id=enrollment.id, 
                date=booking_date, 
                timeslot_id=timeslot_id
            ).first()
            
            if existing:
                flash('Booking untuk tanggal dan jam tersebut sudah ada!', 'error')
            else:
                new_booking = Booking(
                    enrollment_id=enrollment.id,
                    date=booking_date,
                    timeslot_id=timeslot_id,
                    teacher_id=teacher_id, # Added
                    subject_id=subject_id, # Added
                    status='booked'
                )
                db.session.add(new_booking)
                db.session.commit()
                flash('Override jadwal (Sesi Tambahan) berhasil dibuat.')

        return redirect(url_for('admin.student_detail', user_id=user_id))

    booking_date_cutoff = date.today()
    manual_bookings = Booking.query.filter(
        Booking.enrollment_id == enrollment.id,
        Booking.status != 'completed',
        Booking.date >= booking_date_cutoff
    ).order_by(Booking.date).all()

    subjects = Subject.query.all()
    timeslots = TimeSlot.query.all()
    teachers = User.query.filter_by(role='teacher').all()
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    return render_template('admin/student_detail.html', student=student, enrollment=enrollment, subjects=subjects, timeslots=timeslots, teachers=teachers, days=days, manual_bookings=manual_bookings)

@bp.route('/booking/delete/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    uid = booking.enrollment.student_id
    db.session.delete(booking)
    db.session.commit()
    flash('Booking manual dihapus.')
    return redirect(url_for('admin.student_detail', user_id=uid))

@bp.route('/schedule/delete/<int:sched_id>')
@login_required
@admin_required
def delete_schedule(sched_id):
    sched = StudentSchedule.query.get_or_404(sched_id)
    uid = sched.enrollment.student_id
    db.session.delete(sched)
    db.session.commit()
    flash('Jadwal dihapus.')
    return redirect(url_for('admin.student_detail', user_id=uid))

@bp.route('/master-schedule')
@login_required
@admin_required
def master_schedule():
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    timeslots = TimeSlot.query.all()
    schedule_map = {i: {slot.id: [] for slot in timeslots} for i in range(7)}
    
    # Query all schedules is heavier, better filter per slot via loop or join
    # Simple loop approach:
    for i in range(7):
        for slot in timeslots:
            schedule_map[i][slot.id] = StudentSchedule.query.filter_by(day_of_week=i, timeslot_id=slot.id).all()
            
    return render_template('admin/master_schedule.html', days=days, timeslots=timeslots, schedule_map=schedule_map)

# --- PROGRAM ---
@bp.route('/programs', methods=['GET', 'POST'])
@login_required
@admin_required
def program_manage():
    if request.method == 'POST':
        name = request.form['name']
        sessions = int(request.form['total_sessions'])
        is_batch = True if request.form.get('is_batch_based') else False
        
        new_prog = Program(name=name, total_sessions=sessions, is_batch_based=is_batch)
        db.session.add(new_prog)
        db.session.commit()
        
        # Add Subjects
        sub_ids = request.form.getlist('subjects')
        for sid in sub_ids:
            db.session.add(ProgramSubject(program_id=new_prog.id, subject_id=int(sid)))
        db.session.commit()
        flash('Program ditambahkan.')
        return redirect(url_for('admin.program_manage'))

    programs = Program.query.all()
    subjects = Subject.query.all()
    return render_template('admin/program_list.html', programs=programs, subjects=subjects)

@bp.route('/program/edit/<int:prog_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def program_edit(prog_id):
    prog = Program.query.get_or_404(prog_id)
    if request.method == 'POST':
        prog.name = request.form['name']
        prog.total_sessions = int(request.form['total_sessions'])
        prog.is_batch_based = True if request.form.get('is_batch_based') else False
        
        ProgramSubject.query.filter_by(program_id=prog.id).delete()
        for sid in request.form.getlist('subjects'):
            db.session.add(ProgramSubject(program_id=prog.id, subject_id=int(sid)))
        db.session.commit()
        flash('Program diupdate.')
        return redirect(url_for('admin.program_manage'))

    current_sub_ids = [ps.subject_id for ps in prog.subjects]
    return render_template('admin/program_edit.html', program=prog, subjects=Subject.query.all(), current_sub_ids=current_sub_ids)

# --- BATCH MANAGEMENT ---
@bp.route('/batch/add', methods=['POST'])
@login_required
@admin_required
def add_batch():
    program_id = int(request.form['program_id'])
    name = request.form['name']
    max_students = int(request.form['max_students'])
    
    new_batch = Batch(program_id=program_id, name=name, max_students=max_students, is_active=True)
    db.session.add(new_batch)
    db.session.commit()
    flash('Batch berhasil ditambahkan.')
    return redirect(url_for('admin.program_edit', prog_id=program_id))

@bp.route('/batch/edit/<int:batch_id>', methods=['POST'])
@login_required
@admin_required
def edit_batch(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    batch.name = request.form['name']
    batch.max_students = int(request.form['max_students'])
    batch.is_active = True if request.form.get('is_active') else False
    
    db.session.commit()
    flash('Batch diperbarui.')
    return redirect(url_for('admin.program_edit', prog_id=batch.program_id))

@bp.route('/batch/delete/<int:batch_id>', methods=['POST'])
@login_required
@admin_required
def delete_batch(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    program_id = batch.program_id
    
    # Check for enrolled students
    if Enrollment.query.filter_by(batch_id=batch.id).first():
        flash('Gagal menghapus: Masih ada siswa yang terdaftar di batch ini.', 'error')
        return redirect(url_for('admin.program_edit', prog_id=program_id))
        
    try:
        db.session.delete(batch)
        db.session.commit()
        flash('Batch dihapus.')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus batch: {str(e)}', 'error')
        
    return redirect(url_for('admin.program_edit', prog_id=program_id))

# --- TEACHER ---
@bp.route('/teachers', methods=['GET', 'POST'])
@login_required
@admin_required
def teacher_list():
    if request.method == 'POST':
        email = request.form['email']
        # Cek duplicate
        if User.query.filter_by(email=email).first():
            flash('Email sudah ada.')
        else:
            new_t = User(
                email=email, 
                name=request.form['name'], 
                phone_number=request.form['phone'], 
                role='teacher'
            )
            # PASSWORD DEFAULT
            new_t.set_password('guru123')
            db.session.add(new_t)
            db.session.commit()
            flash('Guru ditambahkan. Password default: guru123')
            return redirect(url_for('admin.teacher_list'))

    teachers = User.query.filter_by(role='teacher').all()
    return render_template('admin/teacher_list.html', teachers=teachers)

@bp.route('/teacher/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def teacher_detail(user_id):
    teacher = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        if 'update_profile' in request.form:
            teacher.name = request.form['name']
            teacher.email = request.form['email']
            teacher.phone_number = request.form['phone']
            db.session.commit()
            flash('Profil diupdate.')
            
        elif 'update_skills' in request.form:
            TeacherSkill.query.filter_by(teacher_id=teacher.id).delete()
            for sid in request.form.getlist('subject_ids'):
                db.session.add(TeacherSkill(teacher_id=teacher.id, subject_id=int(sid)))
            db.session.commit()
            flash('Skill diupdate.')
            
        elif 'update_avail' in request.form:
            TeacherAvailability.query.filter_by(teacher_id=teacher.id).delete()
            for item in request.form.getlist('slots'):
                day, slot = item.split('_')
                db.session.add(TeacherAvailability(teacher_id=teacher.id, day_of_week=int(day), timeslot_id=int(slot)))
            db.session.commit()
            flash('Jadwal ketersediaan diupdate.')
            
        return redirect(url_for('admin.teacher_detail', user_id=user_id))

    subjects = Subject.query.all()
    timeslots = TimeSlot.query.all()
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    
    my_skill_ids = [s.subject_id for s in teacher.skills]
    avail_map = {i: {t.id: False for t in timeslots} for i in range(7)}
    for av in teacher.availabilities:
        avail_map[av.day_of_week][av.timeslot_id] = True
        
    return render_template('admin/teacher_detail.html', teacher=teacher, subjects=subjects, timeslots=timeslots, days=days, my_skill_ids=my_skill_ids, avail_map=avail_map)

# --- DELETE ROUTES ---
@bp.route('/student/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_student(user_id):
    student = User.query.get_or_404(user_id)
    if student.role != 'student':
        flash('User bukan siswa.')
        return redirect(url_for('admin.student_list'))
        
    try:
        db.session.delete(student)
        db.session.commit()
        flash('Siswa dihapus.')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus: {str(e)}')
        
    return redirect(url_for('admin.student_list'))

@bp.route('/program/delete/<int:prog_id>', methods=['POST'])
@login_required
@admin_required
def delete_program(prog_id):
    prog = Program.query.get_or_404(prog_id)
    try:
        db.session.delete(prog)
        db.session.commit()
        flash('Program dihapus.')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus program: {str(e)}')
        
    return redirect(url_for('admin.program_manage'))

@bp.route('/teacher/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_teacher(user_id):
    teacher = User.query.get_or_404(user_id)
    if teacher.role != 'teacher':
        flash('User bukan guru.')
        return redirect(url_for('admin.teacher_list'))
        
    try:
        db.session.delete(teacher)
        db.session.commit()
        flash('Guru dihapus.')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus guru: {str(e)}')
        
    return redirect(url_for('admin.teacher_list'))