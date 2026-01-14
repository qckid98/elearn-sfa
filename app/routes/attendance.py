import os
from flask import Blueprint, request, flash, redirect, url_for, render_template, abort
from flask_login import login_required, current_user
from app import db
from app.models import TimeSlot
from app.models import Attendance, Enrollment, User, Booking
from app.security import csrf_protect
from datetime import date, datetime, timedelta

bp = Blueprint('attendance', __name__, url_prefix='/attendance')

def is_within_timeslot(timeslot):
    """Cek apakah waktu sekarang dalam rentang timeslot (dengan toleransi 15 menit sebelumnya)"""
    if not timeslot:
        return False
    
    now = datetime.now().time()
    # Toleransi 15 menit sebelum start untuk persiapan
    start_with_tolerance = (datetime.combine(date.today(), timeslot.start_time) - timedelta(minutes=15)).time()
    end_time = timeslot.end_time
    
    return start_with_tolerance <= now <= end_time

@bp.route('/submit', methods=['POST'])
@login_required
@csrf_protect
def submit_attendance():
    if current_user.role != 'teacher':
        abort(403)
    
    # Validasi: Cek timeslot dari booking pertama dan pastikan dalam waktu yang tepat
    booking_ids = request.form.getlist('booking_ids')
    if booking_ids:
        first_booking = Booking.query.get(booking_ids[0])
        if first_booking and first_booking.timeslot:
            if not is_within_timeslot(first_booking.timeslot):
                flash(f'⏰ Belum waktunya absen! Sesi {first_booking.timeslot.name} dimulai pukul {first_booking.timeslot.start_time.strftime("%H:%M")}', 'warning')
                return redirect(url_for('attendance.view_form', timeslot_id=first_booking.timeslot_id))

    # Data dari Form HTML Absensi
    booking_ids = request.form.getlist('booking_ids')
    program_name = request.form.get('program_name', 'Sesi Harian')
    
    hadir_count = 0
    izin_count = 0
    alpha_count = 0
    list_nama_hadir = []
    skipped_count = 0

    for b_id in booking_ids:
        # Validasi 1: Cek booking exists
        booking = Booking.query.get(b_id)
        if not booking:
            skipped_count += 1
            continue
        
        # Validasi 2: Cek ownership - hanya booking milik teacher ini
        if booking.teacher_id != current_user.id:
            skipped_count += 1
            continue
        
        # Validasi 3: Cek status booking - hanya yang belum completed
        if booking.status == 'completed':
            skipped_count += 1
            continue
        
        # Validasi 4: Cek duplicate attendance
        existing_attendance = Attendance.query.filter_by(booking_id=booking.id).first()
        if existing_attendance:
            skipped_count += 1
            continue
        
        status = request.form.get(f'status_{b_id}')
        notes = request.form.get(f'notes_{b_id}')
        
        # Validasi status
        if status not in ['Hadir', 'Izin', 'Alpha']:
            status = 'Alpha'  # Default jika tidak valid
        
        # 1. Simpan ke Database
        attendance = Attendance(
            booking_id=booking.id,
            teacher_id=current_user.id,
            date=date.today(),
            status=status,
            notes=notes
        )
        db.session.add(attendance)
        
        # 2. Update Sisa Sesi Siswa (Jika Hadir) - gunakan ClassEnrollment
        if status == 'Hadir':
            # Update via ClassEnrollment jika ada
            if booking.class_enrollment:
                booking.class_enrollment.sessions_remaining -= 1
            hadir_count += 1
            list_nama_hadir.append(booking.enrollment.student.name)
        elif status == 'Izin':
            # Track izin usage di ClassEnrollment
            if booking.class_enrollment:
                booking.class_enrollment.izin_used += 1
            izin_count += 1
        else:
            alpha_count += 1
            
        # Tandai booking selesai
        booking.status = 'completed'

    db.session.commit()

    # Rekap WA akan dikirim otomatis oleh scheduler H+2 jam setelah sesi selesai
    flash(f'Absensi berhasil disimpan! (Hadir: {hadir_count}, Izin: {izin_count}, Alpha: {alpha_count})')
    return redirect(url_for('main.dashboard'))

@bp.route('/view/<int:timeslot_id>', methods=['GET'])
@login_required
def view_form(timeslot_id):
    if current_user.role != 'teacher':
        abort(403)
    
    from datetime import timedelta
    from app.models import StudentSchedule
    
    today = date.today()
    timeslot = TimeSlot.query.get_or_404(timeslot_id)
    
    # Ambil semua booking hari ini di jam ini yang belum selesai DAN milik teacher ini
    bookings = Booking.query.filter_by(
        date=today, 
        timeslot_id=timeslot_id,
        teacher_id=current_user.id  # Hanya booking milik teacher ini
    ).filter(Booking.status != 'completed').all()
    
    # --- UPCOMING SCHEDULES (7 hari ke depan) ---
    upcoming = []
    days_name = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    
    for i in range(1, 8):  # Next 7 days
        future_date = today + timedelta(days=i)
        day_of_week = future_date.weekday()  # 0=Monday
        
        # 1. Cari dari regular schedules yang diajar oleh teacher ini DAN sesuai timeslot
        regular_schedules = StudentSchedule.query.filter_by(
            day_of_week=day_of_week,
            teacher_id=current_user.id,
            timeslot_id=timeslot_id  # Filter by current session
        ).all()
        
        for sched in regular_schedules:
            # Cek apakah sudah ada booking untuk jadwal ini
            existing_booking = Booking.query.filter_by(
                enrollment_id=sched.enrollment_id,
                date=future_date,
                timeslot_id=sched.timeslot_id
            ).first()
            
            if not existing_booking:
                upcoming.append({
                    'date': future_date,
                    'day_name': days_name[day_of_week],
                    'student_name': sched.enrollment.student.name,
                    'program_name': sched.enrollment.program.name,
                    'subject_name': sched.subject.name if sched.subject else '-',
                    'timeslot_name': sched.timeslot.name if sched.timeslot else '-',
                    'type': 'regular'
                })
        
        # 2. Cari dari future bookings yang diajar oleh teacher ini DAN sesuai timeslot
        future_bookings = Booking.query.filter_by(
            date=future_date,
            teacher_id=current_user.id,
            timeslot_id=timeslot_id  # Filter by current session
        ).filter(Booking.status != 'completed').all()
        
        for booking in future_bookings:
            upcoming.append({
                'date': future_date,
                'day_name': days_name[day_of_week],
                'student_name': booking.enrollment.student.name,
                'program_name': booking.enrollment.program.name,
                'subject_name': booking.subject.name if booking.subject else '-',
                'timeslot_name': booking.timeslot.name if booking.timeslot else '-',
                'type': 'booking'
            })
    
    # Sort by date
    upcoming.sort(key=lambda x: x['date'])
    
    # Cek apakah sesi sedang aktif
    is_session_active = is_within_timeslot(timeslot)
    current_time = datetime.now().strftime("%H:%M")
    
    return render_template(
        'attendance_form.html', 
        bookings=bookings, 
        timeslot=timeslot,
        today_date=today.strftime("%d %B %Y"),
        upcoming_schedules=upcoming,
        is_session_active=is_session_active,
        current_time=current_time
    )