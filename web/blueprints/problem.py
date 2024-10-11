from flask import Blueprint, render_template, g, flash, request, url_for, redirect, abort, current_app
from util.coder import parse_tags
from util.db import db_pool
from util.flag_check import check_flag
from traceback import format_exc
from util.wrapper import login_required, admin_required
from datetime import datetime, timedelta
import collections

bp = Blueprint('problem', __name__, url_prefix='/problem')


@bp.before_request
@login_required
def access_check():
    start_time = current_app.config['START_TIME']
    
    if not g.is_admin:
        if start_time and datetime.now() < start_time:
            return render_template('pages/errors/too_early.html', start_time=start_time), 425


@bp.route('/')
def show_problem_list():
    with db_pool.connection() as conn:
        g.problems = list(conn.execute('''
WITH t AS (SELECT problem_id, string_agg(task.id::text, '|' ORDER BY task.id) AS tasks FROM task GROUP BY problem_id),
p AS (SELECT problem.*, tasks FROM problem LEFT JOIN t ON problem.id = t.problem_id),
score AS (SELECT problem_id, SUM(point) as total_point FROM view_task_score GROUP BY problem_id),
r AS (SELECT p.*, score.total_point FROM p LEFT JOIN score ON p.id = score.problem_id),
solves AS (SELECT problem_id, string_agg(v.cnt::text, ' / ' ORDER BY task_id) as solve_info FROM view_task_solve_cnt AS v GROUP BY problem_id)
SELECT r.*, solve_info FROM r LEFT JOIN solves ON r.id = solves.problem_id WHERE (is_visible or %s) ORDER BY id
''', [g.is_admin]).fetchall())
        g.accepted = list(conn.execute(
            'SELECT task_id FROM accepted_submit WHERE user_id = %s', [g.user['id']]).fetchall())
        g.running_problems = list(conn.execute("SELECT problem_id FROM instance WHERE user_id = %s AND status = 'running'", [g.user['id']]).fetchall())
        g.running_problems = [x['problem_id'] for x in g.running_problems]

    g.accepted = [str(x['task_id']) for x in g.accepted]

    for x in g.problems:
        x['tag_list'] = parse_tags(x.pop('tag'))
        x['task_list'] = parse_tags(x.pop('tasks'))

    # 对所有题目的 tag 进行计数
    all_tags = [ tag.lower() for x in g.problems for tag in x['tag_list'] ]
    g.tags_count = collections.Counter(all_tags)

    # 获取 head_tags
    with db_pool.connection() as conn:
        dbres = conn.execute(
            "SELECT config_value FROM site_config WHERE config_key = 'head_tags'"
        ).fetchone()
        g.head_tags = parse_tags(dbres["config_value"])

    return render_template('problem/list.html')


@bp.route('/<int:pid>', methods=['GET', 'POST'])
def show_problem_detail(pid):
    if request.method == 'POST':
        try:
            task_id = int(request.form.get('taskid'))
            flag = request.form.get('flag')
            assert len(flag) > 0
        except Exception:
            abort(418)

        with db_pool.connection() as conn:
            prob_info = conn.execute('SELECT problem.* FROM problem JOIN task ON problem.id = task.problem_id WHERE task.id = %s', [task_id]).fetchone()

            is_exists = conn.execute('SELECT id FROM task WHERE id = %s', [task_id]).fetchone()
            is_alreay_accepted = conn.execute('SELECT id FROM accepted_submit WHERE task_id = %s AND user_id = %s', [
                                              task_id, g.user['id']]).fetchone()
        if not prob_info or not is_exists or is_alreay_accepted:
            abort(418)
        
        if prob_info['is_visible'] == False and not g.is_admin:
            abort(418)

        with db_pool.connection() as conn:
            submit_id = conn.execute('INSERT INTO log_flag(task_id, user_id, flag) VALUES (%s, %s, %s) RETURNING id', [
                                     task_id, g.user['id'], flag]).fetchone()['id']
            checker = conn.execute('SELECT checker FROM task WHERE id = %s', [
                                   task_id]).fetchone()['checker']
        
        try:
            res, checker_msg = check_flag(
                checker, 
                flag, 
                info={
                    'task_id': task_id,
                    'user_id': g.user['id']
                })
        except Exception:
            print(format_exc())
            flash('An error occured. Please contact admin.', 'error')

            with db_pool.connection() as conn:
                conn.execute('UPDATE log_flag SET checker_msg = %s WHERE id = %s', [
                             format_exc(), submit_id])
        else:
            if res:
                msg = checker_msg or 'Accepted. Congratulations!'
                flash(msg, 'success')

                end_time = current_app.config['END_TIME']

                if end_time and datetime.now() > end_time:
                    flash('Contest time exceeded :(', 'info')
                else:
                    with db_pool.connection() as conn:
                        conn.execute('INSERT INTO accepted_submit(task_id, user_id, flag, flag_log_id) VALUES (%s, %s, %s, %s)', [
                                    task_id, g.user['id'], flag, submit_id])
            else:
                msg = checker_msg or 'Incorrect flag.'
                flash(msg, 'warning')

            with db_pool.connection() as conn:
                conn.execute('UPDATE log_flag SET is_accepted = %s, checker_msg = %s WHERE id = %s', [
                             res, checker_msg, submit_id])

        return redirect(url_for('problem.show_problem_detail', pid=pid))

    with db_pool.connection() as conn:
        g.detail = conn.execute(
            'SELECT * FROM problem WHERE id = %s', [pid]).fetchone()
        
        if not g.detail:
            abort(404)
        
        if g.detail['is_visible'] == False and not g.is_admin:
            abort(403)

        g.tasks = list(conn.execute(
            'SELECT id, point FROM view_task_score WHERE problem_id = %s ORDER BY id', [pid]).fetchall())
        g.accepted = list(conn.execute('SELECT task_id FROM accepted_submit WHERE user_id = %s', [
                          g.user['id']]).fetchall())
        
        g.points = list(conn.execute('SELECT id, point FROM view_task_score WHERE problem_id = %s', [pid]))
        g.files = list(conn.execute('SELECT * FROM file WHERE problem_id = %s ORDER BY id', [pid]))
        solver_list = list(conn.execute(
            'SELECT task_id, username, submit_time, user_id FROM view_user_solve WHERE problem_id = %s ORDER BY submit_time', [pid]))

    g.detail['tag_list'] = parse_tags(g.detail.pop('tag'))
    g.accepted = [x['task_id'] for x in g.accepted]
    # g.solves = [x['cnt'] for x in g.solves]

    g.solves = {
        x['id']: {'cnt': 0, 'users': []} for x in g.tasks
    }

    for r in solver_list:
        task_id = r['task_id']

        g.solves[task_id]['cnt'] += 1
        g.solves[task_id]['users'].append(r)
    
    g.solves = sorted(g.solves.items())

    g.total_points = sum([x['point'] for x in g.points])
    g.solved_points = sum([x['point'] for x in g.points if x['id'] in g.accepted])

    for index in range(len(g.tasks)):
        g.tasks[index]['id_in_problem'] = index + 1

    with db_pool.connection() as conn:
        if g.detail['instance_type'] == 'shared':
            g.instance = conn.execute('SELECT * FROM instance WHERE problem_id = %s ORDER BY id DESC LIMIT 1', [pid]).fetchone()
        elif g.detail['instance_type'] == 'private':
            g.instance = conn.execute('SELECT * FROM instance WHERE problem_id = %s AND user_id = %s ORDER BY id DESC LIMIT 1', [pid, g.user['id']]).fetchone()

    g.warning_time = datetime.now() + timedelta(seconds=10)

    return render_template('problem/detail.html')


@bp.route('/reset_task/<int:pid>/<int:taskid>')
@admin_required
def reset_task_progress(pid, taskid):
    with db_pool.connection() as conn:
        conn.execute('DELETE FROM accepted_submit WHERE task_id = %s and user_id = %s', [taskid, g.user['id']])
    return redirect(url_for('problem.show_problem_detail', pid=pid))
