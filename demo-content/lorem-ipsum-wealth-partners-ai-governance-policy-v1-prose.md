# Lorem Ipsum Wealth Partners — AI Governance Policy

**Document reference:** LIWP-POL-AI-001
**Owner:** Director of AI Governance, Second Line
**Approver:** Operating Risk Committee
**Version:** 1.4
**Effective date:** January 2026
**Review cycle:** Annual

## 1. Purpose and scope

This Policy sets out how Lorem Ipsum Wealth Partners ("the Firm") governs the on-boarding, development and operation of artificial intelligence ("AI") systems used in connection with its business. It is intended to give Business Sponsors, model owners and second-line reviewers a single point of reference, consistent with the Firm's risk appetite, its fiduciary obligations to clients, and applicable regulatory requirements.

The Firm has adopted the **FINOS AI Readiness (AIR) Governance Framework** as its foundational catalogue of AI risks and mitigations. References in this Policy to FINOS risk identifiers (e.g. AIR-OP-018) and mitigation identifiers (e.g. AIR-PREV-005) are to the FINOS AIR Governance Framework as published at <https://air-governance-framework.finos.org/>. Where this Policy and another Firm policy speak to the same control, the more stringent expectation applies.

This Policy applies to all AI Systems used in connection with the Firm's business activities, whether developed internally, procured from third parties or accessed via cloud services. It applies regardless of the underlying technology (rules-based, statistical, machine learning, generative).

## 2. Definitions

For the purposes of this Policy:

- **AI System.** Any automated process that produces an inference, recommendation, decision, content or score from input data using statistical or learned patterns.
- **Consequential Recommendation.** An output that a reasonable end user would be expected to rely upon in making a financial or operational decision affecting a client, an employee, a counterparty or the Firm itself.
- **Customer-Facing System.** An AI System whose outputs are visible to, communicated to, or substantially shape communications with the Firm's clients, whether directly or via an advisor.
- **Human-in-the-Loop ("HITL").** An arrangement under which a qualified human reviews AI output before that output is acted upon or transmitted.
- **AI Governance Committee.** The standing cross-functional body responsible for overseeing AI risk across the Firm, chaired by the Chief Risk Officer.

Terms not defined here take the meaning given in the Firm's Risk Taxonomy.

## 3. Roles and responsibilities

The **Business Sponsor** proposing or operating an AI System is responsible for completing the AI Risk Assessment and ensuring controls remain effective over the system's lifecycle.

The **AI Governance Office** (Second Line) reviews all submissions, assigns the Risk Tier in accordance with §4, validates that the proposed control set meets §5 and any applicable §7 domain-specific obligations, and is the approval authority for Low and Medium tier deployments.

The **AI Governance Committee** is the approval authority for High tier deployments and for any exception under §9.

**Model Risk Management** performs independent validation of AI Systems where the System falls within the perimeter of the Firm's Model Risk Policy. The interaction between this Policy and the Model Risk Policy is described in Annex A.

## 4. Risk tier classification

Every AI System within scope must be classified into one of three Risk Tiers — Low, Medium or High — at the point of deployment review and re-confirmed at each annual review.

### 4.1 Tier criteria

The factors below shall be considered when assigning a Risk Tier. No single factor is determinative; the reviewer shall use judgment.

a. **Audience.** Whether the System's outputs are seen by, or substantially shape what is seen by, clients of the Firm. Customer-Facing Systems are typically Medium or High.
b. **Consequence of error.** The reasonably foreseeable impact on a client, the Firm or a third party of an incorrect or inappropriate output. Systems producing Consequential Recommendations are typically High where they are also Customer-Facing.
c. **Reversibility.** Whether actions taken on the basis of System output can be readily corrected without harm.
d. **Population scope.** The volume of clients or employees subject to the System over a twelve-month horizon.
e. **Regulatory sensitivity.** Whether the use case sits within a domain expressly identified in §7.
f. **FINOS risk profile.** Whether the System's intended use plausibly engages any of the operational or regulatory FINOS risks (in particular AIR-OP-014 Inadequate System Alignment, AIR-OP-016 Bias and Discrimination, AIR-OP-017 Lack of Explainability, AIR-OP-018 Model Overreach, AIR-RC-022 Regulatory Compliance and Oversight). Material engagement is a factor in favour of a higher tier.

### 4.2 Default classifications

Systems whose outputs are purely back-office and have no effect on client outcomes are presumed Low absent factors to the contrary. Systems making Consequential Recommendations to clients are presumed High. The reviewer may depart from the presumption with documented rationale.

## 5. Minimum control requirements by tier

The minimum controls that must be in place before launch, and maintained thereafter, vary by Risk Tier. The detailed description of each control listed below is given in the Firm's AI Control Standards (Annex A); where Annex A references a FINOS mitigation, the FINOS description applies.

### 5.1 Low tier

- Documented purpose and approved Business Sponsor.
- Model card or equivalent describing inputs, outputs and intended use.
- Basic monitoring of usage and material incidents.
- Inclusion in the AI Deployment Register.

### 5.2 Medium tier

All Low tier controls, plus:

- Pre-launch internal review of representative outputs (per AIR-PREV-005).
- A defined HITL arrangement consistent with §8.
- A monitoring plan submitted to the AI Governance Office prior to launch and reviewed semi-annually thereafter.
- Recorded training data provenance and a documented basis for fitness-for-purpose (per AIR-PREV-006).
- Domain-specific obligation mapping per §7 where applicable.

### 5.3 High tier

All Medium tier controls, plus:

- Independent validation by Model Risk Management.
- Pre-launch red-team exercise covering reasonably foreseeable misuse and failure modes.
- An incident response runbook approved by the AI Governance Committee.
- Quarterly red-team rotation post-launch, or an alternative continuous evaluation arrangement that the AI Governance Office determines provides equivalent assurance.
- Citations and source traceability on Customer-Facing outputs (per AIR-DET-013).
- AI Governance Committee approval prior to deployment.

### 5.5 Stress-testing adequacy for risk-advisory systems

Where an AI System is used to inform risk-management decisions — running scenarios, computing exposures, proposing hedges, or escalating breaches — the Firm shall operate the System against a documented standing scenario set covering the desks' risk profile to a standard of substantive adequacy. The standing set shall, at minimum, cover tail events, correlation breakdown and liquidity stress for the desks served, and shall be reviewed at least annually by a party independent of the desk.

Ad-hoc scenarios constructed or selected outside the standing set are supplementary to it, not a substitute for it. Each ad-hoc scenario shall be reviewed by an independent qualified party before its results inform any consequential action. A scenario methodology trail shall be maintained for every scenario the System runs, recording what selected it, what data and calibration informed it, and the model version under which it was reasoned about.

### 5.6 Concentration limit ceiling for risk-advisory systems

A risk-advisory AI System shall operate against a book whose desk-level concentration limits, by counterparty, do not exceed twenty-five per cent of the desk's gross notional. The desk may set tighter limits; it may not set looser ones without prior approval from the AI Governance Committee on the basis of a documented business case. The limit applies to every desk the System serves and shall be recorded in the desk's risk-appetite statement.

## 6. AI deployment lifecycle

All in-scope AI Systems shall follow the deployment lifecycle set out below. The lifecycle applies to net-new deployments, to materially changed existing deployments, and to vendor or model substitutions affecting an in-flight deployment.

The Business Sponsor initiates a submission by completing the standard AI Risk Assessment Form, including a proposed Risk Tier. The submission is assessed by the AI Governance Office, which confirms or revises the Tier, identifies any gaps against §5 and §7, and either approves (Low/Medium), refers to the AI Governance Committee (High), or returns the submission with specified conditions. Conditional approvals must specify the conditions and the timeframe in which they are to be met.

Decisions and conditions are recorded in the **AI Deployment Register**. Conditions imposed in prior approvals shall be considered as precedent when reviewing comparable subsequent deployments, and shall be carried forward unless materially differing circumstances are documented.

## 7. Domain-specific obligations

Where an AI System is used in a domain identified below, the obligations of that domain apply in addition to the controls in §5.

### 7.1 Advice and recommendations to clients

AI Systems that produce or shape recommendations on which clients may rely shall be designed and operated consistently with the Firm's obligations under Regulation Best Interest, including a documented fee-comparison surface in the recommendation workflow. The reviewer shall confirm that this and other applicable Reg BI obligations have been addressed, having regard to AIR-OP-018 (Model Overreach / Expanded Use), in particular the example of LLMs designed for client communications being repurposed for investment recommendations.

### 7.2 Credit and lending decisions

AI Systems used in credit or lending shall comply with the Firm's Fair Lending Policy and shall address AIR-OP-016 (Bias and Discrimination).

### 7.3 Privacy and data protection

AI Systems processing personal data shall comply with the Firm's Privacy Policy and applicable data protection regulation.

## 8. Human-in-the-Loop

Where a Risk Tier requires a HITL arrangement, the arrangement shall be described in the submission. A qualified human shall review each AI output before that output is acted upon. The HITL design shall be documented in sufficient detail that the AI Governance Office can determine whether the human reviewer is in a position to make an informed judgment, including the time available for review and the information presented at the point of review.

For the avoidance of doubt, an arrangement in which the AI output is the operational default and the human role consists of choosing not to override does not, in itself, constitute HITL for the purposes of this Policy.

## 9. Exceptions and escalations

Departures from the requirements of §5 may be approved in writing by the AI Governance Committee on the basis of a documented business case, a description of mitigating controls, and a defined re-review date. Exceptions shall be recorded in the AI Deployment Register and reported quarterly to the Operating Risk Committee.

## 10. Monitoring and oversight

All in-scope AI Systems shall be subject to ongoing monitoring proportionate to their Risk Tier. Monitoring is a baseline requirement for production AI Systems. Monitoring requirements may be deferred at the discretion of the AI Governance Office for Low tier Systems with limited population scope, with quarterly review thereafter to confirm continued fitness.

Material incidents shall be reported promptly to the AI Governance Office and, for Medium and High tier Systems, to the AI Governance Committee at the next scheduled meeting.

### 10.3 Material breach incidents

Where a stress scenario shows simulated exposure breaching the Firm's defined risk appetite — by P&L, VaR or any other documented threshold — the breach shall be classified by the desk and reported to the Risk Committee within the office-reporting clock applicable to material incidents. Classification shall identify whether the breach is an exceedance of a documented threshold, the realisation of a tail-scenario outcome, or a correlation breakdown in which a hedge failed to hedge. Breaches identified by an AI-assisted risk-advisory System are reportable on the same clock as breaches identified by other means.

## 11. Review

This Policy shall be reviewed annually by the AI Governance Office and approved by the Operating Risk Committee. Interim revisions may be issued by the AI Governance Office to address regulatory change, supported by a written rationale.

---

**Annex A — AI Control Standards.** Reserved. [To be populated in the next revision.]
