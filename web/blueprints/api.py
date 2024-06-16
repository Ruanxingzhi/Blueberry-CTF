from flask import Blueprint, abort, g, url_for, redirect, flash, current_app
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
        user_current_container_count = conn.execute("SELECT COUNT(*) as cnt FROM instance WHERE user_id = %s AND status = 'running'", [uid]).fetchone()['cnt']

    container_limit = int(current_app.config['PLAYER_MAX_CONTAINER_NUM'])
    if user_current_container_count >= container_limit:
        flash(f'You can only have {container_limit} running containers.', 'warning')
        return redirect(url_for('problem.show_problem_detail', pid=pid))

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

@bp.route('/extend_instance_time/<int:pid>', methods = ["GET"])
def extend_instance_time(pid):
    uid = g.user['id']

    with db_pool.connection() as conn:
        instance_id = conn.execute("SELECT id FROM instance WHERE user_id = %s AND problem_id = %s AND status = 'running'", [uid, pid]).fetchone()['id']

    if not instance_id:
        abort(418)

    with db_pool.connection() as conn:
        conn.execute("UPDATE instance SET end_time = end_time + INTERVAL '1 hour' WHERE id = %s", [instance_id])

    return redirect(url_for('problem.show_problem_detail', pid=pid))