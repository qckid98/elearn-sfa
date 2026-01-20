"""
Seed Teachers Script
Data pengajar dari VPS production yang disimpan untuk re-seeding.

Penggunaan:
    python seed_teachers.py          # Seed teachers ke database
    
Jalankan SETELAH seed_admin.py karena membutuhkan MasterClass dan TimeSlot.
"""

from app import create_app, db
from app.models import User, TeacherSkill, TeacherAvailability, MasterClass, TimeSlot

app = create_app()

# Data pengajar dari VPS production
TEACHERS_DATA = [
    {
        "email": "honokalvaredh278@gmail.com",
        "name": "Sir Honok A",
        "phone": "081389247655",
        "password_hash": "scrypt:32768:8:1$oiuiPvgZ4tXlsDga$7cad9c8c409a2cc6e0ae9cb01d58a4a926368059c36445fea18c1828a44641e6946741b864315ae892ca3cb85183679fc1eabe24bab5c7e4c298e63269690a45",
        # Skills: mengajar kelas apa saja
        "skills": ["Fashion Design FF", "PCSW FF", "Exploration FF"],
        # Availability: (day_of_week, timeslot_name) - day: 0=Senin, 6=Minggu
        "availability": [
            (6, "Sesi Pagi"),   # Minggu Pagi
            (6, "Sesi Siang"), # Minggu Siang
        ]
    },
    {
        "email": "kurniapratiwi21@gmail.com",
        "name": "Ms. Figih Kurnia",
        "phone": "085781406577",
        "password_hash": "scrypt:32768:8:1$sMT6LiRVBw5WKfgy$c15770f422dceb810a882e1190f4c58781afefd5bd0ff6f9f14dbf534d67ef2eb4dac9ac93b6fc235b166f7dbdd73cee5fbc5a34b7ca9ef903258267e1a961a0",
        "skills": ["Fashion Design FF", "PCSW FF", "Exploration FF"],
        "availability": [
            (1, "Sesi Siang"),  # Selasa Siang
        ]
    },
    {
        "email": "zohraenny.sfa@gmail.com",
        "name": "Ms. Zohraenny",
        "phone": "085813428870",
        "password_hash": "scrypt:32768:8:1$cyaABsTFTNfJwav1$62a4fe391154879e8a7b270f95cc990ee5cd3f5ade2ca9ef72855a10836f239972f6f085717cbc4c57f0a40865f20b281d34e7c3cf018c6ecca26f1943557650",
        "skills": ["Fashion Design FF", "PCSW FF", "Exploration FF"],
        "availability": [
            (0, "Sesi Pagi"),   # Senin Pagi
            (0, "Sesi Malam"),  # Senin Malam
            (3, "Sesi Pagi"),   # Kamis Pagi
            (3, "Sesi Siang"),  # Kamis Siang
        ]
    },
    {
        "email": "elissachristharyanto@gmail.com",
        "name": "Ms. Elissa C Haryanto",
        "phone": "081585943338",
        "password_hash": "scrypt:32768:8:1$936lcWZ7CDDdIl85$5c15fecf9ec80d5d66720fcf36fa61698353f61ab7a57ea8eef5ce98e2f2d024329c87abb65670e6c129030928cbc2c284b0ce13a4b93300478c4f17c3b9ae08",
        "skills": ["Fashion Design SPF", "PCSW SPF", "Exploration SPF", "CAD"],
        "availability": [
            (2, "Sesi Malam"),  # Rabu Malam
            (5, "Sesi Pagi"),   # Sabtu Pagi
        ]
    }
]


def seed_teachers():
    """Seed teachers dari data VPS production"""
    print("=" * 50)
    print("🧑‍🏫 SEEDING TEACHERS")
    print("=" * 50)
    
    # Cache MasterClass dan TimeSlot
    mc_cache = {mc.name: mc.id for mc in MasterClass.query.all()}
    ts_cache = {ts.name: ts.id for ts in TimeSlot.query.all()}
    
    print(f"\n📚 MasterClasses found: {list(mc_cache.keys())}")
    print(f"⏰ TimeSlots found: {list(ts_cache.keys())}\n")
    
    for t_data in TEACHERS_DATA:
        print(f"\n--- {t_data['name']} ---")
        
        # Create or get teacher
        teacher = User.query.filter_by(email=t_data["email"]).first()
        
        if teacher:
            print(f"  ℹ️  User sudah ada (ID: {teacher.id})")
        else:
            teacher = User(
                email=t_data["email"],
                name=t_data["name"],
                phone_number=t_data["phone"],
                password_hash=t_data["password_hash"],
                role="teacher"
            )
            db.session.add(teacher)
            db.session.flush()
            print(f"  ✅ User dibuat (ID: {teacher.id})")
        
        # Add skills
        for skill_name in t_data["skills"]:
            mc_id = mc_cache.get(skill_name)
            if not mc_id:
                print(f"  ⚠️  MasterClass '{skill_name}' tidak ditemukan!")
                continue
                
            existing = TeacherSkill.query.filter_by(
                teacher_id=teacher.id,
                master_class_id=mc_id
            ).first()
            
            if not existing:
                skill = TeacherSkill(teacher_id=teacher.id, master_class_id=mc_id)
                db.session.add(skill)
                print(f"  ✅ Skill: {skill_name}")
            else:
                print(f"  ℹ️  Skill '{skill_name}' sudah ada")
        
        # Add availability
        for day, ts_name in t_data["availability"]:
            ts_id = ts_cache.get(ts_name)
            if not ts_id:
                print(f"  ⚠️  TimeSlot '{ts_name}' tidak ditemukan!")
                continue
                
            existing = TeacherAvailability.query.filter_by(
                teacher_id=teacher.id,
                day_of_week=day,
                timeslot_id=ts_id
            ).first()
            
            if not existing:
                avail = TeacherAvailability(
                    teacher_id=teacher.id,
                    day_of_week=day,
                    timeslot_id=ts_id
                )
                db.session.add(avail)
                day_names = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
                print(f"  ✅ Available: {day_names[day]} - {ts_name}")
            else:
                print(f"  ℹ️  Availability sudah ada")
    
    db.session.commit()
    
    print("\n" + "=" * 50)
    print("🎉 TEACHER SEEDING COMPLETE!")
    print("=" * 50)
    
    # Summary
    print("\n📋 SUMMARY:")
    teachers = User.query.filter_by(role='teacher').all()
    for teacher in teachers:
        skills_count = TeacherSkill.query.filter_by(teacher_id=teacher.id).count()
        avail_count = TeacherAvailability.query.filter_by(teacher_id=teacher.id).count()
        print(f"   {teacher.name}: {skills_count} skills, {avail_count} slots")


if __name__ == '__main__':
    with app.app_context():
        seed_teachers()
