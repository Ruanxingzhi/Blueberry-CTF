from flask import Blueprint, render_template, g
from util.db import db_pool

bp = Blueprint('ranking', __name__, url_prefix='/ranking')


@bp.route('/')
def show_ranking_list():
    with db_pool.connection() as conn:
        g.list = list(conn.execute('''
WITH t AS (SELECT user_id, SUM(point) AS total_point, MAX(submit_time) AS last_submit FROM view_user_solve GROUP BY user_id)
SELECT id, username, email, total_point, last_submit FROM user_info JOIN t ON user_info.id = t.user_id ORDER BY total_point DESC, last_submit
        '''))

    return render_template('ranking/list.html')
