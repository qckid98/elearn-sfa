from app import create_app, db
from app.models import User, Program, Subject, ProgramSubject, TimeSlot, TeacherSkill, TeacherAvailability, Batch
from datetime import time

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
    
    # 3. Programs
    prog_3in1 = get_or_create(Program, name="FF 3 in 1", total_sessions=48)
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
    s1 = get_or_create(TimeSlot, name="Sesi 1", start_time=time(10,0), end_time=time(13,0))
    s2 = get_or_create(TimeSlot, name="Sesi 2", start_time=time(14,0), end_time=time(17,0))
    db.session.commit()

    # 5. Teachers
    if not User.query.filter_by(email='teacher1@school.com').first():
        t_design = User(email='teacher1@school.com', name='Ms. Sarah (Design)', role='teacher')
        t_design.set_password('123')
        db.session.add(t_design)
        db.session.flush()
        
        db.session.add(TeacherSkill(teacher_id=t_design.id, subject_id=design.id))
        db.session.add(TeacherAvailability(teacher_id=t_design.id, day_of_week=0, timeslot_id=s1.id))
        print("✅ Teacher Sarah created")

    if not User.query.filter_by(email='teacher2@school.com').first():
        t_pola = User(email='teacher2@school.com', name='Mr. Budi (Pola)', role='teacher')
        t_pola.set_password('123')
        db.session.add(t_pola)
        db.session.flush()

        db.session.add(TeacherSkill(teacher_id=t_pola.id, subject_id=pcsw.id))
        db.session.add(TeacherAvailability(teacher_id=t_pola.id, day_of_week=1, timeslot_id=s2.id))
        print("✅ Teacher Budi created")

    db.session.commit()
    print("=== SEEDING SELESAI ===")

# INI BAGIAN PENTING: Langsung jalankan fungsi seed(), bukan app.run()
if __name__ == '__main__':
    with app.app_context():
        seed()