import urllib.request
import re
import os

with open("src/frontend/static/fonts/google_fonts.css") as f:
    css = f.read()

# Parse @font-face blocks
blocks = re.findall(r"@font-face\s*\{([^}]+)\}", css)
font_rules = []
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

for idx, b in enumerate(blocks):
    family_match = re.search(r"font-family:\s*['\"]?([^'\";]+)", b)
    weight_match = re.search(r"font-weight:\s*(\d+)", b)
    url_match = re.search(r"url\((https:[^)]+)\)", b)
    range_match = re.search(r"unicode-range:\s*([^;]+);", b)
    
    if family_match and weight_match and url_match:
        family_clean = family_match.group(1).strip().replace("'", "").replace('"', "")
        weight = weight_match.group(1).strip()
        url = url_match.group(1).strip()
        unicode_range = range_match.group(1).strip() if range_match else "U+0000-00FF"
        
        filename = f"{family_clean.replace(' ', '')}-{weight}-{idx}.woff2"
        filepath = os.path.join("src/frontend/static/fonts", filename)
        
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            with open(filepath, "wb") as f_out:
                f_out.write(data)
                
        font_rules.append(f"""@font-face {{
  font-family: '{family_clean}';
  font-style: normal;
  font-weight: {weight};
  font-display: swap;
  src: url('/static/fonts/{filename}') format('woff2');
  unicode-range: {unicode_range};
}}""")

with open("src/frontend/static/fonts/fonts.css", "w") as f:
    f.write("\n\n".join(font_rules))

print(f"Downloaded {len(font_rules)} WOFF2 font files and generated fonts.css successfully.")
