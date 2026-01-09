"""
Security middleware for Sparks Fashion Academy LMS.
Provides protection against common web vulnerabilities.
"""

from functools import wraps
from flask import request, abort, current_app, session
from datetime import datetime, timedelta
import secrets
import re


class SecurityMiddleware:
    """Security middleware for Flask application."""
    
    def __init__(self, app=None):
        self.app = app
        self.failed_login_attempts = {}  # IP -> (count, last_attempt)
        self.blocked_ips = set()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware with Flask app."""
        self.app = app
        
        # Set secure defaults
        app.config.setdefault('MAX_LOGIN_ATTEMPTS', 5)
        app.config.setdefault('LOGIN_BLOCK_DURATION', 900)  # 15 minutes
        app.config.setdefault('SESSION_COOKIE_SECURE', True)
        app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
        app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
        app.config.setdefault('PERMANENT_SESSION_LIFETIME', timedelta(hours=24))
        
        # Register before_request handler
        app.before_request(self._before_request)
        
        # Register after_request handler for security headers
        app.after_request(self._add_security_headers)
        
        # Make security instance available in templates
        @app.context_processor
        def inject_security():
            return {'csrf_token': generate_csrf_token}
    
    def _before_request(self):
        """Check security before each request."""
        ip = self._get_client_ip()
        
        # Check if IP is blocked
        if ip in self.blocked_ips:
            # Check if block has expired
            if ip in self.failed_login_attempts:
                _, last_attempt = self.failed_login_attempts[ip]
                block_duration = current_app.config.get('LOGIN_BLOCK_DURATION', 900)
                if (datetime.now() - last_attempt).total_seconds() > block_duration:
                    self.blocked_ips.discard(ip)
                    self.failed_login_attempts.pop(ip, None)
                else:
                    abort(429, description="Terlalu banyak percobaan login. Silakan coba lagi dalam 15 menit.")
        
        # Check for suspicious patterns (only on specific paths to avoid false positives)
        if self._is_suspicious_request():
            current_app.logger.warning(f"[SECURITY] Request mencurigakan dari {ip}: {request.path}")
            abort(403, description="Akses ditolak")
    
    def _add_security_headers(self, response):
        """Add security headers to response."""
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Content Security Policy - Configured for SFA app
        csp = (
            "default-src 'self'; "
            # Scripts - Bootstrap, jQuery, SweetAlert, etc
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://code.jquery.com; "
            # Styles - Bootstrap, Font Awesome, Google Fonts
            "style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            # Fonts - Google Fonts, Font Awesome
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
            # Images - allow data URIs for inline images
            "img-src 'self' data: https: blob:; "
            # Connect - for AJAX/fetch calls
            "connect-src 'self'; "
            # Frame ancestors - prevent clickjacking
            "frame-ancestors 'self';"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # Permissions Policy
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=()'
        )
        
        return response
    
    def _get_client_ip(self):
        """Get real client IP, considering reverse proxy (Nginx)."""
        # X-Forwarded-For header from Nginx reverse proxy
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        # X-Real-IP header (alternative)
        if request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        return request.remote_addr
    
    def _is_suspicious_request(self):
        """Detect suspicious request patterns."""
        path = request.path.lower()
        query = request.query_string.decode('utf-8', errors='ignore').lower()
        
        # Skip checking for static files and known safe routes
        safe_prefixes = ['/static/', '/login', '/logout', '/activate/']
        if any(path.startswith(prefix) for prefix in safe_prefixes):
            return False
        
        # Common attack patterns to block
        suspicious_patterns = [
            r'\.\./',                    # Path traversal
            r'<script',                  # XSS
            r'javascript:',              # XSS
            r'on\w+\s*=',               # Event handlers XSS
            r'union\s+select',           # SQL injection
            r'select\s+.*\s+from',       # SQL injection
            r'insert\s+into',            # SQL injection
            r'drop\s+table',             # SQL injection
            r';\s*--',                   # SQL comment injection
            r'/etc/passwd',              # LFI
            r'/proc/self',               # LFI
            r'\.php$',                   # PHP file access
            r'\.asp$',                   # ASP file access
            r'wp-admin',                 # WordPress probing
            r'wp-login',                 # WordPress probing
            r'phpmyadmin',               # phpMyAdmin probing
            r'\.git/',                   # Git folder access
            r'\.env$',                   # Env file access
            r'\.htaccess',               # Apache config access
        ]
        
        combined = path + query
        for pattern in suspicious_patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return True
        
        return False
    
    def record_failed_login(self, ip=None):
        """Record a failed login attempt. Call this from auth.login route."""
        if ip is None:
            ip = self._get_client_ip()
        
        now = datetime.now()
        max_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
        block_duration = current_app.config.get('LOGIN_BLOCK_DURATION', 900)
        
        if ip in self.failed_login_attempts:
            count, last_attempt = self.failed_login_attempts[ip]
            
            # Reset if block duration has passed
            if (now - last_attempt).total_seconds() > block_duration:
                self.failed_login_attempts[ip] = (1, now)
                self.blocked_ips.discard(ip)
            else:
                count += 1
                self.failed_login_attempts[ip] = (count, now)
                
                if count >= max_attempts:
                    self.blocked_ips.add(ip)
                    current_app.logger.warning(
                        f"[SECURITY] IP {ip} diblokir setelah {count} percobaan login gagal"
                    )
                    return count, True  # Return count and blocked status
                
                return count, False
        else:
            self.failed_login_attempts[ip] = (1, now)
        
        return 1, False
    
    def reset_failed_login(self, ip=None):
        """Reset failed login counter on successful login."""
        if ip is None:
            ip = self._get_client_ip()
        
        self.failed_login_attempts.pop(ip, None)
        self.blocked_ips.discard(ip)
    
    def get_remaining_attempts(self, ip=None):
        """Get remaining login attempts for an IP."""
        if ip is None:
            ip = self._get_client_ip()
        
        max_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
        
        if ip in self.failed_login_attempts:
            count, _ = self.failed_login_attempts[ip]
            return max(0, max_attempts - count)
        
        return max_attempts


# CSRF Protection utilities
def generate_csrf_token():
    """Generate a CSRF token for forms."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def validate_csrf_token(token):
    """Validate CSRF token."""
    return token and token == session.get('_csrf_token')


def csrf_protect(f):
    """
    Decorator to protect routes from CSRF attacks.
    Usage: @csrf_protect on any POST/PUT/DELETE route
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not validate_csrf_token(token):
                current_app.logger.warning(
                    f"[SECURITY] CSRF token tidak valid dari {request.remote_addr}"
                )
                abort(403, description="Token keamanan tidak valid. Silakan refresh halaman.")
        return f(*args, **kwargs)
    return decorated_function


# Password strength checker
def check_password_strength(password):
    """
    Check password strength. Returns list of error messages.
    Used in activation form.
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password minimal 8 karakter")
    if not re.search(r'[A-Z]', password):
        errors.append("Password harus mengandung huruf besar")
    if not re.search(r'[a-z]', password):
        errors.append("Password harus mengandung huruf kecil")
    if not re.search(r'\d', password):
        errors.append("Password harus mengandung angka")
    
    return errors


# Rate limiting decorator
def rate_limit(max_requests=60, window_seconds=60):
    """
    Simple rate limiting decorator.
    Default: 60 requests per minute
    """
    request_counts = {}
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ',' in str(ip):
                ip = ip.split(',')[0].strip()
            
            now = datetime.now()
            key = f"{ip}:{f.__name__}"
            
            if key in request_counts:
                count, window_start = request_counts[key]
                
                if (now - window_start).total_seconds() > window_seconds:
                    request_counts[key] = (1, now)
                elif count >= max_requests:
                    current_app.logger.warning(
                        f"[SECURITY] Rate limit terlampaui dari {ip} pada {f.__name__}"
                    )
                    abort(429, description="Terlalu banyak request. Silakan tunggu sebentar.")
                else:
                    request_counts[key] = (count + 1, window_start)
            else:
                request_counts[key] = (1, now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Input sanitization
def sanitize_input(text, max_length=1000):
    """
    Sanitize user input. Use for text fields.
    """
    if text is None:
        return None
    
    # Convert to string and strip
    text = str(text).strip()
    
    # Limit length
    text = text[:max_length]
    
    # Remove null bytes (potential security issue)
    text = text.replace('\x00', '')
    
    return text


def sanitize_phone(phone):
    """
    Sanitize and normalize Indonesian phone number.
    Returns phone in 62xxx format.
    """
    if not phone:
        return None
    
    # Remove non-digit characters
    clean = re.sub(r'\D', '', phone)
    
    # Normalize to 62xxx format
    if clean.startswith('0'):
        clean = '62' + clean[1:]
    elif clean.startswith('62'):
        pass  # Already correct
    elif clean.startswith('+62'):
        clean = clean[1:]  # Remove +
    
    return clean


def sanitize_email(email):
    """Sanitize and validate email format."""
    if not email:
        return None
    
    email = email.strip().lower()
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return None
    
    return email


# Security singleton instance
security = SecurityMiddleware()
