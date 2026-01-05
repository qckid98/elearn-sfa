from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from app.models import User, Enrollment, Booking, Attendance, StudentSchedule
from sqlalchemy import func
from datetime import date

bp = Blueprint('teacher', __name__, url_prefix='/teacher')


def get_teacher_students(teacher_id):
    """Get all unique students taught by this teacher"""
    # Find students through StudentSchedule (regular schedules)
    schedule_students = User.query.join(
        Enrollment, User.id == Enrollment.student_id
    ).join(
        StudentSchedule, Enrollment.id == StudentSchedule.enrollment_id
    ).filter(
        StudentSchedule.teacher_id == teacher_id
    ).distinct().all()
    
    # Find students through Bookings (including manual overrides)
    booking_students = User.query.join(
        Enrollment, User.id == Enrollment.student_id
    ).join(
        Booking, Enrollment.id == Booking.enrollment_id
    ).filter(
        Booking.teacher_id == teacher_id
    ).distinct().all()
    
    # Combine and deduplicate
    all_students = {s.id: s for s in schedule_students}
    for s in booking_students:
        all_students[s.id] = s
    
    return list(all_students.values())


@bp.route('/students')
@login_required
def student_list():
    """Teacher view: List all students they teach"""
    if current_user.role != 'teacher':
        abort(403)
    
    students = get_teacher_students(current_user.id)
    
    # Get summary stats for each student
    student_data = []
    for student in students:
        enrollment = Enrollment.query.filter_by(student_id=student.id).first()
        if not enrollment:
            continue
        
        # Count completed sessions
        completed_count = Booking.query.filter(
            Booking.enrollment_id == enrollment.id,
            Booking.teacher_id == current_user.id,
            Booking.status == 'completed'
        ).count()
        
        # Count total sessions with this teacher
        total_sessions = Booking.query.filter(
            Booking.enrollment_id == enrollment.id,
            Booking.teacher_id == current_user.id
        ).count()
        
        # Count attendance stats
        attendance_stats = Attendance.query.join(
            Booking, Attendance.booking_id == Booking.id
        ).filter(
            Booking.enrollment_id == enrollment.id,
            Booking.teacher_id == current_user.id
        ).with_entities(
            Attendance.status, func.count(Attendance.id)
        ).group_by(Attendance.status).all()
        
        attendance_dict = dict(attendance_stats)
        
        student_data.append({
            'student': student,
            'enrollment': enrollment,
            'completed': completed_count,
            'total': total_sessions,
            'hadir': attendance_dict.get('Hadir', 0),
            'izin': attendance_dict.get('Izin', 0),
            'alpha': attendance_dict.get('Alpha', 0),
            'progress_pct': round((completed_count / enrollment.program.total_sessions * 100) if enrollment.program.total_sessions > 0 else 0, 1)
        })
    
    return render_template('teacher/student_list.html', students=student_data)


@bp.route('/students/<int:student_id>/progress')
@login_required
def student_progress(student_id):
    """Teacher view: Detailed progress for a specific student"""
    if current_user.role != 'teacher':
        abort(403)
    
    student = User.query.get_or_404(student_id)
    enrollment = Enrollment.query.filter_by(student_id=student_id).first()
    
    if not enrollment:
        abort(404)
    
    # Verify this teacher actually teaches this student
    teacher_students = get_teacher_students(current_user.id)
    if student not in teacher_students:
        abort(403)
    
    # Get all bookings for this student with this teacher
    bookings = Booking.query.filter(
        Booking.enrollment_id == enrollment.id,
        Booking.teacher_id == current_user.id
    ).order_by(Booking.date.desc()).all()
    
    # Build session history with attendance
    session_history = []
    for booking in bookings:
        session_history.append({
            'date': booking.date,
            'subject': booking.subject.name if booking.subject else '-',
            'timeslot': booking.timeslot.name if booking.timeslot else '-',
            'status': booking.status,
            'attendance': booking.attendance.status if booking.attendance else None,
            'notes': booking.attendance.notes if booking.attendance else None
        })
    
    # Calculate summary stats
    total_program_sessions = enrollment.program.total_sessions
    completed_sessions = sum(1 for s in session_history if s['status'] == 'completed')
    remaining_sessions = enrollment.sessions_remaining
    
    attendance_summary = {
        'hadir': sum(1 for s in session_history if s['attendance'] == 'Hadir'),
        'izin': sum(1 for s in session_history if s['attendance'] == 'Izin'),
        'alpha': sum(1 for s in session_history if s['attendance'] == 'Alpha')
    }
    
    progress_pct = round((completed_sessions / total_program_sessions * 100) if total_program_sessions > 0 else 0, 1)
    
    # Get student's regular schedule with this teacher
    schedules = StudentSchedule.query.filter(
        StudentSchedule.enrollment_id == enrollment.id,
        StudentSchedule.teacher_id == current_user.id
    ).all()
    
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    
    return render_template('teacher/student_progress.html',
                           student=student,
                           enrollment=enrollment,
                           session_history=session_history,
                           completed_sessions=completed_sessions,
                           remaining_sessions=remaining_sessions,
                           total_program_sessions=total_program_sessions,
                           progress_pct=progress_pct,
                           attendance_summary=attendance_summary,
                           schedules=schedules,
                           days=days)
