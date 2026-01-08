from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User, Enrollment, ClassEnrollment

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Email atau password salah.')
        
    return render_template('login.html')

@bp.route('/activate/<token>', methods=['GET', 'POST'])
def activate(token):
    user = User.query.filter_by(activation_token=token).first_or_404()
    
    if request.method == 'POST':
        user.set_password(request.form['password'])
        user.activation_token = None
        user.name = request.form['name']
        
        # Student Profile Fields
        user.nik = request.form.get('nik')
        user.alamat = request.form.get('alamat')
        
        # Parse tanggal lahir
        tanggal_lahir_str = request.form.get('tanggal_lahir')
        if tanggal_lahir_str:
            from datetime import datetime
            user.tanggal_lahir = datetime.strptime(tanggal_lahir_str, '%Y-%m-%d').date()
        
        user.agama = request.form.get('agama')
        user.pekerjaan = request.form.get('pekerjaan')
        user.status_pernikahan = request.form.get('status_pernikahan')
        user.mengetahui_sfa_dari = request.form.get('mengetahui_sfa_dari')
        user.alasan_memilih_sfa = request.form.get('alasan_memilih_sfa')
        
        # Update phone number jika diisi
        phone = request.form.get('phone_number')
        if phone:
            clean_phone = phone.strip().replace('-', '').replace(' ', '')
            if clean_phone.startswith('0'):
                clean_phone = '62' + clean_phone[1:]
            elif clean_phone.startswith('+'):
                clean_phone = clean_phone[1:]
            user.phone_number = clean_phone
        
        db.session.commit()
        
        login_user(user)
        
        # Get enrollment and create ClassEnrollments
        enroll = Enrollment.query.filter_by(student_id=user.id).first()
        
        # Auto-create ClassEnrollments for each class in the program
        if enroll and enroll.program.classes:
            for program_class in enroll.program.classes:
                # Check if ClassEnrollment already exists
                existing = ClassEnrollment.query.filter_by(
                    enrollment_id=enroll.id,
                    program_class_id=program_class.id
                ).first()
                
                if not existing:
                    class_enroll = ClassEnrollment(
                        enrollment_id=enroll.id,
                        program_class_id=program_class.id,
                        sessions_remaining=program_class.total_sessions,
                        status='active'
                    )
                    db.session.add(class_enroll)
            db.session.commit()
            
            # === AUTO CREATE GOOGLE DRIVE FOLDERS ===
            try:
                from app.services.google_drive import get_drive_service
                drive_service = get_drive_service()
                
                if drive_service.service:
                    # Create student root folder
                    student_folder_id = drive_service.create_folder(user.name)
                    user.drive_folder_id = student_folder_id
                    
                    # Create program folder
                    program_folder_id = drive_service.create_folder(
                        enroll.program.name, 
                        student_folder_id
                    )
                    
                    # Create class folders for each ClassEnrollment
                    for ce in enroll.class_enrollments:
                        class_folder_id = drive_service.create_folder(
                            ce.program_class.name,
                            program_folder_id
                        )
                        # Note: could save class_folder_id to ClassEnrollment if needed
                    
                    db.session.commit()
                    flash(f'Folder Google Drive berhasil dibuat untuk {user.name}!', 'success')
            except Exception as e:
                # Log error but don't block activation
                print(f"Error creating Drive folders: {e}")
                flash('Akun berhasil diaktivasi. (Google Drive folder creation skipped)', 'warning')
        
        # Check if ALL classes are batch-based (then skip schedule wizard)
        all_batch_based = all(c.is_batch_based for c in enroll.program.classes) if enroll.program.classes else False
        
        if enroll.program.is_batch_based or all_batch_based:
            # Batch-based program: langsung ke dashboard
            enroll.status = 'active'
            db.session.commit()
            return redirect(url_for('main.dashboard'))
        else:
            # Regular program: masuk ke Wizard Jadwal
            return redirect(url_for('onboarding.schedule_wizard'))
            
    return render_template('activate.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
