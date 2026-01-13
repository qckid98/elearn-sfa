"""
APScheduler Jobs for WhatsApp Notifications
Runs background jobs for scheduled notifications.
"""
import os
import logging
from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Configure logging
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Timezone for scheduling
TIMEZONE = pytz.timezone('Asia/Jakarta')

# Scheduler instance (singleton)
scheduler = None


def get_scheduler():
    """Get or create scheduler instance."""
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler(timezone=TIMEZONE)
    return scheduler


def job_student_reminder_h1():
    """
    Send H-1 reminders to all students who have bookings tomorrow.
    Runs daily at 18:00 WIB.
    """
    from app import create_app, db
    from app.models import Booking, User
    from app.services.notifications import send_student_reminder_h1
    
    app = create_app()
    with app.app_context():
        tomorrow = date.today() + timedelta(days=1)
        
        # Find all bookings for tomorrow
        bookings = Booking.query.filter_by(
            date=tomorrow,
            status='booked'
        ).all()
        
        # Group bookings by student
        student_bookings = {}
        for booking in bookings:
            student_id = booking.enrollment.student_id
            if student_id not in student_bookings:
                student_bookings[student_id] = []
            student_bookings[student_id].append(booking)
        
        # Send reminders
        sent_count = 0
        for student_id, bookings_list in student_bookings.items():
            student = User.query.get(student_id)
            if student and send_student_reminder_h1(student, bookings_list):
                sent_count += 1
        
        logger.info(f"[H-1 Student] Sent {sent_count} reminders for {tomorrow}")


def job_student_reminder_hday():
    """
    Send same-day morning reminders to all students who have bookings today.
    Runs daily at 07:00 WIB.
    """
    from app import create_app, db
    from app.models import Booking, User
    from app.services.notifications import send_student_reminder_hday
    
    app = create_app()
    with app.app_context():
        today = date.today()
        
        # Find all bookings for today
        bookings = Booking.query.filter_by(
            date=today,
            status='booked'
        ).all()
        
        # Group bookings by student
        student_bookings = {}
        for booking in bookings:
            student_id = booking.enrollment.student_id
            if student_id not in student_bookings:
                student_bookings[student_id] = []
            student_bookings[student_id].append(booking)
        
        # Send reminders
        sent_count = 0
        for student_id, bookings_list in student_bookings.items():
            student = User.query.get(student_id)
            if student and send_student_reminder_hday(student, bookings_list):
                sent_count += 1
        
        logger.info(f"[H-Day Student] Sent {sent_count} reminders for {today}")


def job_teacher_reminder_h1():
    """
    Send H-1 reminders to all teachers who have teaching sessions tomorrow.
    Runs daily at 18:00 WIB.
    """
    from app import create_app, db
    from app.models import Booking, User
    from app.services.notifications import send_teacher_reminder_h1
    
    app = create_app()
    with app.app_context():
        tomorrow = date.today() + timedelta(days=1)
        
        # Find all bookings for tomorrow
        bookings = Booking.query.filter_by(
            date=tomorrow,
            status='booked'
        ).all()
        
        # Group bookings by teacher
        teacher_bookings = {}
        for booking in bookings:
            teacher_id = booking.teacher_id
            if teacher_id:
                if teacher_id not in teacher_bookings:
                    teacher_bookings[teacher_id] = []
                teacher_bookings[teacher_id].append(booking)
        
        # Send reminders
        sent_count = 0
        for teacher_id, bookings_list in teacher_bookings.items():
            teacher = User.query.get(teacher_id)
            if teacher and send_teacher_reminder_h1(teacher, bookings_list):
                sent_count += 1
        
        logger.info(f"[H-1 Teacher] Sent {sent_count} reminders for {tomorrow}")


def job_teacher_weekly_summary():
    """
    Send weekly schedule summary to all teachers.
    Runs every Sunday at 07:00 WIB.
    """
    from app import create_app, db
    from app.models import Booking, User
    from app.services.notifications import send_teacher_weekly_summary
    
    app = create_app()
    with app.app_context():
        today = date.today()
        week_start = today
        week_end = today + timedelta(days=7)
        
        # Find all teachers
        teachers = User.query.filter_by(role='teacher', is_active=True).all()
        
        sent_count = 0
        for teacher in teachers:
            # Get all bookings for this teacher in the coming week
            bookings = Booking.query.filter(
                Booking.teacher_id == teacher.id,
                Booking.date >= week_start,
                Booking.date < week_end,
                Booking.status == 'booked'
            ).order_by(Booking.date, Booking.timeslot_id).all()
            
            if not bookings:
                continue
            
            # Group by date
            weekly_bookings = {}
            for booking in bookings:
                if booking.date not in weekly_bookings:
                    weekly_bookings[booking.date] = []
                weekly_bookings[booking.date].append(booking)
            
            if send_teacher_weekly_summary(teacher, weekly_bookings):
                sent_count += 1
        
        logger.info(f"[Weekly Teacher] Sent {sent_count} weekly summaries")


def init_scheduler(app):
    """
    Initialize and start the scheduler with all jobs.
    Should be called from Flask app factory.
    """
    # Check if scheduler should run
    if not os.environ.get('SCHEDULER_ENABLED', 'false').lower() == 'true':
        logger.info("Scheduler is disabled (SCHEDULER_ENABLED != true)")
        return None
    
    # Prevent duplicate schedulers in multi-worker setup
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        sched = get_scheduler()
        
        if sched.running:
            logger.info("Scheduler already running")
            return sched
        
        # Add jobs
        # H-1 reminders at 18:00 WIB
        sched.add_job(
            job_student_reminder_h1,
            CronTrigger(hour=18, minute=0, timezone=TIMEZONE),
            id='student_reminder_h1',
            replace_existing=True
        )
        
        sched.add_job(
            job_teacher_reminder_h1,
            CronTrigger(hour=18, minute=0, timezone=TIMEZONE),
            id='teacher_reminder_h1',
            replace_existing=True
        )
        
        # H-Day reminders at 07:00 WIB
        sched.add_job(
            job_student_reminder_hday,
            CronTrigger(hour=7, minute=0, timezone=TIMEZONE),
            id='student_reminder_hday',
            replace_existing=True
        )
        
        # Weekly summary on Sunday at 07:00 WIB
        sched.add_job(
            job_teacher_weekly_summary,
            CronTrigger(day_of_week='sun', hour=7, minute=0, timezone=TIMEZONE),
            id='teacher_weekly_summary',
            replace_existing=True
        )
        
        sched.start()
        logger.info("Scheduler started with all notification jobs")
        return sched
    
    return None
