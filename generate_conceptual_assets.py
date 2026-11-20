import os
from PIL import Image, ImageDraw, ImageFont

DEST_DIR = "/home/safin313/Downloads/transify-main/src/frontend/static/photos"
DOCS_DIR = "/home/safin313/Downloads/transify-main/docs"
os.makedirs(DEST_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

# Generate rich editorial SVG/WebP graphics for conceptual healthcare assets 05-12
CONCEPTUAL_ASSETS = [
    {
        "name": "care-low-bandwidth",
        "ratio": (16, 9),
        "size": (1600, 900),
        "bg_top": "#14111F", "bg_bot": "#1E1A33",
        "accent": "#0F9D74",
        "title": "Community Low-Bandwidth Care",
        "subtitle": "Offline-Resilient Mobile Health Logging in Rural Bangladesh",
        "badge": "LOW-BANDWIDTH ARCHITECTURE"
    },
    {
        "name": "care-clinician-review",
        "ratio": (16, 9),
        "size": (1600, 900),
        "bg_top": "#14111F", "bg_bot": "#1F1A3A",
        "accent": "#8338EC",
        "title": "Clinician Oversight & Review",
        "subtitle": "Human-in-the-Loop Clinical Verification & Oversight",
        "badge": "HUMAN CLINICAL OVERSIGHT"
    },
    {
        "name": "care-patient-centered",
        "ratio": (4, 3),
        "size": (1200, 900),
        "bg_top": "#14111F", "bg_bot": "#1A2535",
        "accent": "#00A8E8",
        "title": "Patient-Centered Digital Health",
        "subtitle": "Accessible Intake Tailored for Sign, Braille, and Voice",
        "badge": "ACCESSIBLE INTAKE"
    },
    {
        "name": "care-clinical-evidence",
        "ratio": (16, 9),
        "size": (1600, 900),
        "bg_top": "#14111F", "bg_bot": "#241935",
        "accent": "#FFCB05",
        "title": "Evidence-Grounded RAG",
        "subtitle": "Source-Grounded Retrieval from WHO & National Clinical Guidelines",
        "badge": "CLINICAL RAG SYSTEM"
    },
    {
        "name": "care-offline-sync",
        "ratio": (16, 9),
        "size": (1600, 900),
        "bg_top": "#14111F", "bg_bot": "#1B242D",
        "accent": "#0F9D74",
        "title": "Encrypted Offline Sync",
        "subtitle": "Zero-Loss Resilient Client Storage with Automatic Reconciliation",
        "badge": "OFFLINE RESILIENCE"
    },
    {
        "name": "care-inclusive-team",
        "ratio": (16, 9),
        "size": (1600, 900),
        "bg_top": "#14111F", "bg_bot": "#2A1838",
        "accent": "#8338EC",
        "title": "Inclusive Healthcare Collaboration",
        "subtitle": "Clinicians, Interpreters, and Patients in Direct Alignment",
        "badge": "INCLUSIVE CARE TEAM"
    },
    {
        "name": "care-data-privacy",
        "ratio": (4, 3),
        "size": (1200, 900),
        "bg_top": "#14111F", "bg_bot": "#181E2E",
        "accent": "#00B4D8",
        "title": "Patient Trust & Cryptographic Privacy",
        "subtitle": "Consent-Controlled Assistive Health Information Protection",
        "badge": "STRICT PRIVACY"
    },
    {
        "name": "care-healthcare-impact",
        "ratio": (16, 9),
        "size": (1600, 900),
        "bg_top": "#14111F", "bg_bot": "#1F2922",
        "accent": "#0F9D74",
        "title": "HealthSphere CareAnywhere Impact",
        "subtitle": "Accessible Health Communication for 16M+ Disabled Citizens in Bangladesh",
        "badge": "HEALTHSPHERE AI IMPACT"
    }
]

for item in CONCEPTUAL_ASSETS:
    w, h = item["size"]
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{item['bg_top']}"/>
      <stop offset="100%" stop-color="{item['bg_bot']}"/>
    </linearGradient>
    <radialGradient id="glow" cx="80%" cy="20%" r="60%">
      <stop offset="0%" stop-color="{item['accent']}" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="{item['accent']}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <rect width="100%" height="100%" fill="url(#glow)"/>
  <rect width="100%" height="100%" fill="url(#grid)"/>
  
  <g transform="translate(80, {h//3})">
    <rect x="0" y="0" width="{len(item['badge'])*11 + 24}" height="32" rx="16" fill="{item['accent']}" fill-opacity="0.15" stroke="{item['accent']}" stroke-width="1.5"/>
    <text x="12" y="21" font-family="-apple-system, sans-serif" font-size="13" font-weight="700" fill="{item['accent']}" letter-spacing="1">{item['badge']}</text>
    
    <text x="0" y="80" font-family="'Schibsted Grotesk', -apple-system, sans-serif" font-size="44" font-weight="800" fill="#FFFFFF" letter-spacing="-0.5">{item['title']}</text>
    <text x="0" y="125" font-family="'Hind Siliguri', -apple-system, sans-serif" font-size="22" font-weight="400" fill="#B9BAD0">{item['subtitle']}</text>
    
    <line x1="0" y1="160" x2="120" y2="160" stroke="{item['accent']}" stroke-width="3" stroke-linecap="round"/>
  </g>
</svg>"""
    
    # Save SVG
    svg_path = os.path.join(DEST_DIR, f"{item['name']}.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
        
    # Also render WebP & JPG fallback using PIL
    img = Image.new("RGB", (w, h), color=item["bg_top"])
    draw = ImageDraw.Draw(img)
    # Simple editorial composition
    draw.rectangle([0, 0, w, h], fill=item["bg_top"])
    draw.rectangle([0, h-160, w, h], fill=item["bg_bot"])
    draw.rectangle([80, h//3 + 160, 200, h//3 + 164], fill=item["accent"])
    
    webp_path = os.path.join(DEST_DIR, f"{item['name']}.webp")
    jpg_path = os.path.join(DEST_DIR, f"{item['name']}.jpg")
    img.save(webp_path, "WEBP", quality=80)
    img.save(jpg_path, "JPEG", quality=80)

print("Generated conceptual assets 05-12 in SVG and WebP format.")
