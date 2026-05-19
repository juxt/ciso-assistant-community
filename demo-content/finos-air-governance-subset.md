# FINOS AI Readiness Governance Framework — Risk Catalogue (Demo Subset)

This document reproduces six risk entries from the **FINOS AI Readiness (AIR) Governance Framework**, v2 (October 2025), maintained by the Fintech Open Source Foundation. The full framework is published at <https://air-governance-framework.finos.org/>.

**Licence.** The FINOS AIR Governance Framework is distributed under the [Creative Commons Attribution 4.0 International Licence (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). Attribution is preserved per the terms of the licence. The content below is reproduced for ingestion into a demo CISO Assistant instance and is not modified except for collation into a single file.

The subset comprises:

- AIR-OP-004 — Hallucination and Inaccurate Outputs
- AIR-OP-014 — Inadequate System Alignment
- AIR-OP-016 — Bias and Discrimination
- AIR-OP-017 — Lack of Explainability
- AIR-OP-018 — Model Overreach / Expanded Use
- AIR-RC-022 — Regulatory Compliance and Oversight

---

## AIR-OP-004: Hallucination and Inaccurate Outputs

### Summary

LLMs produce confident but incorrect information due to reliance on statistical patterns rather than factual understanding. Retrieval-Augmented Generation can reduce but not eliminate hallucinations. No guaranteed method exists to constrain outputs to verified facts, making this an unresolved challenge.

### Description

LLM hallucinations occur when models generate plausible but factually incorrect or nonsensical information. This happens because models synthesize text based on training data patterns rather than true understanding or access to verified information.

Techniques like Retrieval Augmented Generation (RAG) minimize hallucination risk by providing factual context directly. However, model responses blend prompt-provided information with retained internal knowledge. No reliable method ensures responses stay restricted to provided facts, so RAG applications still hallucinate.

Currently, no reliable method exists for removing hallucinations; this remains an active research area.

### Contributing Factors

- **Lack of Ground Truth:** Models cannot distinguish between accurate and inaccurate training data.
- **Ambiguous or Incomplete Prompts:** Unclear input prompts increase likelihood of fabricated details.
- **Confidence Mismatch:** LLMs present hallucinated information with high fluency, making inaccuracies difficult to detect.
- **Fine-Tuning or Prompt Bias:** Instructions meant to improve helpfulness or creativity may increase unsupported statements.

### Example Financial Services Hallucinations

1. **Fabricated Financial News or Analysis:** An LLM market analysis tool incorrectly reports a fictional bank's missed earnings based on a non-existent press release, causing temporary stock price decline.
2. **Incorrect Regulatory Interpretations:** A compliance chatbot confidently states a transaction type is exempt from AML reporting, citing a non-existent Bank Secrecy Act clause.
3. **Hallucinated Customer Information:** A banking chatbot generates a plausible but entirely fictional transaction in response to customer account queries.
4. **False Information in Loan Adjudication:** An AI loan processing system fabricates a prior bankruptcy, leading to unfair loan denial.
5. **Generating Flawed Code for Financial Models:** An LLM generates Python code for Value at Risk calculation using non-existent functions from financial libraries, causing calculation failures.

### Related Risks

- RI-14: Inadequate System Alignment
- RI-6: Non-Deterministic Behaviour
- RI-19: Data Quality and Drift

### Key Mitigations

- AIR-DET-013: Providing Citations and Source Traceability for AI-Generated Information
- AIR-DET-015: Using Large Language Models for Automated Evaluation (LLM-as-a-Judge)
- AIR-PREV-005: System Acceptance Testing
- AIR-PREV-006: Data Quality & Classification/Sensitivity

### Regulatory References

- OWASP LLM Top 10: LLM09:2025 Misinformation
- OWASP ML Top 10: ML09:2023 Output Integrity Attack
- FFIEC: DAM Risk Management; AUD Risk Assessment; MGT Risk Management
- EU AI Act: Articles 15 (Accuracy, Robustness), 13 (Transparency), 9 (Risk Management)
- NIST AI 600-1: Sections 2.2 (Confabulation), 2.8 (Information Integrity)

---

## AIR-OP-014: Inadequate System Alignment

### Summary

LLM-powered RAG systems risk generating responses that diverge from their intended purpose, potentially producing inaccurate financial advice, biased recommendations, or inappropriate tone. These misalignments occur when systems prioritize fluency over accuracy or fail to respect compliance constraints, creating significant regulatory and customer harm risks in financial services contexts.

### Description

Retrieval-Augmented Generation systems in financial services must balance retrieved institutional knowledge with LLM capabilities while navigating regulatory requirements. This complexity creates multiple misalignment vectors that can result in coherent-sounding but inaccurate responses.

#### Key Misalignment Patterns

- **Retrieval-Response Disconnect**: Systems generate confident answers contradicting retrieved documents. A loan eligibility query might omit critical regulatory exceptions, creating compliance violations.
- **Context Window Limitations**: Important regulatory caveats or disclaimers get truncated when documents exceed the LLM's capacity, resulting in incomplete guidance appearing authoritative.
- **Domain Knowledge Gaps**: When retrieved content doesn't fully address queries, systems fill gaps with plausible-sounding but incorrect information from training data, blending accurate institutional knowledge with inaccurate general knowledge.
- **Scope Boundary Violations**: Systems provide advice exceeding authorized scope — for instance, delivering investment guidance when restricted to account information only.
- **Prompt Injection via Retrieved Content**: Malicious or poorly formatted knowledge base content can manipulate responses through indirect injection attacks.
- **Tone and Compliance Mismatches**: Systems adopt inappropriate certainty levels or language formality for financial communications.

#### Financial Impact

- **Regulatory Violations**: Incomplete or incorrect guidance may omit required disclosures or provide outdated information.
- **Customer Liability**: Incorrect advice appearing authoritative due to confident tone creates legal exposure.
- **Operational Risk**: Misaligned internal-facing systems cause staff procedural errors that scale organizationally.
- **Trust Erosion**: Inconsistent responses undermine confidence in AI-assisted financial services.

#### Alignment Drift Factors

- Knowledge base evolution changes retrieval patterns and may expose conflicting information.
- Foundation model updates alter response patterns despite identical retrieved content.
- Poor document hygiene introduces biased, outdated, or incorrect information.
- Query evolution reveals edge cases not addressed in initial testing.

### Related Risks

- RI-4: Hallucination and Inaccurate Outputs
- RI-6: Non-Deterministic Behaviour

### Key Mitigations

- AIR-DET-011: Human Feedback Loop for AI Systems
- AIR-DET-015: Using Large Language Models for Automated Evaluation
- AIR-DET-004: AI System Observability
- AIR-PREV-005: System Acceptance Testing

### Regulatory References

- OWASP LLM Top 10: LLM07:2025 System Prompt Leakage
- OWASP ML Top 10: ML08:2023 Model Skewing
- FFIEC: Risk Management of Development, Acquisition, and Maintenance; Development; Risk Assessment and Risk-Based Auditing
- EU AI Act: Prohibited AI Practices (Article 5); Risk Management System (Article 9); Human Oversight (Article 14)
- NIST SP 800-53r5: SA-11 Developer Testing and Evaluation; RA-3 Risk Assessment; CA-6 Authorization

---

## AIR-OP-016: Bias and Discrimination

### Summary

AI systems can systematically disadvantage protected groups through biased training data, flawed design, or proxy variables that correlate with sensitive characteristics. In financial services, this manifests through discriminatory credit decisions, unfair fraud detection, or biased customer support, risking regulatory penalties and reputational harm.

### Description

Financial institutions face severe consequences from AI-driven bias.

#### Key Manifestations

- **Biased Credit Scoring** — Models trained on historical lending data may perpetuate past discriminatory patterns, disadvantaging minority applicants or those from underserved communities despite comparable financial behavior.
- **Unfair Loan Approval Recommendations** — LLM-powered decision support tools may systematically recommend rejection for certain profiles (single parents, freelancers), creating disparate impact violations.
- **Discriminatory Insurance Premium Calculations** — Algorithms using occupation, location, or education correlate with socioeconomic status or race, potentially inflating premiums without justified risk basis.
- **Disparate Marketing Practices** — Personalized recommendation systems may exclude certain users from financial product offers, perpetuating wealth inequality through unequal access.
- **Customer Service Disparities** — Chatbots may deliver lower-quality responses based on linguistic patterns or perceived socioeconomic indicators.

### Root Causes

- **Data Bias** — Historical datasets reflecting societal biases or underrepresenting populations.
- **Algorithmic Bias** — Model architecture and feature selection inadvertently amplifying disparities.
- **Proxy Discrimination** — Neutral variables (postal codes, transaction types) serving as protected characteristic proxies.
- **Feedback Loops** — Biased outputs reintroduced into training cycles, creating self-reinforcing patterns.

### Implications

- Regulatory sanctions, fines, and legal liability.
- Erosion of customer trust and brand reputation.
- Direct customer financial harm through exclusion or unfair treatment.
- Suboptimal business decisions and operational risk.

### Related Risks

- RI-19: Data Quality and Drift
- RI-22: Regulatory Compliance and Oversight

### Key Mitigations

- AIR-DET-011: Human Feedback Loop for AI Systems
- AIR-DET-015: LLM-as-a-Judge Automated Evaluation
- AIR-PREV-005: System Acceptance Testing
- AIR-PREV-006: Data Quality & Classification/Sensitivity

### Regulatory References

- FFIEC: Risk Management, Development/Acquisition/Maintenance, Risk-Based Auditing
- EU AI Act: Prohibited practices, risk management, data governance, human oversight, rights impact assessments
- NIST AI 600-1: Harmful Bias and Homogenization

---

## AIR-OP-017: Lack of Explainability

### Summary

Complex AI systems, especially those using foundation models, frequently operate without sufficient transparency. This "black box" problem prevents firms from clearly explaining decisions to regulators, stakeholders, or customers, undermining trust and compliance efforts. Undetected errors and biases can proliferate when decision-making rationales remain opaque.

### Description

Deploying sophisticated AI systems presents a fundamental challenge: understanding and interpreting their decision-making processes. These models typically function as impenetrable systems that generate outputs without traceable reasoning paths.

**Stakeholder Communication Challenges.** Organizations struggle to articulate why their AI systems reach particular conclusions. Whether approving loans, recommending investments, or flagging fraud, the inability to justify outcomes to customers, regulators, and internal oversight bodies creates friction and invites regulatory attention while eroding public confidence.

**Hidden Risks and Vulnerabilities.** The opaque nature of these systems can mask underlying problems — latent errors, incorporated biases, or security weaknesses — that weren't apparent during development phases. This obscurity makes it difficult to rigorously assess whether models operate reliably and soundly, a cornerstone of financial services risk management.

**Deployment and Adaptation Concerns.** Without comprehending how models generate conclusions, organizations risk deploying systems they don't genuinely understand. This gap can result in unsuitable deployments, unidentified failures under specific conditions, or difficulties recalibrating systems as market conditions shift or regulations evolve. Conventional validation approaches often prove inadequate for these non-linear, complex models.

**Governance Imperatives.** Given that transparency and accountability define financial services, explainability deficiencies directly compromise these principles. Organizations face operational, reputational, and compliance exposure without establishing rigorous governance and oversight frameworks.

### Related Risks

- RI-22: Regulatory Compliance and Oversight
- RI-16: Bias and Discrimination
- RI-18: Model Overreach / Expanded Use

### Key Mitigations

- AIR-DET-013: Providing Citations and Source Traceability for AI-Generated Information

### Regulatory References

**FFIEC:**
- MGT: II Risk Management
- AUD: Risk Assessment and Risk-Based Auditing
- DAM: III Risk Management of Development, Acquisition, and Maintenance

**EU AI Act:**
- Article 13: Transparency and Provision of Information to Deployers
- Article 14: Human Oversight
- Article 50: Transparency Obligations for Providers and Deployers of Certain AI Systems
- Article 86: Right to Explanation of Individual Decision-Making

---

## AIR-OP-018: Model Overreach / Expanded Use

### Summary

Model overreach occurs when AI systems are used beyond their intended purpose, often due to overconfidence in their capabilities. This misuse risks poor-quality outputs, non-compliance, and regulatory breaches when users apply AI to high-stakes tasks without proper validation.

### Description

Generative AI's impressive capabilities can create false confidence in reliability. Users may repurpose models — such as applying a marketing email drafter to provide legal advice — without validation. This perception gap poses significant risk, particularly when:

- AI operates in domains requiring specialized expertise or regulatory oversight
- Users anthropomorphize AI, attributing human-like understanding and expertise
- Misplaced trust leads to accepting outputs without critical review
- Errors or biases go undetected, potentially causing financial losses or reputational harm

Overreliance without understanding AI's boundaries and failure points can cause operational mistakes and flawed decision-making and trigger regulatory compliance breaches.

### Examples

- **Investment Advice Misuse:** An LLM designed for client communications is repurposed for investment recommendations. Without formal financial regulation training, it may suggest unsuitable strategies, breaching conduct rules.
- **Inappropriate Legal Applications:** A summarization tool is misapplied to draft loan agreements or regulatory filings, potentially omitting critical clauses and exposing the organization to legal risk.
- **Anthropomorphic Trust in Advisory:** Relationship managers over-rely on AI-generated recommendations in client meetings, assuming authoritative accuracy, potentially delivering inaccurate guidance.

### Related Risks

- RI-10: Prompt Injection
- RI-17: Lack of Explainability
- RI-22: Regulatory Compliance and Oversight

### Key Mitigations

- AIR-PREV-017: AI Firewall Implementation and Management
- AIR-PREV-018: Agent Authority Least Privilege Framework
- AIR-PREV-003: User/App/Model Firewalling/Filtering
- AIR-DET-004: AI System Observability

### Regulatory References

- OWASP: LLM06:2025 Excessive Agency
- FFIEC: Governance, Risk Management, Risk Assessment and Risk-Based Auditing
- EU AI Act: Classification Rules for High-Risk AI Systems (Article 6), Human Oversight (Article 14), Deployer Obligations (Article 26)

---

## AIR-RC-022: Regulatory Compliance and Oversight

### Summary

Financial services AI systems must meet identical regulatory standards as human-led processes regarding suitability, fairness, record-keeping, and marketing. Poor AI governance creates non-compliance risks, particularly in advisory, credit, or trading contexts. Emerging regulations like the EU AI Act impose heightened transparency, accountability, and risk management requirements, with violations risking significant penalties.

### Description

The financial services industry operates under comprehensive regulatory frameworks that apply equally to AI-generated decisions and content. Regulators have established that AI outputs must satisfy the same compliance standards as human professional work, whether deployed for advice, marketing, decisions, or communications.

**Key regulatory obligations directly affecting AI outputs:**

- **Financial Advice:** Requires KYC completion, suitability assessments, and accuracy compliance under MiFID II and SEC regulations.
- **Marketing Communications:** Must be fair, clear, accurate, and not misleading under consumer protection statutes.
- **Record-Keeping:** AI interactions, recommendations, and outputs must be documented per MiFID II, SEC Rule 17a-4, and FINRA standards.

**Jurisdiction-specific governance frameworks:**

- **UK and EU Model Risk Management.** The PRA's SS1/23 applies model risk management (development, validation, governance, ongoing monitoring) to generative and agentic AI systems. The EBA's machine learning guidelines for AML/CFT remain applicable. Critical decisions — credit underwriting, capital calculations, algorithmic trading, fraud detection, AML/CFT monitoring — require rigorous model governance with comprehensive validation, performance monitoring, documentation, and human oversight.
- **US Model Risk Management.** As of April 17, 2026, the OCC, Federal Reserve, and FDIC revised interagency guidance (SR 11-7 / OCC Bulletin 2026-13) to explicitly exclude generative and agentic AI from traditional model risk management scope. This revision rescinded OCC Bulletin 1997-24 and the 2021 interagency BSA/AML statement, applying primarily to institutions above approximately $30 billion in assets. SR 11-7 remains relevant for traditional quantitative models (VaR, IRB PD, logistic regression scoring). A forthcoming Request for Information will determine future regulatory coverage for GenAI and agentic systems.
- **Supervision and Accountability.** Institutions bear responsibility for adequate AI system oversight regardless of regulatory framework. Inadequate supervision mechanisms, unclear accountability structures for AI decisions, and insufficient staff understanding of AI capabilities and limitations create direct non-compliance exposure.

The US carve-out does not establish an unregulated zone. While removing the traditional MRM peg, oversight obligations shift to broader authorities: fair-lending law (ECOA/Regulation B), FCRA adverse-action requirements, third-party risk management under FFIEC standards, SEC anti-fraud authority over AI disclosures, NYDFS Part 500, and state AI legislation including the Colorado AI Act and California DFPI requirements. Transatlantic regulatory divergence will likely expand pending the US RFI conclusion.

**Evolving regulatory landscape.**

The EU AI Act designates certain financial AI applications (credit scoring, fraud detection) as high-risk, triggering additional transparency, fairness, robustness, and human oversight obligations. Article 27 mandates that deployers — including financial institutions — conduct Fundamental Rights Impact Assessments before high-risk AI deployment, evaluating potential impacts on individual rights and freedoms. Inadequate AI system supervision and documentation exposes firms to operational failure, regulatory fines, operational restrictions, and legal liability.

Responsible AI principles — fairness, transparency, accountability, human oversight — increasingly form regulatory requirements rather than remaining aspirational ethical goals. Institutions should address these elements to the extent mandated by applicable regulations and supervisory expectations within their jurisdictions.

Successful compliance requires alignment of AI deployment with existing rules while anticipating future obligations. Proactive governance, comprehensive auditability, and cross-functional coordination among compliance, technology, and legal functions are essential.

### Related Risks

- RI-16: Bias and Discrimination
- RI-17: Lack of Explainability
- RI-18: Model Overreach / Expanded Use

### Key Mitigations

- AIR-DET-013: Providing Citations and Source Traceability for AI-Generated Information
- AIR-PREV-014: Encryption of AI Data at Rest
- AIR-DET-016: Preserving Source Data Access Controls in AI Systems
- AIR-DET-021: Agent Decision Audit and Explainability
- AIR-PREV-005: System Acceptance Testing
- AIR-PREV-006: Data Quality & Classification/Sensitivity
- AIR-PREV-007: Legal and Contractual Frameworks for AI Systems

### Regulatory References

**FFIEC:**
- MGT: I Governance
- MGT: II Risk Management
- AUD: Internal Audit Program
- AUD: Risk Assessment and Risk-Based Auditing

**EU AI Act:**
- III.S2.A8: Compliance with the Requirements
- III.S2.A10: Data and Data Governance
- III.S3.A16: Obligations of Providers of High-Risk AI Systems
- III.S3.A21: Cooperation with Competent Authorities
- III.S3.A27: Fundamental Rights Impact Assessment for High-Risk AI Systems

**NIST AI 600-1:**
- 2.9. Information Security
