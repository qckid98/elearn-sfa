"""
Seed Teachers Script
Membuat user pengajar saja tanpa skills dan availability.

Penggunaan:
    python seed_teachers.py
"""

from app import create_app, db
from app.models import User

app = create_app()

# Data pengajar dari VPS production
TEACHERS_DATA = [
    {
        "email": "honokalvaredh278@gmail.com",
        "name": "Sir Honok A",
        "phone": "081389247655",
        "password_hash": "scrypt:32768:8:1$oiuiPvgZ4tXlsDga$7cad9c8c409a2cc6e0ae9cb01d58a4a926368059c36445fea18c1828a44641e6946741b864315ae892ca3cb85183679fc1eabe24bab5c7e4c298e63269690a45"
    },
    {
        "email": "kurniapratiwi21@gmail.com",
        "name": "Ms. Figih Kurnia",
        "phone": "085781406577",
        "password_hash": "scrypt:32768:8:1$sMT6LiRVBw5WKfgy$c15770f422dceb810a882e1190f4c58781afefd5bd0ff6f9f14dbf534d67ef2eb4dac9ac93b6fc235b166f7dbdd73cee5fbc5a34b7ca9ef903258267e1a961a0"
    },
    {
        "email": "zohraenny.sfa@gmail.com",
        "name": "Ms. Zohraenny",
        "phone": "085813428870",
        "password_hash": "scrypt:32768:8:1$cyaABsTFTNfJwav1$62a4fe391154879e8a7b270f95cc990ee5cd3f5ade2ca9ef72855a10836f239972f6f085717cbc4c57f0a40865f20b281d34e7c3cf018c6ecca26f1943557650"
    },
    {
        "email": "elissachristharyanto@gmail.com",
        "name": "Ms. Elissa C Haryanto",
        "phone": "081585943338",
        "password_hash": "scrypt:32768:8:1$936lcWZ7CDDdIl85$5c15fecf9ec80d5d66720fcf36fa61698353f61ab7a57ea8eef5ce98e2f2d024329c87abb65670e6c129030928cbc2c284b0ce13a4b93300478c4f17c3b9ae08"
    }
]


def seed_teachers():
    """Seed teachers - user only"""
    print("=" * 50)
    print("🧑‍🏫 SEEDING TEACHERS")
    print("=" * 50)
    
    for t_data in TEACHERS_DATA:
        existing = User.query.filter_by(email=t_data["email"]).first()
        
        if existing:
            print(f"  ℹ️  {t_data['name']} sudah ada (ID: {existing.id})")
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
            print(f"  ✅ {t_data['name']} (ID: {teacher.id})")
    
    db.session.commit()
    
    print("\n🎉 TEACHER SEEDING COMPLETE!")
    print("Skills dan availability bisa diisi manual via admin panel.")


if __name__ == '__main__':
    with app.app_context():
        seed_teachers()
