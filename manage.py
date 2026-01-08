from app import create_app, db
from app.models import User, Program, Subject, ProgramSubject, TimeSlot, TeacherSkill, TeacherAvailability, Batch, Enrollment, StudentSchedule, Booking, Tool, ProgramTool, ProgramClass, ClassEnrollment
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

    # 2. Subjects (untuk silabus)
    design = get_or_create(Subject, name="Fashion Design")
    pcsw = get_or_create(Subject, name="PCSW (Pola)")
    cad = get_or_create(Subject, name="CAD")
    exploration = get_or_create(Subject, name="Exploration")
    business = get_or_create(Subject, name="Fashion Business")
    
    db.session.commit()
    print("✅ Subjects created")
    
    # 3. Programs dengan Classes
    # max_izin: FF/SPF regular classes = 8, Exploration = 3, Batch = 0
    programs_data = [
        {
            "name": "Fashion Foundation",
            "is_batch_based": False,
            "classes": [
                {"name": "Fashion Design", "sessions": 48, "per_week": 2, "batch": False, "max_izin": 8, "order": 1},
                {"name": "PCSW", "sessions": 48, "per_week": 2, "batch": False, "max_izin": 8, "order": 2},
                {"name": "CAD", "sessions": 16, "per_week": 0, "batch": True, "max_izin": 0, "order": 3},
            ]
        },
        {
            "name": "SPF",
            "is_batch_based": False,
            "classes": [
                {"name": "Fashion Design", "sessions": 16, "per_week": 1, "batch": False, "max_izin": 8, "order": 1},
                {"name": "PCSW", "sessions": 48, "per_week": 2, "batch": False, "max_izin": 8, "order": 2},
            ]
        },
        {
            "name": "Fast Track",
            "is_batch_based": True,
            "classes": [
                {"name": "Fast Track", "sessions": 13, "per_week": 0, "batch": True, "max_izin": 0, "order": 1},
            ]
        },
        {
            "name": "FF Exploration",
            "is_batch_based": False,
            "classes": [
                {"name": "FF Exploration", "sessions": 4, "per_week": 1, "batch": False, "max_izin": 3, "order": 1},
            ]
        },
        {
            "name": "SPF Exploration",
            "is_batch_based": False,
            "classes": [
                {"name": "SPF Exploration", "sessions": 4, "per_week": 1, "batch": False, "max_izin": 3, "order": 1},
            ]
        },
    ]
    
    for prog_data in programs_data:
        prog = get_or_create(Program, name=prog_data["name"])
        prog.is_batch_based = prog_data["is_batch_based"]
        db.session.flush()
        
        for cls_data in prog_data["classes"]:
            existing_class = ProgramClass.query.filter_by(
                program_id=prog.id, 
                name=cls_data["name"]
            ).first()
            
            if not existing_class:
                program_class = ProgramClass(
                    program_id=prog.id,
                    name=cls_data["name"],
                    total_sessions=cls_data["sessions"],
                    sessions_per_week=cls_data["per_week"],
                    is_batch_based=cls_data["batch"],
                    max_izin=cls_data["max_izin"],
                    order=cls_data["order"]
                )
                db.session.add(program_class)
                izin_info = f", max izin: {cls_data['max_izin']}" if cls_data['max_izin'] > 0 else ""
                print(f"  ✅ Class '{cls_data['name']}' ({cls_data['sessions']} sesi{izin_info}) added to {prog.name}")
        
        print(f"✅ Program '{prog.name}' created")
    
    db.session.commit()
    
    # 4. TimeSlots
    # Pagi: 09:30-12:30 (Offline)
    # Siang: 13:30-16:30 (Offline)
    # Malam: 18:30-21:00 (Online)
    timeslots_data = [
        {"name": "Sesi Pagi", "start": time(9, 30), "end": time(12, 30), "online": False},
        {"name": "Sesi Siang", "start": time(13, 30), "end": time(16, 30), "online": False},
        {"name": "Sesi Malam", "start": time(18, 30), "end": time(21, 0), "online": True},
    ]
    
    for ts in timeslots_data:
        slot = TimeSlot.query.filter_by(name=ts["name"]).first()
        if not slot:
            slot = TimeSlot(name=ts["name"], start_time=ts["start"], end_time=ts["end"], is_online=ts["online"])
            db.session.add(slot)
        else:
            slot.start_time = ts["start"]
            slot.end_time = ts["end"]
            slot.is_online = ts["online"]
    
    db.session.commit()
    print("✅ TimeSlots created: Pagi (09:30-12:30 Offline), Siang (13:30-16:30 Offline), Malam (18:30-21:00 Online)")

    # 5. Teachers with Skills and Availability
    teachers_data = [
        {
            "email": "teacher1@school.com",
            "name": "Ms. Sarah (Design)",
            "phone": "6281200001111",
            "skills": ["Fashion Design"],
            "availability": [
                (0, "Sesi Pagi"), (0, "Sesi Siang"),  # Senin
                (2, "Sesi Pagi"), (2, "Sesi Siang"),  # Rabu
                (4, "Sesi Pagi"),                      # Jumat
            ]
        },
        {
            "email": "teacher2@school.com",
            "name": "Mr. Budi (Pola)",
            "phone": "6281200002222",
            "skills": ["PCSW (Pola)"],
            "availability": [
                (1, "Sesi Pagi"), (1, "Sesi Siang"),  # Selasa
                (3, "Sesi Pagi"), (3, "Sesi Siang"),  # Kamis
                (5, "Sesi Pagi"),                      # Sabtu
            ]
        },
        {
            "email": "teacher3@school.com",
            "name": "Ms. Anita (CAD)",
            "phone": "6281200003333",
            "skills": ["CAD"],
            "availability": [
                (0, "Sesi Siang"),                     # Senin
                (2, "Sesi Pagi"), (2, "Sesi Siang"),  # Rabu
                (4, "Sesi Pagi"), (4, "Sesi Siang"),  # Jumat
            ]
        },
        {
            "email": "teacher4@school.com",
            "name": "Ms. Ratna (Exploration)",
            "phone": "6281200004444",
            "skills": ["Exploration"],
            "availability": [
                (1, "Sesi Pagi"),                      # Selasa
                (3, "Sesi Siang"),                     # Kamis
                (5, "Sesi Pagi"), (5, "Sesi Siang"),  # Sabtu
            ]
        },
        {
            "email": "teacher5@school.com",
            "name": "Mr. Eko (Multi-Skill)",
            "phone": "6281200005555",
            "skills": ["Fashion Design", "PCSW (Pola)"],
            "availability": [
                (0, "Sesi Pagi"), (0, "Sesi Malam"),  # Senin
                (1, "Sesi Siang"), (1, "Sesi Malam"), # Selasa
                (2, "Sesi Pagi"),                      # Rabu
                (3, "Sesi Siang"), (3, "Sesi Malam"), # Kamis
                (4, "Sesi Pagi"),                      # Jumat
            ]
        },
        {
            "email": "teacher6@school.com",
            "name": "Ms. Dian (Full-Time)",
            "phone": "6281200006666",
            "skills": ["Fashion Design", "CAD", "PCSW (Pola)"],
            "availability": [
                (0, "Sesi Pagi"), (0, "Sesi Siang"), (0, "Sesi Malam"),  # Senin
                (1, "Sesi Pagi"), (1, "Sesi Siang"), (1, "Sesi Malam"),  # Selasa
                (2, "Sesi Pagi"), (2, "Sesi Siang"), (2, "Sesi Malam"),  # Rabu
                (3, "Sesi Pagi"), (3, "Sesi Siang"), (3, "Sesi Malam"),  # Kamis
                (4, "Sesi Pagi"), (4, "Sesi Siang"), (4, "Sesi Malam"),  # Jumat
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
            
            for skill_name in t_data["skills"]:
                subj = Subject.query.filter_by(name=skill_name).first()
                if subj:
                    db.session.add(TeacherSkill(teacher_id=teacher.id, subject_id=subj.id))
            
            for day, slot_name in t_data["availability"]:
                slot = TimeSlot.query.filter_by(name=slot_name).first()
                if slot:
                    db.session.add(TeacherAvailability(teacher_id=teacher.id, day_of_week=day, timeslot_id=slot.id))
            
            print(f"✅ Teacher {t_data['name']} created")
        else:
            print(f"ℹ️  Teacher {t_data['email']} already exists")

    db.session.commit()
    
    # 6. Tools
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
    prog_ff = Program.query.filter_by(name="Fashion Foundation").first()
    prog_spf = Program.query.filter_by(name="SPF").first()
    prog_ft = Program.query.filter_by(name="Fast Track").first()
    
    tools_ff = ["Watercolor Set", "Palette", "Kuas Set", "Sketching Paper", "Pensil Warna", "Marker Fashion", "Pita Ukur", "Penggaris Pola", "Software CAD License"]
    for tool_name in tools_ff:
        tool = Tool.query.filter_by(name=tool_name).first()
        if tool and prog_ff and not ProgramTool.query.filter_by(program_id=prog_ff.id, tool_id=tool.id).first():
            db.session.add(ProgramTool(program_id=prog_ff.id, tool_id=tool.id, quantity=1))
    
    tools_spf = ["Watercolor Set", "Kuas Set", "Sketching Paper", "Pita Ukur", "Penggaris Pola"]
    for tool_name in tools_spf:
        tool = Tool.query.filter_by(name=tool_name).first()
        if tool and prog_spf and not ProgramTool.query.filter_by(program_id=prog_spf.id, tool_id=tool.id).first():
            db.session.add(ProgramTool(program_id=prog_spf.id, tool_id=tool.id, quantity=1))
    
    tools_ft = ["Mesin Jahit", "Gunting Kain", "Pita Ukur", "Penggaris Pola"]
    for tool_name in tools_ft:
        tool = Tool.query.filter_by(name=tool_name).first()
        if tool and prog_ft and not ProgramTool.query.filter_by(program_id=prog_ft.id, tool_id=tool.id).first():
            db.session.add(ProgramTool(program_id=prog_ft.id, tool_id=tool.id, quantity=1))
    
    db.session.commit()
    print("✅ Tools assigned to programs")
    
    # 8. Test Student dengan Enrollment dan ClassEnrollments
    test_student = User.query.filter_by(email='student@test.com').first()
    if not test_student:
        test_student = User(
            email='student@test.com',
            name='Test Student',
            phone_number='6281234567890',
            role='student'
        )
        test_student.set_password('student123')
        db.session.add(test_student)
        db.session.flush()
        
        # Create enrollment for Fashion Foundation
        prog_ff = Program.query.filter_by(name='Fashion Foundation').first()
        if prog_ff:
            enrollment = Enrollment(
                student_id=test_student.id,
                program_id=prog_ff.id,
                status='active'
            )
            db.session.add(enrollment)
            db.session.flush()
            
            # Auto-create ClassEnrollments
            for pc in prog_ff.classes:
                ce = ClassEnrollment(
                    enrollment_id=enrollment.id,
                    program_class_id=pc.id,
                    sessions_remaining=pc.total_sessions,
                    izin_used=0,
                    status='active'
                )
                db.session.add(ce)
            
            db.session.commit()
            
            # Create test bookings for izin testing
            from datetime import timedelta
            
            # Get class enrollments
            fd_ce = ClassEnrollment.query.join(ProgramClass).filter(
                ClassEnrollment.enrollment_id == enrollment.id,
                ProgramClass.name == 'Fashion Design'
            ).first()
            
            pcsw_ce = ClassEnrollment.query.join(ProgramClass).filter(
                ClassEnrollment.enrollment_id == enrollment.id,
                ProgramClass.name == 'PCSW'
            ).first()
            
            cad_ce = ClassEnrollment.query.join(ProgramClass).filter(
                ClassEnrollment.enrollment_id == enrollment.id,
                ProgramClass.name == 'CAD'
            ).first()
            
            timeslot_pagi = TimeSlot.query.filter_by(name='Sesi Pagi').first()
            timeslot_siang = TimeSlot.query.filter_by(name='Sesi Siang').first()
            
            teacher = User.query.filter_by(role='teacher').first()
            fd_subject = Subject.query.filter_by(name='Fashion Design').first()
            
            # Booking 1: Tomorrow (can izin)
            tomorrow = date.today() + timedelta(days=1)
            booking1 = Booking(
                enrollment_id=enrollment.id,
                class_enrollment_id=fd_ce.id if fd_ce else None,
                date=tomorrow,
                timeslot_id=timeslot_pagi.id if timeslot_pagi else 1,
                teacher_id=teacher.id if teacher else None,
                subject_id=fd_subject.id if fd_subject else None,
                status='booked'
            )
            db.session.add(booking1)
            
            # Booking 2: Next week (can izin)
            next_week = date.today() + timedelta(days=7)
            booking2 = Booking(
                enrollment_id=enrollment.id,
                class_enrollment_id=pcsw_ce.id if pcsw_ce else None,
                date=next_week,
                timeslot_id=timeslot_siang.id if timeslot_siang else 2,
                teacher_id=teacher.id if teacher else None,
                subject_id=Subject.query.filter_by(name='PCSW').first().id if Subject.query.filter_by(name='PCSW').first() else None,
                status='booked'
            )
            db.session.add(booking2)
            
            # Booking 3: CAD (no izin allowed - batch)
            booking3 = Booking(
                enrollment_id=enrollment.id,
                class_enrollment_id=cad_ce.id if cad_ce else None,
                date=next_week + timedelta(days=1),
                timeslot_id=timeslot_pagi.id if timeslot_pagi else 1,
                teacher_id=teacher.id if teacher else None,
                subject_id=Subject.query.filter_by(name='CAD').first().id if Subject.query.filter_by(name='CAD').first() else None,
                status='booked'
            )
            db.session.add(booking3)
            
            db.session.commit()
            print(f"✅ Test Student created: student@test.com / student123")
            print(f"   Enrolled in: {prog_ff.name} ({len(prog_ff.classes)} classes)")
            print(f"   Test bookings: 3 (tomorrow, next week, next week+1)")
    else:
        print("ℹ️  Test student already exists")
    
    print("\n=== SEEDING SELESAI ===")
    print("\n📊 Summary:")
    for prog in Program.query.all():
        print(f"  • {prog.name}: {prog.total_sessions} total sesi ({len(prog.classes)} kelas)")
        for cls in prog.classes:
            batch_tag = " [BATCH]" if cls.is_batch_based else f" [{cls.sessions_per_week}x/minggu]"
            print(f"      - {cls.name}: {cls.total_sessions} sesi{batch_tag}")

if __name__ == '__main__':
    with app.app_context():
        seed()