# Foil and review runs

Captured chat sessions against the demo stack, used for rehearsal.

Two scripts produce runs here:

- `run_foil.py` — original RolloverAssist foil. Submission pasted inline. Output: `foil-run_*.md`.
- `run_meridian_review.py` — Meridian AI Scenario Advisor review. Submission is bootstrapped as a `RECORD`-type ManagedDocument (`meridian-ai-advisor-submission.md`) so the chat retrieves both the submission and the spec from RAG. Output: `meridian-review_*.md`.

## Canonical Meridian review

`meridian-review_2026-05-21_135946.md` — Allium enabled, three exchanges, all substantive:

1. **Open review** ("Review the Meridian AI Scenario Advisor submission…"). Full structured review: tier classification with `ClassifyHigh / ClassifyMedium / ClassifyLow` evaluated, `engages_material_finos_risks` derived from `finos_risks_engaged.count >= 2`, all nine `ControlRequirement` enum values mapped, HITL components per `HITLArrangement.is_substantive`, conditional findings (AIR-OP-004 coverage; pre-launch closure) and advisory findings (Consequential Recommendation characterisation; AIR-OP-018 dismissal). Recommends conditional approval.
2. **HITL focus** — component-by-component analysis of `HITLArrangement.is_substantive` with `invariant HITLClaimsMustBeSubstantive`, `rule FlagPassiveHITL`, `config.minimum_review_seconds`, `OQ-Hitl-Minimum-Time`.
3. **Model identifier** — `AISystem.vendor_or_model` quoted; `OQ-Vendor-Change` and FINOS AIR-RC-022 surfaced.

Latency: ~60-100s per exchange against live Anthropic. Composed system prompt is ~6.4k chars (TOOL_SYSTEM_PROMPT + trimmed Allium primer).
