#!/usr/bin/env bash

set -Eeuo pipefail

if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

API_ROOT="${API_ROOT:-http://127.0.0.1:8000/api/v1}"
WORKSPACE_ID="${WORKSPACE_ID:-}"

SMOKE_PROVIDER_ID="${SMOKE_PROVIDER_ID:-together}"
SMOKE_PROVIDER_BASE_URL="${SMOKE_PROVIDER_BASE_URL:-https://api.together.xyz/v1}"
SMOKE_PROVIDER_API_KEY="${SMOKE_PROVIDER_API_KEY:-${TOGETHER_API_KEY:-}}"

SMOKE_MODEL_ID="${SMOKE_MODEL_ID:-}"
SMOKE_RUN_ID="${SMOKE_RUN_ID:-$(date +%s)-$$}"

PERSONA_ID=""
SKILL_ID=""
COUNCIL_ID=""
LOOP_ID=""
PROVIDER_CREATED=0
PROVIDER_WAS_ENABLED=0
CLEANUP_STARTED=0

CURL_HEADERS=(
    -H "Accept: application/json"
    -H "Content-Type: application/json"
)

if [[ -n "${WORKSPACE_ID}" ]]; then
    CURL_HEADERS+=(
        -H "X-Workspace-ID: ${WORKSPACE_ID}"
    )
fi

log() {
    printf '\n%s\n' "$*" >&2
}

request() {
    local method="$1"
    local path="$2"
    local body="${3:-}"
    local response_file
    local status

    response_file="$(mktemp)"

    log "→ ${method} ${API_ROOT}${path}"

    if [[ -n "${body}" ]]; then
        status="$(
            curl \
                --silent \
                --show-error \
                --output "${response_file}" \
                --write-out "%{http_code}" \
                --request "${method}" \
                "${CURL_HEADERS[@]}" \
                --data "${body}" \
                "${API_ROOT}${path}"
        )"
    else
        status="$(
            curl \
                --silent \
                --show-error \
                --output "${response_file}" \
                --write-out "%{http_code}" \
                --request "${method}" \
                "${CURL_HEADERS[@]}" \
                "${API_ROOT}${path}"
        )"
    fi

    if (( status >= 200 && status < 300 )); then
        cat "${response_file}"
        rm -f "${response_file}"
        return 0
    fi

    printf '\nHTTP %s: %s %s\n' \
        "${status}" \
        "${method}" \
        "${API_ROOT}${path}" >&2

    cat "${response_file}" >&2
    printf '\n' >&2

    rm -f "${response_file}"
    return 1
}

request_expect_status() {
    local method="$1"
    local path="$2"
    local expected_status="$3"
    local body="${4:-}"
    local response_file
    local status

    response_file="$(mktemp)"

    if [[ -n "${body}" ]]; then
        status="$(
            curl \
                --silent \
                --show-error \
                --output "${response_file}" \
                --write-out "%{http_code}" \
                --request "${method}" \
                "${CURL_HEADERS[@]}" \
                --data "${body}" \
                "${API_ROOT}${path}"
        )"
    else
        status="$(
            curl \
                --silent \
                --show-error \
                --output "${response_file}" \
                --write-out "%{http_code}" \
                --request "${method}" \
                "${CURL_HEADERS[@]}" \
                "${API_ROOT}${path}"
        )"
    fi

    log "→ ${method} ${API_ROOT}${path} [expected ${expected_status}, got ${status}]"

    if [[ "${status}" != "${expected_status}" ]]; then
        cat "${response_file}" >&2
        rm -f "${response_file}"
        return 1
    fi

    rm -f "${response_file}"
}

json_field() {
    local field="$1"

    python3 -c '
import json
import sys

document = json.load(sys.stdin)
value = document

for part in sys.argv[1].split("."):
    value = value[part]

print(value)
' "${field}"
}

select_model_id() {
    python3 -c '
import json
import sys

document = json.load(sys.stdin)
items = document if isinstance(document, list) else document.get("items", [])

available = [item for item in items if item.get("available") is True]

if not available:
    raise SystemExit(1)

print(available[0]["id"])
'
}

provider_state() {
    local provider_id="$1"

    python3 -c '
import json
import sys

provider_id = sys.argv[1]
document = json.load(sys.stdin)

if isinstance(document, list):
    items = document
else:
    items = document.get("items", document.get("providers", []))

for item in items:
    if item.get("provider") == provider_id:
        values = (
            "1" if item.get("configured") else "0",
            "1" if item.get("enabled") else "0",
            "1" if item.get("requires_api_key") else "0",
        )
        print("\t".join(values))
        raise SystemExit(0)

raise SystemExit(f"Provider not found: {provider_id}")
' "${provider_id}"
}

provider_payload() {
    python3 - \
        "${SMOKE_PROVIDER_API_KEY}" \
        "${SMOKE_PROVIDER_BASE_URL}" <<'PY'
import json
import sys

api_key = sys.argv[1]
base_url = sys.argv[2]

payload = {}

if api_key:
    payload["api_key"] = api_key

if base_url:
    payload["base_url"] = base_url

print(json.dumps(payload))
PY
}

cleanup() {
    local exit_code=$?

    if [[ "${CLEANUP_STARTED}" == "1" ]]; then
        return
    fi

    CLEANUP_STARTED=1
    set +e

    log "Cleaning smoke-test resources"

    if [[ -n "${LOOP_ID}" ]]; then
        request DELETE "/loops/delete/${LOOP_ID}" >/dev/null
    fi

    if [[ -n "${COUNCIL_ID}" ]]; then
        request DELETE "/councils/delete/${COUNCIL_ID}" >/dev/null
    fi

    if [[ -n "${SKILL_ID}" ]]; then
        request DELETE "/skills/delete/${SKILL_ID}" >/dev/null
    fi

    if [[ -n "${PERSONA_ID}" ]]; then
        request DELETE "/personas/${PERSONA_ID}" >/dev/null
    fi

    if [[ "${PROVIDER_CREATED}" == "1" ]]; then
        request DELETE "/providers/${SMOKE_PROVIDER_ID}" >/dev/null
    elif [[ "${PROVIDER_WAS_ENABLED}" == "0" ]]; then
        request \
            PATCH \
            "/providers/${SMOKE_PROVIDER_ID}" \
            '{"enabled": false}' \
            >/dev/null
    fi

    if [[ "${exit_code}" != "0" ]]; then
        log "Smoke test failed with exit code ${exit_code}"
    fi

    exit "${exit_code}"
}

trap cleanup EXIT

log "Checking provider catalog"

providers_response="$(request GET "/providers")"

IFS=$'\t' read -r \
    provider_configured \
    provider_enabled \
    provider_requires_key \
    <<< "$(
        printf '%s' "${providers_response}" \
            | provider_state "${SMOKE_PROVIDER_ID}"
    )"

PROVIDER_WAS_ENABLED="${provider_enabled}"

request GET "/providers/${SMOKE_PROVIDER_ID}" >/dev/null

if [[ "${provider_configured}" == "0" ]]; then
    if [[ "${provider_requires_key}" == "1" \
        && -z "${SMOKE_PROVIDER_API_KEY}" ]]; then
        log "Provider ${SMOKE_PROVIDER_ID} requires SMOKE_PROVIDER_API_KEY."
        exit 1
    fi

    request \
        PATCH \
        "/providers/${SMOKE_PROVIDER_ID}" \
        "$(provider_payload)" \
        >/dev/null

    PROVIDER_CREATED=1
fi

request \
    PATCH \
    "/providers/${SMOKE_PROVIDER_ID}" \
    '{"enabled": false}' \
    >/dev/null
request \
    PATCH \
    "/providers/${SMOKE_PROVIDER_ID}" \
    '{"enabled": true}' \
    >/dev/null

log "Checking model catalog"

models_response="$(request GET "/models")"

if [[ -n "${SMOKE_MODEL_ID}" ]]; then
    model_id="${SMOKE_MODEL_ID}"
else
    model_id="$(
        printf '%s' "${models_response}" \
            | select_model_id
    )"
fi

request GET "/models/${model_id}" >/dev/null

log "Creating persona"

persona_response="$(
    request POST "/personas" "$(
        cat <<JSON
{
    "name": "Smoke Persona ${SMOKE_RUN_ID}",
    "description": "Created by scripts/smoke_api.sh",
    "instructions": "Generate a small, correct and maintainable implementation.",
    "metadata": {
        "source": "smoke_api"
    }
}
JSON
    )"
)"

PERSONA_ID="$(printf '%s' "${persona_response}" | json_field "id")"
persona_version="$(printf '%s' "${persona_response}" | json_field "version")"

request GET "/personas/${PERSONA_ID}" >/dev/null
request GET "/personas" >/dev/null

persona_response="$(
    request PATCH "/personas/${PERSONA_ID}" "$(
        cat <<JSON
{
    "expected_version": ${persona_version},
    "description": "Updated by scripts/smoke_api.sh",
    "enabled": false
}
JSON
    )"
)"

request \
    PATCH \
    "/personas/${PERSONA_ID}" \
    '{"enabled": true}' \
    >/dev/null

log "Creating skill"

skill_response="$(
    request POST "/skills/create" "$(
        cat <<JSON
{
    "name": "Smoke Skill ${SMOKE_RUN_ID}",
    "description": "Created by scripts/smoke_api.sh",
    "instructions": "Review correctness, clarity and maintainability.",
    "metadata": {
        "applies_when": [
            "smoke"
        ],
        "default_strictness": {
            "prototype": 20,
            "mvp": 50,
            "production": 80
        }
    }
}
JSON
    )"
)"

SKILL_ID="$(printf '%s' "${skill_response}" | json_field "id")"
skill_version="$(printf '%s' "${skill_response}" | json_field "version")"

request GET "/skills/describe/${SKILL_ID}" >/dev/null
request GET "/skills/list" >/dev/null

skill_response="$(
    request POST "/skills/update/${SKILL_ID}" "$(
        cat <<JSON
{
    "expected_version": ${skill_version},
    "description": "Updated by scripts/smoke_api.sh"
}
JSON
    )"
)"

log "Creating council"

council_response="$(
    request POST "/councils/create" "$(
        cat <<JSON
{
    "name": "Smoke Council ${SMOKE_RUN_ID}",
    "description": "Created by scripts/smoke_api.sh",
    "assignments": [
        {
            "role": "generator",
            "persona_id": "${PERSONA_ID}",
            "skill_ids": [
                "${SKILL_ID}"
            ]
        }
    ]
}
JSON
    )"
)"

COUNCIL_ID="$(printf '%s' "${council_response}" | json_field "id")"
council_version="$(printf '%s' "${council_response}" | json_field "version")"

request GET "/councils/describe/${COUNCIL_ID}" >/dev/null
request GET "/councils/list" >/dev/null

council_response="$(
    request POST "/councils/update/${COUNCIL_ID}" "$(
        cat <<JSON
{
    "expected_version": ${council_version},
    "description": "Updated by scripts/smoke_api.sh"
}
JSON
    )"
)"

log "Checking council dependency protection"

request_expect_status \
    DELETE \
    "/personas/${PERSONA_ID}" \
    409

request_expect_status \
    DELETE \
    "/skills/delete/${SKILL_ID}" \
    409

log "Creating loop"

loop_response="$(
    request POST "/loops/create" "$(
        cat <<JSON
{
    "name": "Smoke Loop ${SMOKE_RUN_ID}",
    "description": "Created by scripts/smoke_api.sh",
    "council_id": "${COUNCIL_ID}",
    "max_iterations": 2,
    "model_bindings": [
        {
            "role": "generator",
            "model_id": "${model_id}"
        }
    ]
}
JSON
    )"
)"

LOOP_ID="$(printf '%s' "${loop_response}" | json_field "id")"
loop_version="$(printf '%s' "${loop_response}" | json_field "version")"

request GET "/loops/describe/${LOOP_ID}" >/dev/null
request GET "/loops/list" >/dev/null

loop_response="$(
    request POST "/loops/update/${LOOP_ID}" "$(
        cat <<JSON
{
    "expected_version": ${loop_version},
    "description": "Updated by scripts/smoke_api.sh",
    "max_iterations": 3
}
JSON
    )"
)"

request POST "/loops/validate/${LOOP_ID}" >/dev/null

log "Checking loop dependency protection"

request_expect_status \
    DELETE \
    "/councils/delete/${COUNCIL_ID}" \
    409

log "Deleting resources in dependency order"

request DELETE "/loops/delete/${LOOP_ID}" >/dev/null
LOOP_ID=""

request DELETE "/councils/delete/${COUNCIL_ID}" >/dev/null
COUNCIL_ID=""

request DELETE "/skills/delete/${SKILL_ID}" >/dev/null
SKILL_ID=""

request DELETE "/personas/${PERSONA_ID}" >/dev/null
PERSONA_ID=""

request GET "/loops/list" >/dev/null
request GET "/councils/list" >/dev/null
request GET "/skills/list" >/dev/null
request GET "/personas" >/dev/null

if [[ "${PROVIDER_CREATED}" == "1" ]]; then
    request DELETE "/providers/${SMOKE_PROVIDER_ID}" >/dev/null
    PROVIDER_CREATED=0
elif [[ "${PROVIDER_WAS_ENABLED}" == "0" ]]; then
    request \
        PATCH \
        "/providers/${SMOKE_PROVIDER_ID}" \
        '{"enabled": false}' \
        >/dev/null
fi

request GET "/providers" >/dev/null

trap - EXIT
log "✓ API smoke test passed"
