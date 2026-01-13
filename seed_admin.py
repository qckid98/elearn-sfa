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
    """Seed hanya admin user"""
    from app import create_app, db
    from app.models import User
    
    app = create_app()
    
    with app.app_context():
        # Pastikan tabel ada
        db.create_all()
        
        print("\n👤 Membuat admin user...")
        
        # Cek apakah admin sudah ada
        existing_admin = User.query.filter_by(email='admin@school.com').first()
        
        if existing_admin:
            print("ℹ️  Admin sudah ada, skip...")
            return
        
        # Buat admin baru
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
