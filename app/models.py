from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# 1. USER MODEL
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(30), unique=True, nullable=True) # WA Number
    password_hash = db.Column(db.String(256))
    name = db.Column(db.String(100))
    role = db.Column(db.String(20), nullable=False) # admin, teacher, student, vendor
    activation_token = db.Column(db.String(100), unique=True)
    
    # Vendor link (for role='vendor')
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=True)
    
    # Student Profile Fields (diisi saat aktivasi pertama kali)
    nik = db.Column(db.String(20), nullable=True)  # NIK (Nomor Induk Kependudukan)
    alamat = db.Column(db.Text, nullable=True)  # Alamat lengkap
    tanggal_lahir = db.Column(db.Date, nullable=True)  # Tanggal lahir
    agama = db.Column(db.String(30), nullable=True)  # Agama
    pekerjaan = db.Column(db.String(100), nullable=True)  # Pekerjaan
    status_pernikahan = db.Column(db.String(20), nullable=True)  # Single/Menikah/etc.
    mengetahui_sfa_dari = db.Column(db.String(100), nullable=True)  # Tau SFA darimana
    alasan_memilih_sfa = db.Column(db.Text, nullable=True)  # Alasan memilih SFA
    drive_folder_id = db.Column(db.String(100), nullable=True)  # Root folder di Google Drive
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    availabilities = db.relationship('TeacherAvailability', backref='teacher', lazy=True)
    skills = db.relationship('TeacherSkill', backref='teacher', lazy=True)
    vendor = db.relationship('Vendor', backref='user_account', foreign_keys=[vendor_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 2. ACADEMIC MODELS
class Program(db.Model):
    __tablename__ = 'programs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_batch_based = db.Column(db.Boolean, default=False)  # Program level batch flag
    
    subjects = db.relationship('ProgramSubject', backref='program', lazy=True)
    batches = db.relationship('Batch', backref='program', lazy=True)
    classes = db.relationship('ProgramClass', backref='program', lazy=True, order_by='ProgramClass.order')
    
    @property
    def total_sessions(self):
        """Calculate total sessions from all classes in this program"""
        return sum(c.total_sessions for c in self.classes)

# MASTER CLASS - Kelas sebagai master data independen
class MasterClass(db.Model):
    __tablename__ = 'master_classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # e.g., "Fashion Design", "PCSW"
    description = db.Column(db.Text, nullable=True)
    default_max_izin = db.Column(db.Integer, default=0)  # Default max izin untuk kelas ini
    
    # Relationships
    program_classes = db.relationship('ProgramClass', backref='master_class', lazy=True)
    teacher_skills = db.relationship('TeacherSkill', backref='master_class', lazy=True)

# NEW: Program Classes (Kelas dalam Program)
class ProgramClass(db.Model):
    __tablename__ = 'program_classes'
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    master_class_id = db.Column(db.Integer, db.ForeignKey('master_classes.id'), nullable=True)  # Referensi ke MasterClass
    name = db.Column(db.String(100), nullable=True)  # Fallback jika master_class_id null (legacy)
    total_sessions = db.Column(db.Integer, nullable=False)  # e.g., 48
    sessions_per_week = db.Column(db.Integer, default=1)  # 1 atau 2 kali per minggu
    is_batch_based = db.Column(db.Boolean, default=False)  # CAD, Fast Track = True
    max_izin = db.Column(db.Integer, default=0)  # Max izin allowed, 0 = no izin
    order = db.Column(db.Integer, default=0)  # Urutan tampilan
    
    @property
    def display_name(self):
        """Get display name from master_class or fallback to name field"""
        if self.master_class:
            return self.master_class.name
        return self.name or "Unknown"

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

class ProgramSubject(db.Model):
    __tablename__ = 'program_subjects'
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    
    subject = db.relationship('Subject')

class Batch(db.Model):
    __tablename__ = 'batches'
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    name = db.Column(db.String(50))
    max_students = db.Column(db.Integer, default=6)
    is_active = db.Column(db.Boolean, default=True)

class TimeSlot(db.Model):
    __tablename__ = 'timeslots'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_online = db.Column(db.Boolean, default=False)  # True = online, False = offline

# 3. TEACHER SPECIFICS
class TeacherSkill(db.Model):
    __tablename__ = 'teacher_skills'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)  # Legacy, akan dihapus
    master_class_id = db.Column(db.Integer, db.ForeignKey('master_classes.id'), nullable=True)  # NEW
    
    # Relationships
    subject = db.relationship('Subject')  # Legacy
    
    @property
    def skill_name(self):
        """Get skill name from master_class or fallback to subject"""
        if self.master_class:
            return self.master_class.name
        return self.subject.name if self.subject else "Unknown"

class TeacherAvailability(db.Model):
    __tablename__ = 'teacher_availabilities'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    master_class_id = db.Column(db.Integer, db.ForeignKey('master_classes.id'), nullable=True)  # NEW: per-class availability
    day_of_week = db.Column(db.Integer)
    timeslot_id = db.Column(db.Integer, db.ForeignKey('timeslots.id'))
    
    timeslot = db.relationship('TimeSlot')
    master_class = db.relationship('MasterClass')

# 4. STUDENT ENROLLMENT & SCHEDULE
class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)
    status = db.Column(db.String(20), default='pending_schedule')
    first_class_date = db.Column(db.Date, nullable=True)  # When student wants to start
    # Note: sessions_remaining moved to ClassEnrollment for per-class tracking
    
    program = db.relationship('Program')
    batch = db.relationship('Batch')
    schedules = db.relationship('StudentSchedule', backref='enrollment', lazy=True)
    bookings = db.relationship('Booking', backref='enrollment', lazy=True)
    class_enrollments = db.relationship('ClassEnrollment', backref='enrollment', lazy=True)
    
    @property
    def sessions_remaining(self):
        """Calculate total remaining sessions from all class enrollments"""
        return sum(ce.sessions_remaining for ce in self.class_enrollments)

# NEW: Class Enrollment (Track progress per kelas)
class ClassEnrollment(db.Model):
    __tablename__ = 'class_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'))
    program_class_id = db.Column(db.Integer, db.ForeignKey('program_classes.id'))
    sessions_remaining = db.Column(db.Integer)  # Sisa sesi untuk kelas ini
    izin_used = db.Column(db.Integer, default=0)  # Izin yang sudah dipakai
    status = db.Column(db.String(20), default='active')  # active, completed
    
    program_class = db.relationship('ProgramClass')
    schedules = db.relationship('StudentSchedule', backref='class_enrollment', lazy=True)
    
    @property
    def izin_remaining(self):
        """Calculate remaining izin for this class"""
        return max(0, self.program_class.max_izin - self.izin_used)

class StudentSchedule(db.Model):
    __tablename__ = 'student_schedules'
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'))
    class_enrollment_id = db.Column(db.Integer, db.ForeignKey('class_enrollments.id'), nullable=True)  # NEW
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)  # Keep for silabus
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    day_of_week = db.Column(db.Integer)
    timeslot_id = db.Column(db.Integer, db.ForeignKey('timeslots.id'))
    
    subject = db.relationship('Subject')
    teacher = db.relationship('User')
    timeslot = db.relationship('TimeSlot')
    # class_enrollment relationship is defined via backref in ClassEnrollment

# 5. OPERATION (BOOKING & ATTENDANCE)
class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'))
    class_enrollment_id = db.Column(db.Integer, db.ForeignKey('class_enrollments.id'), nullable=True)  # NEW
    date = db.Column(db.Date, nullable=False)
    timeslot_id = db.Column(db.Integer, db.ForeignKey('timeslots.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)  # Keep for silabus
    status = db.Column(db.String(20), default='booked')  # booked, completed, cancelled
    
    # Relationships
    timeslot = db.relationship('TimeSlot')
    teacher = db.relationship('User', foreign_keys=[teacher_id])
    subject = db.relationship('Subject')
    class_enrollment = db.relationship('ClassEnrollment', backref='bookings')
    
    # Relasi ke attendance (One-to-One)
    attendance = db.relationship('Attendance', backref='booking', uselist=False, lazy=True)

class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date = db.Column(db.Date)
    status = db.Column(db.String(20)) # Hadir, Izin, Alpha
    notes = db.Column(db.Text)

    # Tambahan: Agar tau siapa guru yang mengabsen
    teacher = db.relationship('User', foreign_keys=[teacher_id])

# 7. TOOLS MODEL
class Tool(db.Model):
    __tablename__ = 'tools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # e.g., "Drawing", "Sewing", "Digital"
    
    programs = db.relationship('ProgramTool', backref='tool', lazy=True)

class ProgramTool(db.Model):
    __tablename__ = 'program_tools'
    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'))
    quantity = db.Column(db.Integer, default=1)  # Jumlah tools yang dibutuhkan
    notes = db.Column(db.String(200))  # Catatan tambahan
    
    program = db.relationship('Program', backref='tools')

# 8. SYLLABUS MODEL - Silabus per kelas
class Syllabus(db.Model):
    __tablename__ = 'syllabus'
    id = db.Column(db.Integer, primary_key=True)
    program_class_id = db.Column(db.Integer, db.ForeignKey('program_classes.id'), nullable=False)
    topic_name = db.Column(db.String(200), nullable=False)
    sessions = db.Column(db.Integer, default=1)  # Jumlah sesi untuk topik ini
    order = db.Column(db.Integer, default=0)  # Urutan tampilan
    
    program_class = db.relationship('ProgramClass', backref=db.backref('syllabus_items', order_by='Syllabus.order'))

# 9. PORTFOLIO MODEL - Portfolio siswa (Google Drive)
class Portfolio(db.Model):
    __tablename__ = 'portfolios'
    id = db.Column(db.Integer, primary_key=True)
    class_enrollment_id = db.Column(db.Integer, db.ForeignKey('class_enrollments.id'), nullable=False)
    syllabus_id = db.Column(db.Integer, db.ForeignKey('syllabus.id'), nullable=False)  # Wajib terhubung ke silabus
    file_name = db.Column(db.String(200), nullable=False)
    drive_file_id = db.Column(db.String(100))  # Google Drive file ID
    drive_url = db.Column(db.String(500))  # Direct link ke file
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    class_enrollment = db.relationship('ClassEnrollment', backref='portfolios')
    syllabus = db.relationship('Syllabus', backref='portfolios')

# 10. ATTENDANCE REQUEST MODEL - Request absen yang sudah lewat
class AttendanceRequest(db.Model):
    __tablename__ = 'attendance_requests'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Requested attendance data
    status_request = db.Column(db.String(20), nullable=False)  # 'Hadir', 'Izin', 'Alpha'
    notes = db.Column(db.Text)
    
    # Request metadata
    reason = db.Column(db.Text, nullable=False)  # Alasan lupa absen
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Approval workflow
    approval_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Relationships
    booking = db.relationship('Booking', backref='attendance_requests')
    teacher = db.relationship('User', foreign_keys=[teacher_id], backref='attendance_requests_made')
    approver = db.relationship('User', foreign_keys=[approved_by])


# 12. TEACHER SESSION OVERRIDE - untuk penggantian pengajar
class TeacherSessionOverride(db.Model):
    __tablename__ = 'teacher_session_overrides'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    timeslot_id = db.Column(db.Integer, db.ForeignKey('timeslots.id'), nullable=False)
    original_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    substitute_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    timeslot = db.relationship('TimeSlot', backref='session_overrides')
    original_teacher = db.relationship('User', foreign_keys=[original_teacher_id], backref='sessions_delegated')
    substitute_teacher = db.relationship('User', foreign_keys=[substitute_teacher_id], backref='sessions_covered')
    creator = db.relationship('User', foreign_keys=[created_by])


# 13. RESCHEDULE REQUEST MODEL - Request pindah jadwal
class RescheduleRequest(db.Model):
    __tablename__ = 'reschedule_requests'
    id = db.Column(db.Integer, primary_key=True)
    
    # Source - jadwal yang ingin di-reschedule (one of these should be set)
    student_schedule_id = db.Column(db.Integer, db.ForeignKey('student_schedules.id'), nullable=True)
    original_booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    original_date = db.Column(db.Date, nullable=False)  # Tanggal asli yang di-reschedule
    original_timeslot_id = db.Column(db.Integer, db.ForeignKey('timeslots.id'), nullable=False)
    original_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Target - jadwal baru yang diminta
    new_date = db.Column(db.Date, nullable=False)
    new_timeslot_id = db.Column(db.Integer, db.ForeignKey('timeslots.id'), nullable=False)
    new_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Tracking
    class_enrollment_id = db.Column(db.Integer, db.ForeignKey('class_enrollments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=True)  # Alasan reschedule (opsional)
    
    # Request metadata
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Student atau Admin
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Approval workflow
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Result - booking yang dibuat setelah approve
    new_booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    
    # Relationships
    student_schedule = db.relationship('StudentSchedule', foreign_keys=[student_schedule_id])
    original_booking = db.relationship('Booking', foreign_keys=[original_booking_id])
    original_timeslot = db.relationship('TimeSlot', foreign_keys=[original_timeslot_id])
    original_teacher = db.relationship('User', foreign_keys=[original_teacher_id])
    new_timeslot = db.relationship('TimeSlot', foreign_keys=[new_timeslot_id])
    new_teacher = db.relationship('User', foreign_keys=[new_teacher_id])
    class_enrollment = db.relationship('ClassEnrollment')
    student = db.relationship('User', foreign_keys=[student_id], backref='reschedule_requests')
    requester = db.relationship('User', foreign_keys=[requested_by])
    approver = db.relationship('User', foreign_keys=[approved_by])
    new_booking = db.relationship('Booking', foreign_keys=[new_booking_id])


# ============================================
# 14. VOUCHER SYSTEM
# ============================================

class Vendor(db.Model):
    """Partner vendor untuk voucher (mesin jahit, manekin, dll)"""
    __tablename__ = 'vendors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    password_hash = db.Column(db.String(256))  # Untuk login vendor
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    voucher_types = db.relationship('VoucherType', backref='vendor', lazy=True)
    payments = db.relationship('VendorPayment', backref='vendor', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def outstanding_balance(self):
        """Calculate total unclaimed vouchers value"""
        from sqlalchemy import func
        claimed = db.session.query(func.sum(VoucherType.value)).join(
            Voucher, Voucher.voucher_type_id == VoucherType.id
        ).filter(
            VoucherType.vendor_id == self.id,
            Voucher.status == 'claimed',
            Voucher.claimed_by_vendor_id == self.id
        ).scalar() or 0
        
        paid = db.session.query(func.sum(VendorPayment.amount)).filter(
            VendorPayment.vendor_id == self.id
        ).scalar() or 0
        
        return claimed - paid


class VoucherType(db.Model):
    """Jenis voucher (Mesin Jahit 1.5jt, Manekin 300k)"""
    __tablename__ = 'voucher_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # "Mesin Jahit", "Manekin"
    value = db.Column(db.Integer, nullable=False)  # 1500000, 300000
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    vouchers = db.relationship('Voucher', backref='voucher_type', lazy=True)


class Voucher(db.Model):
    """Individual voucher instance dengan QR code"""
    __tablename__ = 'vouchers'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # "VCH-XXXX-XXXX"
    voucher_type_id = db.Column(db.Integer, db.ForeignKey('voucher_types.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pin_hash = db.Column(db.String(256), nullable=False)  # Hashed 4-digit PIN
    
    status = db.Column(db.String(20), default='active')  # active, claimed, expired, cancelled
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.Date, nullable=True)  # Optional expiry
    
    # Claim info
    claimed_at = db.Column(db.DateTime, nullable=True)
    claimed_by_vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=True)
    
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Admin
    
    # Relationships
    student = db.relationship('User', foreign_keys=[student_id], backref='vouchers_received')
    claimed_by_vendor = db.relationship('Vendor', foreign_keys=[claimed_by_vendor_id], backref='vouchers_claimed')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def set_pin(self, pin):
        """Set 4-digit PIN"""
        self.pin_hash = generate_password_hash(str(pin))
    
    def check_pin(self, pin):
        """Verify PIN"""
        return check_password_hash(self.pin_hash, str(pin))
    
    @staticmethod
    def generate_code():
        """Generate unique voucher code"""
        import random
        import string
        chars = string.ascii_uppercase + string.digits
        while True:
            code = 'VCH-' + ''.join(random.choices(chars, k=4)) + '-' + ''.join(random.choices(chars, k=4))
            if not Voucher.query.filter_by(code=code).first():
                return code


class VendorPayment(db.Model):
    """Payment record ke vendor"""
    __tablename__ = 'vendor_payments'
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50))  # "Transfer", "Cash"
    reference = db.Column(db.String(100))  # No rekening/bukti
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by])
