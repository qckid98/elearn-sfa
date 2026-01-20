"""
Vendor Routes
Dashboard and voucher claim for vendor users
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Vendor, VoucherType, Voucher, VendorPayment
from datetime import datetime
from functools import wraps

bp = Blueprint('vendor', __name__, url_prefix='/vendor')


def vendor_required(f):
    """Decorator to require vendor role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'vendor':
            flash('Akses ditolak. Halaman ini hanya untuk vendor.', 'error')
            return redirect(url_for('main.dashboard'))
        if not current_user.vendor:
            flash('Akun vendor Anda belum terhubung ke data vendor.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/dashboard')
@login_required
@vendor_required
def dashboard():
    """Vendor dashboard showing outstanding balance and recent claims"""
    vendor = current_user.vendor
    
    # Get claimed vouchers
    claimed_vouchers = Voucher.query.join(VoucherType).filter(
        VoucherType.vendor_id == vendor.id,
        Voucher.status == 'claimed'
    ).order_by(Voucher.claimed_at.desc()).limit(10).all()
    
    # Get payments
    payments = VendorPayment.query.filter_by(vendor_id=vendor.id).order_by(
        VendorPayment.payment_date.desc()
    ).limit(10).all()
    
    # Calculate totals
    all_claimed = Voucher.query.join(VoucherType).filter(
        VoucherType.vendor_id == vendor.id,
        Voucher.status == 'claimed'
    ).all()
    
    total_claimed = sum(v.voucher_type.value for v in all_claimed)
    total_paid = sum(p.amount for p in vendor.payments)
    outstanding = total_claimed - total_paid
    
    return render_template('vendor/dashboard.html',
                          vendor=vendor,
                          claimed_vouchers=claimed_vouchers,
                          payments=payments,
                          total_claimed=total_claimed,
                          total_paid=total_paid,
                          outstanding=outstanding,
                          vouchers_count=len(all_claimed))


@bp.route('/scan')
@login_required
@vendor_required
def scan():
    """Page for scanning voucher QR code"""
    return render_template('vendor/scan.html')


@bp.route('/claim', methods=['POST'])
@login_required
@vendor_required
def claim():
    """Claim a voucher"""
    vendor = current_user.vendor
    
    code = request.form.get('code', '').strip().upper()
    pin = request.form.get('pin', '').strip()
    
    if not code or not pin:
        flash('Kode voucher dan PIN wajib diisi.', 'error')
        return redirect(url_for('vendor.scan'))
    
    # Find voucher
    voucher = Voucher.query.filter_by(code=code).first()
    
    if not voucher:
        flash('Voucher tidak ditemukan.', 'error')
        return redirect(url_for('vendor.scan'))
    
    # Check if voucher belongs to this vendor's type
    if voucher.voucher_type.vendor_id != vendor.id:
        flash('Voucher ini bukan untuk vendor Anda.', 'error')
        return redirect(url_for('vendor.scan'))
    
    # Check status
    if voucher.status == 'claimed':
        flash('Voucher sudah pernah di-claim.', 'error')
        return redirect(url_for('vendor.scan'))
    
    if voucher.status != 'active':
        flash(f'Voucher tidak aktif (status: {voucher.status}).', 'error')
        return redirect(url_for('vendor.scan'))
    
    # Verify PIN
    if not voucher.check_pin(pin):
        flash('PIN salah.', 'error')
        return redirect(url_for('vendor.scan'))
    
    # Claim the voucher
    voucher.status = 'claimed'
    voucher.claimed_at = datetime.utcnow()
    voucher.claimed_by_vendor_id = vendor.id
    
    db.session.commit()
    
    flash(f'✅ Voucher {code} berhasil di-claim! Nilai: Rp {voucher.voucher_type.value:,}', 'success')
    return redirect(url_for('vendor.dashboard'))


@bp.route('/verify/<code>')
@login_required
@vendor_required
def verify(code):
    """Verify voucher by code (from QR scan)"""
    vendor = current_user.vendor
    
    voucher = Voucher.query.filter_by(code=code.upper()).first()
    
    if not voucher:
        return render_template('vendor/verify_result.html', 
                              valid=False, 
                              message='Voucher tidak ditemukan.')
    
    if voucher.voucher_type.vendor_id != vendor.id:
        return render_template('vendor/verify_result.html',
                              valid=False,
                              message='Voucher ini bukan untuk vendor Anda.')
    
    if voucher.status == 'claimed':
        return render_template('vendor/verify_result.html',
                              valid=False,
                              message=f'Voucher sudah di-claim pada {voucher.claimed_at.strftime("%d/%m/%Y")}.')
    
    if voucher.status != 'active':
        return render_template('vendor/verify_result.html',
                              valid=False,
                              message=f'Voucher tidak aktif (status: {voucher.status}).')
    
    # Valid voucher, show PIN form
    return render_template('vendor/verify_result.html',
                          valid=True,
                          voucher=voucher)


@bp.route('/history')
@login_required
@vendor_required
def history():
    """Full claim history"""
    vendor = current_user.vendor
    
    claimed_vouchers = Voucher.query.join(VoucherType).filter(
        VoucherType.vendor_id == vendor.id,
        Voucher.status == 'claimed'
    ).order_by(Voucher.claimed_at.desc()).all()
    
    return render_template('vendor/history.html',
                          vendor=vendor,
                          claimed_vouchers=claimed_vouchers)


@bp.route('/payments')
@login_required
@vendor_required
def payments():
    """Payment history from SFA"""
    vendor = current_user.vendor
    
    payments = VendorPayment.query.filter_by(vendor_id=vendor.id).order_by(
        VendorPayment.payment_date.desc()
    ).all()
    
    total_paid = sum(p.amount for p in payments)
    
    return render_template('vendor/payments.html',
                          vendor=vendor,
                          payments=payments,
                          total_paid=total_paid)
