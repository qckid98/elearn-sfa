from app import create_app, db
from app.models import User, Program, Subject, ProgramSubject, TimeSlot, TeacherSkill, TeacherAvailability, Batch, Enrollment, StudentSchedule, Booking, Tool, ProgramTool, ProgramClass, ClassEnrollment, Syllabus
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
    
    # 3.5 Syllabus untuk setiap kelas
    print("\n--- Creating Syllabus ---")
    
    syllabus_data = {
        # Fashion Design (48 sesi untuk FF, 16 sesi untuk SPF)
        "Fashion Design": [
            {"topic": "Pengenalan Fashion Illustration", "sessions": 2},
            {"topic": "Anatomi Tubuh untuk Fashion", "sessions": 3},
            {"topic": "Proporsi Croquis & Poses", "sessions": 3},
            {"topic": "Sketching Teknik Dasar", "sessions": 4},
            {"topic": "Menggambar Wajah & Rambut", "sessions": 2},
            {"topic": "Menggambar Tangan & Kaki", "sessions": 2},
            {"topic": "Teori Warna Dasar", "sessions": 2},
            {"topic": "Color Harmony & Palette", "sessions": 2},
            {"topic": "Rendering Kain: Cotton & Linen", "sessions": 3},
            {"topic": "Rendering Kain: Silk & Satin", "sessions": 3},
            {"topic": "Rendering Kain: Denim & Leather", "sessions": 3},
            {"topic": "Rendering Kain: Sheer & Lace", "sessions": 2},
            {"topic": "Flat Drawing / Technical Sketch", "sessions": 4},
            {"topic": "Koleksi Mini: Casual Wear", "sessions": 4},
            {"topic": "Koleksi Mini: Formal Wear", "sessions": 4},
            {"topic": "Portfolio Presentation", "sessions": 3},
            {"topic": "Final Project & Review", "sessions": 2},
        ],
        # PCSW - Pattern Cutting & Sewing (48 sesi)
        "PCSW": [
            {"topic": "Pengenalan Alat & Bahan Jahit", "sessions": 2},
            {"topic": "Cara Mengukur Tubuh", "sessions": 2},
            {"topic": "Dasar-Dasar Pola: Bodice Block", "sessions": 4},
            {"topic": "Dasar-Dasar Pola: Skirt Block", "sessions": 3},
            {"topic": "Dasar-Dasar Pola: Sleeve Block", "sessions": 3},
            {"topic": "Manipulasi Dart & Seam", "sessions": 3},
            {"topic": "Pola Rok: A-Line & Flare", "sessions": 3},
            {"topic": "Pola Rok: Pencil & Pleated", "sessions": 3},
            {"topic": "Pola Blouse Dasar", "sessions": 4},
            {"topic": "Pola Kemeja & Kerah", "sessions": 4},
            {"topic": "Pola Dress: Shift & Fit-Flare", "sessions": 4},
            {"topic": "Pola Celana Dasar", "sessions": 4},
            {"topic": "Teknik Jahit: Seam Finishes", "sessions": 2},
            {"topic": "Teknik Jahit: Zipper & Button", "sessions": 3},
            {"topic": "Fitting & Alterations", "sessions": 2},
            {"topic": "Final Garment Project", "sessions": 2},
        ],
        # CAD (16 sesi - batch)
        "CAD": [
            {"topic": "Pengenalan Software Pattern Making", "sessions": 2},
            {"topic": "Interface & Basic Tools", "sessions": 2},
            {"topic": "Digitizing Manual Pattern", "sessions": 2},
            {"topic": "Creating Digital Block Patterns", "sessions": 2},
            {"topic": "Pattern Manipulation Digital", "sessions": 2},
            {"topic": "Grading: Size Range", "sessions": 2},
            {"topic": "Marker Making & Efficiency", "sessions": 2},
            {"topic": "Print & Export for Production", "sessions": 2},
        ],
        # Fast Track (13 sesi - batch intensif)
        "Fast Track": [
            {"topic": "Intensive: Measuring & Block", "sessions": 2},
            {"topic": "Intensive: Skirt Patterns", "sessions": 2},
            {"topic": "Intensive: Top Patterns", "sessions": 2},
            {"topic": "Intensive: Dress Patterns", "sessions": 2},
            {"topic": "Intensive: Pants Patterns", "sessions": 2},
            {"topic": "Sewing Techniques Crash Course", "sessions": 2},
            {"topic": "Final Garment & Assessment", "sessions": 1},
        ],
        # FF Exploration (4 sesi)
        "FF Exploration": [
            {"topic": "Trend Research & Moodboard", "sessions": 1},
            {"topic": "Creative Design Exploration", "sessions": 1},
            {"topic": "Mini Collection Concept", "sessions": 1},
            {"topic": "Portfolio Enhancement", "sessions": 1},
        ],
        # SPF Exploration (4 sesi)
        "SPF Exploration": [
            {"topic": "Advanced Draping Intro", "sessions": 1},
            {"topic": "Experimental Pattern Cutting", "sessions": 1},
            {"topic": "Creative Textile Manipulation", "sessions": 1},
            {"topic": "Runway-Ready Finishing", "sessions": 1},
        ],
    }
    
    for class_name, topics in syllabus_data.items():
        # Find all program classes with this name
        program_classes = ProgramClass.query.filter_by(name=class_name).all()
        
        for pc in program_classes:
            existing_syllabus = Syllabus.query.filter_by(program_class_id=pc.id).first()
            if existing_syllabus:
                print(f"ℹ️  Syllabus for {pc.name} (Program: {pc.program.name}) already exists")
                continue
            
            order = 1
            total_sessions = 0
            for topic_data in topics:
                # Jika total sessions sudah melebihi class sessions, stop
                if total_sessions >= pc.total_sessions:
                    break
                
                # Adjust sessions jika akan melebihi
                topic_sessions = min(topic_data["sessions"], pc.total_sessions - total_sessions)
                
                syllabus = Syllabus(
                    program_class_id=pc.id,
                    topic_name=topic_data["topic"],
                    sessions=topic_sessions,
                    order=order
                )
                db.session.add(syllabus)
                total_sessions += topic_sessions
                order += 1
            
            print(f"  ✅ Syllabus for {pc.name} ({pc.program.name}): {order-1} topics, {total_sessions} sessions")
    
    db.session.commit()
    print("✅ Syllabus created")
    
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
    
    # 8. Sample Students dengan berbagai program dan status
    print("\n--- Creating Sample Students ---")
    
    students_data = [
        {
            "email": "rina@student.com",
            "name": "Rina Wijaya",
            "phone": "6281300001111",
            "program": "Fashion Foundation",
            "status": "active",
            "sessions_used": 5  # Sudah 5 sesi
        },
        {
            "email": "dewi@student.com",
            "name": "Dewi Lestari",
            "phone": "6281300002222",
            "program": "Fashion Foundation",
            "status": "active",
            "sessions_used": 12  # Sudah 12 sesi
        },
        {
            "email": "maya@student.com",
            "name": "Maya Sari",
            "phone": "6281300003333",
            "program": "SPF",
            "status": "active",
            "sessions_used": 3
        },
        {
            "email": "siti@student.com",
            "name": "Siti Nurhaliza",
            "phone": "6281300004444",
            "program": "Fast Track",
            "status": "active",
            "sessions_used": 0,
            "batch": "Batch 1"
        },
        {
            "email": "putri@student.com",
            "name": "Putri Ayu",
            "phone": "6281300005555",
            "program": "SPF",
            "status": "active",
            "sessions_used": 8,
            "extra_program": "SPF Exploration"  # Multi-program
        },
    ]
    
    # Get references
    timeslot_pagi = TimeSlot.query.filter_by(name='Sesi Pagi').first()
    timeslot_siang = TimeSlot.query.filter_by(name='Sesi Siang').first()
    teachers = User.query.filter_by(role='teacher').all()
    
    for idx, s_data in enumerate(students_data):
        existing = User.query.filter_by(email=s_data["email"]).first()
        if existing:
            print(f"ℹ️  Student {s_data['email']} already exists")
            continue
        
        # Create student user
        student = User(
            email=s_data["email"],
            name=s_data["name"],
            phone_number=s_data["phone"],
            role='student'
        )
        student.set_password('student123')
        db.session.add(student)
        db.session.flush()
        
        # Get program
        prog = Program.query.filter_by(name=s_data["program"]).first()
        if not prog:
            print(f"❌ Program {s_data['program']} not found")
            continue
        
        # Get batch if needed
        batch_id = None
        if s_data.get("batch"):
            batch = Batch.query.filter_by(name=s_data["batch"]).first()
            if not batch:
                batch = Batch(program_id=prog.id, name=s_data["batch"], max_students=6, is_active=True)
                db.session.add(batch)
                db.session.flush()
            batch_id = batch.id
        
        # Create enrollment
        enrollment = Enrollment(
            student_id=student.id,
            program_id=prog.id,
            batch_id=batch_id,
            status=s_data["status"]
        )
        db.session.add(enrollment)
        db.session.flush()
        
        # Auto-create ClassEnrollments
        for pc in prog.classes:
            # Distribute sessions used across classes proportionally
            class_sessions_used = min(s_data["sessions_used"], pc.total_sessions)
            sessions_remaining = pc.total_sessions - class_sessions_used
            
            ce = ClassEnrollment(
                enrollment_id=enrollment.id,
                program_class_id=pc.id,
                sessions_remaining=sessions_remaining,
                izin_used=0,
                status='active'
            )
            db.session.add(ce)
            db.session.flush()
            
            # Create sample bookings for upcoming sessions
            teacher = teachers[idx % len(teachers)] if teachers else None
            
            for booking_offset in range(3):  # 3 upcoming bookings per class
                booking_date = date.today() + timedelta(days=booking_offset + 1 + (idx * 2))
                timeslot = timeslot_pagi if booking_offset % 2 == 0 else timeslot_siang
                
                if timeslot:
                    booking = Booking(
                        enrollment_id=enrollment.id,
                        class_enrollment_id=ce.id,
                        date=booking_date,
                        timeslot_id=timeslot.id,
                        teacher_id=teacher.id if teacher else None,
                        status='booked'
                    )
                    db.session.add(booking)
        
        # Handle extra program (multi-enrollment)
        extra_enrollments = []
        if s_data.get("extra_program"):
            extra_prog = Program.query.filter_by(name=s_data["extra_program"]).first()
            if extra_prog:
                extra_enrollment = Enrollment(
                    student_id=student.id,
                    program_id=extra_prog.id,
                    status='active'
                )
                db.session.add(extra_enrollment)
                db.session.flush()
                extra_enrollments.append(extra_enrollment)
                
                for pc in extra_prog.classes:
                    extra_ce = ClassEnrollment(
                        enrollment_id=extra_enrollment.id,
                        program_class_id=pc.id,
                        sessions_remaining=pc.total_sessions,
                        izin_used=0,
                        status='active'
                    )
                    db.session.add(extra_ce)
                
                print(f"   + Extra enrollment: {extra_prog.name}")
        
        db.session.commit()
        
        # Create Google Drive folders for student
        try:
            from app.services.google_drive import get_drive_service, GoogleDriveError
            drive_service = get_drive_service()
            
            if drive_service.is_configured:
                # Get all enrollments for this student
                all_enrollments = [enrollment] + extra_enrollments
                
                # Create folder structure
                folder_result = drive_service.create_student_folders(
                    s_data["name"],
                    all_enrollments
                )
                
                # Save student folder ID to user
                student.drive_folder_id = folder_result['student_folder_id']
                db.session.commit()
                
                print(f"   📁 Drive folders created: {len(folder_result['class_folders'])} class folders")
            else:
                print(f"   ⚠️  Google Drive not configured, skipping folder creation")
        except GoogleDriveError as e:
            print(f"   ⚠️  Drive folder error: {str(e)[:80]}")
        except Exception as e:
            print(f"   ⚠️  Unexpected Drive error: {str(e)[:50]}")
        
        print(f"✅ Student {s_data['name']} created ({s_data['program']}, {s_data['sessions_used']} sessions used)")
    
    # Create original test student as well
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
        
        prog_ff = Program.query.filter_by(name='Fashion Foundation').first()
        if prog_ff:
            enrollment = Enrollment(
                student_id=test_student.id,
                program_id=prog_ff.id,
                status='active'
            )
            db.session.add(enrollment)
            db.session.flush()
            
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
            
            # Create Google Drive folders for test student
            try:
                from app.services.google_drive import get_drive_service, GoogleDriveError
                drive_service = get_drive_service()
                
                if drive_service.is_configured:
                    folder_result = drive_service.create_student_folders(
                        'Test Student',
                        [enrollment]
                    )
                    test_student.drive_folder_id = folder_result['student_folder_id']
                    db.session.commit()
                    print(f"   📁 Drive folders created")
                else:
                    print(f"   ⚠️  Google Drive not configured")
            except GoogleDriveError as e:
                print(f"   ⚠️  Drive folder error: {str(e)[:80]}")
            except Exception as e:
                print(f"   ⚠️  Unexpected Drive error: {str(e)[:50]}")
            
            print(f"✅ Test Student created: student@test.com / student123")
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