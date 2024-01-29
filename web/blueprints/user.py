from flask import Blueprint, render_template, request, flash, redirect, url_for, session, g, abort
from util.db import db_pool
from passlib.hash import bcrypt_sha256
from util.wrapper import login_required
import json

bp = Blueprint('user', __name__, url_prefix='/user')

@bp.route('/login', methods=['GET', 'POST'])
def show_login():
    if request.method == 'GET':
        return render_template('user/login.html')
    
    try:
        cli_username = request.form.get('username')
        cli_password = request.form.get('password')
        assert cli_username and cli_password
    except Exception:
        abort(418)

    with db_pool.connection() as conn:
        user_info = conn.execute('SELECT * FROM user_info WHERE username = %s', [cli_username]).fetchone()
        if not user_info:
            flash('No such user.', 'warning')
            return render_template('user/login.html')

        if not bcrypt_sha256.verify(cli_password, user_info['password']):
            flash('Password error.', 'warning')
            return render_template('user/login.html')

        session['user_id'] = user_info['id']

        if 'next' in request.args:
            return redirect(request.args['next'])

        return redirect(url_for('show_index'))

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('user.show_login'))

@bp.route('/edit', methods=['GET', 'POST'])
@login_required
def show_edit():
    if request.method == 'GET':
        return render_template('user/edit.html')
    else:
        try:
            cli_origin = request.form.get('originpassword')
            cli_new_pwd = request.form.get('newpassword')
            cli_new_pwd2 = request.form.get('newpassword2')

            assert cli_origin and cli_new_pwd and cli_new_pwd2
            assert len(cli_new_pwd) >= 8
        except Exception:
            abort(418)

        if not bcrypt_sha256.verify(cli_origin, g.user['password']):
            flash('Current password incorrect.', 'error')
            return render_template('user/edit.html')

        if cli_new_pwd != cli_new_pwd2:
            flash('New passwords not match.', 'error')
            return render_template('user/edit.html')
        
        pwd_hash = bcrypt_sha256.hash(cli_new_pwd)

        with db_pool.connection() as conn:
            conn.execute('UPDATE user_info SET password = %s WHERE id = %s', [pwd_hash, g.user['id']])

        flash('Password changed.', 'success')
        return render_template('user/edit.html')


@bp.route('/register', methods=['GET', 'POST'])
def show_register():
    with db_pool.connection() as conn:
        is_allow = conn.execute("SELECT config_value FROM site_config WHERE config_key = 'is_allow_register'").fetchone()['config_value']
        if is_allow != 'yes':
            abort(403)

    g.extra = json.loads(conn.execute("SELECT config_value FROM site_config WHERE config_key = 'userinfo_extra_fields'").fetchone()['config_value'])

    if request.method == 'GET':
        return render_template('user/register.html')
    else:
        try:
            cli_username = request.form.get('username')
            cli_email = request.form.get('email')
            cli_password = request.form.get('password')
            cli_password2 = request.form.get('password2')

            assert cli_username and cli_email and cli_password and cli_password2
            assert 8 <= len(cli_password) <= 50
            assert len(cli_username) <= 20

        except Exception:
            abort(418)

        with db_pool.connection() as conn:
            if conn.execute('SELECT * FROM user_info WHERE email = %s', [cli_email]).fetchone():
                flash('Email occupied by another user.', 'warning')
                return render_template('user/register.html')
            
            if conn.execute('SELECT * FROM user_info WHERE username = %s', [cli_username]).fetchone():
                flash('Username occupied by another user.', 'warning')
                return render_template('user/register.html')
            
            if cli_password != cli_password2:
                flash('Passwords not match.', 'warning')
                return render_template('user/register.html')
            
            extra = {
                key:request.form.get(key, '-') for key in g.extra
            }

            extra = json.dumps(extra, ensure_ascii=False)

            conn.execute('INSERT INTO user_info (username, email, password, extra_info) VALUES (%s, %s, %s, %s)', [cli_username, cli_email, bcrypt_sha256.hash(cli_password), extra])
            flash('Register OK, please login.', 'success')
            
            return redirect(url_for('user.show_login'))

@bp.route('/<int:uid>')
@login_required
def show_user_detail(uid):
    with db_pool.connection() as conn:
        info = conn.execute('SELECT * FROM user_info WHERE id = %s', [uid]).fetchone()
        g.solves = list(conn.execute('''
WITH g AS (SELECT u.*, v.point FROM view_user_solve as u JOIN view_task_score as v ON u.task_id = v.id WHERE user_id = %s),
r AS (SELECT g.*, task_order FROM g JOIN view_task_in_problem AS v ON g.task_id = v.task_id)
SELECT r.*, title FROM r JOIN problem ON r.problem_id = problem.id ORDER BY submit_time desc
        ''', [uid]))
    
    if not info:
        abort(404)
    
    if not info['is_visible']:
        abort(403)
    
    info['register_time'] = info['register_time'].strftime('%Y/%m/%d')

    g.info = info
    g.solve_cnt = len(g.solves)
    g.total_point = sum(x['point'] for x in g.solves)

    return render_template('user/detail.html')