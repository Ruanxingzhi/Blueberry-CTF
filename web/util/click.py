from util.db import db_pool
import click
from passlib.hash import bcrypt_sha256
import os

from rich import print

def _drop_schema(conn):
    conn.execute("DROP VIEW IF EXISTS view_user_solve")
    conn.execute("DROP VIEW IF EXISTS view_task_score")
    conn.execute("DROP VIEW IF EXISTS view_task_solve_cnt")
    conn.execute("DROP VIEW IF EXISTS view_task_in_problem")
    conn.execute("DROP TABLE IF EXISTS problem")
    conn.execute("DROP TABLE IF EXISTS task")
    conn.execute("DROP TABLE IF EXISTS user_info")
    conn.execute("DROP TABLE IF EXISTS log_flag")
    conn.execute("DROP TABLE IF EXISTS accepted_submit")
    conn.execute("DROP TABLE IF EXISTS file")
    conn.execute("DROP TABLE IF EXISTS instance")
    conn.execute("DROP TABLE IF EXISTS site_config")


def _create_schema(conn):
    conn.execute(
            """
CREATE TABLE problem (
    id serial primary key,
    title text,
    description text,
    is_visible boolean not null default false,
    tag text,
    instance_type text not null default 'none' check (instance_type in ('none', 'shared', 'private')),
    docker_config text default ''
)"""
        )

    conn.execute(
            """
CREATE TABLE task (
    id serial primary key,
    problem_id integer not null,
    base_point integer not null,
    score_calc_type integer default 0 not null, 
    checker text not null
)"""
        )

    conn.execute(
            """
CREATE TABLE user_info (
    id serial primary key,
    username varchar(100) not null unique,
    email varchar(100) not null unique,
    password varchar(200) not null,
    register_time timestamp default current_timestamp(0) not null,
    is_admin boolean default false not null,
    is_visible boolean default true not null,
    extra_info text
)"""
        )

    conn.execute(
            """
CREATE TABLE log_flag (
    id serial primary key,
    task_id integer not null,
    user_id integer not null,
    submit_time timestamp default current_timestamp(0) not null,
    flag text not null,
    is_accepted boolean,
    checker_msg text
)"""
        )

    conn.execute(
            """
CREATE TABLE accepted_submit (
    id serial primary key,
    task_id integer not null,
    user_id integer not null,
    submit_time timestamp default current_timestamp(0) not null,
    flag text,
    flag_log_id integer,
    UNIQUE (task_id, user_id)
)"""
        )

    conn.execute(
            """
CREATE TABLE file (
    id serial primary key,
    problem_id integer,
    filename text not null,
    download_key text not null,
    upload_time timestamp default current_timestamp(0) not null
)"""
        )

    conn.execute(
            """
CREATE TABLE instance (
    id serial primary key,
    problem_id integer not null,
    user_id integer,
    status text not null check (status in ('pending', 'failed', 'running', 'destroyed')),
    message text,
    connection_info text,
    request_time timestamp not null default current_timestamp(0),
    start_time timestamp,
    end_time timestamp
)"""
        )

    conn.execute(
            """
CREATE TABLE site_config (
    id serial primary key,
    config_key text not null unique,
    config_value text not null
)"""
        )

    conn.execute(
            """CREATE VIEW view_task_in_problem AS (
  SELECT t.id as task_id, problem_id, title, (RANK() OVER (PARTITION BY problem_id ORDER BY t.id)) AS task_order FROM task AS t, problem AS p WHERE t.problem_id = p.id ORDER BY task_id
)"""
        )

    conn.execute(
            """CREATE VIEW view_user_solve AS (
WITH s AS (SELECT problem_id, task_id, user_id, submit_time FROM accepted_submit AS a, task WHERE a.task_id = task.id)
SELECT s.*, username FROM s JOIN user_info ON s.user_id = user_info.id WHERE user_info.is_visible
)"""
        )

    conn.execute(
            """CREATE VIEW view_task_solve_cnt AS (
WITH s AS (SELECT a.* FROM accepted_submit AS a JOIN user_info AS u ON u.id = a.user_id WHERE u.is_visible),
t AS (SELECT task_id, count(*) as cnt FROM s GROUP BY task_id)
SELECT task.problem_id, task.id as task_id, coalesce(cnt, 0) AS cnt FROM t RIGHT JOIN task ON task.id = t.task_id ORDER BY task_id
)"""
        )
    conn.execute(
            """CREATE VIEW view_task_score AS (
--  SELECT task.*, base_point AS point FROM task ORDER BY task.id
WITH decay_lambda AS (SELECT config_value::INTEGER FROM site_config WHERE config_key = 'decay_lambda'),
r AS (SELECT task_id, base_point, cnt, score_calc_type FROM view_task_solve_cnt JOIN task ON task.id = task_id),
s AS (SELECT task_id, (
  CASE
    WHEN score_calc_type=1 THEN ROUND(pow(0.5, LEAST(2.0, GREATEST(cnt-1, 0)/(1.0*(SELECT * FROM decay_lambda)))) * base_point)
    ELSE base_point
  END
) AS point FROM r)
SELECT task.*, s.point FROM s JOIN task ON s.task_id = task.id
)"""
        )


def do_erase_db():
    print("Erase database...")

    os.makedirs("upload", exist_ok=True)
    os.system("rm -f upload/*")

    with db_pool.connection() as conn:
        _drop_schema(conn)
        _create_schema(conn)


@click.command("erase-db")
def erase_db():
    try:
        do_erase_db()
    finally:
        db_pool.close()


def do_init_db():
    print("Init database...")
    os.makedirs("upload", exist_ok=True)

    with db_pool.connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_info'"
        ).fetchone()
        if exists:
            if conn.execute("SELECT 1 FROM user_info LIMIT 1").fetchone():
                print("database already initialized, skip")
                return
        else:
            _create_schema(conn)
        conn.execute(
            "INSERT INTO problem(title, description, tag, is_visible) VALUES (%s, %s, %s, true)",
            [
                "签到",
                "机器猫的神必测试题！\n\nTask 1: 交给我一个 [1000, 2000] 范围内的质数，我就算你通过这题。\nTask 2: flag 是 `flag{aloha-lilac}`\nTask 3: flag 也是 `flag{aloha-lilac}`，但我们有无敌的 WAF，它会删掉你提交的字符串中的 `flag` 子串。所以你不可能通过本题！",
                "crypto | math",
            ],
        )

        conn.execute(
            "INSERT INTO problem(title, description, is_visible, instance_type, docker_config) VALUES (%s, %s, true, %s, %s)",
            [
                "跑马场",
                "送🐴啦！送🐴啦！flag 在环境变量。",
                "private",
                '{"image": "runma-app", "mem_limit": "50m"}',
            ],
        )

        tasks = [
            [
                1,
                30,
                """
def is_prime(num):
  for p in range(2, num):
    if num % p == 0:
      return False, f'No, we found a factor {p}'
    if p*p > num:
      return True, f'OK, {num} is a prime number'

def check(num):
  try:
    num = num.replace('flag{', '').replace('}', '')
    num = int(num)
  except Exception:
    return False, 'give me a number!'  
  if num < 1000 or num > 2000:
    return False, 'num not in [1000, 2000]'

  return is_prime(num)  
""",
            ],
            [1, 30, 'check = lambda x: x == "flag{aloha-lilac}"'],
            [
                1,
                40,
                """
def check(s):
  s = s.replace('flag', '')
  if s == 'flag{aloha-lilac}':
    return True
  else:
    return False, 'Your flag: ' + s
""",
            ],
            [2, 100, "def check(s):\n    return s == dynamic_flag"],
        ]

        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO task(problem_id, base_point, checker) VALUES (%s, %s, %s)",
                tasks,
            )

        admin_user = os.getenv("INIT_ADMIN_USER")
        admin_passwd = os.getenv("INIT_ADMIN_PASSWORD")
        if not admin_user or not admin_passwd:
            raise RuntimeError(
                "INIT_ADMIN_USER and INIT_ADMIN_PASSWORD must be set"
            )

        print(f'admin user: [blue]{admin_user}[/blue]')
        print(f'password: [red]{admin_passwd}[/red]')
        print(f'INIT_ADMIN_USER={admin_user} INIT_ADMIN_PASSWORD={admin_passwd}')

        conn.execute(
            "INSERT INTO user_info(email, username, password, is_admin, is_visible) VALUES (%s, %s, %s, true, false)",
            [f"{admin_user}@localhost", admin_user, bcrypt_sha256.hash(admin_passwd)],
        )

        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO site_config(config_key, config_value) VALUES (%s, %s)",
                [
                    ["site_name", "Blueberry CTF"],
                    ["message_board", "实力，我的**实力**！"],
                    ["use_gravatar", "yes"],
                    ["use_local_resources", "no"],
                    ["is_allow_register", "yes"],
                    ["decay_lambda", "15"],
                    ["userinfo_extra_fields", "[]"],
                    ["start_time", ""],
                    ["end_time", ""],
                    ["head_tags", ""],
                    ["player_max_container_num", "4"]
                ],
            )

@click.command("init-db")
def init_db():
    try:
        do_init_db()
    finally:
        db_pool.close()
