"""
Admin Syllabus Routes
Manage syllabus items per class
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import ProgramClass, Syllabus

bp = Blueprint('admin_syllabus', __name__, url_prefix='/admin/syllabus')


def admin_required(f):
    """Decorator to require admin role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Akses ditolak.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/')
@login_required
@admin_required
def index():
    """List all classes with syllabus count"""
    classes = ProgramClass.query.order_by(ProgramClass.program_id, ProgramClass.order).all()
    
    # Group by program
    programs = {}
    for pc in classes:
        prog_name = pc.program.name
        if prog_name not in programs:
            programs[prog_name] = []
        
        # Calculate total syllabus sessions
        total_syllabus_sessions = sum(s.sessions for s in pc.syllabus_items)
        
        programs[prog_name].append({
            'id': pc.id,
            'name': pc.name,
            'total_sessions': pc.total_sessions,
            'syllabus_count': len(pc.syllabus_items),
            'syllabus_sessions': total_syllabus_sessions,
            'is_complete': total_syllabus_sessions == pc.total_sessions
        })
    
    return render_template('admin/syllabus.html', programs=programs)


@bp.route('/<int:class_id>')
@login_required
@admin_required
def manage(class_id):
    """Manage syllabus for a specific class"""
    program_class = ProgramClass.query.get_or_404(class_id)
    syllabus_items = Syllabus.query.filter_by(program_class_id=class_id).order_by(Syllabus.order).all()
    
    total_syllabus_sessions = sum(s.sessions for s in syllabus_items)
    remaining_sessions = program_class.total_sessions - total_syllabus_sessions
    
    return render_template('admin/syllabus_manage.html',
                           program_class=program_class,
                           syllabus_items=syllabus_items,
                           total_syllabus_sessions=total_syllabus_sessions,
                           remaining_sessions=remaining_sessions)


@bp.route('/<int:class_id>/add', methods=['POST'])
@login_required
@admin_required
def add(class_id):
    """Add a syllabus item"""
    program_class = ProgramClass.query.get_or_404(class_id)
    
    topic_name = request.form.get('topic_name', '').strip()
    sessions = int(request.form.get('sessions', 1))
    
    if not topic_name:
        flash('Nama topik tidak boleh kosong.', 'error')
        return redirect(url_for('admin_syllabus.manage', class_id=class_id))
    
    # Check total sessions
    current_total = sum(s.sessions for s in program_class.syllabus_items)
    if current_total + sessions > program_class.total_sessions:
        flash(f'Total sesi silabus melebihi total sesi kelas ({program_class.total_sessions}).', 'error')
        return redirect(url_for('admin_syllabus.manage', class_id=class_id))
    
    # Get next order
    max_order = db.session.query(db.func.max(Syllabus.order)).filter_by(program_class_id=class_id).scalar() or 0
    
    syllabus = Syllabus(
        program_class_id=class_id,
        topic_name=topic_name,
        sessions=sessions,
        order=max_order + 1
    )
    db.session.add(syllabus)
    db.session.commit()
    
    flash(f'Topik "{topic_name}" berhasil ditambahkan.', 'success')
    return redirect(url_for('admin_syllabus.manage', class_id=class_id))


@bp.route('/<int:class_id>/edit/<int:syllabus_id>', methods=['POST'])
@login_required
@admin_required
def edit(class_id, syllabus_id):
    """Edit a syllabus item"""
    syllabus = Syllabus.query.get_or_404(syllabus_id)
    program_class = ProgramClass.query.get_or_404(class_id)
    
    topic_name = request.form.get('topic_name', '').strip()
    sessions = int(request.form.get('sessions', 1))
    
    if not topic_name:
        flash('Nama topik tidak boleh kosong.', 'error')
        return redirect(url_for('admin_syllabus.manage', class_id=class_id))
    
    # Check total sessions (excluding current item)
    current_total = sum(s.sessions for s in program_class.syllabus_items if s.id != syllabus_id)
    if current_total + sessions > program_class.total_sessions:
        flash(f'Total sesi silabus melebihi total sesi kelas ({program_class.total_sessions}).', 'error')
        return redirect(url_for('admin_syllabus.manage', class_id=class_id))
    
    syllabus.topic_name = topic_name
    syllabus.sessions = sessions
    db.session.commit()
    
    flash(f'Topik "{topic_name}" berhasil diperbarui.', 'success')
    return redirect(url_for('admin_syllabus.manage', class_id=class_id))


@bp.route('/<int:class_id>/delete/<int:syllabus_id>', methods=['POST'])
@login_required
@admin_required
def delete(class_id, syllabus_id):
    """Delete a syllabus item"""
    syllabus = Syllabus.query.get_or_404(syllabus_id)
    topic_name = syllabus.topic_name
    
    db.session.delete(syllabus)
    db.session.commit()
    
    flash(f'Topik "{topic_name}" berhasil dihapus.', 'success')
    return redirect(url_for('admin_syllabus.manage', class_id=class_id))
