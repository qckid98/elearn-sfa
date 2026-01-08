from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        conn = db.engine.connect()
        
        # 1. Create program_classes table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS program_classes (
                    id SERIAL PRIMARY KEY,
                    program_id INTEGER REFERENCES programs(id),
                    name VARCHAR(100) NOT NULL,
                    total_sessions INTEGER NOT NULL,
                    sessions_per_week INTEGER DEFAULT 1,
                    is_batch_based BOOLEAN DEFAULT FALSE,
                    "order" INTEGER DEFAULT 0
                )
            """))
            print("✅ Created program_classes table")
        except Exception as e:
            print(f"⚠️ program_classes: {e}")
        
        # 2. Create class_enrollments table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS class_enrollments (
                    id SERIAL PRIMARY KEY,
                    enrollment_id INTEGER REFERENCES enrollments(id),
                    program_class_id INTEGER REFERENCES program_classes(id),
                    sessions_remaining INTEGER,
                    status VARCHAR(20) DEFAULT 'active'
                )
            """))
            print("✅ Created class_enrollments table")
        except Exception as e:
            print(f"⚠️ class_enrollments: {e}")
        
        # 3. Add class_enrollment_id to student_schedules
        try:
            conn.execute(text("ALTER TABLE student_schedules ADD COLUMN class_enrollment_id INTEGER REFERENCES class_enrollments(id)"))
            print("✅ Added class_enrollment_id to student_schedules")
        except Exception as e:
            print(f"⚠️ student_schedules.class_enrollment_id: {e}")
        
        # 4. Add class_enrollment_id to bookings
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN class_enrollment_id INTEGER REFERENCES class_enrollments(id)"))
            print("✅ Added class_enrollment_id to bookings")
        except Exception as e:
            print(f"⚠️ bookings.class_enrollment_id: {e}")
        
        # 5. Make subject_id nullable in student_schedules (if not already)
        try:
            conn.execute(text("ALTER TABLE student_schedules ALTER COLUMN subject_id DROP NOT NULL"))
            print("✅ Made subject_id nullable in student_schedules")
        except Exception as e:
            print(f"⚠️ student_schedules.subject_id: {e}")
        
        conn.commit()
        conn.close()
        print("\n✅ Database schema updated successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
