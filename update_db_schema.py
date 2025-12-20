from app import create_app,db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Add columns manually if raw SQL needed, or try-except blocks
        conn = db.engine.connect()
        # SQLite syntax for adding columns
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN teacher_id INTEGER REFERENCES users(id)"))
            print("Added teacher_id column")
        except Exception as e:
            print(f"Skipping teacher_id: {e}")
            
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN subject_id INTEGER REFERENCES subjects(id)"))
            print("Added subject_id column")
        except Exception as e:
            print(f"Skipping subject_id: {e}")
            
        conn.commit()
        conn.close()
        print("Database schema updated successfully.")
    except Exception as e:
        print(f"Error: {e}")
