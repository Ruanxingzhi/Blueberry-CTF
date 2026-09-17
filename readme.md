# Blueberry CTF

A CTF platform developed for the Lilac team. Designed for competitions with ~500 players.

Features:

- Private containers & private flags for each player
- Multiple tasks in one problem

Intro: [Blueberry CTF 的设计、实现和反思](https://www.ruanx.net/blueberry-ctf/)

![p1](https://github.com/Ruanxingzhi/Blueberry-CTF/assets/16996226/22def8f7-dd68-4e69-94b2-6e880d4e4741)

![p2](https://github.com/Ruanxingzhi/Blueberry-CTF/assets/16996226/65d8737f-ac36-4018-ab9f-2e78eb7826d7)


## Start

```bash
python3 env-gen.py
docker compose up
```

Blueberry must run behind a reverse proxy. For nginx:

```bash
cp deploy/nginx.conf /etc/nginx/sites-available/default
nginx -t
nginx -s reload
```

For caddy:

```bash
cp deploy/Caddyfile /etc/caddy/Caddyfile
caddy reload --config /etc/caddy/Caddyfile
```

See `.env` for the admin password.

Demo challenge `runma`:

```bash
cd problems/runma
docker compose build
```
