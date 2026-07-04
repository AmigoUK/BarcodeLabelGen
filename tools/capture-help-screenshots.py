#!/usr/bin/env python3
"""Zrzuty ekranu do docs/HELP.{pl,en}.md — headless Chromium + sesja z API."""
#
# Regeneruje zrzuty do docs/HELP.{pl,en}.md.
# Wymagania: pip install playwright && playwright install chromium --with-deps;
# zalogowane sesje curl w /tmp/blg.txt (admin) i /tmp/blg-demo.txt (demo@blg.local)
# oraz szablon demo (id przekazywany argumentem) — patrz docs/PROJECT.md.

import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://linuxserv1.tailc29352.ts.net:18003"
DOMAIN = "linuxserv1.tailc29352.ts.net"
OUT = Path("/var/www/html/BarcodeLabelGen/docs/screenshots/help")
TPL_ID = sys.argv[1] if len(sys.argv) > 1 else "97"

def jar_cookies(path):
    out = []
    for line in Path(path).read_text().splitlines():
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_"):]
        elif line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            name, value = parts[5], parts[6]
            out.append({
                "name": name, "value": value, "domain": DOMAIN,
                "path": "/", "secure": True,
                "httpOnly": name == "session", "sameSite": "Lax",
            })
    return out

DEMO = jar_cookies("/tmp/blg-demo.txt")
ADMIN = jar_cookies("/tmp/blg.txt")

L = {
    "pl": {
        "series": "Generuj serię", "next": "Dalej", "analyze": "Sprawdź",
        "import_zpl": "Importuj ZPL", "export_zpl": "⤒ ZPL",
    },
    "en": {
        "series": "Generate series", "next": "Next", "analyze": "Analyze",
        "import_zpl": "Import ZPL", "export_zpl": "⤒ ZPL",
    },
}

SAMPLE_ZPL = """^XA
^CI28
^FO40,40^A@N,40,40,E:ARI000.TTF^FB720,1,0,L,0^FDHerbata zielona Sencha^FS
^FO40,120^A@N,28,28,E:ARI001.TTF^FDZuzyc do: {DATA}^FS
^FO40,180^BY2^BCN,90,Y,N,N^FD5901234123457^FS
^PQ1,0,1,Y
^XZ"""


def shoot(page, path, clip=None):
    page.screenshot(path=str(path), clip=clip)
    print("saved", path)


def run_lang(browser, lang):
    t = L[lang]
    out = OUT / lang
    out.mkdir(parents=True, exist_ok=True)

    def new_ctx(cookies):
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900}, device_scale_factor=2,
            locale="pl-PL" if lang == "pl" else "en-GB",
        )
        ctx.add_init_script(f"localStorage.setItem('i18nextLng','{lang}')")
        if cookies:
            ctx.add_cookies(cookies)
        return ctx

    # 1. login (bez sesji)
    ctx = new_ctx(None)
    page = ctx.new_page()
    page.goto(BASE + "/login", wait_until="networkidle")
    shoot(page, out / "login.png")
    ctx.close()

    # sesja demo
    ctx = new_ctx(DEMO)
    page = ctx.new_page()

    # 2. lista szablonów
    page.goto(BASE + "/templates", wait_until="networkidle")
    page.wait_for_timeout(400)
    shoot(page, out / "templates.png")

    # 3. edytor
    page.goto(f"{BASE}/templates/{TPL_ID}/edit", wait_until="networkidle")
    page.wait_for_timeout(1500)  # podglądy kodów kreskowych
    shoot(page, out / "editor-overview.png")

    # 4. modal rozmiaru etykiety
    page.locator("button", has_text="📐").first.click()
    page.wait_for_timeout(400)
    shoot(page, out / "label-size.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # 5-6. zaznacz tekst z datą → panel właściwości + chip
    box = page.locator(".konvajs-content").first.bounding_box()
    scale = box["width"] / 50.0  # etykieta 50 mm
    page.mouse.click(box["x"] + 10 * scale, box["y"] + 13.5 * scale)
    page.wait_for_timeout(500)
    aside = page.locator("aside").last
    if aside.locator("textarea").count() == 0:  # nie trafiliśmy — spróbuj nagłówka {{name}}
        page.mouse.click(box["x"] + 8 * scale, box["y"] + 6 * scale)
        page.wait_for_timeout(500)
    ab = aside.bounding_box()
    shoot(page, out / "dynamic-fields.png",
          clip={"x": ab["x"], "y": ab["y"], "width": ab["width"],
                "height": min(ab["height"], 620)})
    chip = page.locator("span", has_text=re.compile(r"\{\{date\+14d\}\} →")).first
    cb = chip.bounding_box()
    if cb:
        shoot(page, out / "date-chip.png",
              clip={"x": ab["x"], "y": max(ab["y"], cb["y"] - 150),
                    "width": ab["width"], "height": cb["height"] + 190})
        print("CHIP-TEXT:", chip.inner_text())
    else:
        print("CHIP NOT FOUND for", lang)

    page.keyboard.press("Escape")

    # 7. kreator serii → krok mapowania
    page.locator("button", has_text=t["series"]).first.click()
    page.wait_for_timeout(400)
    modal = page.locator("div.fixed.inset-0")
    modal.locator("input[type=file]").first.set_input_files("/tmp/demo-data.csv")
    page.wait_for_selector(f"button:has-text('{t['next']}'):not([disabled])", timeout=30000)
    page.locator("button", has_text=t["next"]).first.click()
    page.wait_for_timeout(600)
    shoot(page, out / "series-map.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)

    # 8. import ZPL
    page.locator("button", has_text=t["import_zpl"]).first.click()
    page.wait_for_timeout(300)
    page.locator("div.fixed.inset-0 textarea").last.fill(SAMPLE_ZPL)
    page.locator("button", has_text=t["analyze"]).first.click()
    page.wait_for_timeout(900)
    shoot(page, out / "zpl-import.png")
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)

    # 9. eksport ZPL
    page.locator("button", has_text=t["export_zpl"]).first.click()
    page.wait_for_timeout(900)
    shoot(page, out / "zpl-export.png")
    page.keyboard.press("Escape")
    ctx.close()

    # 10. panel admina (sesja admina, podmiana realnych maili w DOM)
    ctx = new_ctx(ADMIN)
    page = ctx.new_page()
    page.goto(BASE + "/admin/users", wait_until="networkidle")
    page.wait_for_timeout(500)
    page.evaluate("""() => {
        const repl = {'tomasz@mazowszebakery.co.uk': 'jan.kowalski@example.com'};
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let n; while ((n = walker.nextNode())) {
            for (const [a, b] of Object.entries(repl))
                if (n.textContent.includes(a)) n.textContent = n.textContent.replaceAll(a, b);
        }
    }""")
    shoot(page, out / "users-admin.png")
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    for lang in ("pl", "en"):
        run_lang(browser, lang)
    browser.close()
print("DONE")
