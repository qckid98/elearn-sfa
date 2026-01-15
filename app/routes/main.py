from app.utils.whatsapp import send_wa_message, check_wa_status
from flask import Blueprint, render_template, request, flash, url_for, redirect
from flask_login import login_required, current_user
from app.models import User, Enrollment, Program, Batch, Booking, Attendance, ClassEnrollment, StudentSchedule
from app import db
import uuid
from datetime import date, datetime, timedelta

bp = Blueprint('main', __name__)


def generate_upcoming_sessions_from_schedule(schedules, weeks_ahead=4):
    """
    Generate upcoming session dates from weekly schedule patterns.
    Returns list of sessions with specific dates for the next N weeks.
    """
    upcoming = []
    today = date.today()
    end_date = today + timedelta(weeks=weeks_ahead)
    
    for sched in schedules:
        # Find all dates matching this day_of_week in the range
        current_date = today
        while current_date <= end_date:
            if current_date.weekday() == sched.day_of_week:
                # Check if booking already exists for this date/timeslot/enrollment
                existing_booking = Booking.query.filter_by(
                    enrollment_id=sched.enrollment_id,
                    date=current_date,
                    timeslot_id=sched.timeslot_id
                ).first()
                
                upcoming.append({
                    'schedule_id': sched.id,
                    'date': current_date,
                    'day_of_week': sched.day_of_week,
                    'timeslot': sched.timeslot,
                    'teacher': sched.teacher,
                    'class_enrollment_id': sched.class_enrollment_id,
                    'class_enrollment': sched.class_enrollment,
                    'enrollment_id': sched.enrollment_id,
                    'existing_booking': existing_booking,
                    'can_izin': (
                        existing_booking is None and  # No existing booking
                        sched.class_enrollment and
                        sched.class_enrollment.program_class.max_izin > 0 and
                        sched.class_enrollment.izin_remaining > 0
                    )
                })
            current_date += timedelta(days=1)
    
    # Sort by date
    upcoming.sort(key=lambda x: (x['date'], x['timeslot'].start_time))
    return upcoming

@bp.route('/')
@login_required
def dashboard():
    # Fetch ALL enrollments for multi-program support
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    
    # For backward compatibility, keep single enrollment reference
    enrollment = enrollments[0] if enrollments else None
    
    # Mapping Hari
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    
    manual_bookings = []
    student_progress = None
    enrollments_data = []  # List of all enrollment progress data
    
    if enrollments:
        # Gather bookings from ALL enrollments
        enrollment_ids = [e.id for e in enrollments]
        manual_bookings = Booking.query.filter(
            Booking.enrollment_id.in_(enrollment_ids),
            Booking.status != 'completed',
            Booking.date >= date.today()
        ).order_by(Booking.date).all()
        
        # Build progress data for EACH enrollment
        for enroll in enrollments:
            # Get all completed bookings for this enrollment
            completed_bookings = Booking.query.filter(
                Booking.enrollment_id == enroll.id,
                Booking.status == 'completed'
            ).all()
            
            # Get attendance records for completed bookings
            booking_ids = [b.id for b in completed_bookings]
            attendance_records = Attendance.query.filter(
                Attendance.booking_id.in_(booking_ids)
            ).order_by(Attendance.date.desc()).limit(10).all() if booking_ids else []
            
            # Calculate attendance stats
            hadir_count = Attendance.query.filter(
                Attendance.booking_id.in_(booking_ids),
                Attendance.status == 'Hadir'
            ).count() if booking_ids else 0
            
            # Izin count from class_enrollments.izin_used (not from Attendance status)
            izin_count = sum(ce.izin_used for ce in enroll.class_enrollments)
            
            alpha_count = Attendance.query.filter(
                Attendance.booking_id.in_(booking_ids),
                Attendance.status == 'Alpha'
            ).count() if booking_ids else 0
            
            # Calculate progress percentage
            total_sessions = enroll.program.total_sessions
            completed_sessions = total_sessions - enroll.sessions_remaining
            progress_pct = int((completed_sessions / total_sessions) * 100) if total_sessions > 0 else 0
            
            # Build session history with details
            session_history = []
            for att in attendance_records:
                booking = Booking.query.get(att.booking_id)
                if booking:
                    session_history.append({
                        'date': att.date,
                        'subject': booking.subject.name if booking.subject else '-',
                        'timeslot': booking.timeslot.name if booking.timeslot else '-',
                        'status': att.status,
                        'notes': att.notes,
                        'teacher': booking.teacher.name if booking.teacher else '-'
                    })
            
            # Build class enrollments data with detailed stats
            class_enrollments_data = []
            for ce in enroll.class_enrollments:
                # Calculate per-class attendance
                class_hadir = Attendance.query.join(Booking).filter(
                    Booking.class_enrollment_id == ce.id,
                    Attendance.status == 'Hadir'
                ).count()
                
                class_alpha = Attendance.query.join(Booking).filter(
                    Booking.class_enrollment_id == ce.id,
                    Attendance.status == 'Alpha'
                ).count()
                
                class_enrollments_data.append({
                    'id': ce.id,
                    'class_name': ce.program_class.name,
                    'sessions_remaining': ce.sessions_remaining,
                    'total_sessions': ce.program_class.total_sessions,
                    'max_izin': ce.program_class.max_izin,
                    'izin_used': ce.izin_used,
                    'izin_remaining': ce.izin_remaining,
                    'status': ce.status,
                    'is_batch': ce.program_class.is_batch_based,
                    'hadir': class_hadir,
                    'alpha': class_alpha
                })
            
            # Generate upcoming sessions from schedule for izin feature
            upcoming_schedule_sessions = generate_upcoming_sessions_from_schedule(
                enroll.schedules, 
                weeks_ahead=4
            )
            
            enroll_progress = {
                'enrollment_id': enroll.id,
                'program_name': enroll.program.name,
                'program_id': enroll.program.id,
                'status': enroll.status,
                'completed_sessions': completed_sessions,
                'total_sessions': total_sessions,
                'remaining_sessions': enroll.sessions_remaining,
                'progress_pct': progress_pct,
                'hadir': hadir_count,
                'izin': izin_count,
                'alpha': alpha_count,
                'session_history': session_history,
                'class_enrollments': class_enrollments_data,
                'upcoming_schedule_sessions': upcoming_schedule_sessions
            }
            enrollments_data.append(enroll_progress)
        
        # For backward compatibility - use first enrollment's progress
        if enrollments_data:
            student_progress = enrollments_data[0]
    
    # Teacher Calendar Data
    teacher_calendar_events = []
    if current_user.role == 'teacher':
        from app.models import TeacherSessionOverride
        from collections import defaultdict
        
        # Get all bookings for this teacher
        teacher_bookings = Booking.query.filter(
            Booking.teacher_id == current_user.id
        ).order_by(Booking.date).all()
        
        # Get overrides where this teacher is being substituted (exclude these)
        overrides_as_original = TeacherSessionOverride.query.filter_by(
            original_teacher_id=current_user.id
        ).all()
        override_keys_to_exclude = {(o.date, o.timeslot_id) for o in overrides_as_original}
        
        # Get overrides where this teacher is the substitute (include these bookings)
        overrides_as_substitute = TeacherSessionOverride.query.filter_by(
            substitute_teacher_id=current_user.id
        ).all()
        
        # Get bookings from original teachers that this user is substituting
        substitute_bookings = []
        for override in overrides_as_substitute:
            bookings_from_original = Booking.query.filter(
                Booking.teacher_id == override.original_teacher_id,
                Booking.date == override.date,
                Booking.timeslot_id == override.timeslot_id
            ).all()
            substitute_bookings.extend(bookings_from_original)
            
            # If no bookings found, check StudentSchedule for the override date
            if not bookings_from_original:
                day_of_week = override.date.weekday()
                schedules = StudentSchedule.query.filter_by(
                    teacher_id=override.original_teacher_id,
                    timeslot_id=override.timeslot_id,
                    day_of_week=day_of_week
                ).all()
                
                # Create pseudo-bookings for calendar display
                for sched in schedules:
                    # Create a virtual booking-like object
                    class PseudoBooking:
                        def __init__(self, date, timeslot_id, timeslot, enrollment, class_enrollment, status='booked'):
                            self.date = date
                            self.timeslot_id = timeslot_id
                            self.timeslot = timeslot
                            self.enrollment = enrollment
                            self.class_enrollment = class_enrollment
                            self.status = status
                    
                    pseudo = PseudoBooking(
                        date=override.date,
                        timeslot_id=override.timeslot_id,
                        timeslot=override.timeslot,
                        enrollment=sched.enrollment,
                        class_enrollment=ClassEnrollment.query.get(sched.class_enrollment_id) if sched.class_enrollment_id else None
                    )
                    substitute_bookings.append(pseudo)
        
        # Generate upcoming sessions from StudentSchedule for this teacher (4 weeks ahead)
        # This ensures scheduled sessions appear even without existing Booking records
        schedule_generated_bookings = []
        teacher_schedules = StudentSchedule.query.filter_by(
            teacher_id=current_user.id
        ).all()
        
        today = date.today()
        end_date = today + timedelta(weeks=4)
        
        for sched in teacher_schedules:
            # Generate dates for this schedule pattern
            current_date = today
            while current_date <= end_date:
                if current_date.weekday() == sched.day_of_week:
                    key = (current_date, sched.timeslot_id)
                    # Skip if this date is overridden (teacher substituted out)
                    if key not in override_keys_to_exclude:
                        # Check if booking already exists for this slot
                        existing_booking = None
                        for b in teacher_bookings:
                            if b.date == current_date and b.timeslot_id == sched.timeslot_id:
                                existing_booking = b
                                break
                        
                        # Only create pseudo-booking if no real booking exists
                        if not existing_booking:
                            class PseudoBooking:
                                def __init__(self, date, timeslot_id, timeslot, enrollment, class_enrollment, status='booked'):
                                    self.date = date
                                    self.timeslot_id = timeslot_id
                                    self.timeslot = timeslot
                                    self.enrollment = enrollment
                                    self.class_enrollment = class_enrollment
                                    self.status = status
                            
                            pseudo = PseudoBooking(
                                date=current_date,
                                timeslot_id=sched.timeslot_id,
                                timeslot=sched.timeslot,
                                enrollment=sched.enrollment,
                                class_enrollment=ClassEnrollment.query.get(sched.class_enrollment_id) if sched.class_enrollment_id else None
                            )
                            schedule_generated_bookings.append(pseudo)
                current_date += timedelta(days=1)
        
        # Combine: own bookings (excluding overridden) + substitute bookings + schedule-generated
        all_bookings = []
        for booking in teacher_bookings:
            key = (booking.date, booking.timeslot_id)
            if key not in override_keys_to_exclude:
                all_bookings.append(booking)
        all_bookings.extend(substitute_bookings)
        all_bookings.extend(schedule_generated_bookings)
        
        # Group bookings by date + timeslot
        grouped = defaultdict(list)
        for booking in all_bookings:
            key = (booking.date, booking.timeslot_id)
            grouped[key].append(booking)
        
        today = date.today()
        
        for (booking_date, timeslot_id), bookings_in_slot in grouped.items():
            # Get timeslot info from first booking
            first_booking = bookings_in_slot[0]
            timeslot = first_booking.timeslot
            
            # Exclude izin students from count
            active_bookings = [b for b in bookings_in_slot if b.status != 'izin']
            total_students = len(active_bookings)
            
            # Skip if no active students (all izin)
            if total_students == 0:
                continue
            
            completed_count = sum(1 for b in active_bookings if b.status == 'completed')
            booked_count = sum(1 for b in active_bookings if b.status == 'booked')
            
            # Get class name (from first booking with class_enrollment)
            class_name = '-'
            for b in bookings_in_slot:
                if b.class_enrollment:
                    class_name = b.class_enrollment.program_class.name
                    break
                elif b.enrollment and b.enrollment.program:
                    class_name = b.enrollment.program.name
                    break
            
            # Check if this is a substitute session
            is_substitute = (booking_date, timeslot_id) in {(o.date, o.timeslot_id) for o in overrides_as_substitute}
            
            # Determine global status and color
            if completed_count == total_students:
                color = '#28a745'  # Green - selesai
                status = 'Selesai'
            elif booking_date < today:
                color = '#dc3545'  # Red - terlewat (tanggal sudah lewat tapi belum diabsen)
                status = 'Terlewat'
            else:
                color = '#007bff'  # Blue - mendatang
                status = 'Mendatang'
            
            # Build event title with substitute indicator
            title = f"{timeslot.name} ({total_students} siswa)"
            if is_substitute:
                title = f"🔄 {title}"
            
            event = {
                'id': f"{booking_date}_{timeslot_id}",
                'title': title,
                'start': f"{booking_date}T{timeslot.start_time.strftime('%H:%M:%S')}",
                'end': f"{booking_date}T{timeslot.end_time.strftime('%H:%M:%S')}",
                'color': color,
                'extendedProps': {
                    'class_name': class_name,
                    'timeslot': timeslot.name,
                    'total_students': total_students,
                    'status': status,
                    'date': booking_date.strftime('%d %b %Y'),
                    'is_substitute': is_substitute
                }
            }
            teacher_calendar_events.append(event)

    
    # Admin Stats
    stats = None
    if current_user.role == 'admin':
        # Count total students
        total_students = User.query.filter_by(role='student').count()
        # Count total teachers
        total_teachers = User.query.filter_by(role='teacher').count()
        # Count total active programs
        total_programs = Program.query.count()
        # Count sessions today (attendance records for today)
        total_sessions = Attendance.query.filter(
            Attendance.date == date.today()
        ).count()
        
        # Check WhatsApp status
        wa_status = check_wa_status()
        
        stats = {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_programs': total_programs,
            'total_sessions': total_sessions,
            'wa_status': wa_status
        }
    
    return render_template('dashboard.html', 
                           enrollment=enrollment,
                           enrollments=enrollments,
                           enrollments_data=enrollments_data,
                           days=days,
                           manual_bookings=manual_bookings,
                           teacher_calendar_events=teacher_calendar_events,
                           student_progress=student_progress,
                           stats=stats)


# --- API: GET WA QR CODE ---
@bp.route('/api/wa-qr')
@login_required
def api_wa_qr():
    from flask import jsonify
    from app.utils.whatsapp import get_wa_qr
    import re
    import os
    
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    result = get_wa_qr()
    
    # Rewrite to use our proxy endpoint instead of direct wabot URL
    if result.get('success') and result.get('qr_link'):
        qr_link = result['qr_link']
        # Extract filename from the URL (e.g., scan-qr-xxx.png)
        match = re.search(r'/statics/qrcode/([^/]+\.png)', qr_link)
        if match:
            filename = match.group(1)
            # Use our proxy endpoint
            result['qr_link'] = url_for('main.proxy_wa_qr', filename=filename, _external=True)
    
    return jsonify(result)


# --- PROXY: Serve QR image from wabot ---
@bp.route('/api/wa-qr-image/<filename>')
@login_required
def proxy_wa_qr(filename):
    import requests
    from flask import Response
    import os
    
    if current_user.role != 'admin':
        return "Access denied", 403
    
    # Fetch image from wabot internal URL
    wa_url = os.environ.get('WA_API_URL', 'http://wabot:3000')
    image_url = f"{wa_url}/statics/qrcode/{filename}"
    
    try:
        resp = requests.get(image_url, timeout=10)
        if resp.status_code == 200:
            return Response(resp.content, mimetype='image/png')
        else:
            return "Image not found", 404
    except Exception as e:
        return f"Error: {str(e)}", 500


# --- ROUTE UNTUK ADMIN MENDAFTARKAN SISWA (Simpel) ---
@bp.route('/admin/invite', methods=['GET', 'POST'])
@login_required
def admin_invite():
    if current_user.role != 'admin':
        return "Access Denied"
        
    if request.method == 'POST':
        email = request.form['email']
        raw_phone = request.form['phone'] # Input dari form (misal: 08123456)
        program_id = request.form['program_id']
        
        # 1. Format Nomor HP (08xx -> 628xx)
        clean_phone = raw_phone.strip().replace('-', '').replace(' ', '')
        if clean_phone.startswith('0'):
            clean_phone = '62' + clean_phone[1:]
        elif clean_phone.startswith('+'):
            clean_phone = clean_phone[1:]
            
        # 2. Cek apakah email sudah ada
        if User.query.filter_by(email=email).first():
            flash('Email sudah terdaftar!')
            return redirect(url_for('main.admin_invite'))

        # 3. Generate Token & Link (PREPARE DATA)
        token = str(uuid.uuid4())
        link = url_for('auth.activate', token=token, _external=True)
        
        pesan = (
            f"Halo! Selamat datang di *Sparks Fashion Academy*.\n\n"
            f"Akun Anda telah dibuat. Silakan klik link di bawah ini untuk mengatur password dan jadwal belajar Anda:\n\n"
            f"{link}\n\n"
            f"Terima kasih!"
        )
        target_wa = f"{clean_phone}@s.whatsapp.net"
        
        # 4. KIRIM WHATSAPP DULUAN (ATOMIC CHECK)
        if send_wa_message(target_wa, pesan):
            # Jika SUKSES kirim, baru simpan ke DB
            try:
                new_user = User(
                    email=email, 
                    phone_number=clean_phone,
                    role='student', 
                    activation_token=token,
                    name="New Student"
                )
                db.session.add(new_user)
                db.session.flush() # Get ID
                
                prog = Program.query.get(program_id)
                batch_id = request.form.get('batch_id') if prog.is_batch_based else None
                
                enroll = Enrollment(
                    student_id=new_user.id,
                    program_id=program_id,
                    batch_id=batch_id,
                    status='pending_schedule'
                )
                db.session.add(enroll)
                db.session.commit()
                
                flash(f'Sukses! Link aktivasi dikirim ke WA {clean_phone} dan User dibuat.')
            except Exception as e:
                db.session.rollback()
                flash(f'WA Terkirim, tapi Gagal simpan DB: {str(e)}. Harap hubungi admin.')
        else:
            # Jika GAGAL kirim, Jangan buat user
            flash(f'GAGAL kirim WA ke {clean_phone}. User TIDAK dibuat. Cek koneksi bot.')
            
        return redirect(url_for('main.admin_invite'))

    programs = Program.query.all()
    batches = Batch.query.filter_by(is_active=True).all()
    return render_template('admin_invite.html', programs=programs, batches=batches)


# --- ROUTE UNTUK BATCH INVITE (MULTIPLE STUDENTS) ---
@bp.route('/admin/batch-invite', methods=['GET', 'POST'])
@login_required
def batch_invite():
    if current_user.role != 'admin':
        return "Access Denied"
    
    programs = Program.query.all()
    batches = Batch.query.filter_by(is_active=True).all()
    results = []
    
    if request.method == 'POST':
        program_id = request.form.get('program_id')
        batch_id = request.form.get('batch_id') or None
        students_data = request.form.get('students_data', '').strip()
        
        if not students_data:
            flash('Data siswa tidak boleh kosong!', 'error')
            return redirect(url_for('main.batch_invite'))
        
        prog = Program.query.get(program_id)
        if not prog:
            flash('Program tidak ditemukan!', 'error')
            return redirect(url_for('main.batch_invite'))
        
        # Parse data: format "email,phone" per baris
        lines = students_data.split('\n')
        success_count = 0
        fail_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse email dan phone (dipisah koma atau tab)
            parts = line.replace('\t', ',').split(',')
            if len(parts) < 2:
                results.append({'line': line, 'status': 'error', 'message': 'Format salah (butuh email,phone)'})
                fail_count += 1
                continue
            
            email = parts[0].strip().lower()
            raw_phone = parts[1].strip()
            
            # Validasi email
            if '@' not in email:
                results.append({'line': line, 'status': 'error', 'message': 'Email tidak valid'})
                fail_count += 1
                continue
            
            # Format nomor HP
            clean_phone = raw_phone.replace('-', '').replace(' ', '')
            if clean_phone.startswith('0'):
                clean_phone = '62' + clean_phone[1:]
            elif clean_phone.startswith('+'):
                clean_phone = clean_phone[1:]
            
            # Cek apakah email sudah ada
            if User.query.filter_by(email=email).first():
                results.append({'line': line, 'status': 'skip', 'message': 'Email sudah terdaftar'})
                fail_count += 1
                continue
            
            # Generate token & link
            token = str(uuid.uuid4())
            link = url_for('auth.activate', token=token, _external=True)
            
            pesan = (
                f"Halo! Selamat datang di *Sparks Fashion Academy*.\n\n"
                f"Akun Anda telah dibuat. Silakan klik link di bawah ini untuk mengatur password dan jadwal belajar Anda:\n\n"
                f"{link}\n\n"
                f"Terima kasih!"
            )
            target_wa = f"{clean_phone}@s.whatsapp.net"
            
            # Kirim WA
            if send_wa_message(target_wa, pesan):
                try:
                    new_user = User(
                        email=email,
                        phone_number=clean_phone,
                        role='student',
                        activation_token=token,
                        name="New Student"
                    )
                    db.session.add(new_user)
                    db.session.flush()
                    
                    enroll = Enrollment(
                        student_id=new_user.id,
                        program_id=program_id,
                        batch_id=batch_id if prog.is_batch_based else None,
                        status='pending_schedule'
                    )
                    db.session.add(enroll)
                    db.session.commit()
                    
                    results.append({'line': line, 'status': 'success', 'message': f'Berhasil! WA terkirim ke {clean_phone}'})
                    success_count += 1
                except Exception as e:
                    db.session.rollback()
                    results.append({'line': line, 'status': 'error', 'message': f'DB Error: {str(e)}'})
                    fail_count += 1
            else:
                results.append({'line': line, 'status': 'error', 'message': f'Gagal kirim WA ke {clean_phone}'})
                fail_count += 1
        
        flash(f'Selesai! Berhasil: {success_count}, Gagal: {fail_count}', 'info')
    
    return render_template('admin_batch_invite.html', programs=programs, batches=batches, results=results)

# --- ROUTE UNTUK STUDENT REQUEST IZIN ---
@bp.route('/request-izin/<int:booking_id>', methods=['POST'])
@login_required
def request_izin(booking_id):
    from datetime import datetime, timedelta
    
    if current_user.role != 'student':
        flash('Akses ditolak.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get booking and verify ownership
    booking = Booking.query.get_or_404(booking_id)
    if booking.enrollment.student_id != current_user.id:
        flash('Anda tidak memiliki akses ke booking ini.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if booking is still 'booked' status
    if booking.status != 'booked':
        flash(f'Booking ini sudah berstatus "{booking.status}", tidak bisa diizinkan.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Calculate booking datetime
    booking_datetime = datetime.combine(booking.date, booking.timeslot.start_time)
    now = datetime.now()
    time_until_booking = booking_datetime - now
    
    # Check H-1 jam rule: must be at least 1 hour before
    if time_until_booking < timedelta(hours=1):
        flash('Izin harus diajukan minimal 1 jam sebelum jadwal dimulai.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get class enrollment to check izin quota
    ce = booking.class_enrollment
    if ce:
        if ce.program_class.max_izin == 0:
            flash(f'Kelas {ce.program_class.name} tidak memiliki kuota izin.', 'error')
            return redirect(url_for('main.dashboard'))
        
        if ce.izin_remaining <= 0:
            flash(f'Kuota izin untuk kelas {ce.program_class.name} sudah habis.', 'error')
            return redirect(url_for('main.dashboard'))
        
        # Update izin used
        ce.izin_used += 1
    
    # Change booking status to 'izin' (session NOT consumed, will shift to next schedule)
    booking.status = 'izin'
    db.session.commit()
    
    # Send WhatsApp notification to teacher
    if booking.teacher:
        from app.services.notifications import send_teacher_student_izin
        class_name = ce.program_class.name if ce else booking.enrollment.program.name
        send_teacher_student_izin(
            teacher=booking.teacher,
            student_name=current_user.name,
            class_name=class_name,
            booking_date=booking.date
        )
    
    class_name = ce.program_class.name if ce else 'kelas'
    flash(f'Izin berhasil diajukan untuk {class_name} tanggal {booking.date.strftime("%d %b %Y")}. Sesi akan digeser ke jadwal berikutnya.', 'success')
    return redirect(url_for('main.dashboard'))


# --- ROUTE UNTUK STUDENT REQUEST IZIN DARI JADWAL RUTIN ---
@bp.route('/request-izin-schedule', methods=['POST'])
@login_required
def request_izin_schedule():
    """
    Request izin from regular schedule (StudentSchedule).
    Creates a Booking with status='izin' on-the-fly.
    """
    if current_user.role != 'student':
        flash('Akses ditolak.', 'error')
        return redirect(url_for('main.dashboard'))
    
    schedule_id = request.form.get('schedule_id', type=int)
    izin_date_str = request.form.get('izin_date')
    
    if not schedule_id or not izin_date_str:
        flash('Data tidak lengkap.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Parse date
    try:
        izin_date = datetime.strptime(izin_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Format tanggal tidak valid.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get schedule and verify ownership
    schedule = StudentSchedule.query.get_or_404(schedule_id)
    if schedule.enrollment.student_id != current_user.id:
        flash('Anda tidak memiliki akses ke jadwal ini.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Verify date matches schedule day_of_week
    if izin_date.weekday() != schedule.day_of_week:
        flash('Tanggal tidak sesuai dengan hari jadwal.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check H-1 jam rule
    booking_datetime = datetime.combine(izin_date, schedule.timeslot.start_time)
    now = datetime.now()
    time_until_booking = booking_datetime - now
    
    if time_until_booking < timedelta(hours=1):
        flash('Izin harus diajukan minimal 1 jam sebelum jadwal dimulai.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if booking already exists
    existing_booking = Booking.query.filter_by(
        enrollment_id=schedule.enrollment_id,
        date=izin_date,
        timeslot_id=schedule.timeslot_id
    ).first()
    
    if existing_booking:
        flash(f'Sudah ada booking untuk tanggal ini dengan status: {existing_booking.status}', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check izin quota
    ce = schedule.class_enrollment
    if ce:
        if ce.program_class.max_izin == 0:
            flash(f'Kelas {ce.program_class.name} tidak memiliki kuota izin.', 'error')
            return redirect(url_for('main.dashboard'))
        
        if ce.izin_remaining <= 0:
            flash(f'Kuota izin untuk kelas {ce.program_class.name} sudah habis.', 'error')
            return redirect(url_for('main.dashboard'))
        
        # Update izin used
        ce.izin_used += 1
    
    # Create booking with status='izin'
    new_booking = Booking(
        enrollment_id=schedule.enrollment_id,
        class_enrollment_id=schedule.class_enrollment_id,
        date=izin_date,
        timeslot_id=schedule.timeslot_id,
        teacher_id=schedule.teacher_id,
        status='izin'
    )
    db.session.add(new_booking)
    db.session.commit()
    
    # Send WhatsApp notification to teacher
    if schedule.teacher:
        from app.services.notifications import send_teacher_student_izin
        class_name = ce.program_class.name if ce else schedule.enrollment.program.name
        send_teacher_student_izin(
            teacher=schedule.teacher,
            student_name=current_user.name,
            class_name=class_name,
            booking_date=izin_date
        )
    
    class_name = ce.program_class.name if ce else 'kelas'
    flash(f'Izin berhasil diajukan untuk {class_name} tanggal {izin_date.strftime("%d %b %Y")}. Sesi akan digeser ke jadwal berikutnya.', 'success')
    return redirect(url_for('main.dashboard'))