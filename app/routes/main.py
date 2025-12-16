from app.utils.whatsapp import send_wa_message
from flask import Blueprint, render_template, request, flash, url_for, redirect
from flask_login import login_required, current_user
from app.models import User, Enrollment, Program, Batch # Tambah import Batch
from app import db
import uuid

bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def dashboard():
    enrollment = Enrollment.query.filter_by(student_id=current_user.id).first()
    
    # Mapping Hari
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    
    return render_template('dashboard.html', 
                           enrollment=enrollment, 
                           days=days)

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
            
        # 2. Generate Token & Create User
        token = str(uuid.uuid4())
        
        # Cek apakah email sudah ada
        if User.query.filter_by(email=email).first():
            flash('Email sudah terdaftar!')
            return redirect(url_for('main.admin_invite'))

        new_user = User(
            email=email, 
            phone_number=clean_phone, # Simpan format 628xx
            role='student', 
            activation_token=token,
            name="New Student" # Placeholder name
        )
        db.session.add(new_user)
        db.session.flush() # Get ID
        
        # 3. Create Enrollment
        prog = Program.query.get(program_id)
        batch_id = request.form.get('batch_id') if prog.is_batch_based else None
        
        enroll = Enrollment(
            student_id=new_user.id,
            program_id=program_id,
            batch_id=batch_id,
            sessions_remaining=prog.total_sessions if not prog.is_batch_based else 0
        )
        db.session.add(enroll)
        db.session.commit()
        
        # 4. KIRIM WHATSAPP
        # Generate Link Full (http://domain.com/activate/token)
        link = url_for('auth.activate', token=token, _external=True)
        
        pesan = (
            f"Halo! Selamat datang di *Fashion School*.\n\n"
            f"Akun Anda telah dibuat. Silakan klik link di bawah ini untuk mengatur password dan jadwal belajar Anda:\n\n"
            f"{link}\n\n"
            f"Terima kasih!"
        )
        
        # Kirim ke nomor user (tambah suffix sesuai library aldinokemal)
        target_wa = f"{clean_phone}@s.whatsapp.net"
        
        if send_wa_message(target_wa, pesan):
            flash(f'Sukses! Link aktivasi dikirim ke WA {clean_phone}')
        else:
            flash(f'User dibuat, TAPI Gagal kirim WA ke {clean_phone}. Cek bot.')
            
        return redirect(url_for('main.admin_invite'))

    programs = Program.query.all()
    batches = Batch.query.filter_by(is_active=True).all()
    return render_template('admin_invite.html', programs=programs, batches=batches)