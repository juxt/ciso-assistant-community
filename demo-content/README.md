# Demo content

Source-of-truth markdown for documents that get pasted into CISO Assistant ManagedDocuments during demo setup. The chat signal patch (`patches/signals.py`) auto-indexes a `DocumentRevision` into Qdrant when its status flips to Published.

## Files

- **`finos-air-governance-subset.md`** — A subset of the FINOS AI Readiness (AIR) Governance Framework, v2 (Oct 2025), reproduced under CC BY 4.0. Six risks: AIR-OP-004, AIR-OP-014, AIR-OP-016, AIR-OP-017, AIR-OP-018, AIR-RC-022. Goes in as the foundational risk catalogue the firm operationalises against.
- **`lorem-ipsum-wealth-partners-ai-governance-policy-v1-prose.md`** — The fictional firm's natural-language AI Governance Policy, written as its operationalisation of FINOS. This is the *foil* version. The AI struggles to apply it consistently because corporate prose is ambiguous.

## Seeded ambiguities in the policy

These are deliberate. The foil exists to show what the AI does when its grounding is competent prose.

- **§4 tier criteria** — soft language ("typically", "no single factor is determinative", "in favour of"). Reviewer judgment required.
- **§5 control list** — Medium and High tier lists reference Annex A for control descriptions. Annex A is reserved.
- **§8 HITL** — Definition in §2 is one sentence; §8 expands it with a "for the avoidance of doubt" clause that contradicts a literal reading of §2.
- **§7.1 Reg BI** — names fee comparison; says "other applicable Reg BI obligations" without enumerating them.
- **§6 precedent** — Refers to the AI Deployment Register, which is not included; says conditions "shall be carried forward unless materially differing circumstances are documented", without naming any precedent.
- **§10 monitoring** — "Monitoring is a baseline requirement for production AI Systems" sits one sentence away from a deferral clause for Low tier.

## Bringing the demo up

Run `../sync-demo.sh` from the repo root. It is idempotent and handles everything: starting the stack, waiting for backend health, initialising Qdrant, indexing the framework libraries the first time only, and running the `setup_demo` management command to publish the two policies.

`setup_demo` reads the markdown files in this directory and:

1. Creates the **Lorem Ipsum Wealth Partners** Folder.
2. Creates a Policy `FINOS AI Readiness Governance Framework (adopted)` and publishes a DocumentRevision with the contents of `finos-air-governance-subset.md`.
3. Creates a Policy `AI Governance Policy` and publishes a DocumentRevision with the contents of `lorem-ipsum-wealth-partners-ai-governance-policy-v1-prose.md`.

The signals patch (`patches/signals.py`) indexes both into Qdrant the moment their revisions are published.

To start over from a clean slate:

```bash
docker compose exec backend poetry run python manage.py setup_demo --reset
```

To edit a policy: change the markdown here, then re-run `./sync-demo.sh`. The command notices the content change and publishes a new revision; the signals patch retires the old chunks and indexes the new ones automatically.

## Attribution

The FINOS AIR Governance Framework is © Fintech Open Source Foundation and contributors, distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Source: <https://air-governance-framework.finos.org/>.
