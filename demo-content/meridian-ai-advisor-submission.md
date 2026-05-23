# AI Deployment Risk Assessment — Meridian AI Scenario Advisor v1.0

> Submitted to the AI Governance Office, Lorem Ipsum Wealth Partners
> Form reference: AI-RA-2026-072
> Submitted: 19 May 2026
> Status: Pending second-line review

## 1. System summary

| Field | Value |
|---|---|
| System name | Meridian AI Scenario Advisor |
| Internal codename | Lighthouse |
| Business sponsor | David Tanaka, Head of Equity Derivatives Risk, Markets Division |
| Technical owner | Priya Sundaram, Quant Engineering Lead |
| Vendor / model | Anthropic, `claude-sonnet-4-6` (direct API) |
| Stage | Built and tested; pilot scheduled June 2026 |
| User population | ~25 risk analysts across the New York and London desks |
| Client population (twelve-month horizon) | None — no client-facing surface |

## 2. Purpose

Lighthouse is an internal copilot that sits alongside Meridian, the firm's deterministic equity-derivatives risk system. A risk analyst asks a question in natural language (e.g. "Vol on STM-FP has spiked — propose stress scenarios for this book and tell me which exposures to look at first"). Lighthouse runs a reasoning loop against `claude-sonnet-4-6`, calls a fixed set of four tools against Meridian's existing HTTP APIs (fetch portfolio, fetch market data, identify concentration risk, run scenario), and returns a structured recommendation with severity, headline, narrative, evidence and proposed actions.

The analyst reviews the recommendation and clicks Accept or Reject. The deterministic core of Meridian is unchanged — Lighthouse uses Meridian's public HTTP surface only, and writes nothing other than `ScenarioTask` records equivalent to those an analyst can create manually today.

## 3. Risk tier self-assessment

**Proposed tier: Medium.**

Rationale: Lighthouse is not customer-facing. It does not make a recommendation that reaches a client, and it does not act autonomously on portfolios. Its outputs are advisory only — the recommended scenarios and follow-ups sit on the analyst's screen until the analyst clicks Accept, and even an accepted recommendation does not bypass Meridian's existing controls. We therefore consider it a productivity tool for a small, qualified internal population rather than a customer-facing decision system. The advisor's `run_scenario` calls reuse the desk's existing scenario engine; the engine's outputs are interpreted and actioned by the analyst as they would be in any unassisted session, so we treat the AI layer as advisory in posture.

FINOS risks engaged: **AIR-OP-014** (Inadequate System Alignment), **AIR-OP-017** (Lack of Explainability). We have considered **AIR-OP-018** (Model Overreach) and judge it not material at this tier given the closed tool registry (four tools, none of which act outside Meridian's public surface).

Regulatory domain: none. Operational risk adjacent through the Markets Division's standard model-risk pipeline; not within the scope of §7.1 (Reg BI), §7.2 (fair lending) or §7.3 (privacy).

## 4. Controls in place

| Control | Status |
|---|---|
| Documented purpose and approved Business Sponsor | Yes — see §1 |
| Model card (Anthropic system card for claude-sonnet-4-6) | Yes — attached |
| Inclusion in the AI Deployment Register | On approval |
| Basic monitoring | Yes — session-level audit log on every advisor session |
| Pre-launch internal review | Conducted by Quant Engineering and Risk Methodology, May 2026 |
| Defined HITL | Yes — see §5 |
| Monitoring plan pre-launch | Yes — see §6 |
| Training data provenance | Per Anthropic's vendor documentation; no firm-specific fine-tuning |
| Domain obligation mapping (§5.2) | Not applicable — no §7 regulatory domain engaged |

## 5. Human-in-the-Loop arrangement

Every advisor session produces one structured recommendation. The analyst — a credentialed risk analyst with five or more years of equity-derivatives experience — reviews the recommendation in the Lighthouse panel and must affirmatively click Accept or Reject. There is no implicit approval, no time-based default, and no rule by which an unattended session is treated as accepted. Expected review time is sixty seconds or more on representative scenarios; this comfortably exceeds the policy's fifteen-second minimum for substantive review.

The information available to the analyst at review includes: the recommendation severity and headline, the full narrative explaining the recommendation, the proposed list of `run_scenario` actions with their parameters, and an evidence list summarising what the model considered. The analyst can drill into any scenario the model has materialised before deciding.

## 6. Monitoring and audit

Every advisor session writes three boundary entries to an append-only audit log: session opened, session completed (with the recommendation produced), and review decided (accept or reject, with reviewer identity). The audit file is preserved across service restarts and is exposed through the Lighthouse audit view. Operational metrics — session count, completion rate, accept/reject rate, latency — are tracked via the existing Meridian observability stack.

## 7. Deployment context

Rollout: pilot of fifteen analysts in New York and London for four weeks from 8 June 2026; broader scale-up re-submitted thereafter. Success criteria: at least 60% accept-rate on representative scenarios; no session failures requiring re-work; analyst NPS of +20 or better at four weeks. Rollback: a feature flag hides the Lighthouse top-nav entry; the deterministic core is unaffected.

## 8. Outstanding items

- Final UX review of the audit view, scheduled 27 May
- Analyst onboarding materials, in progress

## 9. Requested approval

We request approval to pilot under Medium tier controls for four weeks commencing 8 June 2026, with scale-up to be re-submitted ahead of broader deployment.

---

**Submitted by:** David Tanaka
**For attention of:** Director of AI Governance, Second Line
