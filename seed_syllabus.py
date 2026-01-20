"""
Seed Syllabus for MasterClasses
Run with: python seed_syllabus.py
Or via Docker: docker exec -it <container> python seed_syllabus.py
"""

from app import create_app, db
from app.models import MasterClass, Program, ProgramClass, Syllabus

app = create_app()

def seed_syllabus():
    print("=== SEEDING SYLLABUS ===\n")
    
    # Clear existing syllabus
    Syllabus.query.delete()
    db.session.commit()
    print("Cleared existing syllabus\n")
    
    # ============ FASHION DESIGN FF (48 sessions) ============
    fd_ff_class = ProgramClass.query.join(Program).join(MasterClass).filter(
        Program.name == 'Fashion Foundation 3 In 1',
        MasterClass.name == 'Fashion Design FF'
    ).first()
    
    if fd_ff_class:
        fd_syllabus = [
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
        
        order = 1
        total = 0
        for topic, sessions in fd_syllabus:
            s = Syllabus(program_class_id=fd_ff_class.id, topic_name=topic, sessions=sessions, order=order)
            db.session.add(s)
            order += 1
            total += sessions
        print(f"✅ Fashion Design FF: {len(fd_syllabus)} topics, {total} sessions")
    else:
        print("⚠️  Fashion Design FF class not found")
    
    # ============ PCSW FF (48 sessions) ============
    pcsw_ff_class = ProgramClass.query.join(Program).join(MasterClass).filter(
        Program.name == 'Fashion Foundation 3 In 1',
        MasterClass.name == 'PCSW FF'
    ).first()
    
    if pcsw_ff_class:
        pcsw_syllabus = [
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
        
        order = 1
        total = 0
        for topic, sessions in pcsw_syllabus:
            s = Syllabus(program_class_id=pcsw_ff_class.id, topic_name=topic, sessions=sessions, order=order)
            db.session.add(s)
            order += 1
            total += sessions
        print(f"✅ PCSW FF: {len(pcsw_syllabus)} topics, {total} sessions")
    else:
        print("⚠️  PCSW FF class not found")
    
    # ============ FAST TRACK (48 sessions) ============
    ft_class = ProgramClass.query.join(Program).join(MasterClass).filter(
        Program.name == 'Fast Track',
        MasterClass.name == 'Fast Track'
    ).first()
    
    if ft_class:
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
        
        order = 1
        total = 0
        for topic, sessions in ft_syllabus:
            s = Syllabus(program_class_id=ft_class.id, topic_name=topic, sessions=sessions, order=order)
            db.session.add(s)
            order += 1
            total += sessions
        print(f"✅ Fast Track: {len(ft_syllabus)} topics, {total} sessions")
    else:
        print("⚠️  Fast Track class not found")
    
    db.session.commit()
    print("\n=== SYLLABUS SEEDING COMPLETE ===")


if __name__ == '__main__':
    with app.app_context():
        seed_syllabus()
