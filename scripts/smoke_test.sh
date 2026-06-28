#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

log() {
  printf 'smoke: %s\n' "$*"
}

fail() {
  printf 'smoke failed: %s\n' "$*" >&2
  exit 1
}

request() {
  local method="$1"
  local path="$2"
  local output="$3"
  shift 3

  curl -sS \
    -X "$method" \
    -D "$output.headers" \
    -o "$output.body" \
    -w '%{http_code}' \
    "$@" \
    "$BASE_URL$path"
}

expect_status() {
  local actual="$1"
  local expected="$2"
  local label="$3"

  if [ "$actual" != "$expected" ]; then
    printf '%s\n' "Unexpected response for $label" >&2
    printf 'expected: %s\nactual:   %s\n' "$expected" "$actual" >&2
    printf '%s\n' 'response body:' >&2
    cat "$TMP_DIR/$label.body" >&2 || true
    exit 1
  fi
}

json_get() {
  local file="$1"
  local expression="$2"

  python3 - "$file" "$expression" <<'PY'
import json
import sys

path, expression = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

value = data
for part in expression.split("."):
    if part.isdigit():
        value = value[int(part)]
    else:
        value = value[part]

if value is None:
    print("")
else:
    print(value)
PY
}

json_assert() {
  local file="$1"
  local expression="$2"

  python3 - "$file" "$expression" <<'PY'
import json
import sys

path, expression = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

scope = {"data": data}
if not eval(expression, {"__builtins__": {}}, scope):
    raise SystemExit(1)
PY
}

cookie_value() {
  local headers="$1"
  local name="$2"

  python3 - "$headers" "$name" <<'PY'
from http.cookies import SimpleCookie
import sys

headers_path, cookie_name = sys.argv[1], sys.argv[2]
with open(headers_path, encoding="utf-8") as handle:
    for line in handle:
        if not line.lower().startswith("set-cookie:"):
            continue
        cookie = SimpleCookie()
        cookie.load(line.split(":", 1)[1].strip())
        if cookie_name in cookie:
            print(cookie[cookie_name].value)
            raise SystemExit(0)
raise SystemExit(1)
PY
}

log "waiting for $BASE_URL"
for attempt in {1..60}; do
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    break
  fi
  if [ "$attempt" = 60 ]; then
    fail "application did not become healthy at $BASE_URL"
  fi
  sleep 1
done

status="$(request GET /health "$TMP_DIR/health")"
expect_status "$status" 200 health
json_assert "$TMP_DIR/health.body" 'data["status"] == "ok"'
log "health ok"

status="$(request GET /openapi.json "$TMP_DIR/openapi")"
expect_status "$status" 200 openapi
json_assert "$TMP_DIR/openapi.body" '"/auth/register" in data["paths"]'
json_assert "$TMP_DIR/openapi.body" '"/parcels" in data["paths"]'
log "openapi ok"

email="smoke-$(date +%s)-$$@example.com"
password="securepass123"
register_payload="{\"email\":\"$email\",\"password\":\"$password\"}"

status="$(
  request POST /auth/register "$TMP_DIR/register" \
    -H 'Content-Type: application/json' \
    -d "$register_payload"
)"
expect_status "$status" 201 register
json_assert "$TMP_DIR/register.body" 'data["token_type"] == "bearer"'
log "register ok"

status="$(
  request POST /auth/login "$TMP_DIR/login" \
    -H 'Content-Type: application/json' \
    -d "$register_payload"
)"
expect_status "$status" 200 login
access_token="$(json_get "$TMP_DIR/login.body" access_token)"
refresh_token="$(cookie_value "$TMP_DIR/login.headers" refresh_token)"
csrf_token="$(cookie_value "$TMP_DIR/login.headers" refresh_csrf)"
test -n "$access_token" || fail "login did not return access token"
test -n "$refresh_token" || fail "login did not set refresh_token cookie"
test -n "$csrf_token" || fail "login did not set refresh_csrf cookie"
log "login ok"

cookie_header="refresh_token=$refresh_token; refresh_csrf=$csrf_token"
status="$(
  request POST /auth/refresh "$TMP_DIR/refresh" \
    -H "Cookie: $cookie_header" \
    -H "X-CSRF-Token: $csrf_token"
)"
expect_status "$status" 200 refresh
access_token="$(json_get "$TMP_DIR/refresh.body" access_token)"
refresh_token="$(cookie_value "$TMP_DIR/refresh.headers" refresh_token)"
csrf_token="$(cookie_value "$TMP_DIR/refresh.headers" refresh_csrf)"
test -n "$access_token" || fail "refresh did not return access token"
log "refresh ok"

status="$(request GET '/parcel-types?limit=20&offset=0' "$TMP_DIR/parcel-types")"
expect_status "$status" 200 parcel-types
json_assert "$TMP_DIR/parcel-types.body" 'data["total"] >= 3'
parcel_type_id="$(
  python3 - "$TMP_DIR/parcel-types.body" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
for item in data["items"]:
    if item["name"] == "electronics":
        print(item["id"])
        raise SystemExit(0)
raise SystemExit(1)
PY
)"
test -n "$parcel_type_id" || fail "electronics parcel type not found"
log "parcel types ok"

parcel_payload="$(
  python3 - "$parcel_type_id" <<'PY'
import json
import sys

print(
    json.dumps(
        {
            "name": "Smoke test parcel",
            "weightKg": "1.200",
            "declaredValueUsd": "129.99",
            "parcelTypeId": sys.argv[1],
        }
    )
)
PY
)"

status="$(
  request POST /parcels "$TMP_DIR/create-unauthorized" \
    -H 'Content-Type: application/json' \
    -d "$parcel_payload"
)"
expect_status "$status" 401 create-unauthorized
log "unauthorized create rejected"

status="$(
  request POST /parcels "$TMP_DIR/create-parcel" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $access_token" \
    -d "$parcel_payload"
)"
expect_status "$status" 201 create-parcel
parcel_id="$(json_get "$TMP_DIR/create-parcel.body" id)"
test -n "$parcel_id" || fail "create parcel did not return id"
log "create parcel ok"

status="$(
  request GET '/parcels?limit=10&offset=0&has_cost=false' "$TMP_DIR/list-parcels" \
    -H "Authorization: Bearer $access_token"
)"
expect_status "$status" 200 list-parcels
python3 - "$TMP_DIR/list-parcels.body" "$parcel_id" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
if not any(item["id"] == sys.argv[2] for item in data["items"]):
    raise SystemExit(1)
PY
log "list parcels ok"

status="$(
  request GET "/parcels/$parcel_id" "$TMP_DIR/detail-parcel" \
    -H "Authorization: Bearer $access_token"
)"
expect_status "$status" 200 detail-parcel
json_assert "$TMP_DIR/detail-parcel.body" 'data["name"] == "Smoke test parcel"'
log "parcel detail ok"

status="$(request GET '/parcel-types?limit=0' "$TMP_DIR/validation")"
expect_status "$status" 422 validation
log "validation error ok"

status="$(request POST /tasks/recalc-delivery "$TMP_DIR/admin-disabled")"
expect_status "$status" 403 admin-disabled
log "disabled admin task ok"

status="$(request GET /metrics "$TMP_DIR/metrics")"
expect_status "$status" 200 metrics
grep -Eq 'http_requests_total|process_cpu_seconds_total|python_info' \
  "$TMP_DIR/metrics.body" || fail "metrics payload did not look like Prometheus"
log "metrics ok"

cookie_header="refresh_token=$refresh_token; refresh_csrf=$csrf_token"
status="$(
  request POST /auth/logout "$TMP_DIR/logout" \
    -H "Cookie: $cookie_header" \
    -H "X-CSRF-Token: $csrf_token"
)"
expect_status "$status" 204 logout
log "logout ok"

log "all checks passed"
