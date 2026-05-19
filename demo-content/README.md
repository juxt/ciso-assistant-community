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

## Demo ingestion order

1. Create a ManagedDocument of type Policy with name "FINOS AI Readiness Governance Framework". Paste `finos-air-governance-subset.md` into the latest DocumentRevision. Set status to Published.
2. Create a ManagedDocument of type Policy with name "AI Governance Policy". Paste `lorem-ipsum-wealth-partners-ai-governance-policy-v1-prose.md` into the latest DocumentRevision. Set status to Published.
3. Wait for the signal handler to index both (look for `auto_queued_document_revision_for_indexing` in backend logs).
4. Verify with the chat that retrieval reaches both documents.

## Attribution

The FINOS AIR Governance Framework is © Fintech Open Source Foundation and contributors, distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Source: <https://air-governance-framework.finos.org/>.
