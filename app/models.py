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
    role = db.Column(db.String(20), nullable=False) # admin, teacher, student
    activation_token = db.Column(db.String(100), unique=True)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    availabilities = db.relationship('TeacherAvailability', backref='teacher', lazy=True)
    skills = db.relationship('TeacherSkill', backref='teacher', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 2. ACADEMIC MODELS
class Program(db.Model):
    __tablename__ = 'programs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    total_sessions = db.Column(db.Integer, default=0)
    is_batch_based = db.Column(db.Boolean, default=False)
    
    subjects = db.relationship('ProgramSubject', backref='program', lazy=True)
    batches = db.relationship('Batch', backref='program', lazy=True)

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

# 3. TEACHER SPECIFICS
class TeacherSkill(db.Model):
    __tablename__ = 'teacher_skills'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    
    # Perbaikan penting: Relasi ke Subject agar {{ skill.subject.name }} jalan
    subject = db.relationship('Subject')

class TeacherAvailability(db.Model):
    __tablename__ = 'teacher_availabilities'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    day_of_week = db.Column(db.Integer)
    timeslot_id = db.Column(db.Integer, db.ForeignKey('timeslots.id'))
    
    timeslot = db.relationship('TimeSlot')

# 4. STUDENT ENROLLMENT & SCHEDULE
class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)
    sessions_remaining = db.Column(db.Integer)
    status = db.Column(db.String(20), default='pending_schedule') 
    
    program = db.relationship('Program')
    batch = db.relationship('Batch')
    schedules = db.relationship('StudentSchedule', backref='enrollment', lazy=True)
    bookings = db.relationship('Booking', backref='enrollment', lazy=True)

class StudentSchedule(db.Model):
    __tablename__ = 'student_schedules'
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    day_of_week = db.Column(db.Integer)
    timeslot_id = db.Column(db.Integer, db.ForeignKey('timeslots.id'))
    
    subject = db.relationship('Subject')
    teacher = db.relationship('User')
    timeslot = db.relationship('TimeSlot')

# 5. OPERATION (BOOKING & ATTENDANCE)
class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'))
    date = db.Column(db.Date, nullable=False)
    timeslot_id = db.Column(db.Integer, db.ForeignKey('timeslots.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id')) # Added
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id')) # Added
    status = db.Column(db.String(20), default='booked') # booked, completed, cancelled
    
    # Relationships
    timeslot = db.relationship('TimeSlot') 
    teacher = db.relationship('User', foreign_keys=[teacher_id]) # Added
    subject = db.relationship('Subject') # Added
    
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