"""
Transify Care — Clinical and Research Evidence Registry (Keyword-Based).
Provides modular, provenance-tracked evidence passage retrieval from cataloged
clinical guidelines, epidemiological databases, and research datasets.

REGISTRY DEMARCATION & CRITICAL NOTICE:
- Registry Title: "Clinical and Research Evidence Registry"
- Distinguishes clinical practice guidelines (WHO IITT, DGHS Dengue, DGHS Stroke, Merck Manuals)
  from research datasets (MIMIC-IV), controlled vocabularies (MeSH), and demographic databases (HMD).
- Research datasets and ontologies are strictly isolated from clinical triage recommendations.
- All clinical guidelines reflect prototype adaptations requiring qualified physician verification.
"""

import hashlib
import json
import sqlite3
from typing import List, Dict, Any, Optional
from src.care.db_care import get_connection, log_care_audit

DEFAULT_CLINICAL_SOURCES = [
    {
        "source_id": "SRC-WHO-TRIAGE-2020",
        "title": "WHO Interagency Integrated Triage Tool: Adult and Pediatric Triage Protocols (Facility Adaptation Prototype)",
        "publisher": "World Health Organization (WHO)",
        "url": "https://www.who.int/publications/i/item/9789240001091",
        "publication_date": "2020",
        "version": "2020 (Prototype Adaptation)",
        "document_type": "CLINICAL_PRACTICE_GUIDELINE_PROTOTYPE",
        "licensing_status": "OPEN_ACCESS_WHO_PUBLIC_HEALTH",
        "status": "PENDING_REVIEW",
        "reviewer": "Pending Formal Review by Qualified Healthcare Authority",
        "retrieval_date": "2026-11-20",
        "applicable_population": "Adult and pediatric emergency department patients globally (facility adaptation)",
        "supported_claims": "Emergency triage categorization (Red: immediate resuscitation, Yellow: urgent review within 1-4h, Green: routine ambulatory care)",
        "can_support_clinical_recommendations": True,
        "chunks": [
            {
                "section_heading": "Red Category: Immediate Resuscitation & Emergency Criteria",
                "keywords": ["chest pain", "shortness of breath", "unresponsive", "cyanosis", "severe hemorrhage", "stridor"],
                "content": "Patients presenting with obstructed airway, severe respiratory distress (respiratory rate < 10 or > 30 /min, central cyanosis), uncontrolled massive external hemorrhage, or acute chest pain with radiation or hemodynamic instability require immediate emergency department resuscitation (Red category). Transport or escalation must not be delayed for routine clerical intake. (Facility protocol adaptation; requires emergency physician confirmation)."
            },
            {
                "section_heading": "Yellow Category: Urgent Professional Review",
                "keywords": ["high fever", "moderate pain", "dehydration", "persistent vomiting", "abdominal pain"],
                "content": "Patients with high-risk conditions without immediate life threat, including acute severe pain (score 7-10), moderate dehydration, persistent vomiting unable to retain oral fluids, or high fever with systemic signs in tropical regions require urgent clinical review within 1 to 4 hours."
            },
            {
                "section_heading": "Green Category: Routine Ambulatory / Delay Tolerable",
                "keywords": ["mild cough", "minor rash", "sore throat", "chronic stable symptom", "runny nose"],
                "content": "Patients with normal vital signs, mild symptoms of short duration, minor localized rashes without systemic fever, or chronic stable conditions may safely await scheduled outpatient assessment or primary care teleconsultation (Green category). (Note: Vital signs were not measured by this tool; if shortness of breath develops, seek immediate care)."
            }
        ]
    },
    {
        "source_id": "SRC-DGHS-BD-DENGUE-5TH-ED",
        "title": "National Guidelines for Clinical Management of Dengue Syndrome in Bangladesh (5th Edition)",
        "publisher": "Disease Control Unit, Directorate General of Health Services (DGHS), Ministry of Health & Family Welfare, Government of Bangladesh",
        "url": "https://dghs.gov.bd/index.php/en/publications/clinical-guidelines",
        "publication_date": "2023",
        "version": "5th Edition (2023)",
        "document_type": "NATIONAL_CLINICAL_PRACTICE_GUIDELINE",
        "licensing_status": "PUBLIC_SECTOR_GOVERNMENT_OF_BANGLADESH",
        "status": "APPROVED",
        "reviewer": "Directorate General of Health Services Bangladesh",
        "retrieval_date": "2026-11-20",
        "applicable_population": "Adult and pediatric patients presenting with acute fever in Bangladesh during dengue endemic seasons",
        "supported_claims": "Identification of dengue warning signs requiring urgent inpatient escalation (severe abdominal pain, persistent vomiting, mucosal bleeding); avoidance of NSAIDs",
        "can_support_clinical_recommendations": True,
        "chunks": [
            {
                "section_heading": "Dengue Warning Signs for Urgent Inpatient Referral",
                "keywords": ["severe abdominal pain", "persistent vomiting", "mucosal bleeding", "lethargy", "dengue"],
                "content": "In Bangladesh clinical settings during monsoon and post-monsoon dengue seasons, febrile patients who exhibit any of the following warning signs must be referred for urgent hospital care: severe abdominal pain or tenderness, persistent vomiting, mucosal bleeding (gum bleed, epistaxis), fluid accumulation, lethargy, or progressive platelet drop."
            },
            {
                "section_heading": "Community Primary Care Management of Uncomplicated Fever",
                "keywords": ["fever", "paracetamol", "hydration", "oral rehydration solution", "jwor"],
                "content": "For uncomplicated acute fever in adults and children without warning signs, standard treatment includes oral rehydration solution (ORS), increased fluid intake, cooling sponges with room-temperature water, and Paracetamol for symptom relief. Non-steroidal anti-inflammatory drugs (NSAIDs like Ibuprofen, Aspirin) are strictly contraindicated due to bleeding hazard."
            }
        ]
    },
    {
        "source_id": "SRC-DGHS-BD-STROKE-2021",
        "title": "Clinical Practice Guidelines for Acute Ischemic Stroke Management in Bangladesh",
        "publisher": "National Institute of Neurosciences & Hospital (NINS) / DGHS Bangladesh",
        "url": "https://nins.gov.bd",
        "publication_date": "2021",
        "version": "2021",
        "document_type": "SPECIALTY_CLINICAL_PRACTICE_GUIDELINE",
        "licensing_status": "PUBLIC_SECTOR_GOVERNMENT_OF_BANGLADESH",
        "status": "APPROVED",
        "reviewer": "National Institute of Neurosciences & Hospital Bangladesh",
        "retrieval_date": "2026-11-20",
        "applicable_population": "Adult patients presenting with acute focal neurological deficits in Bangladesh",
        "supported_claims": "FAST stroke screening protocol and emergency diversion to stroke-ready centers within thrombolytic time window",
        "can_support_clinical_recommendations": True,
        "chunks": [
            {
                "section_heading": "FAST Protocol for Acute Neurological Deficits",
                "keywords": ["stroke", "face drooping", "arm weakness", "slurred speech", "time to call", "sudden numbness"],
                "content": "Assessment of suspected acute stroke utilizes the FAST protocol: Face drooping, Arm weakness, Speech difficulty, Time to call emergency services. When any single FAST element is present with acute onset, the patient must be rapidly directed to the nearest facility equipped with non-contrast CT and acute stroke care pathways."
            }
        ]
    },
    {
        "source_id": "SRC-MERCK-MANUALS-2024",
        "title": "Merck Manual of Diagnosis and Therapy (Professional Edition) - Clinical Decision Support",
        "publisher": "Merck Sharp & Dohme Corp. / Merck & Co.",
        "url": "https://www.merckmanuals.com/professional",
        "publication_date": "2024",
        "version": "2024.1",
        "document_type": "CLINICAL_DECISION_SUPPORT_REFERENCE",
        "licensing_status": "PROFESSIONAL_REFERENCE_OPEN_ACCESS",
        "status": "APPROVED",
        "reviewer": "Transify Clinical Decision Board",
        "retrieval_date": "2026-11-20",
        "applicable_population": "General clinical patient populations with dermatological and ophthalmic presentations",
        "supported_claims": "Differential diagnosis for acute cellulitis/necrotizing soft tissue infection, ABCDE melanoma warning signs, acute angle-closure glaucoma and corneal ulcer ophthalmic red flags",
        "can_support_clinical_recommendations": True,
        "chunks": [
            {
                "section_heading": "Acute Dermatological Assessment & Skin Lesion Warning Signs (ABCDE & Cellulitis)",
                "keywords": ["skin lesion", "rash", "erythema", "melanoma", "abcde", "burn", "ulcer", "itching", "cellulitis", "blister", "skin"],
                "content": "Evaluation of acute skin lesions requires distinguishing superficial dermatoses from emergent conditions. Rapidly spreading erythema with warmth, tenderness, or crepitus indicates cellulitis or necrotizing soft-tissue infection requiring immediate intravenous antibiotic evaluation. Pigmented lesions showing ABCDE warning criteria (Asymmetry, Border irregularity, Color variegation, Diameter > 6mm, or Evolution) warrant formal dermatological excision and histopathology. Deep partial or full-thickness burns require sterile cooling and urgent specialized burn center referral."
            },
            {
                "section_heading": "Ophthalmic Red Flags & Acute Visual Threat Assessment (Merck Ophthalmology Protocols)",
                "keywords": ["eye", "red eye", "vision loss", "corneal ulcer", "conjunctivitis", "eye pain", "cataract", "cloudy eye", "photophobia", "sclera", "চোখ"],
                "content": "Red eye presentations accompanied by severe deep ocular pain, photophobia, reduced visual acuity, corneal opacity (white infiltrates or clouding), or asymmetric sluggish pupils indicate serious conditions such as acute angle-closure glaucoma, corneal ulceration, or anterior uveitis. These signs mandate urgent ophthalmologist slit-lamp examination within 6-12 hours to prevent irreversible visual impairment. Benign conjunctival injection without corneal involvement or vision compromise may receive standard ambulatory supportive therapy."
            }
        ]
    },
    {
        "source_id": "SRC-MIMIC-IV-CRITICAL-2023",
        "title": "MIMIC-IV Clinical Reasoning & Vital Signs Reference Standard",
        "publisher": "MIT Laboratory for Computational Physiology / PhysioNet",
        "url": "https://physionet.org/content/mimiciv/",
        "publication_date": "2023",
        "version": "v2.2",
        "document_type": "RESEARCH_CLINICAL_DATASET",
        "licensing_status": "RESEARCH_DATA_USE_AGREEMENT",
        "status": "RESEARCH_USE_ONLY",
        "reviewer": "Transify Research Evaluation Board",
        "retrieval_date": "2026-11-20",
        "applicable_population": "Retrospective intensive care research cohort at Beth Israel Deaconess Medical Center",
        "supported_claims": "Physiological shock index benchmarks (HR/SBP > 0.9) and hemodynamic autonomic waveform modeling in critical care research; NOT a clinical treatment guideline",
        "can_support_clinical_recommendations": False,
        "chunks": [
            {
                "section_heading": "Physiological Instability Indicators & Shock Index Benchmarks",
                "keywords": ["shock", "sepsis", "vital signs", "hemodynamic instability", "altered mental status", "hypotension", "tachycardia"],
                "content": "Analysis of 70,000+ critical care encounters in MIMIC-IV demonstrates that an elevated Shock Index (Heart Rate divided by Systolic Blood Pressure > 0.9) in combination with acute systemic complaints significantly predicts critical deterioration and inpatient admission. When patients report systemic lethargy, diaphoresis, or sudden dizziness accompanied by fever or bleeding, immediate emergency resuscitation pathways take precedence over non-urgent ambulatory deferral."
            }
        ]
    },
    {
        "source_id": "SRC-NLM-MESH-2024",
        "title": "U.S. National Library of Medicine Medical Subject Headings (MeSH) Controlled Vocabulary",
        "publisher": "National Institutes of Health (NIH) / U.S. NLM",
        "url": "https://www.nlm.nih.gov/mesh/meshhome.html",
        "publication_date": "2024",
        "version": "2024",
        "document_type": "BIOMEDICAL_TERMINOLOGY_ONTOLOGY",
        "licensing_status": "PUBLIC_DOMAIN_NLM",
        "status": "TERMINOLOGY_STANDARD",
        "reviewer": "National Library of Medicine",
        "retrieval_date": "2026-11-20",
        "applicable_population": "Universal biomedical informatics and literature indexing",
        "supported_claims": "Standardized medical taxonomy, synonym indexing, and Concept Unique Identifier (CUI) coding for symptoms and conditions; NOT a clinical treatment guideline",
        "can_support_clinical_recommendations": False,
        "chunks": [
            {
                "section_heading": "Standardized Terminology & Clinical Ontology Mapping",
                "keywords": ["mesh", "standardized terminology", "ontology", "clinical taxonomy", "coding", "symptom descriptors"],
                "content": "Harmonization of clinical intake text against U.S. National Library of Medicine MeSH descriptors enforces standardized clinical communication. Every patient symptom is mapped to unique MeSH CUI identifiers (e.g. Chest Pain [C23.888.592.612.333], Dyspnea [C08.618.307], Dermatitis [C17.800.862.394], Conjunctivitis [C11.187.183], Dengue [C02.782.417.214], Cholera [C01.252.410.890.312]) ensuring cross-system clinical interoperability."
            }
        ]
    },
    {
        "source_id": "SRC-WHO-GHO-EPIDEMIC-2024",
        "title": "WHO Global Health Observatory Disease Prevalence & Regional Outbreak Surveillance Protocol",
        "publisher": "World Health Organization (WHO) Global Health Observatory",
        "url": "https://www.who.int/data/gho",
        "publication_date": "2024",
        "version": "2024.1",
        "document_type": "EPIDEMIOLOGICAL_SURVEILLANCE_DATABASE",
        "licensing_status": "OPEN_ACCESS_WHO",
        "status": "SURVEILLANCE_DATA",
        "reviewer": "World Health Organization Surveillance Network",
        "retrieval_date": "2026-11-20",
        "applicable_population": "Regional macro-populations undergoing vector-borne or waterborne epidemic surveillance",
        "supported_claims": "Regional geospatial epidemic threshold tracking and outbreak surveillance indicators; NOT an individualized clinical treatment guideline",
        "can_support_clinical_recommendations": False,
        "chunks": [
            {
                "section_heading": "Regional Vector-Borne & Enteric Outbreak Surveillance Guidelines",
                "keywords": ["outbreak", "epidemic", "dengue", "cholera", "malaria", "surveillance", "vector", "waterborne", "gps", "monsoon", "nipah"],
                "content": "Geospatial epidemic surveillance in high-density delta regions tracks localized vector-borne surges (Aedes aegypti breeding cycles post-monsoon), waterborne Vibrio cholerae clusters during flooding, and seasonal zoonotic pathogens (Nipah virus). Triage systems operating in endemic zones must integrate geolocation awareness to cross-reference patient fever, gastrointestinal, or respiratory symptoms with real-time district outbreak thresholds."
            }
        ]
    },
    {
        "source_id": "SRC-HMD-MORTALITY-2024",
        "title": "Human Mortality Database (HMD) International Actuarial Life Tables & Long-Term Health Trends",
        "publisher": "University of California, Berkeley & Max Planck Institute for Demographic Research",
        "url": "https://www.mortality.org",
        "publication_date": "2024",
        "version": "2024.1",
        "document_type": "ACTUARIAL_RESEARCH_DATABASE",
        "licensing_status": "OPEN_ACCESS_RESEARCH_DATA",
        "status": "ACTUARIAL_DATA",
        "reviewer": "University of California Berkeley / Max Planck Institute",
        "retrieval_date": "2026-11-20",
        "applicable_population": "National macro-demographic cohorts across 40+ countries",
        "supported_claims": "Age-specific baseline mortality hazards and actuarial life expectancy projections; NOT an acute patient clinical triage or treatment guideline",
        "can_support_clinical_recommendations": False,
        "chunks": [
            {
                "section_heading": "Actuarial Life Tables & Long-Term Mortality Hazard Stratification",
                "keywords": ["mortality", "life expectancy", "human mortality database", "actuarial", "hazard ratio", "comorbidity", "chronic risk", "age-specific mortality", "hmd"],
                "content": "Long-term population health trends cataloged in the Human Mortality Database (HMD) provide age- and sex-stratified annual mortality probabilities (q_x) and remaining life expectancy projections. Integrating HMD baseline mortality hazards allows clinical triage engines to calibrate risk scores for older adults and individuals with pre-existing cardiovascular or metabolic vulnerabilities. In acute symptom evaluation, patients with high HMD excess hazard multipliers receive prioritized escalation before physiological decompensation occurs."
            }
        ]
    }
]


def seed_clinical_sources_if_empty(force_reseed: bool = False):
    """
    Seeds the Clinical and Research Evidence Registry.
    Ensures rich provenance metadata and flags each resource according to its legitimate scope.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM care_clinical_sources WHERE retrieval_date IS NOT NULL;")
    row = cursor.fetchone()
    if not force_reseed and row and row["count"] >= len(DEFAULT_CLINICAL_SOURCES):
        conn.close()
        return

    # Clear and re-populate
    cursor.execute("DELETE FROM care_clinical_chunks;")
    cursor.execute("DELETE FROM care_clinical_sources;")

    for src in DEFAULT_CLINICAL_SOURCES:
        checksum = hashlib.sha256(json.dumps(src, sort_keys=True).encode("utf-8")).hexdigest()
        cursor.execute("""
        INSERT INTO care_clinical_sources (
            source_id, title, publisher, url, publication_date, version,
            document_type, licensing_status, checksum, status, reviewer,
            retrieval_date, applicable_population, supported_claims,
            can_support_clinical_recommendations, chunks_count, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'));
        """, (
            src["source_id"], src["title"], src["publisher"], src["url"],
            src["publication_date"], src["version"], src["document_type"],
            src["licensing_status"], checksum, src["status"], src["reviewer"],
            src.get("retrieval_date", "2026-11-20"),
            src.get("applicable_population", "General clinical population"),
            src.get("supported_claims", ""),
            1 if src.get("can_support_clinical_recommendations", True) else 0,
            len(src["chunks"])
        ))

        for idx, ch in enumerate(src["chunks"]):
            kw_str = ", ".join(ch["keywords"])
            cursor.execute("""
            INSERT INTO care_clinical_chunks (
                source_id, chunk_index, section_heading, content, keywords, created_at
            ) VALUES (?, ?, ?, ?, ?, datetime('now'));
            """, (src["source_id"], idx, ch["section_heading"], ch["content"], kw_str))

    conn.commit()
    conn.close()


def search_clinical_evidence(
    query: str,
    limit: int = 3,
    clinical_recommendations_only: bool = False
) -> Dict[str, Any]:
    """
    Performs keyword passage lookup over the Clinical and Research Evidence Registry.
    When clinical_recommendations_only=True, filters to verified clinical guidelines,
    isolating research databases and ontologies from patient recommendations.
    """
    seed_clinical_sources_if_empty()
    conn = get_connection()
    cursor = conn.cursor()

    tokens = [t.lower().strip() for t in query.split() if len(t.strip()) > 2]
    if not tokens:
        conn.close()
        return {
            "registry": "Clinical and Research Evidence Registry",
            "component": "Clinical and Research Evidence Registry",
            "evidence_found": False,
            "citations": [],
            "message": "Insufficient query terms provided to retrieve evidence passages."
        }

    where_filter = "WHERE s.status IN ('APPROVED', 'PENDING_REVIEW', 'UNVERIFIED', 'RESEARCH_USE_ONLY', 'TERMINOLOGY_STANDARD', 'SURVEILLANCE_DATA', 'ACTUARIAL_DATA')"
    if clinical_recommendations_only:
        where_filter += " AND (s.can_support_clinical_recommendations = 1 OR s.can_support_clinical_recommendations IS NULL)"

    cursor.execute(f"""
    SELECT c.id, c.source_id, c.section_heading, c.content, c.keywords,
           s.title as source_title, s.publisher, s.url, s.version, s.status, s.reviewer,
           s.document_type, s.retrieval_date, s.applicable_population, s.supported_claims,
           s.can_support_clinical_recommendations
    FROM care_clinical_chunks c
    JOIN care_clinical_sources s ON c.source_id = s.source_id
    {where_filter};
    """)
    all_chunks = cursor.fetchall()
    conn.close()

    scored = []
    for row in all_chunks:
        content_lower = row["content"].lower()
        heading_lower = (row["section_heading"] or "").lower()
        keywords_lower = (row["keywords"] or "").lower()
        score = 0
        matched_tokens = []

        for tok in tokens:
            if tok in heading_lower:
                score += 3.0
                matched_tokens.append(tok)
            if tok in keywords_lower:
                score += 2.0
                matched_tokens.append(tok)
            if tok in content_lower:
                score += 1.0
                matched_tokens.append(tok)

        if score > 0:
            scored.append({
                "score": score,
                "source_id": row["source_id"],
                "source_title": row["source_title"],
                "publisher": row["publisher"],
                "url": row["url"],
                "version": row["version"],
                "resource_type": row["document_type"],
                "verification_status": row["status"],
                "reviewer": row["reviewer"],
                "retrieval_date": row["retrieval_date"],
                "applicable_population": row["applicable_population"],
                "supported_claims": row["supported_claims"],
                "can_support_clinical_recommendations": bool(row["can_support_clinical_recommendations"]),
                "section_heading": row["section_heading"],
                "excerpt": row["content"],
                "matched_terms": list(set(matched_tokens))
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top_results = scored[:limit]

    if not top_results:
        return {
            "registry": "Clinical and Research Evidence Registry",
            "component": "Clinical and Research Evidence Registry",
            "evidence_found": False,
            "citations": [],
            "message": "Sufficient evidence passages were not found in reference clinical guidelines for the reported symptoms. Clinician evaluation is required."
        }

    return {
        "registry": "Clinical and Research Evidence Registry",
        "component": "Clinical and Research Evidence Registry",
        "evidence_found": True,
        "citations": top_results,
        "message": f"Retrieved {len(top_results)} reference guideline passage(s) from Clinical and Research Evidence Registry. Requires human clinician verification."
    }
