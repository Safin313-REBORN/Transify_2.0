# Clinical Evidence Lookup Architecture & Provenance: Transify Care
**Module**: `src/care/clinical_rag.py`  
**Standard**: Verifiable Clinical Provenance & Prototype Evidence Retrieval
**Status**: Clinical Evidence Lookup Prototype (Keyword-Based)

---

## 1. Rationale for Grounded Clinical Retrieval

Generic Large Language Models (LLMs) and unconstrained generative agents are prone to medical confabulation, inventing plausible-sounding but lethal drug dosages, non-existent contraindications, or downplaying acute emergencies.

In primary care intake, autonomous generative clinical advice is inappropriate. The current Transify Care implementation provides a deterministic, keyword-based **Clinical Evidence Lookup Prototype** over curated guidelines, rather than an unconstrained generative LLM or vector RAG:

1. **Approved Protocol Passages**: Excerpts are drawn from established public health protocols (WHO, DGHS Bangladesh 5th Edition 2023, NINS).
2. **Review Status**: Seeded sources are tagged with `review_status: "PENDING_REVIEW"` and `reviewed_by: "Pending Formal Review by Qualified Healthcare Authority"` until formal institutional validation is completed.
3. **Exact Excerpt Retrieval**: Passages are stored verbatim with publisher, edition, and official source URLs.
4. **Transparent Prototype Scope**: The WHO Interagency Integrated Triage Tool (IITT) / IMAI protocol is facility-based; its adaptation for remote digital intake is explicitly noted as a prototype requiring local clinical validation.
5. **Explicit No-Evidence Fallback**: When queries do not match indexed protocols, the system explicitly returns `evidence_found: False` with a transparent disclaimer rather than improvising.

---

## 2. Seeded Protocol Knowledge Base

### Source 1: WHO Integrated Primary Care Guidance (Prototype Remote Adaptation)
- **Title**: *WHO Integrated Management of Adolescent and Adult Illness (IMAI): Emergency and First-Line Primary Care Triage Protocols*
- **Publisher**: World Health Organization (WHO)
- **Version**: 2020.2 Guidelines
- **Review Status**: PENDING_REVIEW (Facility-based triage adapted as research prototype; requires local validation)
- **Indexed Chunks**:
  - `WHO-IMAI-CHEST-01`: Acute chest pain red flags (substernal pressure, diaphoresis, left arm radiation) indicating potential acute coronary syndrome.
  - `WHO-IMAI-RESP-01`: Severe respiratory distress (stridor, cyanosis, inability to speak complete sentences).
  - `WHO-IMAI-ABDO-01`: Acute abdomen red flags (guarding, rebound tenderness, progressive vomiting).

### Source 2: DGHS Bangladesh National Dengue Guidelines
- **Title**: *National Guidelines for Clinical Management of Dengue Syndrome in Bangladesh (5th Edition, 2023)*
- **Publisher**: Directorate General of Health Services (DGHS), Ministry of Health & Family Welfare, Government of the People's Republic of Bangladesh
- **Version**: 5th Edition (2023)
- **Review Status**: PENDING_REVIEW
- **Indexed Chunks**:
  - `DGHS-DENGUE-WARN-01`: Febrile warning signs: high fever (103°F+) accompanied by persistent vomiting (>24h), severe abdominal tenderness, lethargy, or mucosal bleeding. Advises prompt physical evaluation and hematocrit monitoring.
  - `DGHS-DENGUE-MILD-02`: Classic dengue fever without warning signs: supportive oral hydration, rest, paracetamol; avoid NSAIDs (ibuprofen, aspirin).

### Source 3: NINS National Stroke Emergency Protocol
- **Title**: *National Clinical Protocol for Acute Ischemic Stroke and Hemorrhagic Triage*
- **Publisher**: National Institute of Neurosciences & Hospital (NINS), Dhaka, Bangladesh
- **Version**: 2021.1 Clinical Guidance
- **Review Status**: PENDING_REVIEW
- **Indexed Chunks**:
  - `NINS-STROKE-EMERG-01`: Recognition of focal neurological deficits: sudden unilateral weakness, facial asymmetry, slurred speech. Advises immediate transport to stroke-ready center within 4.5 hours.

---

## 3. Retrieval Algorithm & Schema

The retriever operates a deterministic multi-field weighted keyword scoring mechanism over indexed condition titles, tags, and protocol text:
$$\text{Score} = w_{\text{title}} \cdot \mathbb{I}(\text{title}) + w_{\text{keywords}} \cdot \text{count}(\text{matches}) + w_{\text{tags}} \cdot \text{jaccard}$$

Returned Schema:
```json
{
  "query": "high fever and severe persistent stomach pain",
  "evidence_found": true,
  "match_count": 1,
  "citations": [
    {
      "source_id": 2,
      "source_title": "National Guidelines for Clinical Management of Dengue Syndrome in Bangladesh (5th Edition, 2023)",
      "publisher": "Directorate General of Health Services (DGHS), Ministry of Health and Family Welfare, Government of the People's Republic of Bangladesh",
      "version": "5th Edition (2023)",
      "review_status": "PENDING_REVIEW",
      "reviewed_by": "Pending Formal Review by Qualified Healthcare Authority",
      "url": "https://dghs.gov.bd/index.php/en/dengue-guidelines",
      "condition": "Dengue Fever with Warning Signs",
      "excerpt": "Patients with high fever and warning signs (severe abdominal pain, persistent vomiting, mucosal bleed, lethargy) require immediate same-day hospital admission and serial hematocrit monitoring.",
      "score": 3.8
    }
  ]
}
```
