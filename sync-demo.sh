#!/usr/bin/env bash
# sync-demo.sh
#
# Bring this clone of the demo to a runnable end-to-end state.
# Idempotent. Re-runnable. Safe to run after a fresh clone.
#
# Prereqs:
#   - Docker (OrbStack required on macOS) with the daemon running. The
#     script checks the context but won't switch it for you.
#   - .env at the repo root (see .env.example)
#
# Opt-in env vars:
#   INDEX_LIBRARIES=1   Also index the 150+ shipped framework libraries
#                       (ISO 27001, NIST CSF, SOC 2, etc.) into qdrant.
#                       Slow (~30 min on CPU). Not needed for DEMO-SCRIPT;
#                       only useful if you're exercising the chat's
#                       `search_library` tool against shipped frameworks.
#
# Gotcha: this project uses fixed container names (backend, huey, qdrant,
# caddy, frontend, litellm). A second checkout of ciso-assistant-community
# with its stack up will hold those names and the bring-up will fail with
# a "container name already in use" error. The pre-flight check below
# detects that case and tells you what to run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

step() { printf '\n==> %s\n' "$*"; }
fail() { printf '    FAIL: %s\n' "$*" >&2; exit 1; }

# --- Prerequisites ---

step "checking .env"
[[ -f .env ]] || fail ".env not found. Copy .env.example to .env and fill in real values."
grep -qE '^ANTHROPIC_API_KEY=sk-ant-' .env \
  || fail "ANTHROPIC_API_KEY in .env is missing or still a placeholder.
        Generate at https://console.anthropic.com/settings/keys"
grep -qE '^DJANGO_SUPERUSER_EMAIL=' .env \
  || fail "DJANGO_SUPERUSER_EMAIL missing in .env."
grep -qE '^DJANGO_SUPERUSER_PASSWORD=' .env \
  || fail "DJANGO_SUPERUSER_PASSWORD missing in .env."
echo "    ok"

step "checking docker daemon"
docker info >/dev/null 2>&1 \
  || fail "docker daemon not reachable.
        On macOS with OrbStack: ensure DOCKER_HOST is unset and run
        'docker context use orbstack' first."
echo "    ok (context: $(docker context show 2>/dev/null || echo default))"

step "checking for orphan containers from other checkouts"
# Fixed container names this project owns. If any of these exist but
# weren't created by *this* working directory, a sibling checkout is
# holding the name and `docker compose up` will fail opaquely.
OWNED_DIR="$SCRIPT_DIR"
COLLISIONS=()
for name in backend huey qdrant caddy frontend litellm; do
  cid=$(docker ps -aq --filter "name=^${name}$" 2>/dev/null) || continue
  [[ -z "$cid" ]] && continue
  owner=$(docker inspect "$cid" --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}' 2>/dev/null)
  if [[ -n "$owner" && "$owner" != "$OWNED_DIR" ]]; then
    COLLISIONS+=("${name} (owned by ${owner})")
  fi
done
if (( ${#COLLISIONS[@]} > 0 )); then
  printf '    collisions:\n'
  printf '      - %s\n' "${COLLISIONS[@]}"
  fail "another checkout is holding container names.
        Stop it with: (cd <other-checkout> && docker compose down)
        Do NOT use 'docker rm' — that loses the other project's state."
fi
echo "    ok"

# --- Stack ---

step "bringing up the stack"
UP_LOG=$(mktemp -t sync-demo-up.XXXXXX)
if ! docker compose up -d >"$UP_LOG" 2>&1; then
  echo
  cat "$UP_LOG" >&2
  rm -f "$UP_LOG"
  fail "docker compose up failed. See output above."
fi
rm -f "$UP_LOG"
echo "    containers up"

step "waiting for backend health (up to 5 minutes for first boot)"
for i in $(seq 1 60); do
  if docker compose ps backend 2>/dev/null | grep -q "(healthy)"; then
    printf '\n    healthy after %d second(s)\n' "$((i * 5))"
    break
  fi
  printf '.'
  sleep 5
  if [[ $i -eq 60 ]]; then
    printf '\n'
    fail "backend did not become healthy within 5 minutes."
  fi
done

# --- Vector store ---

step "initialising qdrant collection (idempotent)"
docker compose exec -T backend poetry run python manage.py init_qdrant 2>&1 | tail -3

step "indexing model objects (idempotent)"
docker compose exec -T backend poetry run python manage.py index_objects 2>&1 | tail -3

step "framework library indexing"
# The 150+ shipped framework libraries (ISO 27001, NIST CSF, SOC 2, etc.)
# back the chat's `search_library` tool. The DEMO-SCRIPT does not touch
# them: it works against the custom Allium spec and the FINRA excerpt,
# both indexed via `index_objects` into the model partition.
# Indexing all libraries takes ~30 minutes on CPU and costs ~60k qdrant
# chunks. Opt in only if you actually need the library partition.
LIB_COUNT=$(curl -sS -X POST http://localhost:6333/collections/ciso_assistant/points/count \
  -H "Content-Type: application/json" \
  -d '{"filter":{"must":[{"key":"source_type","match":{"value":"library"}}]}}' \
  2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['count'])" \
  2>/dev/null || echo "0")
echo "    library chunks currently in qdrant: $LIB_COUNT"

if [[ "${INDEX_LIBRARIES:-0}" == "1" ]]; then
  step "indexing framework libraries — slow path, ~30 minutes on CPU"
  echo "    INDEX_LIBRARIES=1 set; running full library indexing."
  docker compose exec -T backend poetry run python manage.py index_libraries --sync
else
  echo "    skipping (DEMO-SCRIPT does not need this)."
  echo "    to index anyway: INDEX_LIBRARIES=1 ./sync-demo.sh"
fi

# --- Demo content ---

step "bootstrapping demo folder and policies"
docker compose exec -T backend poetry run python manage.py setup_demo 2>&1 | tail -12

step "waiting for policy indexing (Huey is async; ~40s on first ingest)"
# setup_demo queues each published policy revision for indexing via Huey.
# verify_demo asserts the chunks are present in Qdrant, so we have to wait
# for the queue to drain before running it. Poll Qdrant for both expected
# filename prefixes via the REST API.
poll_indexed() {
  curl -sS -X POST http://localhost:6333/collections/ciso_assistant/points/scroll \
    -H 'Content-Type: application/json' \
    -d '{"filter":{"must":[{"key":"source_type","match":{"value":"document"}}]},"limit":500,"with_payload":["filename"]}' \
    2>/dev/null \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
want = {'policy-AI Governance Policy-rev', 'policy-FINOS AI Readiness Governance Framework (adopted)-rev'}
seen = set()
for p in data.get('result', {}).get('points', []):
    fn = (p.get('payload') or {}).get('filename', '')
    for w in want:
        if fn.startswith(w):
            seen.add(w)
print(len(seen))
" 2>/dev/null
}
for i in $(seq 1 60); do
  if [[ "$(poll_indexed)" == "2" ]]; then
    printf '\n    both policies indexed after %d second(s)\n' "$((i * 2))"
    break
  fi
  printf '.'
  sleep 2
  if [[ $i -eq 60 ]]; then
    printf '\n'
    fail "policy indexing did not complete within 2 minutes. Check huey logs:
        docker compose logs huey | tail -50"
  fi
done

# --- Post-setup verification ---

step "verifying patches and integrations"
if ! docker compose exec -T backend poetry run python manage.py verify_demo; then
  fail "verify_demo failed. The demo is NOT in a known-good state. Inspect the output above."
fi

# --- Done ---

EMAIL=$(grep '^DJANGO_SUPERUSER_EMAIL=' .env | cut -d= -f2)

cat <<DONE

==> demo is ready

    app:    https://localhost:8443    (accept the self-signed cert)
    login:  ${EMAIL}
    chat:   bottom-right widget once logged in

    re-run this script any time to bring the stack back to demo-ready state.
DONE
