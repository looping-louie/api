#!/usr/bin/env bash

set -Eeuo pipefail

if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

API_ROOT="${API_ROOT:-http://127.0.0.1:2000/api/v1}"
PROJECT_ID="${PROJECT_ID:-}"

SMOKE_PROVIDER_ID="${SMOKE_PROVIDER_ID:-together}"
SMOKE_PROVIDER_BASE_URL="${SMOKE_PROVIDER_BASE_URL:-https://api.together.xyz/v1}"
SMOKE_PROVIDER_API_KEY="${SMOKE_PROVIDER_API_KEY:-}"
SMOKE_LINKED_SERVICE_NAME="${SMOKE_LINKED_SERVICE_NAME:-smoke_linked_service}"

SMOKE_MODEL_ID="${SMOKE_MODEL_ID:-}"
SMOKE_RUN_ID="${SMOKE_RUN_ID:-$(date +%s)-$$}"
WORKER_ID=""

PERSONA_ID=""
SKILL_ID=""
ACTIVITY_ID=""
ACTIVITY_RUN_ID=""
ACTIVITY_RUN_TOKEN=""
PIPELINE_ID=""
PIPELINE_RUN_ID=""
PIPELINE_RUN_LEASE_TOKEN=""
LINKED_SERVICE_ID=""
CLEANUP_STARTED=0

CURL_HEADERS=(
    -H "Accept: application/json"
    -H "Content-Type: application/json"
)

if [[ -n "${PROJECT_ID}" ]]; then
    CURL_HEADERS+=(
        -H "X-Project-ID: ${PROJECT_ID}"
    )
fi

log() {
    printf '\n%s\n' "$*" >&2
}

request() {
    local method="$1"
    local path="$2"
    local body="${3:-}"
    local extra_header="${4:-}"
    local -a extra_curl_headers=()
    local response_file
    local status

    if [[ -n "${extra_header}" ]]; then
        extra_curl_headers=(-H "${extra_header}")
    fi

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
                "${extra_curl_headers[@]}" \
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
                "${extra_curl_headers[@]}" \
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

json_first_claim_etag() {
    python3 -c '
import json
import sys

document = json.load(sys.stdin)
items = document.get("items", [])

if not items or not isinstance(items[0].get("etag"), str):
    raise SystemExit("Claimable run response does not contain an ETag.")

print(items[0]["etag"])
'
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

cleanup() {
    local exit_code=$?

    if [[ "${CLEANUP_STARTED}" == "1" ]]; then
        return
    fi

    CLEANUP_STARTED=1
    set +e

    log "Cleaning smoke-test resources"

    if [[ -n "${PIPELINE_ID}" ]]; then
        request \
            PATCH \
            "/pipelines/${PIPELINE_ID}" \
            '{"steps":[{"type":"human_gate","gate_type":"approval"},{"type":"human_gate","gate_type":"approval"}]}' \
            >/dev/null
        request DELETE "/pipelines/${PIPELINE_ID}" >/dev/null
    fi

    if [[ -n "${ACTIVITY_ID}" ]]; then
        request DELETE "/activities/${ACTIVITY_ID}" >/dev/null
    fi

    if [[ -n "${SKILL_ID}" ]]; then
        request DELETE "/skills/${SKILL_ID}" >/dev/null
    fi

    if [[ -n "${PERSONA_ID}" ]]; then
        request DELETE "/personas/${PERSONA_ID}" >/dev/null
    fi

    if [[ -n "${LINKED_SERVICE_ID}" ]]; then
        request DELETE "/linked-services/${LINKED_SERVICE_ID}" >/dev/null
    fi

    if [[ "${exit_code}" != "0" ]]; then
        log "Smoke test failed with exit code ${exit_code}"
    fi

    exit "${exit_code}"
}

trap cleanup EXIT

log "Checking static catalogs"

request GET "/catalog/providers" >/dev/null
request GET "/catalog/models" >/dev/null
request GET "/catalog/personas" >/dev/null
request GET "/catalog/skills" >/dev/null

log "Checking current user"

request POST "/users" >/dev/null
request GET "/users/me" >/dev/null
request PATCH "/users/me" '{"default_harness":null}' >/dev/null

log "Checking projects"

project_response="$(
    request POST "/projects" "$(
    cat <<JSON
{
    "name": "Smoke Project ${SMOKE_RUN_ID}"
}
JSON
)"
)"
PROJECT_ID="$(printf '%s' "${project_response}" | json_field id)"
request GET "/projects" >/dev/null
request GET "/projects/${PROJECT_ID}" >/dev/null
request \
    PATCH \
    "/projects/${PROJECT_ID}" \
    "{\"name\":\"Smoke Project updated ${SMOKE_RUN_ID}\"}" \
    >/dev/null

log "Checking linked services"

linked_service_response="$(
    request \
        POST \
        "/linked-services" \
        "$(python3 - "${SMOKE_LINKED_SERVICE_NAME}" "${SMOKE_PROVIDER_ID}" "${SMOKE_PROVIDER_API_KEY}" "${SMOKE_PROVIDER_BASE_URL}" <<'PY'
import json
import sys

name, provider_type, api_key, base_url = sys.argv[1:]
config = {"base_url": base_url}
if api_key:
    config["api_key"] = api_key
print(json.dumps({"name": name, "provider_type": provider_type, "config": config}))
PY
)"
)"
LINKED_SERVICE_ID="$(printf '%s' "${linked_service_response}" | json_field id)"
request GET "/linked-services/${LINKED_SERVICE_ID}" >/dev/null
request PATCH "/linked-services/${LINKED_SERVICE_ID}" '{"enabled":false}' >/dev/null
request GET "/linked-services" >/dev/null

log "Checking model catalog"

models_response="$(request GET "/users/me/models")"

if [[ -n "${SMOKE_MODEL_ID}" ]]; then
    model_id="${SMOKE_MODEL_ID}"
else
    model_id="$(
        printf '%s' "${models_response}" \
            | select_model_id
    )"
fi

request GET "/users/me/models/${model_id}" >/dev/null

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
    request POST "/skills" "$(
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

request GET "/skills/${SKILL_ID}" >/dev/null
request GET "/skills" >/dev/null

skill_response="$(
    request PATCH "/skills/${SKILL_ID}" "$(
        cat <<JSON
{
    "expected_version": ${skill_version},
    "description": "Updated by scripts/smoke_api.sh",
    "enabled": false
}
JSON
    )"
)"

request \
    PATCH \
    "/skills/${SKILL_ID}" \
    '{"enabled": true}' \
    >/dev/null

log "Creating activity"

activity_response="$(
    request POST "/activities" "$(
        cat <<JSON
{
    "title": "Smoke Activity ${SMOKE_RUN_ID}",
    "description": "Created by scripts/smoke_api.sh",
    "type": "loop",
    "config": {
        "type": "loop",
        "flow": "direct",
        "stop_conditions": {
            "max_iterations": 2
        },
        "agents": [
            {
                "model_id": "${model_id}",
                "persona_id": "${PERSONA_ID}",
                "role": "generator"
            }
        ],
        "output_contract": {
            "type": "text",
            "description": "Produce a smoke-test answer."
        }
    }
}
JSON
    )"
)"

ACTIVITY_ID="$(printf '%s' "${activity_response}" | json_field "id")"

request GET "/activities/${ACTIVITY_ID}" >/dev/null
request GET "/activities?offset=0" >/dev/null
request \
    PATCH \
    "/activities/${ACTIVITY_ID}" \
    '{"description":"Updated by scripts/smoke_api.sh"}' \
    >/dev/null
request GET "/activities/${ACTIVITY_ID}/changelog?offset=0" >/dev/null

log "Creating pipeline"

pipeline_response="$(
    request POST "/pipelines" "$(
        cat <<JSON
{
    "title": "Smoke Pipeline ${SMOKE_RUN_ID}",
    "description": "Created by scripts/smoke_api.sh",
    "steps": [
        {
            "activity_id": "${ACTIVITY_ID}"
        },
        {
            "activity_id": "${ACTIVITY_ID}"
        }
    ]
}
JSON
    )"
)"

PIPELINE_ID="$(
    printf '%s' "${pipeline_response}" | json_field "id"
)"

worker_project_response="$(
    request POST "/projects" "$(
        cat <<JSON
{
    "name": "Worker Project ${SMOKE_RUN_ID}"
}
JSON
    )"
)"
WORKER_PROJECT_ID="$(printf '%s' "${worker_project_response}" | json_field "id")"
worker_instance_response="$(
    request POST "/workers/instances" "$(
        cat <<JSON
{
    "project_id": "${PROJECT_ID}",
    "harnesses": []
}
JSON
    )"
)"
WORKER_INSTANCE_ID="$(printf '%s' "${worker_instance_response}" | json_field "id")"
request GET "/workers/instances" >/dev/null
request \
    POST \
    "/workers/instances/${WORKER_INSTANCE_ID}/heartbeat" \
    '{"harnesses":[]}' \
    >/dev/null
request \
    POST \
    "/workers/instances/${WORKER_INSTANCE_ID}/projects/${WORKER_PROJECT_ID}" \
    '{}' \
    >/dev/null
request GET "/pipelines/${PIPELINE_ID}" >/dev/null
request GET "/pipelines?offset=0&status=active&search=Smoke" >/dev/null
pipeline_run_response="$(
    request POST "/pipelines/${PIPELINE_ID}/runs" \
        '{"input":"Produce a pipeline smoke-test answer."}'
)"
PIPELINE_RUN_ID="$(printf '%s' "${pipeline_run_response}" | json_field "id")"
request GET "/pipeline-runs?offset=0" >/dev/null
request GET "/pipelines/${PIPELINE_ID}/runs/${PIPELINE_RUN_ID}" >/dev/null
request GET "/pipelines/${PIPELINE_ID}/runs/${PIPELINE_RUN_ID}/events" >/dev/null
request POST "/pipelines/${PIPELINE_ID}/runs/${PIPELINE_RUN_ID}/start" '{}' >/dev/null
request GET "/pipelines/${PIPELINE_ID}/runs/${PIPELINE_RUN_ID}/readiness" >/dev/null
pipeline_claimable_response="$(
    request GET "/pipelines/${PIPELINE_ID}/runs?claimable=true"
)"
PIPELINE_RUN_ETAG="$(
    printf '%s' "${pipeline_claimable_response}" | json_first_claim_etag
)"
pipeline_claim_response="$(
    request \
        PATCH \
        "/pipelines/${PIPELINE_ID}/runs/${PIPELINE_RUN_ID}" \
        "{\"worker_id\":\"${WORKER_ID}\",\"status\":\"claimed\"}" \
        "If-Match: ${PIPELINE_RUN_ETAG}"
)"
PIPELINE_RUN_LEASE_TOKEN="$(
    printf '%s' "${pipeline_claim_response}" | json_field "lease_token"
)"
request \
    POST \
    "/pipelines/${PIPELINE_ID}/runs/${PIPELINE_RUN_ID}/lease" \
    "{\"lease_token\":\"${PIPELINE_RUN_LEASE_TOKEN}\"}" \
    >/dev/null
request POST "/pipelines/${PIPELINE_ID}/runs/${PIPELINE_RUN_ID}/continue" '{}' >/dev/null
request \
    PATCH \
    "/pipelines/${PIPELINE_ID}" \
    '{"description":"Updated by scripts/smoke_api.sh"}' \
    >/dev/null
request \
    GET \
    "/pipelines/${PIPELINE_ID}/changelog?offset=0" \
    >/dev/null

log "Checking loop dependency protection"

request_expect_status \
    DELETE \
    "/personas/${PERSONA_ID}" \
    409

log "Deleting resources in dependency order"

request \
    PATCH \
    "/pipelines/${PIPELINE_ID}" \
    "{\"steps\":[{\"activity_id\":\"${ACTIVITY_ID}\"},{\"activity_id\":\"${ACTIVITY_ID}\"}]}" \
    >/dev/null
request DELETE "/pipelines/${PIPELINE_ID}" >/dev/null
PIPELINE_ID=""

request DELETE "/activities/${ACTIVITY_ID}" >/dev/null
ACTIVITY_ID=""

request DELETE "/skills/${SKILL_ID}" >/dev/null
SKILL_ID=""

request DELETE "/personas/${PERSONA_ID}" >/dev/null
PERSONA_ID=""

request GET "/activities" >/dev/null
request GET "/pipelines" >/dev/null
request GET "/skills" >/dev/null
request GET "/personas" >/dev/null

trap - EXIT
log "✓ API smoke test passed"
