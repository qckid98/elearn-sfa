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
    from app.routes import auth, main, onboarding, attendance, admin, teacher, admin_syllabus, portfolio, admin_voucher, vendor
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(onboarding.bp)
    app.register_blueprint(attendance.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(teacher.bp)
    app.register_blueprint(admin_syllabus.bp)
    app.register_blueprint(portfolio.bp)
    app.register_blueprint(admin_voucher.bp)
    app.register_blueprint(vendor.bp)

    # Context Processor untuk menyisipkan waktu server ke semua template
    from datetime import datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    
    # Context Processor untuk pending attendance requests count (admin sidebar badge)
    @app.context_processor
    def inject_pending_attendance():
        from flask_login import current_user
        if current_user.is_authenticated and current_user.role == 'admin':
            from app.models import AttendanceRequest
            count = AttendanceRequest.query.filter_by(approval_status='pending').count()
            return {'pending_attendance_count': count}
        return {'pending_attendance_count': 0}
    
    # Context Processor untuk pending reschedule requests count (admin sidebar badge)
    @app.context_processor
    def inject_pending_reschedule():
        from flask_login import current_user
        if current_user.is_authenticated and current_user.role == 'admin':
            from app.models import RescheduleRequest
            count = RescheduleRequest.query.filter_by(status='pending').count()
            return {'pending_reschedule_count': count}
        return {'pending_reschedule_count': 0}

    # Initialize scheduler for background notification jobs
    from app.scheduler import init_scheduler
    init_scheduler(app)

    return app

from app import models

@login.user_loader
def load_user(id):
    return models.User.query.get(int(id))