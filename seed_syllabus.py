"""
Seed Syllabus for MasterClasses
Run with: python seed_syllabus.py
Or via Docker: docker exec -it <container> python seed_syllabus.py
"""

from app import create_app, db
from app.models import MasterClass, Program, ProgramClass, Syllabus

app = create_app()

def get_program_class(program_name, master_class_name):
    """Find ProgramClass by program name and master class name"""
    program = Program.query.filter_by(name=program_name).first()
    if not program:
        print(f"  ⚠️  Program '{program_name}' tidak ditemukan")
        return None
    
    master_class = MasterClass.query.filter_by(name=master_class_name).first()
    if not master_class:
        print(f"  ⚠️  MasterClass '{master_class_name}' tidak ditemukan")
        return None
    
    pc = ProgramClass.query.filter_by(
        program_id=program.id,
        master_class_id=master_class.id
    ).first()
    
    if not pc:
        print(f"  ⚠️  ProgramClass '{master_class_name}' in '{program_name}' tidak ditemukan")
    
    return pc

def seed_class_syllabus(program_name, master_class_name, syllabus_items):
    """Seed syllabus for a specific program class"""
    pc = get_program_class(program_name, master_class_name)
    if not pc:
        return False
    
    order = 1
    total = 0
    for topic, sessions in syllabus_items:
        # Check if already exists
        existing = Syllabus.query.filter_by(
            program_class_id=pc.id,
            topic_name=topic
        ).first()
        
        if not existing:
            s = Syllabus(
                program_class_id=pc.id,
                topic_name=topic,
                sessions=sessions,
                order=order
            )
            db.session.add(s)
        order += 1
        total += sessions
    
    db.session.commit()
    print(f"  ✅ {master_class_name}: {len(syllabus_items)} topics, {total} sessions")
    return True

def seed_syllabus():
    print("=== SEEDING SYLLABUS ===\n")
    
    # Clear existing syllabus
    Syllabus.query.delete()
    db.session.commit()
    print("Cleared existing syllabus\n")
    
    # ============ FASHION DESIGN FF (48 sessions) ============
    fd_ff_syllabus = [
        ('Color Theory', 2),
        ('Color Application', 2),
        ('Line, Swirl, Texture', 2),
        ('Basic Figure Drawing', 3),
        ('Figurine Drawing & Coloring', 3),
        ('Figurine Details', 3),
        ('Design Principles', 1),
        ('Fashion Illustration Project', 1),
        ('Fashion Illustration Project: Street Style Project', 3),
        ('Technical Drawing', 2),
        ('Textile Knowledge', 2),
        ('Fashion Culture & History', 1),
        ('Fashion Culture & History: Fashion Movie Project', 2),
        ('Personal Style Research & Analysis', 2),
        ('Final Project: Moodboard & Design Direction', 2),
        ('Final Project: Visual Research & Exploration', 3),
        ('Final Project: Creative Textile Exploration', 3),
        ('Final Project: Perancangan Desain & Pengembangan', 4),
        ('Final Project: Finalisasi & Membuat Buku Portfolio', 3),
        ('Masterclass Session', 2),
        ('Final Project: Final Review', 2),
    ]
    seed_class_syllabus('Fashion Foundation 3 In 1', 'Fashion Design FF', fd_ff_syllabus)
    
    # ============ PCSW FF (48 sessions) ============
    pcsw_ff_syllabus = [
        ('Basic Measurement & Ruler Introduction', 1),
        ('Sewing Introduction / Teknik Menjahit', 1),
        ('Skirt Pattern Block & Dummy', 2),
        ('Skirt Project Exercise: Pattern Construction, Cutting, Sewing & Finishing', 4),
        ('Technical Sheet: Skirt', 1),
        ('Basic Block Pattern, Fitted Bodice, & Dummy', 2),
        ('Sleeves Block Pattern & Dummy', 1),
        ('Fragments: Collar, Cuff, & Opening', 4),
        ('Shirt Project Exercise: Pattern Construction, Cutting, Sewing & Finishing', 5),
        ('Technical Sheet: Shirt', 1),
        ('Review Assessment', 1),
        ('Dress Project Exercise: Pattern Construction, Cutting, Sewing & Finishing', 5),
        ('Technical Sheet: Dress', 1),
        ('Basic Pants Block', 1),
        ('Fragments: Pocket, Golbi', 1),
        ('Pants Project: Pattern Construction, Cutting, Sewing & Finishing', 5),
        ('Technical Sheet: Pants', 1),
        ('Review Assessment 2', 1),
        ('Final Project Realization', 10),
    ]
    seed_class_syllabus('Fashion Foundation 3 In 1', 'PCSW FF', pcsw_ff_syllabus)
    
    # ============ FAST TRACK (13 sessions total based on data) ============
    ft_syllabus = [
        ('Brand Concept Development (Business Fundamental, Brand DNA Discover)', 3),
        ('Launching Plan (Cash Flow & Profitability, Enter to Market & Pricing Strategy, Launching Strategy)', 3),
        ('Application of Design: Fashion Supply Chain & Trend Forecast', 1),
        ('Application of Design: Personal Style & Style Diagram', 1),
        ('Application of Design: Production Cycle & Collection Plan', 1),
        ('Application of Design: Collection Plan Review', 1),
        ('Application of Design: Prototype Review + Market Research', 1),
        ('Application of Design: Final Review & Digital Marketing', 1),
        ('Group Discussion: Final Presentation', 1),
    ]
    seed_class_syllabus('Fast Track', 'Fast Track', ft_syllabus)
    
    print("\n=== SYLLABUS SEEDING COMPLETE ===")


if __name__ == '__main__':
    with app.app_context():
        seed_syllabus()
