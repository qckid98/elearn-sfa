from app import create_app, db
from app.models import User, Program, Subject, ProgramSubject, TimeSlot, TeacherSkill, TeacherAvailability, Batch, Enrollment, StudentSchedule, Booking, Tool, ProgramTool
from datetime import time, date, timedelta

app = create_app()

def get_or_create(model, **kwargs):
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        db.session.add(instance)
        db.session.flush()
        return instance

def seed():
    print("=== MEMULAI SEEDING DATABASE ===")
    db.create_all()
    
    # 1. Admin
    if not User.query.filter_by(email='admin@school.com').first():
        admin = User(email='admin@school.com', name='Super Admin', role='admin', phone_number='628123456789')
        admin.set_password('admin123')
        db.session.add(admin)
        print("✅ Admin created")
    else:
        print("ℹ️  Admin already exists")

    # 2. Subjects
    design = get_or_create(Subject, name="Fashion Design")
    pcsw = get_or_create(Subject, name="PCSW (Pola)")
    cad = get_or_create(Subject, name="CAD")
    business = get_or_create(Subject, name="Fashion Business")
    
    # 3. Programs
    prog_3in1 = get_or_create(Program, name="FF 3 in 1", total_sessions=96)
    prog_ft = get_or_create(Program, name="Fast Track (FT)", is_batch_based=True)
    
    db.session.commit()

    # Link Program -> Subject
    def link_prog_subject(prog, subj):
        if not ProgramSubject.query.filter_by(program_id=prog.id, subject_id=subj.id).first():
            db.session.add(ProgramSubject(program_id=prog.id, subject_id=subj.id))

    link_prog_subject(prog_3in1, design)
    link_prog_subject(prog_3in1, pcsw)
    link_prog_subject(prog_3in1, cad)
    
    # 4. TimeSlots
    s1 = get_or_create(TimeSlot, name="Sesi 1", start_time=time(00,1), end_time=time(13,0))
    s2 = get_or_create(TimeSlot, name="Sesi 2", start_time=time(13,1), end_time=time(23,59))
    db.session.commit()

    # 5. Teachers with Skills and Availability
    teachers_data = [
        {
            "email": "teacher1@school.com",
            "name": "Ms. Sarah (Design)",
            "phone": "6281200001111",
            "skills": ["Fashion Design"],
            "availability": [
                (0, "Sesi 1"), (0, "Sesi 2"),  # Senin
                (2, "Sesi 1"), (2, "Sesi 2"),  # Rabu
                (4, "Sesi 1"),                  # Jumat pagi
            ]
        },
        {
            "email": "teacher2@school.com",
            "name": "Mr. Budi (Pola)",
            "phone": "6281200002222",
            "skills": ["PCSW (Pola)"],
            "availability": [
                (1, "Sesi 1"), (1, "Sesi 2"),  # Selasa
                (3, "Sesi 1"), (3, "Sesi 2"),  # Kamis
                (5, "Sesi 1"),                  # Sabtu pagi
            ]
        },
        {
            "email": "teacher3@school.com",
            "name": "Ms. Anita (CAD)",
            "phone": "6281200003333",
            "skills": ["CAD"],
            "availability": [
                (0, "Sesi 2"),                  # Senin siang
                (2, "Sesi 1"), (2, "Sesi 2"),  # Rabu
                (4, "Sesi 1"), (4, "Sesi 2"),  # Jumat
            ]
        },
        {
            "email": "teacher4@school.com",
            "name": "Ms. Ratna (Business)",
            "phone": "6281200004444",
            "skills": ["Fashion Business"],
            "availability": [
                (1, "Sesi 1"),                  # Selasa pagi
                (3, "Sesi 2"),                  # Kamis siang
                (5, "Sesi 1"), (5, "Sesi 2"),  # Sabtu
            ]
        },
        {
            "email": "teacher5@school.com",
            "name": "Mr. Eko (Multi-Skill)",
            "phone": "6281200005555",
            "skills": ["Fashion Design", "PCSW (Pola)"],
            "availability": [
                (0, "Sesi 1"),                  # Senin pagi
                (1, "Sesi 2"),                  # Selasa siang
                (2, "Sesi 1"),                  # Rabu pagi
                (3, "Sesi 2"),                  # Kamis siang
                (4, "Sesi 1"),                  # Jumat pagi
            ]
        },
        {
            "email": "teacher6@school.com",
            "name": "Ms. Dian (Full-Time)",
            "phone": "6281200006666",
            "skills": ["Fashion Design", "CAD", "Fashion Business"],
            "availability": [
                (0, "Sesi 1"), (0, "Sesi 2"),  # Senin
                (1, "Sesi 1"), (1, "Sesi 2"),  # Selasa
                (2, "Sesi 1"), (2, "Sesi 2"),  # Rabu
                (3, "Sesi 1"), (3, "Sesi 2"),  # Kamis
                (4, "Sesi 1"), (4, "Sesi 2"),  # Jumat
            ]
        },
    ]
    
    for t_data in teachers_data:
        if not User.query.filter_by(email=t_data["email"]).first():
            teacher = User(
                email=t_data["email"],
                name=t_data["name"],
                role='teacher',
                phone_number=t_data["phone"]
            )
            teacher.set_password('guru123')
            db.session.add(teacher)
            db.session.flush()
            
            # Add skills
            for skill_name in t_data["skills"]:
                subj = Subject.query.filter_by(name=skill_name).first()
                if subj:
                    db.session.add(TeacherSkill(teacher_id=teacher.id, subject_id=subj.id))
            
            # Add availabilities
            for day, slot_name in t_data["availability"]:
                slot = TimeSlot.query.filter_by(name=slot_name).first()
                if slot:
                    db.session.add(TeacherAvailability(teacher_id=teacher.id, day_of_week=day, timeslot_id=slot.id))
            
            print(f"✅ Teacher {t_data['name']} created")
        else:
            print(f"ℹ️  Teacher {t_data['email']} already exists")

    db.session.commit()
    
    # 6. Students with Enrollments and Matching Schedules
    # Schedule based on teacher availability:
    # Ms. Sarah (Design): Mon (S1,S2), Wed (S1,S2), Fri (S1)
    # Mr. Budi (Pola): Tue (S1,S2), Thu (S1,S2), Sat (S1)
    # Ms. Anita (CAD): Mon (S2), Wed (S1,S2), Fri (S1,S2)
    # Ms. Ratna (Business): Tue (S1), Thu (S2), Sat (S1,S2)
    # Mr. Eko (Multi): Mon (S1), Tue (S2), Wed (S1), Thu (S2), Fri (S1)
    # Ms. Dian (Full): Mon-Fri (S1,S2)
    
    students_data = [
        {
            "email": "siswa1@school.com", 
            "name": "Rina Wijaya", 
            "phone": "6281234567001", 
            "sessions_remaining": 96,
            "schedule": {
                "day": 0,  # Senin
                "timeslot": "Sesi 1",
                "teacher_email": "teacher1@school.com",  # Ms. Sarah available Mon S1
                "subject": "Fashion Design"
            }
        },
        {
            "email": "siswa2@school.com", 
            "name": "Dewi Lestari", 
            "phone": "6281234567002", 
            "sessions_remaining": 36,
            "schedule": {
                "day": 1,  # Selasa
                "timeslot": "Sesi 1",
                "teacher_email": "teacher2@school.com",  # Mr. Budi available Tue S1
                "subject": "PCSW (Pola)"
            }
        },
        {
            "email": "siswa3@school.com", 
            "name": "Siti Nurhaliza", 
            "phone": "6281234567003", 
            "sessions_remaining": 24,
            "schedule": {
                "day": 2,  # Rabu
                "timeslot": "Sesi 2",
                "teacher_email": "teacher3@school.com",  # Ms. Anita available Wed S2
                "subject": "CAD"
            }
        },
        {
            "email": "siswa4@school.com", 
            "name": "Putri Ayu", 
            "phone": "6281234567004", 
            "sessions_remaining": 12,
            "schedule": {
                "day": 3,  # Kamis
                "timeslot": "Sesi 2",
                "teacher_email": "teacher4@school.com",  # Ms. Ratna available Thu S2
                "subject": "Fashion Business"
            }
        },
        {
            "email": "siswa5@school.com", 
            "name": "Maya Sari", 
            "phone": "6281234567005", 
            "sessions_remaining": 96,
            "schedule": {
                "day": 4,  # Jumat
                "timeslot": "Sesi 1",
                "teacher_email": "teacher6@school.com",  # Ms. Dian available Fri S1
                "subject": "Fashion Design"
            }
        },
    ]
    
    prog_3in1 = Program.query.filter_by(name="FF 3 in 1").first()
    
    for s_data in students_data:
        existing_student = User.query.filter_by(email=s_data["email"]).first()
        
        if not existing_student:
            student = User(
                email=s_data["email"],
                name=s_data["name"],
                role='student',
                phone_number=s_data["phone"]
            )
            student.set_password('siswa123')
            db.session.add(student)
            db.session.flush()
            
            # Create enrollment
            enrollment = Enrollment(
                student_id=student.id,
                program_id=prog_3in1.id,
                sessions_remaining=s_data["sessions_remaining"],
                status='active'
            )
            db.session.add(enrollment)
            db.session.flush()
            
            # Get schedule data
            sched = s_data["schedule"]
            timeslot = TimeSlot.query.filter_by(name=sched["timeslot"]).first()
            teacher = User.query.filter_by(email=sched["teacher_email"]).first()
            subject = Subject.query.filter_by(name=sched["subject"]).first()
            
            schedule = StudentSchedule(
                enrollment_id=enrollment.id,
                subject_id=subject.id,
                teacher_id=teacher.id,
                day_of_week=sched["day"],
                timeslot_id=timeslot.id
            )
            db.session.add(schedule)
            
            # Create upcoming booking
            today = date.today()
            days_until = (sched["day"] - today.weekday()) % 7
            if days_until == 0:
                days_until = 7
            booking_date = today + timedelta(days=days_until)
            
            booking = Booking(
                enrollment_id=enrollment.id,
                date=booking_date,
                timeslot_id=timeslot.id,
                teacher_id=teacher.id,
                subject_id=subject.id,
                status='booked'
            )
            db.session.add(booking)
            
            print(f"✅ Student {s_data['name']} created with enrollment")
        else:
            # Update existing student's schedule to match teacher availability
            enrollment = Enrollment.query.filter_by(student_id=existing_student.id).first()
            if enrollment:
                # Delete old schedules and bookings
                StudentSchedule.query.filter_by(enrollment_id=enrollment.id).delete()
                Booking.query.filter_by(enrollment_id=enrollment.id).delete()
                
                # Create new matching schedule
                sched = s_data["schedule"]
                timeslot = TimeSlot.query.filter_by(name=sched["timeslot"]).first()
                teacher = User.query.filter_by(email=sched["teacher_email"]).first()
                subject = Subject.query.filter_by(name=sched["subject"]).first()
                
                schedule = StudentSchedule(
                    enrollment_id=enrollment.id,
                    subject_id=subject.id,
                    teacher_id=teacher.id,
                    day_of_week=sched["day"],
                    timeslot_id=timeslot.id
                )
                db.session.add(schedule)
                
                # Create new booking
                today = date.today()
                days_until = (sched["day"] - today.weekday()) % 7
                if days_until == 0:
                    days_until = 7
                booking_date = today + timedelta(days=days_until)
                
                booking = Booking(
                    enrollment_id=enrollment.id,
                    date=booking_date,
                    timeslot_id=timeslot.id,
                    teacher_id=teacher.id,
                    subject_id=subject.id,
                    status='booked'
                )
                db.session.add(booking)
                
                print(f"🔄 Student {s_data['name']} schedule updated to match teacher availability")
            else:
                print(f"⚠️  Student {s_data['email']} has no enrollment")
    
    db.session.commit()
    
    # 7. Tools
    tools_data = [
        {"name": "Watercolor Set", "category": "Coloring", "description": "Set cat air 24 warna"},
        {"name": "Palette", "category": "Coloring", "description": "Palette untuk mencampur warna"},
        {"name": "Kuas Set", "category": "Drawing", "description": "Set kuas berbagai ukuran"},
        {"name": "Sketching Paper", "category": "Drawing", "description": "Kertas gambar A3"},
        {"name": "Pensil Warna", "category": "Coloring", "description": "Pensil warna 48 pcs"},
        {"name": "Mesin Jahit", "category": "Sewing", "description": "Mesin jahit portable"},
        {"name": "Gunting Kain", "category": "Sewing", "description": "Gunting khusus kain"},
        {"name": "Pita Ukur", "category": "Pattern", "description": "Pita ukur 150cm"},
        {"name": "Penggaris Pola", "category": "Pattern", "description": "Set penggaris pola kurva"},
        {"name": "Marker Fashion", "category": "Drawing", "description": "Marker fashion illustration"},
        {"name": "Software CAD License", "category": "Digital", "description": "Lisensi software pattern making"},
        {"name": "Graphics Tablet", "category": "Digital", "description": "Tablet gambar digital"},
    ]
    
    for t_data in tools_data:
        tool = get_or_create(Tool, name=t_data["name"])
        tool.category = t_data["category"]
        tool.description = t_data["description"]
    
    db.session.commit()
    print("✅ Tools created")
    
    # Assign tools to programs
    prog_3in1 = Program.query.filter_by(name="FF 3 in 1").first()
    prog_ft = Program.query.filter_by(name="Fast Track (FT)").first()
    
    # Tools for 3in1 program
    tools_3in1 = ["Watercolor Set", "Palette", "Kuas Set", "Sketching Paper", "Pensil Warna", "Marker Fashion", "Pita Ukur", "Penggaris Pola", "Software CAD License"]
    for tool_name in tools_3in1:
        tool = Tool.query.filter_by(name=tool_name).first()
        if tool and not ProgramTool.query.filter_by(program_id=prog_3in1.id, tool_id=tool.id).first():
            db.session.add(ProgramTool(program_id=prog_3in1.id, tool_id=tool.id, quantity=1))
    
    # Tools for FT program
    tools_ft = ["Mesin Jahit", "Gunting Kain", "Pita Ukur", "Penggaris Pola", "Graphics Tablet"]
    for tool_name in tools_ft:
        tool = Tool.query.filter_by(name=tool_name).first()
        if tool and prog_ft and not ProgramTool.query.filter_by(program_id=prog_ft.id, tool_id=tool.id).first():
            db.session.add(ProgramTool(program_id=prog_ft.id, tool_id=tool.id, quantity=1))
    
    db.session.commit()
    print("✅ Tools assigned to programs")
    
    print("=== SEEDING SELESAI ===")

# INI BAGIAN PENTING: Langsung jalankan fungsi seed(), bukan app.run()
if __name__ == '__main__':
    with app.app_context():
        seed()