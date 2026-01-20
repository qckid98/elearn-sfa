"""
Script untuk reset database dan seed admin only.

Penggunaan:
    python seed_admin.py          # Reset DB + seed admin
    python seed_admin.py --skip-reset  # Seed admin tanpa reset DB
"""

import os
import sys
import argparse
from pathlib import Path

def reset_database():
    """Reset database - drop all tables dan buat ulang"""
    from app import create_app, db
    
    app = create_app()
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    
    with app.app_context():
        # Handle SQLite - hapus file langsung
        if db_uri.startswith('sqlite:///'):
            db_file = db_uri.replace('sqlite:///', '')
            
            # Handle relative paths
            if not os.path.isabs(db_file):
                db_file = os.path.join(os.path.dirname(__file__), db_file)
            
            if os.path.exists(db_file):
                os.remove(db_file)
                print(f"🗑️  Database SQLite dihapus: {db_file}")
            else:
                print(f"ℹ️  Database tidak ditemukan: {db_file}")
        
        # Handle PostgreSQL/MySQL - drop all tables
        elif 'postgresql' in db_uri or 'mysql' in db_uri:
            print("🗑️  Dropping semua tabel...")
            db.drop_all()
            print("✅ Semua tabel berhasil di-drop")
        
        else:
            print("⚠️  Database type tidak dikenali, mencoba drop_all()...")
            db.drop_all()
            print("✅ drop_all() berhasil")

def run_migrations():
    """Jalankan flask db upgrade"""
    print("\n📦 Menjalankan migrasi database...")
    
    # Set FLASK_APP environment variable
    os.environ['FLASK_APP'] = 'run.py'
    
    # Run flask db upgrade
    result = os.system('flask db upgrade')
    
    if result == 0:
        print("✅ Migrasi berhasil")
    else:
        print("❌ Migrasi gagal")
        sys.exit(1)

def seed_admin():
    """Seed admin user, master classes, dan timeslots"""
    from app import create_app, db
    from app.models import User, MasterClass, TimeSlot
    from datetime import time
    
    app = create_app()
    
    with app.app_context():
        # Pastikan tabel ada
        db.create_all()
        
        # === 1. ADMIN USER ===
        print("\n👤 Membuat admin user...")
        
        existing_admin = User.query.filter_by(email='admin@school.com').first()
        
        if existing_admin:
            print("ℹ️  Admin sudah ada, skip...")
        else:
            admin = User(
                email='admin@school.com',
                name='Super Admin',
                role='admin',
                phone_number='628123456789'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin berhasil dibuat!")
        
        # === 2. MASTER CLASSES ===
        print("\n📚 Membuat master classes...")
        
        master_classes_data = [
            {"name": "Fashion Design FF", "description": "Kelas desain dan ilustrasi fashion", "default_max_izin": 8},
            {"name": "PCSW FF", "description": "Pattern Cutting & Sewing - Pola dan jahit", "default_max_izin": 8},
            {"name": "CAD", "description": "Computer Aided Design untuk pattern making", "default_max_izin": 0},
            {"name": "Fast Track", "description": "Program intensif", "default_max_izin": 0},
            {"name": "Exploration FF", "description": "Kelas eksplorasi kreatif", "default_max_izin": 3},
            {"name": "Exploration SPF", "description": "Kelas eksplorasi kreatif", "default_max_izin": 3},
            {"name": "Fashion Design SPF", "description": "Kelas desain dan ilustrasi fashion", "default_max_izin": 8},
            {"name": "PCSW SPF", "description": "Pattern Cutting & Sewing - Pola dan jahit", "default_max_izin": 8},
        ]
        
        for mc_data in master_classes_data:
            existing = MasterClass.query.filter_by(name=mc_data["name"]).first()
            if not existing:
                mc = MasterClass(**mc_data)
                db.session.add(mc)
                print(f"  ✅ {mc_data['name']}")
            else:
                print(f"  ℹ️  {mc_data['name']} sudah ada")
        
        db.session.commit()
        
        # === 3. TIME SLOTS ===
        print("\n⏰ Membuat time slots...")
        
        timeslots_data = [
            {"name": "Sesi Pagi", "start": time(9, 30), "end": time(12, 30), "online": False},
            {"name": "Sesi Siang", "start": time(13, 30), "end": time(16, 30), "online": False},
            {"name": "Sesi Malam", "start": time(18, 30), "end": time(21, 0), "online": True},
        ]
        
        for ts_data in timeslots_data:
            existing = TimeSlot.query.filter_by(name=ts_data["name"]).first()
            if not existing:
                ts = TimeSlot(
                    name=ts_data["name"],
                    start_time=ts_data["start"],
                    end_time=ts_data["end"],
                    is_online=ts_data["online"]
                )
                db.session.add(ts)
                print(f"  ✅ {ts_data['name']}")
            else:
                print(f"  ℹ️  {ts_data['name']} sudah ada")
        
        db.session.commit()
        
        # === 4. PROGRAMS ===
        print("\n📋 Membuat programs...")
        
        # Define programs and their classes
        # Format: {program_name: [(master_class_name, total_sessions, sessions_per_week, is_batch, max_izin)]}
        programs_data = {
            "Fashion Foundation 3 In 1": [
                ("Fashion Design FF", 48, 1, False, 8),
                ("PCSW FF", 48, 1, False, 8),
                ("CAD", 12, 1, True, 0),
            ],
            "Fast Track": [
                ("Fast Track", 48, 2, True, 0),
            ],
            "SPF": [
                ("Fashion Design SPF", 48, 1, False, 8),
                ("PCSW SPF", 48, 1, False, 8),
            ],
            "FF Exploration": [
                ("Exploration FF", 12, 1, False, 3),
            ],
            "SPF Exploration": [
                ("Exploration SPF", 12, 1, False, 3),
            ],
            "FF PCSW Only": [
                ("PCSW FF", 48, 1, False, 8),
            ],
            "FF Design Only": [
                ("Fashion Design FF", 48, 1, False, 8),
            ],
        }
        
        # Import Program and ProgramClass models
        from app.models import Program, ProgramClass
        
        for program_name, classes_list in programs_data.items():
            # Check if program exists
            existing_program = Program.query.filter_by(name=program_name).first()
            
            if existing_program:
                print(f"  ℹ️  Program '{program_name}' sudah ada")
                continue
            
            # Create new program
            is_batch_based = any(c[3] for c in classes_list)  # Program is batch-based if any class is
            program = Program(
                name=program_name,
                is_batch_based=is_batch_based
            )
            db.session.add(program)
            db.session.flush()  # Get program.id
            
            # Add classes to program
            for order, (mc_name, total_sessions, sessions_per_week, is_batch, max_izin) in enumerate(classes_list):
                # Find MasterClass
                master_class = MasterClass.query.filter_by(name=mc_name).first()
                if not master_class:
                    print(f"    ⚠️  MasterClass '{mc_name}' tidak ditemukan, skip...")
                    continue
                
                program_class = ProgramClass(
                    program_id=program.id,
                    master_class_id=master_class.id,
                    total_sessions=total_sessions,
                    sessions_per_week=sessions_per_week,
                    is_batch_based=is_batch,
                    max_izin=max_izin,
                    order=order
                )
                db.session.add(program_class)
            
            print(f"  ✅ {program_name} ({len(classes_list)} kelas)")
        
        db.session.commit()
        
        print("\n" + "="*50)
        print("📝 KREDENSIAL ADMIN:")
        print("   Email    : admin@school.com")
        print("   Password : admin123")
        print("="*50 + "\n")

def main():
    parser = argparse.ArgumentParser(description='Reset database dan seed admin')
    parser.add_argument('--skip-reset', action='store_true', 
                        help='Skip reset database, hanya seed admin')
    parser.add_argument('--skip-migrate', action='store_true',
                        help='Skip migrasi database')
    
    args = parser.parse_args()
    
    print("="*50)
    print("🔧 E-LEARN SFA - Database Setup (Admin Only)")
    print("="*50)
    
    if not args.skip_reset:
        reset_database()
    else:
        print("⏭️  Skip reset database")
    
    if not args.skip_migrate:
        run_migrations()
    else:
        print("⏭️  Skip migrasi")
    
    seed_admin()
    
    print("🎉 Setup selesai!")

if __name__ == '__main__':
    main()
