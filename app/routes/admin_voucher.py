"""
Admin Voucher Routes
Manage vendors, voucher types, vouchers, and vendor payments
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Vendor, VoucherType, Voucher, VendorPayment, User
from datetime import datetime, date
import random

bp = Blueprint('admin_voucher', __name__, url_prefix='/admin/voucher')


def admin_required(f):
    """Decorator to require admin role"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Akses ditolak.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# VENDOR MANAGEMENT
# ============================================

@bp.route('/vendors')
@login_required
@admin_required
def vendor_list():
    """List all vendors"""
    vendors = Vendor.query.order_by(Vendor.name).all()
    return render_template('admin/voucher/vendors.html', vendors=vendors)


@bp.route('/vendors/add', methods=['GET', 'POST'])
@login_required
@admin_required
def vendor_add():
    """Add new vendor"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '').strip()
        
        if not name:
            flash('Nama vendor wajib diisi.', 'error')
            return redirect(request.url)
        
        if not password:
            flash('Password vendor wajib diisi.', 'error')
            return redirect(request.url)
        
        vendor = Vendor(
            name=name,
            phone=phone,
            email=email,
            address=address
        )
        vendor.set_password(password)
        
        db.session.add(vendor)
        db.session.commit()
        
        flash(f'Vendor "{name}" berhasil ditambahkan.', 'success')
        return redirect(url_for('admin_voucher.vendor_list'))
    
    return render_template('admin/voucher/vendor_form.html', vendor=None)


@bp.route('/vendors/<int:vendor_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def vendor_edit(vendor_id):
    """Edit vendor"""
    vendor = Vendor.query.get_or_404(vendor_id)
    
    if request.method == 'POST':
        vendor.name = request.form.get('name', '').strip()
        vendor.phone = request.form.get('phone', '').strip()
        vendor.email = request.form.get('email', '').strip()
        vendor.address = request.form.get('address', '').strip()
        vendor.is_active = request.form.get('is_active') == 'on'
        
        new_password = request.form.get('password', '').strip()
        if new_password:
            vendor.set_password(new_password)
        
        db.session.commit()
        flash(f'Vendor "{vendor.name}" berhasil diperbarui.', 'success')
        return redirect(url_for('admin_voucher.vendor_list'))
    
    return render_template('admin/voucher/vendor_form.html', vendor=vendor)


# ============================================
# VOUCHER TYPE MANAGEMENT
# ============================================

@bp.route('/types')
@login_required
@admin_required
def voucher_type_list():
    """List all voucher types"""
    voucher_types = VoucherType.query.order_by(VoucherType.vendor_id, VoucherType.name).all()
    return render_template('admin/voucher/voucher_types.html', voucher_types=voucher_types)


@bp.route('/types/add', methods=['GET', 'POST'])
@login_required
@admin_required
def voucher_type_add():
    """Add new voucher type"""
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        value = request.form.get('value', '0')
        vendor_id = request.form.get('vendor_id')
        description = request.form.get('description', '').strip()
        
        if not name or not vendor_id:
            flash('Nama dan vendor wajib diisi.', 'error')
            return redirect(request.url)
        
        voucher_type = VoucherType(
            name=name,
            value=int(value),
            vendor_id=int(vendor_id),
            description=description
        )
        
        db.session.add(voucher_type)
        db.session.commit()
        
        flash(f'Tipe voucher "{name}" berhasil ditambahkan.', 'success')
        return redirect(url_for('admin_voucher.voucher_type_list'))
    
    return render_template('admin/voucher/voucher_type_form.html', 
                          voucher_type=None, vendors=vendors)


@bp.route('/types/<int:type_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def voucher_type_edit(type_id):
    """Edit voucher type"""
    voucher_type = VoucherType.query.get_or_404(type_id)
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()
    
    if request.method == 'POST':
        voucher_type.name = request.form.get('name', '').strip()
        voucher_type.value = int(request.form.get('value', '0'))
        voucher_type.vendor_id = int(request.form.get('vendor_id'))
        voucher_type.description = request.form.get('description', '').strip()
        voucher_type.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash(f'Tipe voucher "{voucher_type.name}" berhasil diperbarui.', 'success')
        return redirect(url_for('admin_voucher.voucher_type_list'))
    
    return render_template('admin/voucher/voucher_type_form.html',
                          voucher_type=voucher_type, vendors=vendors)


# ============================================
# VOUCHER MANAGEMENT
# ============================================

@bp.route('/vouchers')
@login_required
@admin_required
def voucher_list():
    """List all vouchers with filters"""
    status_filter = request.args.get('status', '')
    voucher_type_filter = request.args.get('type', '')
    
    query = Voucher.query
    
    if status_filter:
        query = query.filter(Voucher.status == status_filter)
    if voucher_type_filter:
        query = query.filter(Voucher.voucher_type_id == int(voucher_type_filter))
    
    vouchers = query.order_by(Voucher.issued_at.desc()).all()
    voucher_types = VoucherType.query.filter_by(is_active=True).all()
    
    return render_template('admin/voucher/vouchers.html',
                          vouchers=vouchers,
                          voucher_types=voucher_types,
                          status_filter=status_filter,
                          type_filter=voucher_type_filter)


@bp.route('/vouchers/generate', methods=['GET', 'POST'])
@login_required
@admin_required
def voucher_generate():
    """Generate voucher for a student"""
    voucher_types = VoucherType.query.filter_by(is_active=True).all()
    students = User.query.filter_by(role='student').order_by(User.name).all()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        voucher_type_id = request.form.get('voucher_type_id')
        notes = request.form.get('notes', '').strip()
        
        if not student_id or not voucher_type_id:
            flash('Siswa dan tipe voucher wajib dipilih.', 'error')
            return redirect(request.url)
        
        # Generate unique code and PIN
        code = Voucher.generate_code()
        pin = str(random.randint(1000, 9999))  # 4-digit PIN
        
        voucher = Voucher(
            code=code,
            voucher_type_id=int(voucher_type_id),
            student_id=int(student_id),
            notes=notes,
            created_by=current_user.id
        )
        voucher.set_pin(pin)
        
        db.session.add(voucher)
        db.session.commit()
        
        # Show the PIN to admin (only this time!)
        flash(f'Voucher {code} berhasil dibuat. PIN: {pin} (catat ini!)', 'success')
        return redirect(url_for('admin_voucher.voucher_detail', voucher_id=voucher.id, show_pin=pin))
    
    return render_template('admin/voucher/voucher_generate.html',
                          voucher_types=voucher_types,
                          students=students)


@bp.route('/vouchers/<int:voucher_id>')
@login_required
@admin_required
def voucher_detail(voucher_id):
    """View voucher detail with QR code"""
    voucher = Voucher.query.get_or_404(voucher_id)
    show_pin = request.args.get('show_pin')  # Only shown after generation
    
    return render_template('admin/voucher/voucher_detail.html',
                          voucher=voucher, show_pin=show_pin)


@bp.route('/vouchers/<int:voucher_id>/cancel', methods=['POST'])
@login_required
@admin_required
def voucher_cancel(voucher_id):
    """Cancel a voucher"""
    voucher = Voucher.query.get_or_404(voucher_id)
    
    if voucher.status == 'claimed':
        flash('Voucher yang sudah di-claim tidak bisa dibatalkan.', 'error')
        return redirect(url_for('admin_voucher.voucher_detail', voucher_id=voucher_id))
    
    voucher.status = 'cancelled'
    db.session.commit()
    
    flash(f'Voucher {voucher.code} berhasil dibatalkan.', 'success')
    return redirect(url_for('admin_voucher.voucher_list'))


# ============================================
# OUTSTANDING BALANCE
# ============================================

@bp.route('/balance')
@login_required
@admin_required
def vendor_balance():
    """View outstanding balance for all vendors"""
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()
    
    balance_data = []
    for vendor in vendors:
        # Count vouchers claimed
        claimed_vouchers = Voucher.query.join(VoucherType).filter(
            VoucherType.vendor_id == vendor.id,
            Voucher.status == 'claimed'
        ).all()
        
        total_claimed = sum(v.voucher_type.value for v in claimed_vouchers)
        total_paid = sum(p.amount for p in vendor.payments)
        
        balance_data.append({
            'vendor': vendor,
            'vouchers_claimed': len(claimed_vouchers),
            'total_claimed': total_claimed,
            'total_paid': total_paid,
            'outstanding': total_claimed - total_paid
        })
    
    return render_template('admin/voucher/balance.html', balance_data=balance_data)


@bp.route('/balance/<int:vendor_id>')
@login_required
@admin_required
def vendor_balance_detail(vendor_id):
    """View detailed balance for a vendor"""
    vendor = Vendor.query.get_or_404(vendor_id)
    
    claimed_vouchers = Voucher.query.join(VoucherType).filter(
        VoucherType.vendor_id == vendor.id,
        Voucher.status == 'claimed'
    ).order_by(Voucher.claimed_at.desc()).all()
    
    payments = VendorPayment.query.filter_by(vendor_id=vendor_id).order_by(VendorPayment.payment_date.desc()).all()
    
    total_claimed = sum(v.voucher_type.value for v in claimed_vouchers)
    total_paid = sum(p.amount for p in payments)
    
    return render_template('admin/voucher/balance_detail.html',
                          vendor=vendor,
                          claimed_vouchers=claimed_vouchers,
                          payments=payments,
                          total_claimed=total_claimed,
                          total_paid=total_paid,
                          outstanding=total_claimed - total_paid)


@bp.route('/payments/add', methods=['GET', 'POST'])
@login_required
@admin_required
def payment_add():
    """Record payment to vendor"""
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()
    vendor_id = request.args.get('vendor_id')
    
    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id')
        amount = request.form.get('amount', '0')
        payment_date = request.form.get('payment_date')
        payment_method = request.form.get('payment_method', '').strip()
        reference = request.form.get('reference', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not vendor_id or not amount or not payment_date:
            flash('Vendor, jumlah, dan tanggal wajib diisi.', 'error')
            return redirect(request.url)
        
        payment = VendorPayment(
            vendor_id=int(vendor_id),
            amount=int(amount),
            payment_date=datetime.strptime(payment_date, '%Y-%m-%d').date(),
            payment_method=payment_method,
            reference=reference,
            notes=notes,
            created_by=current_user.id
        )
        
        db.session.add(payment)
        db.session.commit()
        
        vendor = Vendor.query.get(vendor_id)
        flash(f'Pembayaran Rp {int(amount):,} ke {vendor.name} berhasil dicatat.', 'success')
        return redirect(url_for('admin_voucher.vendor_balance_detail', vendor_id=vendor_id))
    
    return render_template('admin/voucher/payment_form.html',
                          vendors=vendors,
                          selected_vendor_id=int(vendor_id) if vendor_id else None)


# ============================================
# QR CODE ENDPOINT
# ============================================

@bp.route('/vouchers/<int:voucher_id>/qr')
@login_required
@admin_required
def voucher_qr(voucher_id):
    """Generate QR code for voucher"""
    import io
    from flask import Response
    
    try:
        import qrcode
    except ImportError:
        return "QR Code library not installed", 500
    
    voucher = Voucher.query.get_or_404(voucher_id)
    
    # QR contains the voucher code
    qr_data = voucher.code
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return Response(buffer.getvalue(), mimetype='image/png')
