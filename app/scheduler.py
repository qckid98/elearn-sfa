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


def job_attendance_recap(timeslot_id):
    """
    Send attendance recap for a specific timeslot.
    Groups attendance by MasterClass/ProgramClass with teacher details.
    """
    import os
    from app import create_app, db
    from app.models import Attendance, Booking, TimeSlot, User
    from app.utils.whatsapp import send_wa_message
    
    app = create_app()
    with app.app_context():
        today = date.today()
        timeslot = TimeSlot.query.get(timeslot_id)
        
        if not timeslot:
            logger.warning(f"[Attendance Recap] Timeslot {timeslot_id} not found")
            return
        
        # Get all attendance records for today's timeslot
        attendances = Attendance.query.join(
            Booking, Attendance.booking_id == Booking.id
        ).filter(
            Booking.date == today,
            Booking.timeslot_id == timeslot_id
        ).all()
        
        if not attendances:
            logger.info(f"[Attendance Recap] No attendance for {timeslot.name} today")
            return
        
        # Group by class (via ClassEnrollment -> ProgramClass)
        class_data = {}
        for att in attendances:
            booking = att.booking
            
            # Get class name from ClassEnrollment or fallback
            class_name = "Kelas Umum"
            if booking.class_enrollment and booking.class_enrollment.program_class:
                class_name = booking.class_enrollment.program_class.display_name
            
            # Get teacher name
            teacher_name = booking.teacher.name if booking.teacher else "Unknown"
            
            # Create class key combining class and teacher
            class_key = f"{class_name}|{teacher_name}"
            
            if class_key not in class_data:
                class_data[class_key] = {
                    'class_name': class_name,
                    'teacher_name': teacher_name,
                    'hadir': [],
                    'izin': [],
                    'alpha': []
                }
            
            # Get student name and notes
            student_name = booking.enrollment.student.name if booking.enrollment and booking.enrollment.student else "Unknown"
            notes = att.notes or ""
            
            if att.status == 'Hadir':
                class_data[class_key]['hadir'].append(student_name)
            elif att.status == 'Izin':
                class_data[class_key]['izin'].append({'name': student_name, 'notes': notes})
            else:
                class_data[class_key]['alpha'].append(student_name)
        
        # Build message
        today_str = today.strftime("%A, %d %B %Y")
        days_indo = {
            'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu',
            'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'
        }
        day_name = today.strftime("%A")
        today_str_indo = f"{days_indo.get(day_name, day_name)}, {today.strftime('%d %B %Y')}"
        
        message_lines = [
            f"📋 *REKAP {timeslot.name.upper()}*",
            f"📅 {today_str_indo}",
            f"🕐 {timeslot.start_time.strftime('%H:%M')} - {timeslot.end_time.strftime('%H:%M')}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━"
        ]
        
        total_hadir = 0
        total_izin = 0
        total_alpha = 0
        
        # Add each class section
        for class_key, data in class_data.items():
            hadir_count = len(data['hadir'])
            izin_count = len(data['izin'])
            alpha_count = len(data['alpha'])
            
            total_hadir += hadir_count
            total_izin += izin_count
            total_alpha += alpha_count
            
            message_lines.append("")
            message_lines.append(f"👗 *{data['class_name'].upper()}*")
            message_lines.append(f"👩‍🏫 Pengajar: {data['teacher_name']}")
            message_lines.append(f"✅ Hadir: {hadir_count} | ⚠️ Izin: {izin_count} | ❌ Alpha: {alpha_count}")
            message_lines.append("")
            message_lines.append("📝 Detail:")
            
            # List hadir
            for name in data['hadir']:
                message_lines.append(f"• {name} ✅")
            
            # List izin with notes
            for item in data['izin']:
                if item['notes']:
                    message_lines.append(f"• {item['name']} ⚠️ ({item['notes']})")
                else:
                    message_lines.append(f"• {item['name']} ⚠️")
            
            # List alpha
            for name in data['alpha']:
                message_lines.append(f"• {name} ❌")
            
            message_lines.append("")
            message_lines.append("━━━━━━━━━━━━━━━━━━━━━")
        
        # Total summary
        total = total_hadir + total_izin + total_alpha
        hadir_pct = round(total_hadir / total * 100) if total > 0 else 0
        izin_pct = round(total_izin / total * 100) if total > 0 else 0
        alpha_pct = round(total_alpha / total * 100) if total > 0 else 0
        
        message_lines.append("")
        message_lines.append(f"📊 *TOTAL {timeslot.name.upper()}:*")
        message_lines.append(f"👥 Total Siswa: {total}")
        message_lines.append(f"✅ Hadir: {total_hadir} ({hadir_pct}%)")
        message_lines.append(f"⚠️ Izin: {total_izin} ({izin_pct}%)")
        message_lines.append(f"❌ Alpha: {total_alpha} ({alpha_pct}%)")
        
        # Send to WA Group
        wa_group_id = os.environ.get('WA_GROUP_ID', '')
        if wa_group_id:
            message = "\n".join(message_lines)
            send_wa_message(wa_group_id, message)
            logger.info(f"[Attendance Recap] Sent recap for {timeslot.name}: {total} students")
        else:
            logger.warning("[Attendance Recap] WA_GROUP_ID not set")


def job_attendance_recap_pagi():
    """Rekap Sesi Pagi - runs at 14:30 (H+2 jam dari 12:30)"""
    job_attendance_recap(timeslot_id=1)


def job_attendance_recap_siang():
    """Rekap Sesi Siang - runs at 18:30 (H+2 jam dari 16:30)"""
    job_attendance_recap(timeslot_id=2)


def job_attendance_recap_malam():
    """Rekap Sesi Malam - runs at 23:00 (H+2 jam dari 21:00)"""
    job_attendance_recap(timeslot_id=3)


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
        
        # === ATTENDANCE RECAP JOBS ===
        # Rekap Sesi Pagi at 14:00 WIB (H+1.5 jam dari 12:30)
        sched.add_job(
            job_attendance_recap_pagi,
            CronTrigger(hour=14, minute=0, timezone=TIMEZONE),
            id='attendance_recap_pagi',
            replace_existing=True
        )
        
        # Rekap Sesi Siang at 18:00 WIB (H+1.5 jam dari 16:30)
        sched.add_job(
            job_attendance_recap_siang,
            CronTrigger(hour=18, minute=0, timezone=TIMEZONE),
            id='attendance_recap_siang',
            replace_existing=True
        )
        
        # Rekap Sesi Malam at 22:30 WIB (H+1.5 jam dari 21:00)
        sched.add_job(
            job_attendance_recap_malam,
            CronTrigger(hour=22, minute=30, timezone=TIMEZONE),
            id='attendance_recap_malam',
            replace_existing=True
        )
        
        sched.start()
        logger.info("Scheduler started with all notification jobs")
        return sched
    
    return None
