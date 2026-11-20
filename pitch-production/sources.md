# Transify Care — Academic & Clinical Knowledge Sources
**Project**: Transify Care (AI Builders Congress • HealthSphere AI)  
**Standard**: APA 7th Edition & NLM Format

---

## 1. Primary Empirical Evidence & Epidemiological Context

1. **Healthcare Accessibility for Persons with Disabilities in Bangladesh**:
   - **Citation**: Nawshin Torsha, A., Rahman, M., Hossain, M. S., & Ahmed, S. (2022). Disability-friendly healthcare at public health facilities in Bangladesh: a mixed-method study to explore the existing situation. *BMC Health Services Research*, 22, Article 1178.
   - **DOI**: [10.1186/s12913-022-08538-6](https://doi.org/10.1186/s12913-022-08538-6)
   - **Key Finding Used**: 59.1% of survey respondents dissatisfied with access to healthcare information and communication at public healthcare facilities.
   - **Context**: Explores existing physical, communication, and procedural accessibility gaps across health facilities in Bangladesh.

2. **Global Disability & Health Equity**:
   - **Citation**: World Health Organization. (2022). *Global report on health equity for persons with disabilities*. World Health Organization. Geneva, Switzerland. ISBN: 978-92-4-006360-0.
   - **Key Finding Used**: Over 1.3 billion individuals (16% of global population) experience significant disability, facing higher mortality risks and systematic barriers in primary healthcare triage.

---

## 2. Seeded Clinical Guidelines (Clinical Evidence Lookup Prototype)

The Transify Care Clinical Evidence Lookup module (`src/care/clinical_rag.py`) operates as a keyword-based retrieval prototype over seeded excerpts. Sources are cataloged with status `PENDING_REVIEW` pending formal validation by qualified healthcare authorities:

1. **WHO Integrated Primary Care & Emergency Triage Protocol (Prototype Remote Adaptation)**:
   - **Title**: Integrated Management of Adolescent and Adult Illness (IMAI): Emergency and First-Line Primary Care Triage Protocols
   - **Publisher**: World Health Organization (WHO), Department of Maternal, Newborn, Child and Adolescent Health
   - **Edition/Version**: 2020.2 Guidelines
   - **Scope**: Facility-based primary triage protocol adapted as a triage research prototype. Deterministic detection of red-flag symptoms: sudden crushing substernal chest pressure, hemiparesis, sudden respiratory failure, anaphylaxis, and acute altered consciousness.
   - **Review Status**: PENDING_REVIEW (Remote triage adaptation requires local clinical validation before real-world deployment)
   - **URL**: [https://www.who.int/publications/i/item/9789241548847](https://www.who.int/publications/i/item/9789241548847)

2. **DGHS Bangladesh National Dengue Clinical Management Protocol**:
   - **Title**: National Guidelines for Clinical Management of Dengue Syndrome in Bangladesh (5th Edition, 2023)
   - **Publisher**: Directorate General of Health Services (DGHS), Ministry of Health and Family Welfare, Government of the People's Republic of Bangladesh
   - **Edition/Version**: 5th Edition (2023)
   - **Scope**: Warning signs for severe febrile illness: high fever (103°F+) accompanied by persistent vomiting (>24 hours), inability to tolerate oral fluids, severe abdominal tenderness, and mucosal bleeding. Advises physical evaluation and hematocrit monitoring.
   - **Review Status**: PENDING_REVIEW
   - **URL**: [https://dghs.gov.bd/index.php/en/dengue-guidelines](https://dghs.gov.bd/index.php/en/dengue-guidelines)

3. **NINS Acute Stroke Emergency Protocol**:
   - **Title**: National Clinical Protocol for Acute Ischemic Stroke and Hemorrhagic Triage
   - **Publisher**: National Institute of Neurosciences & Hospital (NINS), Dhaka, Bangladesh
   - **Edition/Version**: 2021.1 Clinical Guidance
   - **Scope**: Emergency recognition of sudden focal neurological deficits: facial droop, unilateral arm/leg weakness, slurred speech, and acute ataxia within the 4.5-hour thrombolysis window.
   - **Review Status**: PENDING_REVIEW
   - **URL**: [https://nins.gov.bd/clinical-guidelines](https://nins.gov.bd/clinical-guidelines)

---

## 3. Assistive AI & Computer Vision Foundations

1. **Sign Language Landmark Extraction & Graph Modeling**:
   - **Citation**: Lugaresi, C., Tang, J., Nash, H., McClanahan, C., Uboweja, E., Hays, M., Zhang, F., Wang, C. L., Chen, B., Venugopalan, S., & Grundmann, M. (2019). *MediaPipe: A Framework for Building Perception Pipelines*. arXiv preprint arXiv:1906.08172.
   - **Citation**: Kapitanov, A., Kvanchiani, K., & Nagaeva, E. (2022). *HaGRID — HAnd Gesture Recognition Image Dataset*. arXiv preprint arXiv:2206.08219.

2. **Optical Braille Recognition (OBR)**:
   - **Citation**: Li, J., & Yan, X. (2021). *Optical Braille Recognition Based on Deep Neural Networks and Morphological Cell Analysis*. IEEE Access, 9, 39420-39430.
   - **Standard**: Unified English Braille (UEB) Grade 1 Standard Specification (International Council on English Braille, 2016).
