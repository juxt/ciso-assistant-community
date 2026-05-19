#!/usr/bin/env bash
# sync-demo.sh
#
# Bring this clone of the demo to a runnable end-to-end state.
# Idempotent. Re-runnable. Skips the slow library indexing if it has
# already been done. Safe to run after a fresh clone.
#
# Prereqs:
#   - Docker (OrbStack recommended on macOS) with the daemon running
#   - .env at the repo root (see .env.example)

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

# --- Stack ---

step "bringing up the stack"
docker compose up -d >/dev/null 2>&1
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

step "checking framework library indexing status"
LIB_COUNT=$(curl -sS -X POST http://localhost:6333/collections/ciso_assistant/points/count \
  -H "Content-Type: application/json" \
  -d '{"filter":{"must":[{"key":"source_type","match":{"value":"library"}}]}}' \
  2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['count'])" \
  2>/dev/null || echo "0")
echo "    library chunks currently in qdrant: $LIB_COUNT"

if [[ "$LIB_COUNT" -lt 50000 ]]; then
  step "indexing framework libraries — slow path, ~30 minutes on CPU"
  echo "    this only needs to run once per qdrant volume. Time for a coffee."
  docker compose exec -T backend poetry run python manage.py index_libraries --sync
else
  echo "    already indexed; skipping the slow path"
fi

# --- Demo content ---

step "bootstrapping demo folder and policies"
docker compose exec -T backend poetry run python manage.py setup_demo 2>&1 | tail -12

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
