#!/usr/bin/env bash
# Start the local MySQL server for the BrightPath project.
# This is a dev-only convenience script -- real companies run MySQL as an
# OS service (systemd) or a managed cloud database, not a manual script.
#
# Usage:
#   ./start_mysql.sh          start the server (no-op if already running)
#   ./start_mysql.sh stop     stop the server
#
# Passwords are never stored in this file. Set them in your shell first:
#   export BRIGHTPATH_MYSQL_PASSWORD='...'        # brightpath_app user
#   export BRIGHTPATH_MYSQL_ROOT_PASSWORD='...'   # root, needed for "stop"

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$PROJECT_DIR/.mysql-data"
SOCKET="$DATA_DIR/mysql.sock"
PIDFILE="$DATA_DIR/mysqld.pid"
LOGFILE="$DATA_DIR/mysqld.log"
PORT=3307
MYSQLD=/opt/anaconda3/bin/mysqld
MYSQLADMIN=/opt/anaconda3/bin/mysqladmin

if [[ "${1:-}" == "stop" ]]; then
    if [[ -f "$PIDFILE" ]]; then
        echo "Stopping MySQL (pid $(cat "$PIDFILE"))..."
        "$MYSQLADMIN" --socket="$SOCKET" -u root \
            -p"${BRIGHTPATH_MYSQL_ROOT_PASSWORD:?Set BRIGHTPATH_MYSQL_ROOT_PASSWORD first}" shutdown
    else
        echo "No pidfile found -- server is probably not running."
    fi
    exit 0
fi

if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "MySQL is already running (pid $(cat "$PIDFILE"))."
    exit 0
fi

echo "Starting MySQL on port $PORT ..."
nohup "$MYSQLD" \
    --datadir="$DATA_DIR" \
    --basedir=/opt/anaconda3 \
    --socket="$SOCKET" \
    --port="$PORT" \
    --bind-address=127.0.0.1 \
    --pid-file="$PIDFILE" \
    > "$LOGFILE" 2>&1 &
disown

for i in $(seq 1 20); do
    if [[ -f "$PIDFILE" ]]; then
        echo "MySQL is up (pid $(cat "$PIDFILE"))."
        echo
        echo "Connect with:"
        echo "  Host: 127.0.0.1   Port: $PORT"
        echo '  User: brightpath_app   Password: $BRIGHTPATH_MYSQL_PASSWORD   Schema: brightpath'
        exit 0
    fi
    sleep 0.5
done

echo "MySQL did not start in time -- check $LOGFILE"
exit 1
