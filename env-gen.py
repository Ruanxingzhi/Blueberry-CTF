#!/usr/bin/env python3
import argparse
import os
import secrets
import sys

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def generate() -> str:
    return (
        f"POSTGRES_PASSWORD={secrets.token_urlsafe(16)}\n"
        f"SECRET_KEY={secrets.token_urlsafe(16)}\n"
        f"FLAG_GEN_KEY={secrets.token_hex(8)}\n"
        f"INIT_ADMIN_USER=admin\n"
        f"INIT_ADMIN_PASSWORD={secrets.token_urlsafe(10)}\n"
        f"INSTANCE_PORT_START=25000\n"
        f"INSTANCE_PORT_END=26000\n"
        f"PGSQL_LISTEN=127.0.0.1:11450\n"
        f"WEB_LISTEN=127.0.0.1:11451\n"
        f"ADMINER_LISTEN=127.0.0.1:11452\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a random .env for Blueberry CTF"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing .env",
    )
    args = parser.parse_args()

    if os.path.exists(ENV_PATH) and not args.force:
        print(
            f"{ENV_PATH} already exists. Use --force to overwrite.",
            file=sys.stderr,
        )
        return 1

    with open(ENV_PATH, "w", encoding="utf-8") as fh:
        fh.write(generate())

    print(f"Wrote {ENV_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
