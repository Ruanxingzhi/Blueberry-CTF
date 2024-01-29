from flask import Blueprint, abort, g, url_for, redirect, flash
from util.db import db_pool
from util.wrapper import login_required

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.before_request
@login_required
def login_req():
    pass

@bp.route('/launch_instance/<int:pid>')
def launch_instance(pid):
    uid = g.user['id']

    with db_pool.connection() as conn:
        problem_info = conn.execute('SELECT * FROM problem WHERE id = %s', [pid]).fetchone()
        latest_info = conn.execute('SELECT * FROM instance WHERE user_id = %s AND problem_id = %s ORDER BY request_time DESC LIMIT 1', [uid, pid]).fetchone()

    if not problem_info:
        abort(418)
    
    if problem_info['instance_type'] != 'private':
        abort(418)
    
    if not problem_info['is_visible'] and not g.user['is_admin']:
        abort(418)

    if latest_info:
        if latest_info['status'] in ['pending', 'running']:
            flash('Instance is running.', 'warning')
            return redirect(url_for('problem.show_problem_detail', pid=pid))

    with db_pool.connection() as conn:
        conn.execute("INSERT INTO instance(user_id, problem_id, status) VALUES (%s, %s, 'pending')", [uid, pid])

    return redirect(url_for('problem.show_problem_detail', pid=pid))

@bp.route('/destroy_instance/<int:pid>')
def destroy_instance(pid):
    uid = g.user['id']

    with db_pool.connection() as conn:
        latest_info = conn.execute('SELECT * FROM instance WHERE user_id = %s AND problem_id = %s ORDER BY request_time DESC LIMIT 1', [uid, pid]).fetchone()

    if not latest_info:
        abort(418)

    if latest_info['status'] != 'running':
        return redirect(url_for('problem.show_problem_detail', pid=pid))

    with db_pool.connection() as conn:
        conn.execute("UPDATE instance SET end_time = current_timestamp(0) WHERE id = %s", [latest_info['id']])

    return redirect(url_for('problem.show_problem_detail', pid=pid))

@bp.route('/get_instance_status/<int:pid>', methods = ["POST"])
def get_instance_status(pid):
    uid = g.user['id']

    with db_pool.connection() as conn:
        latest_info = conn.execute('SELECT * FROM instance WHERE user_id = %s AND problem_id = %s ORDER BY request_time DESC LIMIT 1', [uid, pid]).fetchone()

    if not latest_info:
        abort(418)

    return {"status": latest_info["status"]}