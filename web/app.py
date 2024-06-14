from flask import Flask, render_template, g, session
from hashlib import md5
from util.db import db_pool
from util.env import env
from util.refresh_config import refresh_config

app = Flask(__name__)
app.config["SECRET_KEY"] = env("SECRET_KEY")
app.config["SESSION_COOKIE_NAME"] = 'session_blueberry'


with app.app_context():
    try:
        refresh_config()
    except Exception as e:
        pass



@app.before_request
def prepare_user_data():
    uid = session.get("user_id")
    if uid:
        with db_pool.connection() as conn:
            g.user = conn.execute(
                "SELECT * FROM user_info WHERE id = %s", [uid]
            ).fetchone()

            if not g.user:
                session.clear()
                return

            g.is_admin = g.user["is_admin"]
    else:
        g.user = None
        g.is_admin = False


@app.context_processor
def avatar_processor():
    def avatar_url(user, size):
        if app.config["USE_GRAVATAR"] == "yes":
            hash_hex = md5(user["email"].lower().encode()).hexdigest()
            return f"https://gravatar.pion1eer.workers.dev/avatar/{hash_hex}?s={size}&d=mp"
        else:
            return "/static/img/anonymous.png"

    return dict(avatar_url=avatar_url)


@app.route("/")
def show_index():
    with db_pool.connection() as conn:
        msgboard = conn.execute(
            "SELECT config_value FROM site_config WHERE config_key = 'message_board'"
        ).fetchone()["config_value"]
    return render_template("pages/index.html", msgboard=msgboard)


@app.errorhandler(404)
def show_404(_):
    return render_template("pages/errors/404.html")


@app.errorhandler(403)
def show_403(_):
    return render_template("pages/errors/403.html")


@app.errorhandler(418)
def show_418(_):
    return render_template("pages/errors/418.html")


from blueprints import user

app.register_blueprint(user.bp)

from blueprints import problem

app.register_blueprint(problem.bp)

from blueprints import ranking

app.register_blueprint(ranking.bp)

from blueprints import file

app.register_blueprint(file.bp)

from blueprints import admin

app.register_blueprint(admin.bp)

from blueprints import api

app.register_blueprint(api.bp)


from util.click import erase_db, init_db

app.cli.add_command(erase_db)
app.cli.add_command(init_db)

if __name__ == "__main__":
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.run("0.0.0.0", 11451, debug=True)
