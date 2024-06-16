from flask import Blueprint, request, render_template, g, redirect, url_for, abort
from util.db import db_pool
from util.wrapper import admin_required
from util.coder import parse_tags
from util.refresh_config import refresh_config
import psutil
import uuid
import os

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
@admin_required
def admin_req():
    pass


@bp.route("/")
def show_admin_board():
    with db_pool.connection() as conn:
        info = conn.execute(
            """
SELECT 
    (SELECT COUNT(*) AS problem_num FROM problem),
    (SELECT COUNT(*) AS task_num FROM task),
    (SELECT COUNT(*) AS user_num FROM user_info),
    (SELECT COUNT(*) AS submit_num FROM log_flag),
    (SELECT COUNT(*) AS solve_num FROM accepted_submit)
"""
        ).fetchone()

    return render_template("admin/board.html", info=info, psutil=psutil)


@bp.route("/site")
def show_site_config():
    with db_pool.connection() as conn:
        config_list = list(
            conn.execute("SELECT config_key, config_value FROM site_config ORDER BY id")
        )

    site_config = {x["config_key"]: x["config_value"] for x in config_list}

    return render_template("admin/site_config.html", site_config=site_config)


@bp.route("/user")
def show_user_list():
    with db_pool.connection() as conn:
        users = list(conn.execute("SELECT * FROM user_info ORDER BY id"))

    return render_template("admin/user_list.html", users=users)


@bp.route("/user/<int:uid>")
def show_user_detail(uid):
    with db_pool.connection() as conn:
        g.info = conn.execute("SELECT * FROM user_info WHERE id = %s", [uid]).fetchone()
        g.latest_submits = list(
            conn.execute(
                """
WITH s AS (SELECT * FROM log_flag WHERE user_id = %s ORDER BY id DESC LIMIT 100)
SELECT s.*, problem_id, title, task_order FROM s JOIN view_task_in_problem AS v ON v.task_id = s.task_id ORDER BY submit_time DESC
        """,
                [uid],
            )
        )

    return render_template("admin/user_detail.html")


@bp.route("/problem")
def show_problem_list():
    with db_pool.connection() as conn:
        g.problems = list(conn.execute("SELECT * FROM problem ORDER BY id"))

    for x in g.problems:
        x["tag_list"] = parse_tags(x.pop("tag"))

    return render_template("admin/problem_list.html")


@bp.route("/problem/<int:pid>")
def show_problem_detail(pid):
    with db_pool.connection() as conn:
        g.problem_info = conn.execute(
            "SELECT * FROM problem WHERE id = %s", [pid]
        ).fetchone()

        if not g.problem_info:
            abort(404)

        g.tasks = list(
            conn.execute("SELECT * FROM task WHERE problem_id = %s ORDER BY id", [pid])
        )
        g.files = list(
            conn.execute("SELECT * FROM file WHERE problem_id = %s ORDER BY id", [pid])
        )

    return render_template("admin/problem_detail.html")


@bp.post("/api/set_siteconfig")
def api_set_siteconfig():
    keys = ["site_name", "is_allow_register", "use_gravatar", "use_local_resources", "start_time", "end_time", "decay_lambda", "userinfo_extra_fields", "head_tags", "player_max_container_num"]

    config_items = [[request.form.get(key).strip(), key] for key in keys]

    with db_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE site_config SET config_value = %s WHERE config_key = %s",
                config_items,
            )

    refresh_config()

    return redirect(url_for("admin.show_site_config"))


@bp.post("/api/set_msgboard")
def api_set_msgboard():
    content = request.form.get("msgboard")
    with db_pool.connection() as conn:
        conn.execute(
            "UPDATE site_config SET config_value = %s WHERE config_key = 'message_board'",
            [content],
        )
    return redirect(url_for("admin.show_site_config"))


@bp.route("/api/set_admin/<int:uid>")
def api_set_admin(uid):
    with db_pool.connection() as conn:
        conn.execute("UPDATE user_info SET is_admin = true WHERE id = %s", [uid])
    return redirect(url_for("admin.show_user_detail", uid=uid))


@bp.route("/api/unset_admin/<int:uid>")
def api_unset_admin(uid):
    with db_pool.connection() as conn:
        conn.execute("UPDATE user_info SET is_admin = false WHERE id = %s", [uid])
    return redirect(url_for("admin.show_user_detail", uid=uid))


@bp.route("/api/set_visible/<int:uid>")
def api_set_visible(uid):
    with db_pool.connection() as conn:
        conn.execute("UPDATE user_info SET is_visible = true WHERE id = %s", [uid])
    return redirect(url_for("admin.show_user_detail", uid=uid))


@bp.route("/api/unset_visible/<int:uid>")
def api_unset_visible(uid):
    with db_pool.connection() as conn:
        conn.execute("UPDATE user_info SET is_visible = false WHERE id = %s", [uid])
    return redirect(url_for("admin.show_user_detail", uid=uid))


@bp.route("/api/add_problem")
def api_add_problem():
    with db_pool.connection() as conn:
        conn.execute(
            "INSERT INTO problem(title, description, is_visible) VALUES ('隐藏题目', '题目描述', false)"
        )

    return redirect(url_for("admin.show_problem_list"))


@bp.post("/api/modify_problem/<int:pid>")
def api_modify_problem(pid):
    title = request.form.get("title")
    description = request.form.get("description")
    tag = request.form.get("tag")
    is_visible = request.form.get("visible")
    docker_config = request.form.get("docker_config")
    instance_type = request.form.get("instance_type")

    with db_pool.connection() as conn:
        conn.execute(
            "UPDATE problem SET title=%s, description=%s, tag=%s, is_visible=%s, docker_config=%s, instance_type=%s WHERE id = %s",
            [title, description, tag, is_visible, docker_config, instance_type, pid],
        )

    return redirect(url_for("admin.show_problem_detail", pid=pid))


@bp.post("/api/modify_task/<int:tid>")
def api_modify_task(tid):
    point = request.form.get("point")
    checker = request.form.get("checker")
    score_calc_type = request.form.get("score_calc_type")

    with db_pool.connection() as conn:
        pid = conn.execute(
            "UPDATE task SET base_point = %s, checker = %s, score_calc_type = %s WHERE id = %s RETURNING problem_id",
            [point, checker, score_calc_type, tid],
        ).fetchone()

    return redirect(url_for("admin.show_problem_detail", pid=pid["problem_id"]))


@bp.post("/api/add_task/<int:pid>")
def api_add_task(pid):
    point = request.form.get("point")
    checker = request.form.get("checker")

    with db_pool.connection() as conn:
        conn.execute(
            "INSERT INTO task(problem_id, base_point, checker) VALUES (%s, %s, %s)",
            [pid, point, checker],
        )

    return redirect(url_for("admin.show_problem_detail", pid=pid))


@bp.post("/api/add_file/<int:pid>")
def api_add_file(pid):
    file = request.files["file"]

    download_key = str(uuid.uuid4())

    with db_pool.connection() as conn:
        conn.execute(
            "INSERT INTO file(download_key, filename, problem_id) VALUES (%s, %s, %s)",
            [download_key, file.filename, pid],
        )

    file.save(os.path.join("upload", download_key))

    return redirect(url_for("admin.show_problem_detail", pid=pid))


@bp.route("/api/remove_file/<int:fid>")
def api_remove_file(fid):
    with db_pool.connection() as conn:
        pid = conn.execute(
            "SELECT problem_id FROM file WHERE id = %s", [fid]
        ).fetchone()["problem_id"]
        conn.execute("DELETE FROM file WHERE id = %s", [fid])

    return redirect(url_for("admin.show_problem_detail", pid=pid))

def delete_task(tid):
    with db_pool.connection() as conn:
        conn.execute("DELETE FROM task WHERE id = %s",[tid])
        conn.execute("DELETE FROM accepted_submit WHERE task_id = %s",[tid])


@bp.route("/api/remove_task/<int:pid>/<int:tid>")
def api_remove_task(pid, tid):
    delete_task(tid)

    return redirect(url_for("admin.show_problem_detail", pid=pid))

@bp.route("/api/remove_problem/<int:pid>")
def api_remove_problem(pid):
    with db_pool.connection() as conn:
        tasks = conn.execute('SELECT * FROM task WHERE problem_id = %s', [pid]).fetchall()

    for t in tasks:
        delete_task(t['id'])
    
    with db_pool.connection() as conn:
        conn.execute('DELETE FROM problem WHERE id = %s', [pid])

    return redirect(url_for("admin.show_problem_list"))