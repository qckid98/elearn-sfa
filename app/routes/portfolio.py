from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import ClassEnrollment, Syllabus, Portfolio
from werkzeug.utils import secure_filename
import io

bp = Blueprint('portfolio', __name__, url_prefix='/portfolio')

def student_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'student':
            flash('Akses ditolak.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@login_required
@student_required
def index():
    """Show all classes with syllabus and portfolio status"""
    from app.models import Enrollment
    
    enrollment = Enrollment.query.filter_by(student_id=current_user.id).first()
    if not enrollment:
        flash('Anda belum terdaftar di program manapun.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    # Get all class enrollments with syllabus data
    class_data = []
    for ce in enrollment.class_enrollments:
        syllabus_items = Syllabus.query.filter_by(
            program_class_id=ce.program_class_id
        ).order_by(Syllabus.order).all()
        
        # Calculate completion based on sessions
        total = ce.program_class.total_sessions
        remaining = ce.sessions_remaining or 0
        sessions_completed = total - remaining
        cumulative = 0
        completed_topics = 0
        
        syllabus_with_status = []
        for s in syllabus_items:
            cumulative += s.sessions
            is_complete = sessions_completed >= cumulative
            is_current = not is_complete and sessions_completed >= (cumulative - s.sessions)
            
            # Get portfolio for this syllabus item
            portfolio = Portfolio.query.filter_by(
                class_enrollment_id=ce.id,
                syllabus_id=s.id
            ).first()
            
            syllabus_with_status.append({
                'syllabus': s,
                'is_complete': is_complete,
                'is_current': is_current,
                'portfolio': portfolio,
                'cumulative_end': cumulative
            })
            
            if is_complete:
                completed_topics += 1
        
        class_data.append({
            'class_enrollment': ce,
            'program_class': ce.program_class,
            'syllabus_items': syllabus_with_status,
            'completed_topics': completed_topics,
            'total_topics': len(syllabus_items),
            'sessions_completed': sessions_completed
        })
    
    return render_template('student/portfolio.html',
                           enrollment=enrollment,
                           class_data=class_data)

@bp.route('/upload/<int:syllabus_id>', methods=['GET', 'POST'])
@login_required
@student_required
def upload(syllabus_id):
    """Upload portfolio for a specific syllabus topic"""
    from app.models import Enrollment
    
    syllabus = Syllabus.query.get_or_404(syllabus_id)
    
    # Find the class enrollment for current user
    enrollment = Enrollment.query.filter_by(student_id=current_user.id).first()
    if not enrollment:
        flash('Anda belum terdaftar di program manapun.', 'error')
        return redirect(url_for('portfolio.index'))
    
    class_enrollment = ClassEnrollment.query.filter_by(
        enrollment_id=enrollment.id,
        program_class_id=syllabus.program_class_id
    ).first()
    
    if not class_enrollment:
        flash('Anda tidak terdaftar di kelas ini.', 'error')
        return redirect(url_for('portfolio.index'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Tidak ada file yang dipilih.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Tidak ada file yang dipilih.', 'error')
            return redirect(request.url)
        
        if file:
            filename = secure_filename(file.filename)
            
            # Upload to Google Drive
            try:
                from app.services.google_drive import get_drive_service
                drive_service = get_drive_service()
                
                if drive_service.service:
                    # Read file content
                    file_content = file.read()
                    file_stream = io.BytesIO(file_content)
                    
                    # Get folder structure: Student > Program > Class
                    student_folder_id = current_user.drive_folder_id
                    
                    if not student_folder_id:
                        flash('Folder Google Drive belum dikonfigurasi untuk akun Anda.', 'error')
                        return redirect(url_for('portfolio.index'))
                    
                    # Find or create Program folder
                    program_name = class_enrollment.enrollment.program.name
                    program_folder_id = drive_service.find_or_create_folder(program_name, student_folder_id)
                    
                    # Find or create Class folder
                    class_name = class_enrollment.program_class.name
                    class_folder_id = drive_service.find_or_create_folder(class_name, program_folder_id)
                    
                    # Upload file to class folder
                    result = drive_service.upload_file(
                        file_stream,
                        filename,
                        class_folder_id,
                        file.content_type or 'application/octet-stream'
                    )
                    
                    # Save portfolio record
                    portfolio = Portfolio(
                        class_enrollment_id=class_enrollment.id,
                        syllabus_id=syllabus.id,
                        file_name=filename,
                        drive_file_id=result['id'],
                        drive_url=result['url']
                    )
                    db.session.add(portfolio)
                    db.session.commit()
                    
                    flash(f'Portfolio "{filename}" berhasil diupload!', 'success')
                    return redirect(url_for('portfolio.index'))
                else:
                    flash('Google Drive service tidak tersedia.', 'error')
            except Exception as e:
                flash(f'Error uploading: {str(e)}', 'error')
                print(f"Upload error: {e}")
    
    # GET request - show upload form
    return render_template('student/portfolio_upload.html',
                           syllabus=syllabus,
                           class_enrollment=class_enrollment)

@bp.route('/delete/<int:portfolio_id>', methods=['POST'])
@login_required
@student_required
def delete(portfolio_id):
    """Delete a portfolio item"""
    portfolio = Portfolio.query.get_or_404(portfolio_id)
    
    # Verify ownership
    if portfolio.class_enrollment.enrollment.student_id != current_user.id:
        flash('Akses ditolak.', 'error')
        return redirect(url_for('portfolio.index'))
    
    # Delete from Google Drive
    try:
        from app.services.google_drive import get_drive_service
        drive_service = get_drive_service()
        
        if drive_service.service and portfolio.drive_file_id:
            drive_service.delete_file(portfolio.drive_file_id)
    except Exception as e:
        print(f"Error deleting from Drive: {e}")
    
    # Delete from database
    filename = portfolio.file_name
    db.session.delete(portfolio)
    db.session.commit()
    
    flash(f'Portfolio "{filename}" berhasil dihapus.', 'success')
    return redirect(url_for('portfolio.index'))
