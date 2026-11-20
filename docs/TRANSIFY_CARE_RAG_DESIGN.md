# Clinical RAG Architecture & Citation Design: Transify Care
**Module**: `src/care/clinical_rag.py`  
**Standard**: Verifiable Clinical Provenance & Zero Hallucination

---

## 1. Rationale for Grounded Clinical Retrieval

Generic Large Language Models (LLMs) and unconstrained generative agents are notoriously prone to medical confabulation, inventing plausible-sounding but lethal drug dosages, non-existent contraindications, or downplaying acute emergencies.

In low-resource healthcare ecosystems, autonomous generative clinical advice is unacceptable. Transify Care's Clinical Retrieval-Augmented Generation (RAG) architecture follows a strict, verifiable design:

1. **Approved Source Corpus Only**: Evidence is retrieved exclusively from approved, peer-reviewed clinical protocols (WHO, DGHS Bangladesh, NINS).
2. **Exact Excerpt Retrieval**: Chunks are stored with verbatim clinical text, publisher, version, and official publication URL.
3. **Structured Citation Payload**: Every retrieved chunk returned to patient and doctor retains its complete metadata envelope.
4. **Explicit No-Evidence Fallback**: When queries do not match clinical protocols, the system explicitly returns `evidence_found: False` with a transparent disclaimer rather than improvising.

---

## 2. Seeded Protocol Knowledge Base

### Source 1: WHO Integrated Primary Care Guidance
- **Title**: *WHO Integrated Management of Adolescent and Adult Illness (IMAI): Primary and Emergency Triage*
- **Publisher**: World Health Organization (WHO)
- **Version**: 2020.2 Guidelines
- **Indexed Chunks**:
  - `WHO-IMAI-CHEST-01`: Acute chest pain red flags (substernal pressure, diaphoresis, left arm radiation) indicating acute coronary syndrome.
  - `WHO-IMAI-RESP-01`: Severe respiratory distress (stridor, cyanosis, inability to speak complete sentences).
  - `WHO-IMAI-ABDO-01`: Acute abdomen red flags (guarding, rebound tenderness, progressive vomiting).

### Source 2: DGHS Bangladesh National Dengue Guidelines
- **Title**: *National Guidelines for Clinical Management of Dengue Syndrome in Bangladesh (5th Edition)*
- **Publisher**: Directorate General of Health Services (DGHS), Ministry of Health & Family Welfare, Bangladesh
- **Version**: 2024.1 National Protocol
- **Indexed Chunks**:
  - `DGHS-DENGUE-WARN-01`: Febrile warning signs: high fever (103°F+) accompanied by persistent vomiting (>24h), severe abdominal tenderness, lethargy, or mucosal bleeding.
  - `DGHS-DENGUE-MILD-02`: Classic dengue fever without warning signs: supportive oral hydration, rest, paracetamol; avoid NSAIDs (ibuprofen, aspirin).

### Source 3: NINS National Stroke Emergency Protocol
- **Title**: *National Clinical Protocol for Acute Ischemic Stroke and Hemorrhagic Triage*
- **Publisher**: National Institute of Neurosciences & Hospital (NINS), Dhaka, Bangladesh
- **Version**: 2021.1 Clinical Protocol
- **Indexed Chunks**:
  - `NINS-STROKE-EMERG-01`: Fast recognition of focal neurological deficits: sudden unilateral weakness, facial asymmetry, slurred speech. Requires immediate transport to stroke-ready center within 4.5 hours.

---

## 3. Retrieval Algorithm & Schema

The retriever operates a multi-field weighted scoring mechanism:
$$\text{Score} = w_{\text{title}} \cdot \mathbb{I}(\text{title}) + w_{\text{keywords}} \cdot \sum \text{tf-idf} + w_{\text{tags}} \cdot \text{jaccard}$$

Returned Schema:
```json
{
  "query": "high fever and severe persistent stomach pain",
  "evidence_found": true,
  "match_count": 1,
  "citations": [
    {
      "source_id": 2,
      "source_title": "National Guidelines for Clinical Management of Dengue Syndrome in Bangladesh (5th Edition)",
      "publisher": "Directorate General of Health Services (DGHS), Bangladesh",
      "version": "2024.1",
      "url": "https://dghs.gov.bd/index.php/en/dengue-guidelines",
      "condition": "Dengue Fever with Warning Signs",
      "excerpt": "Patients with high fever and warning signs (severe abdominal pain, persistent vomiting, mucosal bleed, lethargy) require immediate same-day hospital admission and serial hematocrit monitoring.",
      "score": 3.8
    }
  ]
}
```
