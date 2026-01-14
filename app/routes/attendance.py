import os
from flask import Blueprint, request, flash, redirect, url_for, render_template, abort
from flask_login import login_required, current_user
from app import db
from app.models import TimeSlot
from app.models import Attendance, Enrollment, User, Booking, AttendanceRequest
from app.security import csrf_protect
from datetime import date, datetime, timedelta

bp = Blueprint('attendance', __name__, url_prefix='/attendance')

def get_session_status(timeslot, booking_date=None):
    """
    Cek status sesi berdasarkan tanggal dan waktu.
    Returns: 'active' (dalam jam sesi), 'not_yet' (belum waktunya), 'passed' (sudah lewat)
    """
    if not timeslot:
        return 'not_yet'
    
    now = datetime.now()
    today = date.today()
    check_date = booking_date if booking_date else today
    
    # Combine date with timeslot times
    session_start = datetime.combine(check_date, timeslot.start_time) - timedelta(minutes=15)
    session_end = datetime.combine(check_date, timeslot.end_time)
    
    if now > session_end:
        return 'passed'  # Sesi sudah lewat
    elif now >= session_start:
        return 'active'  # Dalam jam sesi (dengan toleransi 15 menit sebelum)
    else:
        return 'not_yet'  # Belum waktunya

def is_within_timeslot(timeslot):
    """Backward compatible: Cek apakah waktu sekarang dalam rentang timeslot"""
    return get_session_status(timeslot) == 'active'

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
            session_status = get_session_status(first_booking.timeslot, first_booking.date)
            if session_status == 'passed':
                flash(f'⛔ Sesi {first_booking.timeslot.name} sudah lewat. Hubungi admin jika Anda lupa absen.', 'danger')
                return redirect(url_for('attendance.view_form', timeslot_id=first_booking.timeslot_id))
            elif session_status == 'not_yet':
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
    
    # Ambil booking hari ini yang status 'booked' (siswa yang hadir) - default Hadir
    bookings_hadir = Booking.query.filter_by(
        date=today, 
        timeslot_id=timeslot_id,
        teacher_id=current_user.id,
        status='booked'
    ).all()
    
    # Ambil booking hari ini yang status 'izin' (siswa yang sudah request izin) - default Izin tapi bisa diganti Hadir
    bookings_izin = Booking.query.filter_by(
        date=today, 
        timeslot_id=timeslot_id,
        teacher_id=current_user.id,
        status='izin'
    ).all()
    
    # Gabungkan semua booking untuk backward compatibility (total count, dll)
    bookings = bookings_hadir + bookings_izin
    
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
                # Get class enrollment for regular schedule
                class_enrollment = None
                if sched.class_enrollment_id:
                    from app.models import ClassEnrollment
                    class_enrollment = ClassEnrollment.query.get(sched.class_enrollment_id)
                
                upcoming.append({
                    'date': future_date,
                    'day_name': days_name[day_of_week],
                    'student_name': sched.enrollment.student.name,
                    'program_name': sched.enrollment.program.name,
                    'subject_name': sched.subject.name if sched.subject else '-',
                    'timeslot_name': sched.timeslot.name if sched.timeslot else '-',
                    'timeslot_id': sched.timeslot_id,
                    'type': 'regular',
                    'enrollment': sched.enrollment,
                    'class_enrollment': class_enrollment
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
                'timeslot_id': booking.timeslot_id,
                'type': 'booking',
                'enrollment': booking.enrollment,
                'class_enrollment': booking.class_enrollment
            })
    
    # Sort by date
    upcoming.sort(key=lambda x: x['date'])
    
    # === GROUP UPCOMING BY SESSION (date + timeslot) ===
    from collections import defaultdict
    from app.models import Syllabus
    
    grouped = defaultdict(list)
    for item in upcoming:
        key = (item['date'], item['timeslot_id'], item['timeslot_name'])
        grouped[key].append(item)
    
    upcoming_sessions = []
    for (session_date, ts_id, ts_name), students in grouped.items():
        day_of_week = session_date.weekday()
        
        # Build student details with class and syllabus info
        student_details = []
        for s in students:
            # Get class and current topic
            class_name = '-'
            current_topic = None
            
            if s['class_enrollment']:
                ce = s['class_enrollment']
                class_name = ce.program_class.name
                
                # Calculate current topic
                total = ce.program_class.total_sessions
                remaining = ce.sessions_remaining or 0
                completed = total - remaining
                
                syllabus_items = Syllabus.query.filter_by(
                    program_class_id=ce.program_class_id
                ).order_by(Syllabus.order).all()
                
                cumulative = 0
                for syl in syllabus_items:
                    prev_cumulative = cumulative
                    cumulative += syl.sessions
                    if completed < cumulative:
                        session_in_topic = completed - prev_cumulative + 1
                        if syl.sessions > 1:
                            current_topic = f"{syl.topic_name} - {session_in_topic}"
                        else:
                            current_topic = syl.topic_name
                        break
                else:
                    if syllabus_items:
                        current_topic = syllabus_items[-1].topic_name + " (Selesai)"
            elif s['enrollment']:
                class_name = s['enrollment'].program.name
            
            student_details.append({
                'name': s['student_name'],
                'class_name': class_name,
                'current_topic': current_topic,
                'type': s['type']
            })
        
        upcoming_sessions.append({
            'date': session_date,
            'day_name': days_name[day_of_week],
            'timeslot_id': ts_id,
            'timeslot_name': ts_name,
            'students': student_details,
            'student_count': len(student_details)
        })
    
    # Sort by date
    upcoming_sessions.sort(key=lambda x: x['date'])
    
    # Cek status sesi: 'active', 'not_yet', atau 'passed'
    session_status = get_session_status(timeslot, today)
    is_session_active = session_status == 'active'
    current_time = datetime.now().strftime("%H:%M")
    
    return render_template(
        'attendance_form.html', 
        bookings=bookings,
        bookings_hadir=bookings_hadir,
        bookings_izin=bookings_izin,
        timeslot=timeslot,
        timeslot_date=today,
        today_date=today.strftime("%d %B %Y"),
        upcoming_schedules=upcoming,  # Keep for backward compat
        upcoming_sessions=upcoming_sessions,  # New grouped data
        is_session_active=is_session_active,
        session_status=session_status,
        current_time=current_time
    )


# === REQUEST ABSEN LEWAT ===

@bp.route('/request-late/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def request_late(booking_id):
    """Form dan submit request absen untuk sesi yang sudah lewat"""
    if current_user.role != 'teacher':
        abort(403)
    
    booking = Booking.query.get_or_404(booking_id)
    
    # Validasi: Hanya booking milik teacher ini
    if booking.teacher_id != current_user.id:
        abort(403)
    
    # Validasi: Booking harus dalam range H+2 hari
    today = date.today()
    max_date = booking.date + timedelta(days=2)
    if today > max_date:
        flash('⛔ Batas waktu request sudah lewat. Maksimal H+2 hari dari tanggal sesi.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # Validasi: Belum ada request pending untuk booking ini
    existing = AttendanceRequest.query.filter_by(
        booking_id=booking_id,
        approval_status='pending'
    ).first()
    if existing:
        flash('⚠️ Sudah ada request pending untuk booking ini.', 'warning')
        return redirect(url_for('attendance.my_requests'))
    
    # Validasi: Belum ada attendance untuk booking ini
    if booking.attendance:
        flash('⚠️ Absensi untuk booking ini sudah ada.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        status_request = request.form.get('status_request')
        notes = request.form.get('notes', '')
        reason = request.form.get('reason', '')
        
        # Validasi
        if status_request not in ['Hadir', 'Izin', 'Alpha']:
            flash('Status tidak valid.', 'danger')
            return redirect(url_for('attendance.request_late', booking_id=booking_id))
        
        if len(reason) < 20:
            flash('Alasan minimal 20 karakter.', 'danger')
            return redirect(url_for('attendance.request_late', booking_id=booking_id))
        
        # Simpan request
        att_request = AttendanceRequest(
            booking_id=booking_id,
            teacher_id=current_user.id,
            status_request=status_request,
            notes=notes,
            reason=reason
        )
        db.session.add(att_request)
        db.session.commit()
        
        flash('✅ Request absen berhasil dikirim! Menunggu approval dari admin.', 'success')
        return redirect(url_for('attendance.my_requests'))
    
    return render_template(
        'attendance_request_form.html',
        booking=booking
    )


@bp.route('/my-requests')
@login_required
def my_requests():
    """Riwayat request absen teacher - grouped per sesi"""
    if current_user.role != 'teacher':
        abort(403)
    
    requests = AttendanceRequest.query.filter_by(
        teacher_id=current_user.id
    ).order_by(AttendanceRequest.request_date.desc()).all()
    
    # Group by date + timeslot
    from collections import defaultdict
    grouped = defaultdict(list)
    
    for req in requests:
        booking = req.booking
        if booking:
            key = (booking.date, booking.timeslot_id, req.reason, req.request_date.date())
            grouped[key].append(req)
    
    # Build grouped sessions
    grouped_sessions = []
    for (booking_date, timeslot_id, reason, request_date), reqs in grouped.items():
        if not reqs:
            continue
        
        first_req = reqs[0]
        first_booking = first_req.booking
        timeslot = first_booking.timeslot if first_booking else None
        
        # Get class name
        class_name = '-'
        for r in reqs:
            if r.booking and r.booking.class_enrollment:
                class_name = r.booking.class_enrollment.program_class.name
                break
            elif r.booking and r.booking.enrollment:
                class_name = r.booking.enrollment.program.name
                break
        
        # Count statuses
        pending_count = sum(1 for r in reqs if r.approval_status == 'pending')
        approved_count = sum(1 for r in reqs if r.approval_status == 'approved')
        rejected_count = sum(1 for r in reqs if r.approval_status == 'rejected')
        
        # Determine overall status
        if pending_count > 0:
            overall_status = 'pending'
        elif rejected_count > 0:
            overall_status = 'rejected'
        else:
            overall_status = 'approved'
        
        grouped_sessions.append({
            'date': booking_date,
            'timeslot': timeslot,
            'class_name': class_name,
            'student_count': len(reqs),
            'reason': reason,
            'request_date': request_date,
            'overall_status': overall_status,
            'pending_count': pending_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'requests': reqs
        })
    
    # Sort by request_date desc
    grouped_sessions.sort(key=lambda x: x['request_date'], reverse=True)
    
    return render_template(
        'attendance_my_requests.html',
        grouped_sessions=grouped_sessions
    )


@bp.route('/pending-bookings')
@login_required
def pending_bookings():
    """Daftar sesi yang belum diabsen (dalam range H-2 sampai hari ini), grouped per sesi"""
    if current_user.role != 'teacher':
        abort(403)
    
    today = date.today()
    min_date = today - timedelta(days=2)  # H-2
    
    # Query bookings milik teacher ini dalam range H-2 sampai hari ini
    bookings = Booking.query.filter(
        Booking.teacher_id == current_user.id,
        Booking.date >= min_date,
        Booking.date <= today,
        Booking.status != 'completed'
    ).order_by(Booking.date.desc()).all()
    
    # Group by date + timeslot
    from collections import defaultdict
    grouped = defaultdict(list)
    
    for booking in bookings:
        # Skip jika sudah ada attendance
        if booking.attendance:
            continue
        
        # Skip jika sudah ada pending request untuk booking ini
        existing_request = AttendanceRequest.query.filter_by(
            booking_id=booking.id,
            approval_status='pending'
        ).first()
        if existing_request:
            continue
        
        key = (booking.date, booking.timeslot_id)
        grouped[key].append(booking)
    
    # Build pending sessions
    pending_sessions = []
    for (booking_date, timeslot_id), bookings_in_slot in grouped.items():
        if not bookings_in_slot:
            continue
            
        first_booking = bookings_in_slot[0]
        timeslot = first_booking.timeslot
        session_status = get_session_status(timeslot, booking_date)
        
        # Hanya tampilkan yang sudah lewat
        if session_status == 'passed':
            # Get class name
            class_name = '-'
            for b in bookings_in_slot:
                if b.class_enrollment:
                    class_name = b.class_enrollment.program_class.name
                    break
                elif b.enrollment and b.enrollment.program:
                    class_name = b.enrollment.program.name
                    break
            
            pending_sessions.append({
                'date': booking_date,
                'timeslot': timeslot,
                'timeslot_id': timeslot_id,
                'bookings': bookings_in_slot,
                'student_count': len(bookings_in_slot),
                'class_name': class_name,
                'session_status': session_status
            })
    
    # Sort by date desc, then by timeslot
    pending_sessions.sort(key=lambda x: (x['date'], x['timeslot'].start_time), reverse=True)
    
    return render_template(
        'attendance_pending_bookings.html',
        pending_sessions=pending_sessions
    )


@bp.route('/request-late-session/<date_str>/<int:timeslot_id>', methods=['GET', 'POST'])
@login_required
def request_late_session(date_str, timeslot_id):
    """Form dan submit request absen untuk satu sesi (semua siswa dalam sesi)"""
    if current_user.role != 'teacher':
        abort(403)
    
    # Parse date
    try:
        from datetime import datetime
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Format tanggal tidak valid.', 'danger')
        return redirect(url_for('attendance.pending_bookings'))
    
    timeslot = TimeSlot.query.get_or_404(timeslot_id)
    
    # Get all bookings for this teacher, date, timeslot
    bookings = Booking.query.filter(
        Booking.teacher_id == current_user.id,
        Booking.date == booking_date,
        Booking.timeslot_id == timeslot_id,
        Booking.status != 'completed'
    ).all()
    
    # Filter out yang sudah ada attendance atau pending request
    valid_bookings = []
    for booking in bookings:
        if booking.attendance:
            continue
        existing = AttendanceRequest.query.filter_by(
            booking_id=booking.id,
            approval_status='pending'
        ).first()
        if existing:
            continue
        valid_bookings.append(booking)
    
    if not valid_bookings:
        flash('Tidak ada booking yang perlu di-request untuk sesi ini.', 'warning')
        return redirect(url_for('attendance.pending_bookings'))
    
    # Validasi: Booking harus dalam range H+2 hari
    today = date.today()
    max_date = booking_date + timedelta(days=2)
    if today > max_date:
        flash('⛔ Batas waktu request sudah lewat. Maksimal H+2 hari dari tanggal sesi.', 'danger')
        return redirect(url_for('attendance.pending_bookings'))
    
    if request.method == 'POST':
        reason = request.form.get('reason', '')
        
        # Validasi alasan
        if len(reason) < 20:
            flash('Alasan minimal 20 karakter.', 'danger')
            return redirect(url_for('attendance.request_late_session', date_str=date_str, timeslot_id=timeslot_id))
        
        # Process each booking
        for booking in valid_bookings:
            status_request = request.form.get(f'status_{booking.id}', 'Hadir')
            notes = request.form.get(f'notes_{booking.id}', '')
            
            if status_request not in ['Hadir', 'Izin', 'Alpha']:
                status_request = 'Hadir'
            
            # Create AttendanceRequest
            att_request = AttendanceRequest(
                booking_id=booking.id,
                teacher_id=current_user.id,
                status_request=status_request,
                notes=notes,
                reason=reason  # Same reason for all
            )
            db.session.add(att_request)
        
        db.session.commit()
        
        flash(f'✅ Request absen untuk {len(valid_bookings)} siswa berhasil dikirim! Menunggu approval admin.', 'success')
        return redirect(url_for('attendance.my_requests'))
    
    return render_template(
        'attendance_request_session_form.html',
        bookings=valid_bookings,
        timeslot=timeslot,
        booking_date=booking_date
    )