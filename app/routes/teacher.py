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
    
    # === PORTFOLIO DATA FOR TAB ===
    from app.models import Syllabus, Portfolio
    portfolio_data = []
    
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
        
        portfolio_data.append({
            'class_enrollment': ce,
            'program_class': ce.program_class,
            'syllabus_items': syllabus_with_status,
            'completed_topics': completed_topics,
            'total_topics': len(syllabus_items),
            'sessions_completed': sessions_completed
        })
    
    # === CLASS PROGRESS DATA ===
    class_progress = []
    for ce in enrollment.class_enrollments:
        total = ce.program_class.total_sessions
        remaining = ce.sessions_remaining or 0
        completed = total - remaining
        progress_pct_class = int((completed / total) * 100) if total > 0 else 0
        
        # Get bookings for this class
        class_bookings = Booking.query.filter_by(class_enrollment_id=ce.id).all()
        class_booking_ids = [b.id for b in class_bookings]
        
        # Attendance stats
        hadir = Attendance.query.filter(
            Attendance.booking_id.in_(class_booking_ids),
            Attendance.status == 'Hadir'
        ).count() if class_booking_ids else 0
        
        izin = Attendance.query.filter(
            Attendance.booking_id.in_(class_booking_ids),
            Attendance.status == 'Izin'
        ).count() if class_booking_ids else 0
        
        alpha = Attendance.query.filter(
            Attendance.booking_id.in_(class_booking_ids),
            Attendance.status == 'Alpha'
        ).count() if class_booking_ids else 0
        
        # Recent attendances (last 5)
        recent_attendances = []
        recent_att_records = Attendance.query.filter(
            Attendance.booking_id.in_(class_booking_ids)
        ).order_by(Attendance.date.desc()).limit(5).all() if class_booking_ids else []
        
        for att in recent_att_records:
            recent_attendances.append({
                'date': att.date,
                'status': att.status,
                'teacher': att.teacher.name if att.teacher else '-',
                'notes': att.notes
            })
        
        # Get current topic from syllabus
        current_topic = None
        syllabus_items = Syllabus.query.filter_by(
            program_class_id=ce.program_class_id
        ).order_by(Syllabus.order).all()
        
        cumulative = 0
        for s in syllabus_items:
            prev_cumulative = cumulative
            cumulative += s.sessions
            if completed < cumulative:
                # Calculate which session within this topic (1-indexed)
                session_in_topic = completed - prev_cumulative + 1
                if s.sessions > 1:
                    current_topic = f"{s.topic_name} - {session_in_topic}"
                else:
                    current_topic = s.topic_name
                break
        else:
            # All topics completed
            if syllabus_items:
                current_topic = syllabus_items[-1].topic_name + " (Selesai)"
        
        class_progress.append({
            'class_enrollment_id': ce.id,
            'class_name': ce.program_class.name,
            'total_sessions': total,
            'completed_sessions': completed,
            'sessions_remaining': remaining,
            'progress_pct': progress_pct_class,
            'max_izin': ce.program_class.max_izin,
            'izin_used': ce.izin_used,
            'izin_remaining': ce.izin_remaining,
            'stats': {
                'hadir': hadir,
                'izin': izin,
                'alpha': alpha
            },
            'recent_attendances': recent_attendances,
            'status': ce.status,
            'current_topic': current_topic
        })
    
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
                           days=days,
                           portfolio_data=portfolio_data,
                           class_progress=class_progress)
