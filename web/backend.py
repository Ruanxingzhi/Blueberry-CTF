import docker
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
import dotenv
import os
import json
import hashlib
from traceback import format_exc
from time import sleep
from rich import print
from random import shuffle
from Cryptodome.Cipher import AES
import struct

dotenv.load_dotenv()

container_name_prefix = 'bbctf-' + hashlib.md5(os.getenv("PGSQL_URI").encode()).hexdigest()[:10]

db_pool = ConnectionPool(
    os.getenv("PGSQL_URI"), min_size=1, kwargs={"row_factory": dict_row}
)

client = docker.from_env()

avaliable_ports = list(range(25000, 26000))
shuffle(avaliable_ports)


def get_port_from_pool():
    p = avaliable_ports.pop(0)
    print(f"Get port number {p} from pool")
    return p


def put_port_to_pool(p):
    print(f"Put port number {p} to pool")
    avaliable_ports.append(p)


def start_container(config, pid, uid):
    config["name"] = f"{container_name_prefix}-u{uid}-p{pid}"
    # config['publish_all_ports'] = True
    config["detach"] = True

    image_name = config["image"]

    if "ports" in config:
        print("ports from config:", config["ports"])
        exposed_port = config["ports"]
        config.pop("ports")
    elif "port" in config:
        print("port from config:", config["port"])
        exposed_port = [config["port"]]
        config.pop("port")
    else:
        exposed_port = list(
            client.images.get(image_name)
            .attrs["ContainerConfig"]["ExposedPorts"]
            .keys()
        )

    print('ports:', exposed_port)

    # 尽管这里可以设置 {"exposed_port": 0} 来让 docker 自行选择端口
    # 但这种实现所暴露的公共端口范围为 32768-65535
    # 考虑到现实中常常需要进行范围端口转发，这会占用公网 vps 一半的端口数量
    # 且此种实现也使得「内网 A、B 机器各开一个 blueberry，转发到外网 C 机器」不可行
    # 故我们在此选择手动分配 public_port
    port_map = {p: get_port_from_pool() for p in exposed_port}
    config["ports"] = port_map

    # 默认 cpu 限制：0.25 个核
    if 'cpu_quota' not in config:
        config["cpu_quota"] = 25000
    if 'cpu_period' not in config:
        config["cpu_period"] = 100000

    print(f'[green]+ create {config["name"]}[/green]')

    print(config)

    c = client.containers.run(**config)
    c.reload()

    # real_port = c.ports[exposed_port][0]["HostPort"]
    # assert int(real_port) == public_port

    remote = ' , '.join(f"platform_ip:{p}" for p in port_map.values())
    print("remote", remote)

    return remote


def start_shared_instance(pid):
    with db_pool.connection() as conn:
        prob_info = conn.execute(
            "SELECT * FROM problem WHERE id = %s", [pid]
        ).fetchone()

    remote = start_container(json.loads(prob_info["docker_config"]), pid, "shared")

    with db_pool.connection() as conn:
        conn.execute(
            "INSERT INTO instance(problem_id, status, connection_info, start_time, end_time) VALUES (%s, 'running', %s, current_timestamp(0), '2099-01-01')",
            [pid, remote],
        )

def gen_flag(tid, uid):
    engine = AES.new(os.getenv("FLAG_GEN_KEY").encode(), AES.MODE_ECB)
    plaintext = b'BerryCTF' + struct.pack('II', uid, tid)
    ciphertext = engine.encrypt(plaintext)

    return 'flag{' + ciphertext.hex() + '}'


def init():
    c_list = client.containers.list(all=True)

    for c in c_list:
        name = c.name

        if name.startswith(container_name_prefix):
            print(f"[red]- destroy {name}[/red]")
            c.remove(v=True, force=True)

    with db_pool.connection() as conn:
        conn.execute(
            "UPDATE instance SET status = 'destroyed', end_time = current_timestamp(0) WHERE status = 'running'"
        )
        conn.execute(
            "UPDATE instance SET status = 'failed', message = 'Instance manager restart' WHERE status = 'pending'"
        )

        probs = conn.execute(
            "SELECT id FROM problem WHERE instance_type = 'shared'"
        ).fetchall()

    for p in probs:
        start_shared_instance(p["id"])


def handle_launch_request():
    with db_pool.connection() as conn:
        reqs = list(
            conn.execute("SELECT * FROM instance WHERE status = 'pending' limit 1")
        )

    for r in reqs:
        try:
            pid = r["problem_id"]
            uid = r["user_id"]

            with db_pool.connection() as conn:
                config = json.loads(
                    conn.execute(
                        "SELECT docker_config FROM problem WHERE id = %s", [pid]
                    ).fetchone()["docker_config"]
                )
                tasks = conn.execute(
                    "SELECT * FROM view_task_in_problem WHERE problem_id = %s", [pid]
                ).fetchall()

            config["environment"] = {
                f'FLAG{x["task_order"]}': gen_flag(x["task_id"], uid) for x in tasks
            }
            remote = start_container(config, pid, uid)
        except Exception:
            err = format_exc()
            print(err)

            with db_pool.connection() as conn:
                conn.execute(
                    "UPDATE instance SET status = 'failed', message = %s WHERE id = %s",
                    [err, r["id"]],
                )
        else:
            with db_pool.connection() as conn:
                conn.execute(
                    "UPDATE instance SET status = 'running', connection_info = %s, start_time=current_timestamp(0), end_time=current_timestamp(0) + interval '2 hours' WHERE id = %s",
                    [remote, r["id"]],
                )


def destroy_outdated():
    with db_pool.connection() as conn:
        reqs = list(
            conn.execute(
                "SELECT * FROM instance WHERE status = 'running' AND end_time < current_timestamp(0)"
            )
        )

    for r in reqs:
        pid = r["problem_id"]
        uid = r["user_id"]

        name = f"{container_name_prefix}-u{uid}-p{pid}"
        print(f"[red]- destroy {name}[/red]")

        c = client.containers.get(name)

        print(c.ports)

        for x in c.ports.values():
            if x is not None:
                free_port = x[0]["HostPort"]
                put_port_to_pool(free_port)

        c.remove(v=True, force=True)

        with db_pool.connection() as conn:
            conn.execute(
                "UPDATE instance SET status = 'destroyed' WHERE id = %s", [r["id"]]
            )


if __name__ == "__main__":
    init()

    while True:
        handle_launch_request()
        destroy_outdated()

        sleep(1)
