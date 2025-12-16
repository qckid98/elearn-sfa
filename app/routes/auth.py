from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User, Enrollment

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('Email atau password salah.')
        
    return render_template('login.html')

@bp.route('/activate/<token>', methods=['GET', 'POST'])
def activate(token):
    user = User.query.filter_by(activation_token=token).first_or_404()
    
    if request.method == 'POST':
        user.set_password(request.form['password'])
        user.activation_token = None
        user.name = request.form['name']
        db.session.commit()
        
        login_user(user)
        
        # Cek Program untuk Redirect
        enroll = Enrollment.query.filter_by(student_id=user.id).first()
        if enroll.program.is_batch_based:
            # FT langsung ke dashboard
            enroll.status = 'active'
            db.session.commit()
            return redirect(url_for('main.dashboard'))
        else:
            # Regular masuk ke Wizard Jadwal
            return redirect(url_for('onboarding.schedule_wizard'))
            
    return render_template('activate.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))