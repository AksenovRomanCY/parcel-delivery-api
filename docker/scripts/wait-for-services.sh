#!/bin/sh
# Usage:
#   wait-for-services.sh host1:port1 host2:port2 -- cmd arg1 arg2 ...

set -eu

MAX_RETRIES=30
SLEEP_SEC=2

wait_for() {
    host="${1%:*}"
    port="${1#*:}"

    echo "⏳  waiting for $host:$port …"
    i=0
    while ! nc -z "$host" "$port" >/dev/null 2>&1; do
        i=$((i + 1))
        if [ "$i" -ge "$MAX_RETRIES" ]; then
            echo "❌  $host:$port still unreachable." >&2
            exit 1
        fi
        sleep "$SLEEP_SEC"
    done
    echo "✅  $host:$port is up"
}

SERVICES=""
while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do
    SERVICES="$SERVICES $1"
    shift
done

[ "$#" -gt 0 ] && [ "$1" = "--" ] || {
    echo "Usage: wait-for-services.sh host:port [...] -- cmd" >&2
    exit 2
}
shift

for svc in $SERVICES; do
    wait_for "$svc"
done

exec "$@"
