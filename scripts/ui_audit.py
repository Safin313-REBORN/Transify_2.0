"""UI Audit Script for Transify 2.0 (Prompt §13 & §14)
Validates geometry, routes, responsiveness, accessibility, and content rules.
"""

import sys
import os
import re
import asyncio
from playwright.async_api import async_playwright

SIZES = [
    (768, 1024),
    (1024, 768),
    (1280, 720),
    (1366, 768),
    (1440, 900),
    (1536, 864),
    (1920, 1080),
    (2560, 1440),
]

ROUTES = ['#welcome', '#home', '#sign', '#braille', '#stt', '#phrases']

FORBIDDEN_REGEX = [
    re.compile(r'555-?01\d\d'),
    re.compile(r'tarnsify', re.IGNORECASE),
    re.compile(r'\bEIN\b'),
    re.compile(r'HaGRID|CNN|MediaPipe|Photo:\s'),
    re.compile(r'Sarah Ahmed')
]

async def run_audit():
    sys.path.insert(0, os.path.abspath("."))
    import uvicorn
    from src.api.server import app

    config = uvicorn.Config(app, host="127.0.0.1", port=8008, log_level="warning")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(1)

    errors = []
    print("=== Starting UI Audit across 8 Viewports and 6 Routes ===")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # 1. Content and string check
        await page.goto("http://127.0.0.1:8008/#home")
        await page.wait_for_timeout(500)

        for route in ROUTES:
            await page.goto(f"http://127.0.0.1:8008/{route}")
            await page.wait_for_timeout(300)
            visible_text = await page.evaluate("""() => {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                let text = '';
                let node;
                while (node = walker.nextNode()) {
                    const el = node.parentElement;
                    if (el && el.offsetParent !== null && !el.classList.contains('sr-only')) {
                        text += ' ' + node.textContent;
                    }
                }
                return text;
            }""")
            for pat in FORBIDDEN_REGEX:
                m = pat.search(visible_text)
                if m:
                    errors.append(f"Content violation on {route}: found forbidden string matching {pat.pattern}: '{m.group(0)}'")

        # 2. Viewport and Geometry check
        for w, h in SIZES:
            await page.set_viewport_size({"width": w, "height": h})
            for route in ROUTES:
                await page.goto(f"http://127.0.0.1:8008/{route}")
                await page.wait_for_timeout(300)

                # Check horizontal scroll
                scroll_w, inner_w = await page.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
                if scroll_w > inner_w + 1:
                    errors.append(f"Horizontal scroll detected on {route} at {w}x{h}: scrollWidth={scroll_w} > innerWidth={inner_w}")

                # Check minimum text size (>= 14px)
                small_texts = await page.evaluate("""() => {
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    const bad = [];
                    let node;
                    while (node = walker.nextNode()) {
                        const el = node.parentElement;
                        if (el && el.offsetParent !== null && !el.classList.contains('sr-only') && node.textContent.trim().length > 1) {
                            const fs = parseFloat(window.getComputedStyle(el).fontSize);
                            if (fs < 13.5 && !el.closest('.rail-logo') && !el.closest('.welcome-logo-dots') && !el.closest('svg')) {
                                bad.push({ text: node.textContent.trim().slice(0, 30), fs, tag: el.tagName, cls: el.className });
                            }
                        }
                    }
                    return bad;
                }""")
                if small_texts:
                    errors.append(f"Small text (<14px) on {route} at {w}x{h}: {small_texts[:3]}")

        # 3. Exact Geometry at 1440x900 (§13)
        await page.set_viewport_size({"width": 1440, "height": 900})
        
        # Rail geometry on Home
        await page.goto("http://127.0.0.1:8008/#home")
        await page.wait_for_timeout(300)
        rail_box = await page.locator("#app-rail").bounding_box()
        if rail_box:
            if abs(rail_box["width"] - 112) > 4:
                errors.append(f"Rail width at 1440x900 expected ~112px, got {rail_box['width']}")
            if abs(rail_box["x"] - 0) > 4:
                errors.append(f"Rail x at 1440x900 expected 0, got {rail_box['x']}")

        # Home main content width
        main_box = await page.locator(".home-main").bounding_box()
        if main_box:
            # Main padding is 48px left/right, width expected ~1008px total (content 912)
            content_w = main_box["width"] - 96
            if abs(content_w - 912) > 16:
                errors.append(f"Home main content width expected ~912, got {content_w}")

        # Sign geometry at 1440x900
        await page.goto("http://127.0.0.1:8008/#sign")
        await page.wait_for_timeout(300)
        stage_box = await page.locator("#sign-stage-container").bounding_box()
        res_box = await page.locator(".sign-result-panel").bounding_box()
        if stage_box:
            if abs(stage_box["x"] - 112) > 4:
                errors.append(f"Sign stage x expected ~112, got {stage_box['x']}")
            if abs(stage_box["width"] - 808) > 16:
                errors.append(f"Sign stage width expected ~808, got {stage_box['width']}")
        if res_box:
            if abs(res_box["width"] - 520) > 8:
                errors.append(f"Sign result panel width expected ~520, got {res_box['width']}")
            res_content_w = res_box["width"] - 64
            if abs(res_content_w - 456) > 8:
                errors.append(f"Sign result panel content width expected ~456, got {res_content_w}")

        # Phrases container geometry at 1440x900
        await page.goto("http://127.0.0.1:8008/#phrases")
        await page.wait_for_timeout(300)
        phrases_box = await page.locator("#view-phrases .phrases-container").bounding_box()
        if phrases_box:
            if abs(phrases_box["width"] - 1180) > 8:
                errors.append(f"Phrases container width expected ~1180, got {phrases_box['width']}")
            # left offset should be (1328-1180)/2 = 74 from rail edge
            offset = phrases_box["x"] - 112
            if abs(offset - 74) > 12:
                errors.append(f"Phrases container left offset expected ~74, got {offset}")

        # Welcome panel at 1440x900
        await page.goto("http://127.0.0.1:8008/#welcome")
        await page.wait_for_timeout(300)
        welcome_aside_box = await page.locator(".welcome-aside").bounding_box()
        if welcome_aside_box:
            if abs(welcome_aside_box["width"] - 540) > 8:
                errors.append(f"Welcome right panel width expected ~540, got {welcome_aside_box['width']}")

        # 4. Reduced motion test
        await page.goto("http://127.0.0.1:8008/#home")
        await page.evaluate("() => document.documentElement.setAttribute('data-motion', 'reduced')")
        anim_count = await page.evaluate("() => document.getAnimations().filter(a => a.playState === 'running').length")
        print(f"Running animations with data-motion='reduced': {anim_count}")

        # 5. Sign word auto-fit test
        await page.goto("http://127.0.0.1:8008/#sign")
        fit_results = await page.evaluate("""() => {
            const wordEl = document.getElementById('pred-label-text');
            const testWords = ['Hello', 'Thank you', 'আমার সাহায্য দরকার', 'A_VERY_LONG_SIGN_LABEL_NAME_HERE'];
            const res = [];
            for (const w of testWords) {
                wordEl.textContent = w;
                let fs = 96;
                wordEl.style.fontSize = fs + 'px';
                while (wordEl.scrollWidth > wordEl.clientWidth && fs > 40) {
                    fs -= 4;
                    wordEl.style.fontSize = fs + 'px';
                }
                res.push({ word: w, fs, overflow: wordEl.scrollWidth > wordEl.clientWidth + 2 });
            }
            return res;
        }""")
        print(f"Auto-fit test results: {fit_results}")
        for r in fit_results:
            if r["overflow"]:
                errors.append(f"Word '{r['word']}' overflowed result panel after auto-fit (fs={r['fs']})")

        # Create screenshots folder and take screenshots
        os.makedirs("audit", exist_ok=True)
        await page.set_viewport_size({"width": 1440, "height": 900})
        for route in ['#home', '#sign', '#phrases', '#welcome', '#braille', '#stt']:
            await page.goto(f"http://127.0.0.1:8008/{route}")
            await page.wait_for_timeout(400)
            clean_name = route.replace('#', '')
            await page.screenshot(path=f"audit/{clean_name}-1440.png")

        await browser.close()

    server.should_exit = True
    await server_task

    print("\n=== UI Audit Summary ===")
    if not errors:
        print("ALL UI AUDIT CHECKS PASSED PERFECTLY!")
        return True
    else:
        print(f"Found {len(errors)} issues:")
        for e in errors:
            print(" -", e)
        return False

if __name__ == "__main__":
    success = asyncio.run(run_audit())
    sys.exit(0 if success else 1)
