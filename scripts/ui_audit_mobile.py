# tests/ui_audit_mobile.py   run: python tests/ui_audit_mobile.py http://localhost:8000 [--reduced]
import sys, pathlib
from playwright.sync_api import sync_playwright

BASE = next((a for a in sys.argv[1:] if a.startswith("http")), "http://localhost:8000")
REDUCED = "--reduced" in sys.argv
SIZES = [(320,568),(360,640),(360,800),(375,667),(390,844),(393,852),(412,915),(430,932),(844,390)]
ROUTES = ["/", "/#sign", "/#braille", "/#stt", "/#tts"]
OUT = pathlib.Path("ui_audit"); OUT.mkdir(exist_ok=True)

AUDIT = """() => {
  const W = innerWidth, H = innerHeight, bad = [];
  const label = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + ' "' +
    (e.getAttribute('aria-label') || e.textContent.trim().slice(0, 24)) + '"';
  const visible = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0'; };
  const hScroller = e => { for (let p = e.parentElement; p; p = p.parentElement) {
    const s = getComputedStyle(p); if (/(auto|scroll)/.test(s.overflowX) && p.scrollWidth > p.clientWidth) return true; } return false; };
  const ui = [...document.querySelectorAll('button,a[href],input,select,textarea,[role=tab]')].filter(visible);
  if (document.documentElement.scrollWidth > W) bad.push('HSCROLL ' + document.documentElement.scrollWidth + '>' + W);
  ui.forEach(e => { const r = e.getBoundingClientRect();
    if (!hScroller(e) && (r.left < -1 || r.right > W + 1)) bad.push('OFFSCREEN-X ' + label(e));
    if (r.width < 44 || r.height < 44) { if (!e.closest('.sr-only')) bad.push('TARGET<44 ' + label(e) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)); } });
  for (let i = 0; i < ui.length; i++) for (let k = i + 1; k < ui.length; k++) {
    const a = ui[i], b = ui[k]; if (a.contains(b) || b.contains(a)) continue;
    const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
    const ox = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
    const oy = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
    if (ox > 2 && oy > 2) bad.push('OVERLAP ' + label(a) + ' x ' + label(b)); }
  // a decorative layer must never sit over a control
  ui.forEach(e => { const r = e.getBoundingClientRect(), t = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    if (t && t !== e && !e.contains(t) && !t.contains(e)) bad.push('COVERED ' + label(e) + ' by ' + label(t)); });
  // text clipped or wider than its container
  [...document.querySelectorAll('body *')].filter(e => visible(e) && !e.children.length && e.textContent.trim()).forEach(e => {
    if (e.scrollWidth > e.clientWidth + 1 && /(hidden|clip)/.test(getComputedStyle(e).overflowX)) bad.push('TEXT-CLIPPED ' + label(e)); });
  // confidence ring label must fit inside its ring
  const ring = document.querySelector('[data-confidence-ring]');
  if (ring) { const t = ring.querySelector('[data-confidence-text]');
    if (t && t.getBoundingClientRect().width > ring.getBoundingClientRect().width * 0.6) bad.push('RING-TEXT-TOO-WIDE'); }
  // DOM order must equal visual order for focusable controls (top to bottom, ignoring same-row ties)
  let prev = -1; ui.filter(e => getComputedStyle(e).position !== 'fixed').forEach(e => {
    const y = Math.round(e.getBoundingClientRect().top / 40); if (y + 1 < prev) bad.push('ORDER ' + label(e)); prev = Math.max(prev, y); });
  return bad;
}"""

fails = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for (w, h) in SIZES:
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2, has_touch=True, is_mobile=True,
                            reduced_motion="reduce" if REDUCED else "no-preference")
        page = ctx.new_page()
        for r in ROUTES:
            page.goto(BASE + r); page.wait_for_timeout(1500)
            issues = page.evaluate(AUDIT)
            tag = ("reduced-" if REDUCED else "") + (r.strip("/#") or "home") + f"-{w}x{h}"
            page.screenshot(path=str(OUT / f"{tag}.png"))
            print(("FAIL " if issues else "ok   ") + tag)
            for i in issues[:12]: print("     ", i)
            fails += bool(issues)
        ctx.close()
    b.close()
sys.exit(1 if fails else 0)
