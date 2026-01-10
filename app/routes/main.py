from app.utils.whatsapp import send_wa_message
from flask import Blueprint, render_template, request, flash, url_for, redirect
from flask_login import login_required, current_user
from app.models import User, Enrollment, Program, Batch, Booking, Attendance, ClassEnrollment
from app import db
import uuid
from datetime import date

bp = Blueprint('main', __name__)

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
                'class_enrollments': class_enrollments_data
            }
            enrollments_data.append(enroll_progress)
        
        # For backward compatibility - use first enrollment's progress
        if enrollments_data:
            student_progress = enrollments_data[0]
    
    # Teacher Calendar Data
    teacher_calendar_events = []
    if current_user.role == 'teacher':
        # Get all bookings for this teacher (past and future)
        teacher_bookings = Booking.query.filter(
            Booking.teacher_id == current_user.id
        ).order_by(Booking.date).all()
        
        for booking in teacher_bookings:
            # Determine event color based on status
            if booking.status == 'completed':
                color = '#28a745'  # Green for completed
            elif booking.status == 'cancelled':
                color = '#6c757d'  # Gray for cancelled
            else:
                color = '#007bff'  # Blue for upcoming/booked
            
            # Build event data for FullCalendar
            event = {
                'id': booking.id,
                'title': f"{booking.enrollment.student.name}",
                'start': f"{booking.date}T{booking.timeslot.start_time.strftime('%H:%M:%S')}",
                'end': f"{booking.date}T{booking.timeslot.end_time.strftime('%H:%M:%S')}",
                'color': color,
                'extendedProps': {
                    'student': booking.enrollment.student.name,
                    'subject': booking.subject.name if booking.subject else '-',
                    'timeslot': booking.timeslot.name,
                    'status': booking.status,
                    'program': booking.enrollment.program.name
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
        
        stats = {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_programs': total_programs,
            'total_sessions': total_sessions
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
    
    class_name = ce.program_class.name if ce else 'kelas'
    flash(f'Izin berhasil diajukan untuk {class_name} tanggal {booking.date.strftime("%d %b %Y")}. Sesi akan digeser ke jadwal berikutnya.', 'success')
    return redirect(url_for('main.dashboard'))