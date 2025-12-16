from app import create_app, db
from app.models import User, Program, Subject, Batch, Enrollment

# 1. Buat instance aplikasi
app = create_app()

# 2. Context Processor (Opsional tapi berguna)
# Ini agar saat kita debug di terminal pakai 'flask shell', 
# kita tidak perlu import db/model manual terus menerus.
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'Program': Program, 
        'Subject': Subject,
        'Batch': Batch,
        'Enrollment': Enrollment
    }

if __name__ == '__main__':
    # Jalankan app
    app.run(host='0.0.0.0', port=5000, debug=True)