from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app import db
from app.models import User, Enrollment, Attendance, AttendanceRequest, RescheduleRequest, Voucher
from datetime import datetime
import re

bp = Blueprint('profile', __name__, url_prefix='/profile')


def validate_phone_number(phone):
    """
    Validate and format phone number to Indonesian WA format (62xxxxxxxxxx).
    Returns (is_valid, formatted_number, error_message)
    """
    if not phone:
        return True, None, None
    
    # Remove spaces, dashes, and other non-digit characters except +
    clean_phone = re.sub(r'[^\d+]', '', phone.strip())
    
    # Convert to 62 format
    if clean_phone.startswith('+62'):
        clean_phone = clean_phone[1:]  # Remove +
    elif clean_phone.startswith('0'):
        clean_phone = '62' + clean_phone[1:]
    elif not clean_phone.startswith('62'):
        clean_phone = '62' + clean_phone
    
    # Remove the leading 62 for length check
    number_part = clean_phone[2:] if clean_phone.startswith('62') else clean_phone
    
    # Validate length (Indonesian mobile numbers are typically 9-12 digits after country code)
    if len(number_part) < 9 or len(number_part) > 13:
        return False, None, "Nomor telepon harus 10-15 digit"
    
    # Check if it's all digits
    if not clean_phone.isdigit():
        return False, None, "Nomor telepon hanya boleh berisi angka"
    
    return True, clean_phone, None


def validate_email(email, current_user_id):
    """
    Validate email format and uniqueness.
    Returns (is_valid, error_message)
    """
    if not email:
        return False, "Email wajib diisi"
    
    # Basic email format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email.strip().lower()):
        return False, "Format email tidak valid"
    
    # Check uniqueness (excluding current user)
    existing = User.query.filter(
        User.email == email.strip().lower(),
        User.id != current_user_id
    ).first()
    if existing:
        return False, "Email sudah digunakan oleh pengguna lain"
    
    return True, None


@bp.route('/')
@login_required
def index():
    """Main profile page"""
    admin_stats = None
    
    if current_user.role == 'admin':
        # Get admin statistics
        admin_stats = get_admin_stats(current_user.id)
    
    return render_template('profile/index.html', admin_stats=admin_stats)


@bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    """Edit basic profile (name, phone, email for admin)"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone_number', '').strip()
        
        errors = []
        
        # Validate name
        if not name:
            errors.append("Nama wajib diisi")
        
        # Validate phone
        is_valid, formatted_phone, phone_error = validate_phone_number(phone)
        if not is_valid:
            errors.append(phone_error)
        
        # Admin can edit email
        if current_user.role == 'admin':
            email = request.form.get('email', '').strip().lower()
            is_valid, email_error = validate_email(email, current_user.id)
            if not is_valid:
                errors.append(email_error)
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('profile/edit.html')
        
        # Update user data
        current_user.name = name
        current_user.phone_number = formatted_phone
        
        if current_user.role == 'admin':
            current_user.email = email
        
        db.session.commit()
        flash('Profil berhasil diperbarui!', 'success')
        return redirect(url_for('profile.index'))
    
    return render_template('profile/edit.html')


@bp.route('/edit-details', methods=['GET', 'POST'])
@login_required
def edit_details():
    """Edit student-specific details (only for students)"""
    if current_user.role != 'student':
        flash('Halaman ini hanya untuk siswa', 'error')
        return redirect(url_for('profile.index'))
    
    if request.method == 'POST':
        errors = []
        
        # Get form data
        nik = request.form.get('nik', '').strip()
        alamat = request.form.get('alamat', '').strip()
        tanggal_lahir_str = request.form.get('tanggal_lahir', '')
        agama = request.form.get('agama', '').strip()
        pekerjaan = request.form.get('pekerjaan', '').strip()
        status_pernikahan = request.form.get('status_pernikahan', '').strip()
        mengetahui_sfa_dari = request.form.get('mengetahui_sfa_dari', '').strip()
        alasan_memilih_sfa = request.form.get('alasan_memilih_sfa', '').strip()
        
        # Validate NIK (16 digits)
        if nik and (not nik.isdigit() or len(nik) != 16):
            errors.append("NIK harus 16 digit angka")
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('profile/edit_details.html')
        
        # Update student details
        current_user.nik = nik if nik else None
        current_user.alamat = alamat if alamat else None
        
        if tanggal_lahir_str:
            try:
                current_user.tanggal_lahir = datetime.strptime(tanggal_lahir_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        current_user.agama = agama if agama else None
        current_user.pekerjaan = pekerjaan if pekerjaan else None
        current_user.status_pernikahan = status_pernikahan if status_pernikahan else None
        current_user.mengetahui_sfa_dari = mengetahui_sfa_dari if mengetahui_sfa_dari else None
        current_user.alasan_memilih_sfa = alasan_memilih_sfa if alasan_memilih_sfa else None
        
        db.session.commit()
        flash('Detail profil berhasil diperbarui!', 'success')
        return redirect(url_for('profile.index'))
    
    return render_template('profile/edit_details.html')


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password form"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        
        # Validate current password
        if not current_user.check_password(current_password):
            errors.append("Password saat ini salah")
        
        # Validate new password
        if len(new_password) < 8:
            errors.append("Password baru minimal 8 karakter")
        
        # Validate confirmation
        if new_password != confirm_password:
            errors.append("Konfirmasi password tidak cocok")
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('profile/change_password.html')
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Password berhasil diubah!', 'success')
        return redirect(url_for('profile.index'))
    
    return render_template('profile/change_password.html')


def get_admin_stats(admin_id):
    """Get statistics for admin activity"""
    stats = {}
    
    # Count students invited by this admin
    # Students are created through main.admin_invite, we can check by looking at total students
    stats['total_students'] = User.query.filter_by(role='student').count()
    
    # Count attendance requests approved by this admin
    stats['attendance_approved'] = AttendanceRequest.query.filter_by(
        approved_by=admin_id,
        approval_status='approved'
    ).count()
    
    # Count reschedule requests approved by this admin
    stats['reschedule_approved'] = RescheduleRequest.query.filter_by(
        approved_by=admin_id,
        status='approved'
    ).count()
    
    # Count vouchers created by this admin
    stats['vouchers_created'] = Voucher.query.filter_by(created_by=admin_id).count()
    
    # Pending counts
    stats['attendance_pending'] = AttendanceRequest.query.filter_by(approval_status='pending').count()
    stats['reschedule_pending'] = RescheduleRequest.query.filter_by(status='pending').count()
    
    return stats
