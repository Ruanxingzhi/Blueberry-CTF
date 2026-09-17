FROM debian:trixie-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG DEBIAN_MIRROR=http://mirrors.bfsu.edu.cn/debian

RUN echo "deb ${DEBIAN_MIRROR} trixie main" > /etc/apt/sources.list \
    && rm -rf /etc/apt/sources.list.d/* \
    && apt-get update \
    && apt-get -y install --no-install-recommends \
        python3 \
        python3-docker \
        python3-dotenv \
        python3-psycopg-pool \
        python3-rich \
        python3-pycryptodome \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY docker-backend.py /app/docker-backend.py

CMD ["python3", "docker-backend.py"]
