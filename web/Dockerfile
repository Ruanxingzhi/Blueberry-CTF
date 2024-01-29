FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive

RUN echo 'deb http://mirrors.bfsu.edu.cn/debian bookworm main' > /etc/apt/sources.list
RUN rm /etc/apt/sources.list.d/*

RUN apt-get update

RUN apt-get -y install python3 python3-dotenv python3-flask python3-psycopg-pool python3-passlib python3-psutil python3-gevent python3-rich python3-pycryptodome gunicorn  --no-install-recommends 
RUN rm -rf /var/lib/apt/lists/*

RUN mkdir /app
WORKDIR /app

CMD ["sleep", "infinity"]
# CMD ["gunicorn", "app:app"]
EXPOSE 11451