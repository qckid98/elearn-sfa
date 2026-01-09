from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Validate configuration on startup
    Config.validate()

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    
    # Initialize security middleware
    from app.security import security
    security.init_app(app)

    # --- BAGIAN REGISTRASI BLUEPRINT ---
    from app.routes import auth, main, onboarding, attendance, admin, teacher, admin_syllabus, portfolio
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(onboarding.bp)
    app.register_blueprint(attendance.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(teacher.bp)
    app.register_blueprint(admin_syllabus.bp)
    app.register_blueprint(portfolio.bp)

    # Context Processor untuk menyisipkan waktu server ke semua template
    from datetime import datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    return app

from app import models

@login.user_loader
def load_user(id):
    return models.User.query.get(int(id))