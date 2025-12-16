from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from app import db
from app.models import TimeSlot
from app.models import Attendance, Enrollment, User, Booking
from app.utils.whatsapp import send_wa_message
from datetime import date

bp = Blueprint('attendance', __name__, url_prefix='/attendance')

# ID GROUP WA (Bisa ditaruh di .env)
# Cara tau ID Group: Gunakan endpoint /api/my/groups di bot aldinokemal nanti
WA_GROUP_ID = "1234567890-16123456@g.us" 

@bp.route('/submit', methods=['POST'])
@login_required
def submit_attendance():
    if current_user.role != 'teacher':
        return "Access Denied"

    # Data dari Form HTML Absensi
    # Anggap form mengirim list: student_ids[], statuses[] (Hadir/Izin/Alpha)
    booking_ids = request.form.getlist('booking_ids')
    program_name = request.form.get('program_name') # Misal: FF Design
    
    hadir_count = 0
    izin_count = 0
    alpha_count = 0
    list_nama_hadir = []

    for b_id in booking_ids:
        booking = Booking.query.get(b_id)
        status = request.form.get(f'status_{b_id}') # Hadir/Izin
        notes = request.form.get(f'notes_{b_id}')
        
        # 1. Simpan ke Database
        attendance = Attendance(
            booking_id=booking.id,
            teacher_id=current_user.id,
            date=date.today(),
            status=status,
            notes=notes
        )
        db.session.add(attendance)
        
        # 2. Update Sisa Sesi Siswa (Jika Hadir)
        if status == 'Hadir':
            booking.enrollment.sessions_remaining -= 1
            hadir_count += 1
            list_nama_hadir.append(booking.enrollment.student.name)
        elif status == 'Izin':
            izin_count += 1
        else:
            alpha_count += 1
            
        # Tandai booking selesai
        booking.status = 'completed'

    db.session.commit()

    # --- LOGIKA REKAP KE GROUP WA ---
    today_str = date.today().strftime("%d-%m-%Y")
    teacher_name = current_user.name
    
    pesan_rekap = (
        f"📋 *LAPORAN SESI {program_name}*\n"
        f"📅 Tanggal: {today_str}\n"
        f"👩‍🏫 Pengajar: {teacher_name}\n\n"
        f"✅ Hadir: {hadir_count}\n"
        f"⚠️ Izin: {izin_count}\n"
        f"❌ Alpha: {alpha_count}\n\n"
        f"Siswa Hadir:\n"
        + "\n".join([f"- {name}" for name in list_nama_hadir])
    )

    # Kirim ke Group
    send_wa_message(WA_GROUP_ID, pesan_rekap)
    # --------------------------------

    flash('Absensi berhasil disimpan & Rekap dikirim ke WA Group!')
    return redirect(url_for('main.dashboard'))

@bp.route('/view/<int:timeslot_id>', methods=['GET'])
@login_required
def view_form(timeslot_id):
    if current_user.role != 'teacher':
        return "Access Denied"
    
    today = date.today()
    timeslot = TimeSlot.query.get_or_404(timeslot_id)
    
    # Ambil semua booking hari ini di jam ini yang belum selesai
    bookings = Booking.query.filter_by(
        date=today, 
        timeslot_id=timeslot_id
    ).filter(Booking.status != 'completed').all()
    
    return render_template(
        'attendance_form.html', 
        bookings=bookings, 
        timeslot=timeslot,
        today_date=today.strftime("%d %B %Y")
    )