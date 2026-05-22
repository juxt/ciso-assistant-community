# Demo integration — handoff

Wealth-firm AI governance demo, late May 2026. Five-beat flow for senior compliance executives. This document is the handoff from the integration pass; what follows is the state of the system at handoff time, the commands the operator runs in the room, what's still open, and the reasoning behind the decisions taken.

The demo runs across three repos:

- **`ciso-assistant-community`** — the firm's governance platform. Sarah Chen uses its chat (Allium-grounded) for second-line review. Most of this integration's changes landed here.
- **`allium-swarm`** (branch `ai-demo`) — Temporal pipeline that audits codebases against a spec. The `ComplianceAuditWorkflow` was already wired to take an external spec and fan out across multiple codebases.
- **`meridian`** (branch `ai-demo`) — equity-derivatives risk system with the Meridian AI Scenario Advisor extension (codename Lighthouse). Has five deliberate cracks documented in `services/advisor/README.md` and `docs/notes/advisor-handoff.md`. Untouched by this pass.

## What I found in the audit

The bulk of the demo infrastructure already existed when this pass started. Concretely:

- The Meridian advisor was built and merged on `ai-demo` with all five cracks pinned to Open Questions (single-shot HITL, session-boundary-only audit, hardcoded model identifier, no MaterialIncident, autonomy not in tier classification).
- The LIWP spec existed in two forms — the full governance policy (`liwp-ai-governance.allium` v1 + v2) and a split version (`liwp-ai-system-obligations.v1/v2.allium`, `liwp-review-tool.v1/v2.allium`) consumed by the swarm.
- The v2 amendments (A1 `is_agentic`, A2 multi-step HITL, A3 `agent_action_trace_log`, A4 `ModelVersionLedger`, A5 `MaterialIncident`) were already encoded in v2 and parse cleanly.
- The swarm's `ComplianceAuditWorkflow` already took `--spec` and `--codebase name=path` flags, fanned out across codebases in parallel, and wrote consolidated per-codebase findings to JSON + markdown.

What was missing:

1. Sarah had no specific submission to review — the existing flow had her chatting in general about policy.
2. There was no path from a swarm audit back into Sarah's chat. The swarm wrote findings to `/tmp` and that's where they died.
3. The chat's tool-routing step ignored the Allium primer entirely — `query_objects` (data-model search) won every time, so document retrieval rarely fired on cold turns.
4. The Allium primer was 5,318 characters of mostly answer-shaping prose. Most of it was irrelevant to tool routing.

## What I built or changed, and why

All changes live in `ciso-assistant-community`. `allium-swarm` and `meridian` are unchanged.

### Demo content

- **`demo-content/meridian-ai-advisor-submission.md`** (new). 864-word AI deployment submission from the Markets Division for the Meridian AI Scenario Advisor. Sponsor proposes Medium tier on standard factors. Each of the five Meridian cracks is observable in the submission's own claims without being flagged by the sponsor — that's the discovery Sarah's review surfaces.
- **`demo-content/setup_demo.py`** (modified). Added a `RECORDS` block and `_setup_record` method that creates `RECORD`-type `ManagedDocument`s without a Policy parent. The Meridian submission is loaded via this path. The chat's signal patch indexes any `PUBLISHED` `DocumentRevision` regardless of parent type, so records flow into RAG identically to policies.
- **`demo-content/allium-skill-primer.md`** (modified). Trimmed from 5,318 → 2,399 characters (55% reduction). Removed the construct glossary, the workflow narration, and the "for X look at Y" mappings — these duplicate what the spec self-describes. Kept the role framing, the documents-not-data-model rule (with imperative "**Do not call `query_objects`**"), citation rules, and the don't-approve / don't-pick-sides constraints. The imperative form on the `query_objects` warning is load-bearing; trimming it to descriptive form broke turn-1 tool routing in testing.
- **`demo-content/run_meridian_review.py`** (new). Three-exchange runner that drives Sarah's review query against the indexed corpus. Output transcripts land in `demo-content/foil-runs/meridian-review_*.md`.
- **`demo-content/foil-runs/README.md`** (new) and **`demo-content/foil-runs/meridian-review_2026-05-21_135946.md`** (new). Canonical rehearsal transcript — three exchanges, all substantive, citing the right spec constructs.

### Patches mounted into the backend container

- **`patches/providers.py`** (new). Patches the chat's tool-selection step (`OllamaLLM.tool_call` and `OpenAICompatibleLLM.tool_call`). Upstream uses `TOOL_SYSTEM_PROMPT` alone, which says "questions about user's data → `query_objects`". That meant the Allium primer's "submissions are documents, not user data" rule could never fire — by the time the primer's system prompt applied, the wrong tool had already been chosen and `search()` (which auto-injects firm policy chunks) was skipped. The patch introduces `_tool_selection_system_prompt()`, which appends the chat's configured `system_prompt` to `TOOL_SYSTEM_PROMPT` under "ADDITIONAL DOMAIN GUIDANCE". `DEFAULT_SYSTEM_PROMPT` (the generic GRC default) is excluded so the patch only activates when a custom primer is set. Without this patch, Sarah's "review the Meridian submission" opener consistently routed to `query_objects` against assets/controls/assessments, got 0 results, and reported there was nothing to review.
- **`patches/import_audit_findings.py`** (new). Django management command that reads a swarm audit report from `/code/audit-output/{before,after}/audit-{v1,v2}.md` and publishes it as a `RECORD`-type `ManagedDocument`. Each leg gets its own synthetic `Policy` parent — the `ManagedDocument` validator enforces `(policy, locale)` uniqueness per folder, and the Meridian submission already occupies `(None, en)`. Idempotent on content; re-running doesn't churn revisions.

### docker-compose.override.yml

- Mounted `patches/providers.py` and `patches/import_audit_findings.py` into both backend and huey containers.
- Mounted `/tmp/allium-swarm-too/audit:/code/audit-output:ro` so `import_audit_findings` can read the swarm's output.
- Set `GUNICORN_TIMEOUT=240` (up from upstream 100). The composed system prompt and spec-rich responses pushed exchanges past the upstream limit; the startup script reads `GUNICORN_TIMEOUT` directly. Worker still gets `--workers=3 --keep-alive 30`.

## The commands the operator runs, in order

These assume a clean clone with `.env` populated. The OrbStack docker context must be current (`docker context use orbstack`).

**One-off setup (before demo day, or after any patch change):**

```bash
cd ~/code/ciso-assistant-community
./sync-demo.sh
```

This brings the stack up, indexes the framework libraries on first run (~30 min), runs `setup_demo` (loads policies and the Meridian submission), and runs `verify_demo` (8 checks pass).

**On the day, before Sarah opens the chat:**

```bash
docker compose exec backend poetry run python manage.py enable_allium
```

Promotes the Allium spec from draft to published; the signal indexes it; sets the chat's system prompt to the Allium primer.

**Between beat 5 (swarm audit) and beat 6 (reflection):**

In a separate terminal, with `just dev` already running and Temporal + worker healthy in `~/code/allium-swarm`:

```bash
cd ~/code/allium-swarm
just demo-audit-before     # v1 spec; expect 2 findings on advisor, others clean
just demo-audit-after      # v2 spec; expect 7 findings on advisor, others clean
just demo-audit-diff       # show before/after side-by-side
```

Each audit takes ~90s with three codebases in parallel; Temporal UI on `:8233` shows the fan-out. Reports land in `/tmp/allium-swarm-too/audit/{before,after}/audit-{v1,v2}.{json,md}`.

Then, back in `ciso-assistant-community`, publish the findings into Sarah's chat:

```bash
docker compose exec backend poetry run python manage.py import_audit_findings           # the after leg (v2)
docker compose exec backend poetry run python manage.py import_audit_findings --leg before
```

Wait ~40s for Huey to index, then Sarah can ask the chat "what did the latest audit find on the Meridian advisor?" and have it retrieve the report by name and cite findings by spec-construct name (`AgenticSystemsRequireTraceLog`, `MaterialIncidentsReportedPromptly`, etc.).

**For rehearsal of just the chat side, without re-running the swarm:**

```bash
python3 demo-content/run_meridian_review.py
```

Captures a three-exchange Sarah-shaped transcript into `demo-content/foil-runs/meridian-review_{ts}.md`.

## LLM call state — what's real, what's mocked, what's cached

Nothing is mocked or cached for replay in the demo path. Every demo run hits Anthropic live.

| Call site | Path | Cost per demo pair |
|---|---|---|
| CISO Assistant chat | host → Caddy → backend → LiteLLM → Anthropic `claude-sonnet` | small, ~$0.50 per Sarah exchange |
| Allium-swarm audit | Go worker → Anthropic SDK direct with prompt caching | ~$3-5 per before+after pair (three codebases each leg, advisor pulls ~460k input tokens with caching discount) |
| Meridian advisor (if shown live) | Lighthouse → Anthropic SDK | small per scenario request |

Already rehearsed at handoff time:

- `demo-content/foil-runs/meridian-review_2026-05-21_135946.md` — canonical Sarah-review transcript against the live indexed corpus.
- `/tmp/allium-swarm-too/audit/before/audit-v1.{md,json}` — v1 audit, 2 findings on advisor, others clean.
- `/tmp/allium-swarm-too/audit/after/audit-v2.{md,json}` — v2 audit, 7 findings on advisor, others clean.

The swarm has a stub mode (`ALLIUM_STUB_AUDIT=1` on the worker, or `just dev-stub-audit`) that returns canned findings exactly matching the Meridian cracks in ~3 seconds per codebase. The canned content is faithful to the real cracks (see `internal/activity/audit.go:stubAuditFindings`). If Anthropic is unavailable on the day, the stub is the fallback for beat 5; flag this in the rehearsal script as a known degradation.

## Failure modes and fallbacks

- **Anthropic capacity wobble during beat 3 (live elicit).** The current rehearsal version of the amended spec is stored at `demo-content/liwp-ai-governance.v2.allium` and `demo-content/liwp-ai-system-obligations.v2.allium`. If the live elicit can't complete, the operator can fall back to "here's the amendment we landed in rehearsal" and pull up the stored file. The five amendments are tagged `-- AMEND v2:` in the file so they're easy to point at.
- **Bind-mount stale inode after editing a patched file on the host.** macOS / OrbStack sometimes loses the bind mount when files are replaced atomically (Write tool, some editors). Symptom: `ls` shows the file in the directory listing but `cat` says "no such file". Fix: `docker compose restart backend huey`. The directory mounts are stable; only file mounts are affected.
- **Worker timeout on a heavy Sarah exchange.** Upstream gunicorn timeout was 100s; we bumped to 240s via `GUNICORN_TIMEOUT=240`. Composed-prompt-plus-rich-response exchanges run 60-100s typically. If a single exchange genuinely needs more than 240s, something is wrong upstream (Anthropic stalled, LiteLLM retrying internally).
- **Reg BI false positive in the v2 audit.** The v2 audit reliably produces a `RegBIObligationsRequired` finding on the advisor that claims `is_customer_facing=true`, which is wrong (the Meridian advisor is internal-only). Per the user's framing, treat this as a *deliberate* moment in beat 5: "and this is what the human's still here for." Sarah notes it, dismisses it as out-of-scope on the customer-facing test, and moves on. Don't try to engineer it away — it actively strengthens the demo's credibility about AI-assisted compliance rather than AI-replacing compliance.
- **No audit on disk when `import_audit_findings` runs.** Command fails fast with a clear "audit report not found" error pointing at the `/tmp/...` path. Run the swarm first.
- **Submission not retrieved on Sarah's very first turn.** With the `providers.py` patch this is much rarer than it was, but the cold-session retrieval has occasionally still failed in testing. If Sarah opens beat 1 and the chat reports "I can't find the submission", her natural mitigation is to follow up with a spec-construct-named question (e.g. "what does `HITLArrangement.is_substantive` require for this submission?") — that wording reliably triggers `search_library` and the documents arrive in context for the rest of the session.

## What's still open / not done

- **Consolidated findings view styled for back-of-room readability.** The current `audit-v2.md` is plain markdown — readable from a laptop, marginal from the back of a conference room. Options for the next agent: render the JSON as a styled HTML page with severity colouring and per-codebase summary cards; or open the imported `ManagedDocument` in CISO Assistant's existing document viewer and zoom the browser.
- **Rehearsal script with full timing per beat.** This document covers commands and failure modes but not the narrative flow, what Sarah says, where the breath pauses are, when the operator's hands move.
- **Reconciliation pass on the v2 spec.** The stored `liwp-ai-governance.v2.allium` and `liwp-ai-system-obligations.v2.allium` are what the swarm audits against. The live beat-3 elicit may produce slightly different wording. Worth a 10-minute diff after a couple of rehearsals of the live elicit; tighten the stored files to match what the elicit reliably lands on.
- **Caching/replay for deterministic re-runs.** Nothing is cached. Every rehearsal pays full Anthropic cost. Not catastrophic at ~$5/pair, but worth considering a recording-replay layer if rehearsals are frequent. Stub mode is the cheap-and-cheerful version; honest record-and-replay would mean hashing the spec+codebase+tool-call sequence and bottling responses.

## Open questions for the next agent

- **Should the consolidated findings view live inside CISO Assistant** (an HTML render of the imported `ManagedDocument`) **or as a static page hosted separately**? The CISO Assistant route keeps everything in one platform but inherits Caddy's styling. A static page gives full visual control.
- **Should the operator run `import_audit_findings` manually between beats, or should it auto-fire** when the swarm workflow completes? Manual is more reliable (see option B reasoning earlier in this pass); automatic would be more visually integrated. If the next agent wants automatic, the seam is `internal/activity/audit.go:ConsolidateAudit` — add a follow-on activity that POSTs to a new CISO Assistant endpoint, accepting that this adds HTTPS / auth / cert handling on the Go side.
- **How long is beat 5 supposed to feel?** The brief said "30 seconds visible". Three parallel codebase audits take ~60-90s each. Either the brief is talking about the Temporal UI being on screen for 30s while the rest runs in background, or the demo needs the audit pre-warmed and only the consolidated view shown live. Decide what's actually being shown when.
