"""
WhatsApp Notification Service
Provides templated notifications for students and teachers.
"""
from datetime import datetime, date, timedelta
from app.utils.whatsapp import send_wa_message
from app import db
from app.models import User, Booking, StudentSchedule, Enrollment, ClassEnrollment

# Day names in Indonesian
DAYS_ID = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']


def format_phone_for_wa(phone_number: str) -> str:
    """
    Format phone number for WhatsApp API.
    Input: 628123456789 or 08123456789 or +628123456789
    Output: 628123456789@s.whatsapp.net
    """
    if not phone_number:
        return None
    
    # Remove any spaces, dashes, or plus signs
    phone = phone_number.replace(' ', '').replace('-', '').replace('+', '')
    
    # Convert 08xxx to 628xxx
    if phone.startswith('0'):
        phone = '62' + phone[1:]
    
    # Add WhatsApp suffix if not present
    if not phone.endswith('@s.whatsapp.net'):
        phone = phone + '@s.whatsapp.net'
    
    return phone


# ============================================================
# STUDENT NOTIFICATIONS
# ============================================================

def send_student_reminder_h1(student: User, bookings: list):
    """
    Send H-1 reminder to student about tomorrow's schedule.
    Called by scheduler at 18:00 WIB.
    """
    if not student.phone_number or not bookings:
        return False
    
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%d %B %Y")
    day_name = DAYS_ID[tomorrow.weekday()]
    
    # Build schedule list
    schedule_lines = []
    for booking in bookings:
        time_str = booking.timeslot.start_time.strftime("%H:%M") if booking.timeslot else "-"
        class_name = booking.class_enrollment.program_class.name if booking.class_enrollment else booking.enrollment.program.name
        teacher_name = booking.teacher.name if booking.teacher else "-"
        schedule_lines.append(f"⏰ {time_str} - {class_name}\n   👩‍🏫 Pengajar: {teacher_name}")
    
    message = (
        f"📚 *Pengingat Jadwal Besok*\n\n"
        f"Halo {student.name}! 👋\n\n"
        f"Jadwal kelas Anda besok ({day_name}, {tomorrow_str}):\n\n"
        + "\n\n".join(schedule_lines) +
        f"\n\nSampai jumpa di kelas! 🎨"
    )
    
    target = format_phone_for_wa(student.phone_number)
    return send_wa_message(target, message)


def send_student_reminder_hday(student: User, bookings: list):
    """
    Send same-day morning reminder to student.
    Called by scheduler at 07:00 WIB.
    """
    if not student.phone_number or not bookings:
        return False
    
    today = date.today()
    today_str = today.strftime("%d %B %Y")
    day_name = DAYS_ID[today.weekday()]
    
    # Build schedule list
    schedule_lines = []
    for booking in bookings:
        time_str = booking.timeslot.start_time.strftime("%H:%M") if booking.timeslot else "-"
        class_name = booking.class_enrollment.program_class.name if booking.class_enrollment else booking.enrollment.program.name
        schedule_lines.append(f"⏰ {time_str} - {class_name}")
    
    message = (
        f"🌅 *Selamat Pagi, {student.name}!*\n\n"
        f"Pengingat jadwal hari ini ({day_name}, {today_str}):\n\n"
        + "\n".join(schedule_lines) +
        f"\n\nSemangat belajar! 💪"
    )
    
    target = format_phone_for_wa(student.phone_number)
    return send_wa_message(target, message)


def send_student_schedule_change(student: User, old_date, new_date, class_name: str, reason: str = None):
    """
    Send notification when student's schedule is changed/rescheduled.
    Called immediately when admin changes schedule.
    """
    if not student.phone_number:
        return False
    
    old_str = old_date.strftime("%d %B %Y") if old_date else "-"
    new_str = new_date.strftime("%d %B %Y") if new_date else "-"
    
    message = (
        f"📅 *Perubahan Jadwal*\n\n"
        f"Halo {student.name},\n\n"
        f"Jadwal kelas *{class_name}* Anda telah diubah:\n\n"
        f"❌ Jadwal Lama: {old_str}\n"
        f"✅ Jadwal Baru: {new_str}\n"
    )
    
    if reason:
        message += f"\n📝 Alasan: {reason}\n"
    
    message += "\nTerima kasih! 🙏"
    
    target = format_phone_for_wa(student.phone_number)
    return send_wa_message(target, message)


# ============================================================
# TEACHER NOTIFICATIONS
# ============================================================

def send_teacher_reminder_h1(teacher: User, bookings: list):
    """
    Send H-1 reminder to teacher about tomorrow's teaching schedule.
    Called by scheduler at 18:00 WIB.
    """
    if not teacher.phone_number or not bookings:
        return False
    
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%d %B %Y")
    day_name = DAYS_ID[tomorrow.weekday()]
    
    # Group by timeslot
    schedule_lines = []
    for booking in bookings:
        time_str = booking.timeslot.start_time.strftime("%H:%M") if booking.timeslot else "-"
        student_name = booking.enrollment.student.name if booking.enrollment else "-"
        program_name = booking.enrollment.program.name if booking.enrollment else "-"
        schedule_lines.append(f"⏰ {time_str}\n   • {student_name} - {program_name}")
    
    message = (
        f"📋 *Jadwal Mengajar Besok*\n\n"
        f"Halo Kak {teacher.name}! 👋\n\n"
        f"Jadwal mengajar Anda besok ({day_name}, {tomorrow_str}):\n\n"
        + "\n\n".join(schedule_lines) +
        f"\n\nTotal: {len(bookings)} sesi\n"
        f"Terima kasih! 🙏"
    )
    
    target = format_phone_for_wa(teacher.phone_number)
    return send_wa_message(target, message)


def send_teacher_weekly_summary(teacher: User, weekly_bookings: dict):
    """
    Send weekly schedule summary to teacher.
    Called by scheduler on Sunday 07:00 WIB.
    weekly_bookings: {date_obj: [list of bookings]}
    """
    if not teacher.phone_number or not weekly_bookings:
        return False
    
    # Build weekly schedule
    schedule_by_day = []
    total_sessions = 0
    
    for day_date in sorted(weekly_bookings.keys()):
        bookings = weekly_bookings[day_date]
        if not bookings:
            continue
            
        day_name = DAYS_ID[day_date.weekday()]
        date_str = day_date.strftime("%d/%m")
        
        lines = [f"📅 *{day_name} ({date_str})*"]
        for booking in bookings:
            time_str = booking.timeslot.start_time.strftime("%H:%M") if booking.timeslot else "-"
            student_name = booking.enrollment.student.name if booking.enrollment else "-"
            lines.append(f"   ⏰ {time_str} - {student_name}")
            total_sessions += 1
        
        schedule_by_day.append("\n".join(lines))
    
    if not schedule_by_day:
        return False
    
    message = (
        f"📆 *Jadwal Mengajar Minggu Ini*\n\n"
        f"Halo Kak {teacher.name}! 👋\n\n"
        + "\n\n".join(schedule_by_day) +
        f"\n\n📊 Total: {total_sessions} sesi minggu ini\n"
        f"Semangat mengajar! 💪"
    )
    
    target = format_phone_for_wa(teacher.phone_number)
    return send_wa_message(target, message)


def send_teacher_schedule_change(teacher: User, student_name: str, old_date, new_date, class_name: str):
    """
    Send notification when a student's schedule with this teacher is changed.
    Called immediately when admin changes schedule.
    """
    if not teacher.phone_number:
        return False
    
    old_str = old_date.strftime("%d %B %Y") if old_date else "-"
    new_str = new_date.strftime("%d %B %Y") if new_date else "-"
    
    message = (
        f"📅 *Perubahan Jadwal Siswa*\n\n"
        f"Halo Kak {teacher.name},\n\n"
        f"Jadwal siswa *{student_name}* ({class_name}) telah diubah:\n\n"
        f"❌ Jadwal Lama: {old_str}\n"
        f"✅ Jadwal Baru: {new_str}\n\n"
        f"Terima kasih! 🙏"
    )
    
    target = format_phone_for_wa(teacher.phone_number)
    return send_wa_message(target, message)


def send_teacher_new_student(teacher: User, student_name: str, program_name: str, schedule_info: str = None):
    """
    Send notification when a new student is assigned to this teacher.
    Called when admin assigns student to teacher.
    """
    if not teacher.phone_number:
        return False
    
    message = (
        f"👤 *Siswa Baru*\n\n"
        f"Halo Kak {teacher.name}! 👋\n\n"
        f"Ada siswa baru yang di-assign ke Anda:\n\n"
        f"👤 Nama: {student_name}\n"
        f"📚 Program: {program_name}\n"
    )
    
    if schedule_info:
        message += f"📅 Jadwal: {schedule_info}\n"
    
    message += "\nSelamat mengajar! 🎨"
    
    target = format_phone_for_wa(teacher.phone_number)
    return send_wa_message(target, message)


def send_teacher_student_izin(teacher: User, student_name: str, class_name: str, booking_date, reason: str = None):
    """
    Send notification when student requests permission (izin) for a schedule.
    Called immediately when student submits izin.
    """
    if not teacher.phone_number:
        return False
    
    date_str = booking_date.strftime("%d %B %Y") if booking_date else "-"
    day_name = DAYS_ID[booking_date.weekday()] if booking_date else "-"
    
    message = (
        f"⚠️ *Siswa Izin*\n\n"
        f"Halo Kak {teacher.name},\n\n"
        f"Siswa *{student_name}* mengajukan izin:\n\n"
        f"📅 Tanggal: {day_name}, {date_str}\n"
        f"📚 Kelas: {class_name}\n"
    )
    
    if reason:
        message += f"📝 Alasan: {reason}\n"
    
    message += "\nSesi akan digeser ke jadwal berikutnya."
    
    target = format_phone_for_wa(teacher.phone_number)
    return send_wa_message(target, message)
