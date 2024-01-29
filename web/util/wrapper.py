from functools import wraps
from flask import session, abort, flash, redirect, url_for, request, g

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user:
            return f(*args, **kwargs)
        else:
            flash('Please login first!', 'warning')
            return redirect(url_for('user.show_login', next=request.path))
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.is_admin:
            return f(*args, **kwargs)
        else:
            abort(403)
        
    return decorated_function