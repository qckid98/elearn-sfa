from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        conn = db.engine.connect()
        
        # Add student profile columns to users table
        columns_to_add = [
            ("nik", "VARCHAR(20)"),
            ("alamat", "TEXT"),
            ("tanggal_lahir", "DATE"),
            ("agama", "VARCHAR(30)"),
            ("pekerjaan", "VARCHAR(100)"),
            ("status_pernikahan", "VARCHAR(20)"),
            ("mengetahui_sfa_dari", "VARCHAR(100)"),
            ("alasan_memilih_sfa", "TEXT"),
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))
                print(f"Added {column_name} column")
            except Exception as e:
                print(f"Skipping {column_name}: {e}")
        
        conn.commit()
        conn.close()
        print("\nDatabase schema updated successfully!")
        print("Student profile fields added: NIK, alamat, tanggal_lahir, agama, pekerjaan, status_pernikahan, mengetahui_sfa_dari, alasan_memilih_sfa")
    except Exception as e:
        print(f"Error: {e}")
