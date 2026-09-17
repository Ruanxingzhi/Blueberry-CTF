#!/bin/sh
set -e
flask init-db
exec "$@"
