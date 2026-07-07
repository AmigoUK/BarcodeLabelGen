#!/usr/bin/env python3
"""Zrzuty ekranu do docs/HELP.{pl,en}.md — headless Chromium + sesja z API.

Regeneruje wszystkie zrzuty w docs/screenshots/help/{pl,en}/ opisane w
docs/superpowers (F37 help guide). Wymagania:
  pip install playwright && playwright install chromium
  zalogowane sesje curl w /tmp/blg.txt (admin) i /tmp/blg-demo.txt (demo@blg.local)
  demo dataset CSV w /tmp/demo-data.csv (kolumny name,sku,cena)

Jednorazowe dane pomocnicze (foldery, "galeria obiektów", udostępniony
szablon admina, urządzenie z lokalnym agentem, przechwycone etykiety) są
tworzone automatycznie (idempotentnie) przez ensure_setup() poniżej — patrz
funkcja dla pełnej listy encji i identyfikatorów.

Uruchomienie: python3 capture-help-screenshots.py
"""

from __future__ import annotations

import json
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = "https://linuxserv1.tailc29352.ts.net:18003"
DOMAIN = "linuxserv1.tailc29352.ts.net"
OUT = Path("/var/www/html/BarcodeLabelGen/docs/screenshots/help")
SCRATCH = Path(
    "/tmp/claude-0/-var-www-html-BarcodeLabelGen/2144656e-8c4a-44ed-868c-8a7c89da30d7/scratchpad"
)

DEMO_JAR = "/tmp/blg-demo.txt"
ADMIN_JAR = "/tmp/blg.txt"
DEMO_EMAIL = "demo@blg.local"
DEMO_PASSWORD = "demo-docs-password-456!"
ADMIN_EMAIL = "shots-admin@blg.local"
ADMIN_PASSWORD = "shots-admin-pass-789!"
# The account is intentionally toggled back to "must change password" (via
# a self-targeted admin reset-password call) at the end of every admin
# capture block, so each run of this script reproduces the forced
# password-change screen honestly rather than assuming it from a fixture.
ADMIN_FINAL_PASSWORD = "shots-admin-final-2026!"

# Internal dev/test tooling only, never used against production: the target
# is a Tailscale-only staging host serving a self-signed cert (same pattern
# as the `curl -sk` / Playwright `ignore_https_errors=True` used throughout
# this dossier's other capture scripts), so certificate verification is
# intentionally relaxed here.
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

RESULTS: dict[str, dict[str, str]] = {}


def mark(name: str, lang: str, status: str) -> None:
    RESULTS.setdefault(name, {})[lang] = status
    print(f"[{lang}] {name}: {status}")


# --------------------------------------------------------------------------
# Tiny cookie-jar based HTTP client (no `requests` dependency available).
# --------------------------------------------------------------------------


class Session:
    def __init__(self, jar_path: str, email: str, password: str):
        self.jar_path = jar_path
        self.email = email
        self.password = password
        self.cookies: dict[str, str] = {}
        self._load_jar()

    def _load_jar(self) -> None:
        p = Path(self.jar_path)
        if not p.exists():
            return
        for line in p.read_text().splitlines():
            raw = line
            if raw.startswith("#HttpOnly_"):
                raw = raw[len("#HttpOnly_"):]
            elif raw.startswith("#") or not raw.strip():
                continue
            parts = raw.split("\t")
            if len(parts) >= 7:
                self.cookies[parts[5]] = parts[6]

    def _cookie_header(self) -> str:
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())

    def request(self, method: str, path: str, body: dict | None = None, auth: str | None = None):
        url = f"{BASE}{path}"
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = auth
        else:
            headers["Cookie"] = self._cookie_header()
            csrf = self.cookies.get("csrf_token")
            if csrf and method in ("POST", "PUT", "PATCH", "DELETE"):
                headers["X-CSRF-Token"] = csrf
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=20) as resp:
                self._capture_cookies(resp)
                raw = resp.read()
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            self._capture_cookies(e)
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, None

    def _capture_cookies(self, resp) -> None:
        for header in resp.headers.get_all("Set-Cookie") or []:
            kv = header.split(";", 1)[0]
            if "=" in kv:
                k, v = kv.split("=", 1)
                self.cookies[k.strip()] = v.strip()

    def ensure_login(self, password_fallbacks: tuple[str, ...] = ()) -> None:
        status, body = self.request("GET", "/api/me")
        if status == 200:
            return
        # refresh csrf then log in — try the configured password first, then
        # any fallbacks (e.g. the admin account's password after this same
        # script completed its one-time forced change on a previous run).
        self.request("GET", "/api/me")
        for pw in (self.password, *password_fallbacks):
            status, body = self.request(
                "POST", "/api/auth/login", {"email": self.email, "password": pw}
            )
            if status == 200:
                self.password = pw
                return
        raise RuntimeError(f"login failed for {self.email}: {status} {body}")


def api_get(sess: Session, path: str):
    return sess.request("GET", path)


def api_post(sess: Session, path: str, body: dict | None = None):
    return sess.request("POST", path, body)


def api_put(sess: Session, path: str, body: dict | None = None):
    return sess.request("PUT", path, body)


# --------------------------------------------------------------------------
# One-time scratch-data setup (idempotent). Populates fixed IDs used below.
# --------------------------------------------------------------------------

IDS = {
    "tpl_main": 97,  # "Etykieta produktu 50×30" — demo's main shared template
    "rich": None,  # "Zrzuty — obiekty" gallery template (all object types)
    "overflow": None,  # "Zrzuty — przepełnienie" ({{opis}} placeholder — series overflow warnings)
    "warnings_demo": None,  # "Zrzuty — ostrzeżenia PDF" (static long text — single-PDF warning chip)
    "device": None,  # device with a real local connector for the fast path
}


def ensure_setup(demo: Session, admin: Session) -> None:
    print("=== ensure_setup ===")

    # Folders (Produkcja/red already holds tpl 97 from earlier manual setup;
    # Kosmetyki/blue holds a second template so the folder rail shows 2+
    # folders with counts).
    _, folders = api_get(demo, "/api/folders")
    names = {f["name"] for f in folders.get("folders", [])}
    if "Kosmetyki" not in names:
        api_post(demo, "/api/folders", {"name": "Kosmetyki", "color": "#3b82f6"})
    if "Produkcja" not in names:
        api_post(demo, "/api/folders", {"name": "Produkcja", "color": "#ef4444"})

    _, folders = api_get(demo, "/api/folders")
    by_name = {f["name"]: f["id"] for f in folders.get("folders", [])}
    _, templates = api_get(demo, "/api/templates")
    tpl_by_name = {t["name"]: t for t in templates.get("templates", [])}

    if "Kosmetyki" in by_name:
        for t in templates.get("templates", []):
            if t["id"] != IDS["tpl_main"] and t.get("folder_id") is None:
                api_put(demo, f"/api/templates/{t['id']}", {"folder_id": by_name["Kosmetyki"]})
                break

    # "Zrzuty — obiekty" gallery template (created + populated once via a
    # dedicated helper — see setup_rich.py in this dossier's scratchpad for
    # the interactive population step). Re-used verbatim across runs.
    if "Zrzuty — obiekty" in tpl_by_name:
        IDS["rich"] = tpl_by_name["Zrzuty — obiekty"]["id"]
    else:
        _, created = api_post(
            demo,
            "/api/templates",
            {
                "name": "Zrzuty — obiekty",
                "format_id": 8,
                "width_mm": 120,
                "height_mm": 90,
                "canvas_data": {"objects": [], "stage": {"width_mm": 120, "height_mm": 90}},
            },
        )
        IDS["rich"] = created["id"]
        print(f"NOTE: created empty rich template id={IDS['rich']} — populate via setup_rich.py")

    # Overflow-demo template: one text + one autoFit textBlock, used to force
    # PDF/series text-overflow warnings on demand.
    if "Zrzuty — przepełnienie" in tpl_by_name:
        IDS["overflow"] = tpl_by_name["Zrzuty — przepełnienie"]["id"]
    else:
        _, created = api_post(
            demo,
            "/api/templates",
            {
                "name": "Zrzuty — przepełnienie",
                "format_id": 8,
                "width_mm": 40,
                "height_mm": 30,
                "canvas_data": {
                    "stage": {"width_mm": 40, "height_mm": 30},
                    "objects": [
                        {
                            "id": "ov1", "type": "text", "x": 2, "y": 2, "text": "{{name}}",
                            "fontSize": 3, "fontFamily": "Inter, sans-serif", "fill": "#0f172a",
                        },
                        {
                            "id": "ov2", "type": "text", "x": 2, "y": 8, "width": 36, "height": 18,
                            "text": "{{opis}}", "fontSize": 3, "fontFamily": "Inter, sans-serif",
                            "fill": "#0f172a", "autoFit": True, "minFontSize": 2, "maxFontSize": 6,
                        },
                    ],
                },
            },
        )
        IDS["overflow"] = created["id"]

    # Static-text overflow template: a single-PDF generation (no series
    # mapping involved) needs literal long text, not an unresolved
    # `{{placeholder}}` — those render as their raw (short) syntax outside
    # a series job and never overflow.
    if "Zrzuty — ostrzeżenia PDF" in tpl_by_name:
        IDS["warnings_demo"] = tpl_by_name["Zrzuty — ostrzeżenia PDF"]["id"]
    else:
        long_text = (
            "To jest bardzo dlugi tekst ktory na pewno nie zmiesci sie w tym malutkim "
            "bloku niezaleznie od najmniejszej czcionki bo jest zbyt dlugi zdecydowanie "
            "za dlugi naprawde bardzo dlugi tekst"
        )
        _, created = api_post(
            demo,
            "/api/templates",
            {
                "name": "Zrzuty — ostrzeżenia PDF",
                "format_id": 8,
                "width_mm": 40,
                "height_mm": 30,
                "canvas_data": {
                    "stage": {"width_mm": 40, "height_mm": 30},
                    "objects": [
                        {
                            "id": "w1", "type": "text", "x": 2, "y": 2, "width": 36, "height": 24,
                            "text": long_text, "fontSize": 3, "fontFamily": "Inter, sans-serif",
                            "fill": "#0f172a", "autoFit": True, "minFontSize": 2, "maxFontSize": 6,
                        },
                    ],
                },
            },
        )
        IDS["warnings_demo"] = created["id"]

    # Admin-owned shared template so demo's Library "From users" section has
    # a real "Use" button (own shared templates only ever show "Your
    # template").
    _, admin_templates = api_get(admin, "/api/templates")
    if not any(t["name"] == "Etykieta magazynowa (admin)" for t in admin_templates.get("templates", [])):
        _, created = api_post(
            admin,
            "/api/templates",
            {
                "name": "Etykieta magazynowa (admin)",
                "format_id": 7,
                "canvas_data": {
                    "objects": [
                        {"id": "a1", "type": "text", "x": 4, "y": 4, "text": "{{name}}",
                         "fontSize": 5, "fontFamily": "Inter, sans-serif", "fill": "#0f172a"},
                        {"id": "a2", "type": "barcode", "x": 4, "y": 12, "width": 30, "height": 12,
                         "barcodeType": "code128", "data": "{{sku}}"},
                    ]
                },
            },
        )
        api_put(admin, f"/api/templates/{created['id']}", {"is_shared": True})

    # Device + real local connector for the print-modal fast path (F21).
    _, devices = api_get(demo, "/api/devices")
    existing = next((d for d in devices.get("devices", []) if d["name"] == "Ten komputer (test)"), None)
    if existing:
        IDS["device"] = existing["id"]
    else:
        _, created = api_post(demo, "/api/devices", {"name": "Ten komputer (test)"})
        IDS["device"] = created["device"]["id"]
        token = created["token"]
        cfg = SCRATCH / "fastpath-config.yaml"
        cfg.write_text(
            f'server_url: "{BASE}"\n'
            f'token: "{token}"\n'
            "poll_interval_seconds: 5\n"
            "heartbeat_interval_seconds: 10\n"
            'listen: "127.0.0.1:9110"\n'
            "printers:\n"
            '  - name: "test-plik"\n'
            f'    host: "file://{SCRATCH}/blg-wydruki"\n'
            "    port: 9100\n"
        )
        (SCRATCH / "blg-wydruki").mkdir(exist_ok=True)
        subprocess.Popen(
            [str(SCRATCH / "blg-connector-linux-amd64"), "-config", str(cfg)],
            stdout=open(SCRATCH / "connector.log", "a"),
            stderr=subprocess.STDOUT,
        )
        time.sleep(3)

    # A few captured labels for the Devices → Inbox table.
    _, caps = api_get(demo, "/api/captures")
    if len(caps.get("captures", [])) == 0 and IDS["device"]:
        _, devs = api_get(demo, "/api/devices")
        token_dev = next((d for d in devs.get("devices", []) if d["id"] == IDS["device"]), None)
        # Token isn't retrievable after creation; only reachable on first
        # creation above. If captures are already missing and no fresh token
        # is available, skip — non-fatal (best-effort in the report).
        print("NOTE: no captures and no fresh device token available — skip seeding captures")

    print("IDS:", IDS)


def is_local_agent_up() -> bool:
    try:
        req = urllib.request.Request("http://127.0.0.1:9110/status")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


# --------------------------------------------------------------------------
# Playwright helpers
# --------------------------------------------------------------------------


def jar_cookies(path: str) -> list[dict]:
    out = []
    for line in Path(path).read_text().splitlines():
        raw = line
        if raw.startswith("#HttpOnly_"):
            raw = raw[len("#HttpOnly_"):]
        elif raw.startswith("#") or not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) >= 7:
            name, value = parts[5], parts[6]
            out.append(
                {
                    "name": name, "value": value, "domain": DOMAIN, "path": "/",
                    "secure": True, "httpOnly": name == "session", "sameSite": "Lax",
                }
            )
    return out


L = {
    "pl": {
        "series": "Generuj serię", "next": "Dalej", "back": "Wstecz", "analyze": "Sprawdź",
        "import_zpl": "Importuj ZPL", "export_zpl": "⤒ ZPL", "export_tspl": "⤒ TSPL",
        "new_template": "Nowy szablon", "import_tpl": "Importuj", "settings_title": "Folder i udostępnianie",
        "save": "Zapisz", "close": "Zamknij", "cancel": "Anuluj", "create": "Utwórz",
        "new_folder": "Nowy folder", "folder_name_ph": "Nazwa folderu", "edit_folder": "Edytuj folder",
        "share_toggle": "Udostępnij w Bibliotece", "history_btn": "Historia", "preview_btn": "Podgląd",
        "label_size_btn": "📐", "print_btn": "Drukuj", "device_label": "Urządzenie (konektor)",
        "printer_label": "Drukarka", "connect_btn": "Podłącz drukarkę", "create_advanced": "Zaawansowane: utwórz token",
        "device_name_ph": "np. Komputer w magazynie", "use_source": "Użyj tego źródła",
        "show_advanced": "Pokaż zaawansowane", "test_filter": "Sprawdź filtr", "start_series": "Generuj PDF",
        "download_pdf": "Pobierz PDF", "export_btn": "Eksportuj", "choose_file": "Wybierz plik…",
        "create_account": "Utwórz konto", "reset_password": "Resetuj hasło", "used": "Użyj",
    },
    "en": {
        "series": "Generate series", "next": "Next", "back": "Back", "analyze": "Analyze",
        "import_zpl": "Import ZPL", "export_zpl": "⤒ ZPL", "export_tspl": "⤒ TSPL",
        "new_template": "New template", "import_tpl": "Import", "settings_title": "Folder & sharing",
        "save": "Save", "close": "Close", "cancel": "Cancel", "create": "Create",
        "new_folder": "New folder", "folder_name_ph": "Folder name", "edit_folder": "Edit folder",
        "share_toggle": "Share in the Library", "history_btn": "History", "preview_btn": "Preview",
        "label_size_btn": "📐", "print_btn": "Print", "device_label": "Device (connector)",
        "printer_label": "Printer", "connect_btn": "Connect a printer", "create_advanced": "Advanced: create a token",
        "device_name_ph": "e.g. Warehouse PC", "use_source": "Use this source",
        "show_advanced": "Show advanced", "test_filter": "Test filter", "start_series": "Generate PDF",
        "download_pdf": "Download PDF", "export_btn": "Export", "choose_file": "Choose file…",
        "create_account": "Create account", "reset_password": "Reset password", "used": "Use",
    },
}

SAMPLE_ZPL = """^XA
^CI28
^FO40,40^A@N,40,40,E:ARI000.TTF^FB720,1,0,L,0^FDHerbata zielona Sencha^FS
^FO40,120^A@N,28,28,E:ARI001.TTF^FDZuzyc do: {DATA}^FS
^FO40,180^BY2^BCN,90,Y,N,N^FD5901234123457^FS
^PQ1,0,1,Y
^XZ"""


def shoot(page: Page, path: Path, clip=None, full_page=False, name: str | None = None, lang: str = "") -> bool:
    try:
        page.screenshot(path=str(path), clip=clip, full_page=full_page)
    except Exception as e:
        if name:
            mark(name, lang, f"FAIL (screenshot error: {e})")
        return False
    size = path.stat().st_size if path.exists() else 0
    # Tight close-up crops (a few toolbar icons on a flat background)
    # legitimately compress to a couple KB — 1200B is a better floor for
    # "not literally blank" than a flat 5KB rule.
    ok = size > 1200
    if name:
        mark(name, lang, "ok" if ok else f"FAIL (tiny file {size}B)")
    return ok


def clip_of(locator, pad=8):
    box = locator.bounding_box()
    if not box:
        return None
    return {
        "x": max(0, box["x"] - pad), "y": max(0, box["y"] - pad),
        "width": box["width"] + 2 * pad, "height": box["height"] + 2 * pad,
    }


def highlight(page: Page, selector_js: str, color: str = "#6366f1") -> None:
    """Draw an arrow + ring around the first element matched by a JS
    querySelector-style function (passed as a JS expression string)."""
    page.evaluate(
        f"""() => {{
        const el = ({selector_js});
        if (!el) return;
        const r = el.getBoundingClientRect();
        el.style.outline = '3px solid {color}';
        el.style.outlineOffset = '3px';
        el.style.boxShadow = '0 0 0 6px rgba(99,102,241,0.35)';
        const arrow = document.createElement('div');
        // Prefer pointing in from the left; if there isn't ~50px of room
        // there (e.g. a sidebar item flush against the viewport edge),
        // point down from above instead so the arrow is never clipped.
        const hasLeftRoom = r.left >= 50;
        arrow.textContent = hasLeftRoom ? '→' : '↓';
        arrow.style.position = 'fixed';
        if (hasLeftRoom) {{
            arrow.style.left = (r.left - 46) + 'px';
            arrow.style.top = (r.top + r.height/2 - 18) + 'px';
        }} else {{
            arrow.style.left = (r.left + r.width/2 - 12) + 'px';
            arrow.style.top = (Math.max(0, r.top - 40)) + 'px';
        }}
        arrow.style.fontSize = '34px';
        arrow.style.color = '{color}';
        arrow.style.fontWeight = '900';
        arrow.style.zIndex = 99999;
        arrow.setAttribute('data-shot-arrow', '1');
        document.body.appendChild(arrow);
    }}"""
    )


def clear_highlights(page: Page) -> None:
    page.evaluate(
        "() => document.querySelectorAll('[data-shot-arrow]').forEach(e => e.remove())"
    )


def mask_emails(page: Page) -> None:
    page.evaluate(
        """() => {
        const repl = {'tomasz@mazowszebakery.co.uk': 'jan.kowalski@example.com'};
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let n; while ((n = walker.nextNode())) {
            for (const [a, b] of Object.entries(repl))
                if (n.textContent.includes(a)) n.textContent = n.textContent.replaceAll(a, b);
        }
    }"""
    )


# --------------------------------------------------------------------------
# Object gallery (template "Zrzuty — obiekty") — mm-space object map, used to
# click precisely on the canvas by converting mm -> px via the stage scale.
# --------------------------------------------------------------------------

GALLERY_OBJECTS = {
    "text": (20, 7),
    "textblock": (29, 27),
    "rect": (20, 55),
    "line": (20, 75),
    "barcode": (90, 25),
    "table": (85, 52),
    "image": (92, 77),
    "background_gap": (50, 45),  # empty strip between the two columns
}
GALLERY_WIDTH_MM = 120


def canvas_scale(page: Page) -> tuple[float, float, float]:
    box = page.locator(".konvajs-content").first.bounding_box()
    scale = box["width"] / GALLERY_WIDTH_MM
    return scale, box["x"], box["y"]


def click_mm(page: Page, x_mm: float, y_mm: float, shift=False, alt=False) -> None:
    scale, ox, oy = canvas_scale(page)
    x, y = ox + x_mm * scale, oy + y_mm * scale
    if shift:
        page.keyboard.down("Shift")
    if alt:
        page.keyboard.down("Alt")
    try:
        page.mouse.click(x, y)
    finally:
        if shift:
            page.keyboard.up("Shift")
        if alt:
            page.keyboard.up("Alt")


def run_lang(browser, lang: str) -> None:
    t = L[lang]
    out = OUT / lang
    out.mkdir(parents=True, exist_ok=True)
    # Unique-ish suffix for anything this run creates server-side (devices,
    # …) so re-running the script never collides with a leftover from a
    # previous pass (e.g. "device_name_taken").
    run_tag = f"{lang}-{int(time.time())}"

    def new_ctx(cookies):
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900}, device_scale_factor=2,
            locale="pl-PL" if lang == "pl" else "en-GB", ignore_https_errors=True,
            accept_downloads=True,
        )
        ctx.add_init_script(f"localStorage.setItem('i18nextLng','{lang}')")
        if cookies:
            ctx.add_cookies(cookies)
        return ctx

    DEMO = jar_cookies(DEMO_JAR)
    ADMIN = jar_cookies(ADMIN_JAR)

    # ---- 1. login (no session) --------------------------------------------
    ctx = new_ctx(None)
    page = ctx.new_page()
    page.goto(BASE + "/login", wait_until="networkidle")
    shoot(page, out / "login.png", name="login.png", lang=lang)
    ctx.close()

    # ================= demo session : main flows ===========================
    ctx = new_ctx(DEMO)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())

    # ---- 3. dashboard (highlight "Templates" nav item) ---------------------
    page.goto(BASE + "/", wait_until="networkidle")
    page.wait_for_timeout(300)
    highlight(page, "[...document.querySelectorAll('nav a')].find(a => a.getAttribute('href') === '/templates')")
    shoot(page, out / "TODO-dashboard-empty.png", name="TODO-dashboard-empty.png", lang=lang)
    clear_highlights(page)

    # ---- 4/5. Templates page: new-template button + dialog -----------------
    page.goto(BASE + "/templates", wait_until="networkidle")
    page.wait_for_timeout(400)
    highlight(page, f"[...document.querySelectorAll('button')].find(b => b.textContent.includes('{t['new_template']}'))")
    shoot(page, out / "TODO-new-template-button.png", name="TODO-new-template-button.png", lang=lang)
    clear_highlights(page)

    page.locator("button", has_text=t["new_template"]).first.click()
    page.wait_for_timeout(300)
    modal = page.locator("div.fixed.inset-0 > div").first
    modal.locator("input").first.fill("Etykieta testowa")
    # pick the custom-size option (last <optgroup>'s first <option>)
    select = modal.locator("select").first
    try:
        select.select_option(label="Własny rozmiar (zdefiniuj)" if lang == "pl" else "Custom (define size)")
    except Exception:
        opts = select.locator("option")
        select.select_option(index=opts.count() - 1)
    page.wait_for_timeout(300)
    shoot(page, out / "TODO-new-template-dialog.png", clip=clip_of(modal),
          name="TODO-new-template-dialog.png", lang=lang)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # ---- 6. templates list --------------------------------------------------
    page.goto(BASE + "/templates", wait_until="networkidle")
    page.wait_for_timeout(400)
    shoot(page, out / "templates.png", name="templates.png", lang=lang)

    # ---- 9. folder rail close-up ---------------------------------------------
    # NB: AppLayout renders its own nav <aside> too — the folder rail is the
    # *second* <aside> on the page, nested inside <main>.
    rail = page.locator("main aside").first
    shoot(page, out / "TODO-folder-rail.png", clip=clip_of(rail, pad=12),
          name="TODO-folder-rail.png", lang=lang)

    # ---- 10. folder menu on a template card ---------------------------------
    card = page.locator("a[href*='/edit']").first
    card.hover()
    page.wait_for_timeout(200)
    gear_btn = card.locator("button", has_text="⚙").first
    gear_btn.click()
    page.wait_for_timeout(400)
    modal = page.locator("div.fixed.inset-0 > div").first
    shoot(page, out / "TODO-folder-menu.png", clip=clip_of(modal), name="TODO-folder-menu.png", lang=lang)

    # ---- 13. share-template checkbox ----------------------------------------
    modal.locator("input[type=checkbox]").first.check()
    page.wait_for_timeout(200)
    shoot(page, out / "TODO-share-template.png", clip=clip_of(modal), name="TODO-share-template.png", lang=lang)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # ---- 11. folder edit modal (color palette) ------------------------------
    # Edit/delete icons are children of the folder's own <button> (revealed
    # via CSS group-hover). Match on the `title` attribute, not `has_text` —
    # has_text matches ancestor spans too (their concatenated text also
    # "contains" ✎), and .first then resolves to a wrapper whose click
    # point can land on the *delete* icon instead. (Learned the hard way —
    # this deleted the folder twice while developing this script.)
    folder_btn = rail.locator("button", has_text="Kosmetyki").first
    folder_btn.hover()
    page.wait_for_timeout(300)
    pencil = folder_btn.locator(f"span[title='{t['edit_folder']}']").first
    pencil.click()
    page.wait_for_timeout(300)
    modal = page.locator("div.fixed.inset-0 > div").first
    shoot(page, out / "TODO-folder-edit.png", clip=clip_of(modal), name="TODO-folder-edit.png", lang=lang)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # ---- 12. Library page ---------------------------------------------------
    page.goto(BASE + "/library", wait_until="networkidle")
    page.wait_for_timeout(700)
    shoot(page, out / "TODO-library-page.png", full_page=True, name="TODO-library-page.png", lang=lang)

    # ================= editor: template 97 (main demo template) ============
    TPL_ID = IDS["tpl_main"]
    page.goto(f"{BASE}/templates/{TPL_ID}/edit", wait_until="networkidle")
    page.wait_for_timeout(1500)
    shoot(page, out / "editor-overview.png", name="editor-overview.png", lang=lang)

    # ---- label size modal ----------------------------------------------------
    page.locator("button", has_text="📐").first.click()
    page.wait_for_timeout(400)
    shoot(page, out / "label-size.png", name="label-size.png", lang=lang)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # ---- dynamic fields + date chip ------------------------------------------
    box = page.locator(".konvajs-content").first.bounding_box()
    scale97 = box["width"] / 50.0
    page.mouse.click(box["x"] + 10 * scale97, box["y"] + 13.5 * scale97)
    page.wait_for_timeout(500)
    aside = page.locator("aside").last
    if aside.locator("textarea").count() == 0:
        page.mouse.click(box["x"] + 8 * scale97, box["y"] + 6 * scale97)
        page.wait_for_timeout(500)
    ab = aside.bounding_box()
    shoot(page, out / "dynamic-fields.png",
          clip={"x": ab["x"], "y": ab["y"], "width": ab["width"], "height": min(ab["height"], 620)},
          name="dynamic-fields.png", lang=lang)
    chip = page.locator("span", has_text=re.compile(r"\{\{date\+14d\}\} →")).first
    cb = chip.bounding_box()
    if cb:
        shoot(page, out / "date-chip.png",
              clip={"x": ab["x"], "y": max(ab["y"], cb["y"] - 150), "width": ab["width"], "height": cb["height"] + 190},
              name="date-chip.png", lang=lang)
    else:
        mark("date-chip.png", lang, "FAIL (chip not found)")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # ---- alignment bar: select-all then label the 4 groups -------------------
    page.keyboard.press("Control+a")
    page.wait_for_timeout(300)
    anchor_js = {
        "page": "document.querySelector(\"button[title*='lewej krawędzi strony'], button[title*='page left']\")",
        "selection": "document.querySelector(\"button[title*='lewe krawędzie'], button[title*='left edges of selection']\")",
        "distribute": "document.querySelector(\"button[title*='Rozłóż równomiernie poziomo'], button[title*='Distribute horizontally']\")",
        "layer": "document.querySelector(\"button[title*='sam dół'], button[title*='Send to back']\")",
    }
    page.evaluate(
        """(anchors) => {
        // `expr` values are static strings authored in this file (never
        // user input) — each is a plain `document.querySelector(...)` call
        // used only to locate a DOM anchor for an overlay label, so eval()
        // here carries no injection risk. Kept as eval (not Function) only
        // because the expressions reference nothing beyond globals.
        const labels = {page: 'STRONA', selection: 'ZAZNACZENIE', distribute: 'ROZŁÓŻ', layer: 'WARSTWA'};
        for (const [key, expr] of Object.entries(anchors)) {
            const el = eval(expr);
            if (!el) continue;
            const r = el.getBoundingClientRect();
            const lab = document.createElement('div');
            lab.textContent = '↓ ' + labels[key];
            lab.style.position = 'fixed';
            lab.style.left = (r.left - 10) + 'px';
            lab.style.top = (r.top - 22) + 'px';
            lab.style.fontSize = '11px';
            lab.style.fontWeight = '800';
            lab.style.color = '#facc15';
            lab.style.zIndex = 99999;
            lab.setAttribute('data-shot-arrow', '1');
            document.body.appendChild(lab);
        }
    }""",
        anchor_js,
    )
    bar = page.locator("div.flex.items-center.gap-2.border-b").first
    shoot(page, out / "TODO-alignment-bar-groups.png", clip=clip_of(bar, pad=20),
          name="TODO-alignment-bar-groups.png", lang=lang)
    clear_highlights(page)

    # ---- layer buttons close-up ------------------------------------------
    layer_first = page.locator("button[title*='sam dół'], button[title*='Send to back']").first
    layer_last = page.locator("button[title*='sam wierzch'], button[title*='Bring to front']").first
    b1, b2 = layer_first.bounding_box(), layer_last.bounding_box()
    if b1 and b2:
        clip = {"x": b1["x"] - 30, "y": b1["y"] - 10, "width": (b2["x"] + b2["width"]) - b1["x"] + 40, "height": b1["height"] + 20}
        shoot(page, out / "TODO-layer-buttons.png", clip=clip, name="TODO-layer-buttons.png", lang=lang)
    else:
        mark("TODO-layer-buttons.png", lang, "FAIL (buttons not found)")

    # ---- undo/redo close-up ---------------------------------------------
    undo_btn = page.locator("button[title*='Ctrl+Z'], button[title*='(Ctrl+Z)']").first
    redo_btn = page.locator("button[title*='Ctrl+Y'], button[title*='(Ctrl+Y)']").first
    b1, b2 = undo_btn.bounding_box(), redo_btn.bounding_box()
    if b1 and b2:
        clip = {"x": b1["x"] - 15, "y": b1["y"] - 15, "width": (b2["x"] + b2["width"]) - b1["x"] + 30, "height": b1["height"] + 30}
        shoot(page, out / "TODO-undo-redo-buttons.png", clip=clip, name="TODO-undo-redo-buttons.png", lang=lang)
    else:
        mark("TODO-undo-redo-buttons.png", lang, "FAIL (buttons not found)")

    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # ---- editor export-button close-up -----------------------------------
    exp_btn = page.locator("button", has_text=re.compile("Eksportuj|Export$")).first
    dl_btn = page.locator("button", has_text=re.compile("Pobierz PDF|Download PDF")).first
    b1, b2 = exp_btn.bounding_box(), dl_btn.bounding_box()
    if b1 and b2:
        clip = {"x": b1["x"] - 15, "y": b1["y"] - 12, "width": (b2["x"] + b2["width"]) - b1["x"] + 30, "height": b1["height"] + 24}
        shoot(page, out / "TODO-editor-export-button.png", clip=clip, name="TODO-editor-export-button.png", lang=lang)
    else:
        mark("TODO-editor-export-button.png", lang, "FAIL (buttons not found)")

    # ---- autosave status: dirty state --------------------------------------
    page.keyboard.press("Control+a")
    page.wait_for_timeout(150)
    page.keyboard.press("Escape")
    box = page.locator(".konvajs-content").first.bounding_box()
    page.mouse.click(box["x"] + 10 * scale97, box["y"] + 5 * scale97)
    page.wait_for_timeout(300)
    xin = page.locator("aside").last.locator("label", has_text=re.compile("^X")).locator(
        "xpath=following-sibling::input"
    ).first
    if xin.count():
        cur = xin.input_value()
        try:
            xin.fill(str(float(cur) + 1))
            xin.blur()
        except Exception:
            pass
    page.wait_for_timeout(300)
    toolbar = page.locator("div.flex.items-center.justify-between.gap-3.border-b").first
    tb = toolbar.bounding_box()
    if tb:
        shoot(page, out / "TODO-autosave-status.png",
              clip={"x": tb["x"], "y": tb["y"], "width": min(tb["width"], 520), "height": tb["height"]},
              name="TODO-autosave-status.png", lang=lang)
    else:
        mark("TODO-autosave-status.png", lang, "FAIL (toolbar not found)")
    # save so we don't leave the template dirty for later steps
    page.keyboard.press("Control+s")
    page.wait_for_timeout(1200)
    page.keyboard.press("Escape")

    # ---- version history ---------------------------------------------------
    page.locator("button", has_text=t["history_btn"]).first.click()
    page.wait_for_timeout(600)
    modal = page.locator("div.fixed.inset-0 > div").first
    shoot(page, out / "TODO-version-history.png", clip=clip_of(modal), name="TODO-version-history.png", lang=lang)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # ---- print preview -------------------------------------------------------
    page.locator("button", has_text=t["preview_btn"]).first.click()
    page.wait_for_timeout(2500)
    shoot(page, out / "TODO-preview-pdf.png", name="TODO-preview-pdf.png", lang=lang)
    page.locator("div.fixed.inset-0 button", has_text=t["close"]).first.click()
    page.wait_for_timeout(300)

    # ---- TSPL export -----------------------------------------------------
    page.locator("button", has_text=t["export_tspl"]).first.click()
    page.wait_for_timeout(900)
    shoot(page, out / "TODO-tspl-export.png", name="TODO-tspl-export.png", lang=lang)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # ---- ZPL import / export (existing pair) --------------------------------
    page.locator("button", has_text=t["import_zpl"]).first.click()
    page.wait_for_timeout(300)
    page.locator("div.fixed.inset-0 textarea").last.fill(SAMPLE_ZPL)
    page.locator("button", has_text=t["analyze"]).first.click()
    page.wait_for_timeout(900)
    shoot(page, out / "zpl-import.png", name="zpl-import.png", lang=lang)
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)

    page.locator("button", has_text=t["export_zpl"]).first.click()
    page.wait_for_timeout(900)
    shoot(page, out / "zpl-export.png", name="zpl-export.png", lang=lang)
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)

    # ---- print modal: connector device + fast path --------------------------
    local_up = is_local_agent_up()
    page.locator("button", has_text=t["print_btn"]).first.click()
    page.wait_for_timeout(1200)
    if local_up:
        # Local agent running → "⚡ this computer" is preselected by default.
        shoot(page, out / "TODO-connector-fastpath.png", name="TODO-connector-fastpath.png", lang=lang)
        # switch to the real connector device for the queued-print shot
        sel = page.locator("div.fixed.inset-0 select").first
        try:
            sel.select_option(label=re.compile("Ten komputer \\(test\\)|online|●"))
        except Exception:
            opts = sel.locator("option")
            if opts.count() > 1:
                sel.select_option(index=1)
        page.wait_for_timeout(500)
    else:
        mark("TODO-connector-fastpath.png", lang, "FAIL (no local agent reachable)")
    page.wait_for_timeout(400)
    shoot(page, out / "TODO-connector-print-dialog.png", name="TODO-connector-print-dialog-pre.png", lang=lang)
    submit_btn = page.locator("div.fixed.inset-0 button", has_text=t["print_btn"]).last
    if submit_btn.is_enabled():
        submit_btn.click()
        page.wait_for_timeout(1500)
        shoot(page, out / "TODO-connector-print-dialog.png", name="TODO-connector-print-dialog.png", lang=lang)
    else:
        mark("TODO-connector-print-dialog.png", lang, "FAIL (submit disabled)")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # ---- PDF overflow warnings chip (static long text — see warnings_demo) --
    if IDS["warnings_demo"]:
        page.goto(f"{BASE}/templates/{IDS['warnings_demo']}/edit", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.locator("button", has_text=t["download_pdf"]).first.click()
        page.wait_for_timeout(2500)
        chip = page.locator("span", has_text=re.compile(r"⚠")).first
        cb = chip.bounding_box() if chip.count() else None
        if cb:
            shoot(page, out / "TODO-warnings-chip.png",
                  clip={"x": cb["x"] - 40, "y": cb["y"] - 16, "width": cb["width"] + 80, "height": cb["height"] + 32},
                  name="TODO-warnings-chip.png", lang=lang)
        else:
            mark("TODO-warnings-chip.png", lang, "FAIL (no warnings chip appeared)")

    ctx.close()

    # ================= editor: rich object-gallery template =================
    ctx = new_ctx(DEMO)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    RID = IDS["rich"]
    page.goto(f"{BASE}/templates/{RID}/edit", wait_until="networkidle")
    page.wait_for_timeout(1200)

    def select_object_shot(mm_xy, filename):
        click_mm(page, *mm_xy)
        page.wait_for_timeout(400)
        shoot(page, out / filename, name=filename, lang=lang)

    select_object_shot(GALLERY_OBJECTS["text"], "TODO-object-text.png")
    select_object_shot(GALLERY_OBJECTS["textblock"], "TODO-object-textblock.png")
    select_object_shot(GALLERY_OBJECTS["rect"], "TODO-object-shapes.png")
    select_object_shot(GALLERY_OBJECTS["barcode"], "TODO-object-barcode.png")
    select_object_shot(GALLERY_OBJECTS["table"], "TODO-object-table.png")
    select_object_shot(GALLERY_OBJECTS["image"], "TODO-object-image.png")
    select_object_shot(GALLERY_OBJECTS["background_gap"], "TODO-object-background.png")

    # lock/print checkboxes close-up (background object still selected)
    right = page.locator("aside").last
    rb = right.bounding_box()
    if rb:
        shoot(page, out / "TODO-lock-print-checkboxes.png",
              clip={"x": rb["x"], "y": rb["y"], "width": rb["width"], "height": 190},
              name="TODO-lock-print-checkboxes.png", lang=lang)

    # resize handles: select the rect alone
    click_mm(page, *GALLERY_OBJECTS["rect"])
    page.wait_for_timeout(300)
    scale, ox, oy = canvas_scale(page)
    rx, ry = ox + 5 * scale, oy + 45 * scale
    rw, rh = 30 * scale, 20 * scale
    shoot(page, out / "TODO-resize-handles.png",
          clip={"x": rx - 20, "y": ry - 40, "width": rw + 40, "height": rh + 60},
          name="TODO-resize-handles.png", lang=lang)

    # multiselect: barcode + rect + table (shift-click)
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    click_mm(page, *GALLERY_OBJECTS["barcode"])
    page.wait_for_timeout(150)
    click_mm(page, *GALLERY_OBJECTS["rect"], shift=True)
    page.wait_for_timeout(150)
    click_mm(page, *GALLERY_OBJECTS["table"], shift=True)
    page.wait_for_timeout(300)
    shoot(page, out / "TODO-multiselect.png", name="TODO-multiselect.png", lang=lang)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # duplicate via alt+drag: drag the rect, drop it elsewhere
    scale, ox, oy = canvas_scale(page)
    start = (ox + 20 * scale, oy + 55 * scale)
    end = (ox + 95 * scale, oy + 30 * scale)
    page.keyboard.down("Alt")
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(*end, steps=12)
    page.wait_for_timeout(150)
    page.mouse.up()
    page.keyboard.up("Alt")
    page.wait_for_timeout(500)
    shoot(page, out / "TODO-duplicate-altdrag.png", name="TODO-duplicate-altdrag.png", lang=lang)
    page.keyboard.press("Control+z")  # undo the accidental duplicate
    page.wait_for_timeout(300)
    page.keyboard.press("Escape")

    # do NOT save this scratch template's transient edits
    ctx.close()

    # ================= series wizard: upload / csv preview / sqlite / filter / progress ===
    ctx = new_ctx(DEMO)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(f"{BASE}/templates/{TPL_ID}/edit", wait_until="networkidle")
    page.wait_for_timeout(1000)

    page.locator("button", has_text=t["series"]).first.click()
    page.wait_for_timeout(400)
    shoot(page, out / "TODO-series-step1-upload.png", name="TODO-series-step1-upload.png", lang=lang)

    modal = page.locator("div.fixed.inset-0")
    modal.locator("input[type=file]").first.set_input_files("/tmp/demo-data.csv")
    page.wait_for_selector(f"text=/demo-data.csv/", timeout=15000)
    page.wait_for_timeout(400)
    shoot(page, out / "TODO-series-csv-preview.png", name="TODO-series-csv-preview.png", lang=lang)

    page.wait_for_selector(f"button:has-text('{t['next']}'):not([disabled])", timeout=15000)
    page.locator("button", has_text=t["next"]).first.click()
    page.wait_for_timeout(600)
    shoot(page, out / "series-map.png", name="series-map.png", lang=lang)

    page.locator("button", has_text=t["next"]).first.click()
    page.wait_for_timeout(400)
    modal.locator("input[type=checkbox]").first.check()
    page.wait_for_timeout(200)
    col_select = modal.locator("select").first
    try:
        col_select.select_option(label="cena")
    except Exception:
        pass
    op_select = modal.locator("select").nth(1)
    try:
        op_select.select_option(label="większe niż" if lang == "pl" else "greater than")
    except Exception:
        pass
    modal.locator("input[type=text], input:not([type])").last.fill("10")
    page.locator("button", has_text=t["test_filter"]).first.click()
    page.wait_for_timeout(700)
    shoot(page, out / "TODO-series-filter.png", name="TODO-series-filter.png", lang=lang)
    page.locator("button", has_text=t["next"]).first.click()
    page.wait_for_timeout(400)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

    # progress bar: fresh wizard, big CSV
    page.locator("button", has_text=t["series"]).first.click()
    page.wait_for_timeout(400)
    modal = page.locator("div.fixed.inset-0")
    modal.locator("input[type=file]").first.set_input_files(str(SCRATCH / "big-series.csv"))
    page.wait_for_selector("text=/big-series.csv/", timeout=15000)
    page.wait_for_timeout(300)
    page.locator("button", has_text=t["next"]).first.click()  # upload -> map
    page.wait_for_timeout(400)
    page.locator("button", has_text=t["next"]).first.click()  # map -> filter
    page.wait_for_timeout(400)
    page.locator("button", has_text=t["next"]).first.click()  # filter (skipped) -> generate
    page.wait_for_timeout(400)
    page.locator("button", has_text=t["start_series"]).first.click()
    page.wait_for_timeout(120)
    shoot(page, out / "TODO-series-progress.png", name="TODO-series-progress.png", lang=lang)
    page.wait_for_timeout(4000)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    ctx.close()

    # sqlite dataset (separate wizard instance)
    ctx = new_ctx(DEMO)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(f"{BASE}/templates/{TPL_ID}/edit", wait_until="networkidle")
    page.wait_for_timeout(1000)
    page.locator("button", has_text=t["series"]).first.click()
    page.wait_for_timeout(400)
    modal = page.locator("div.fixed.inset-0")
    modal.locator("input[type=file]").first.set_input_files(str(SCRATCH / "produkty.sqlite"))
    page.wait_for_timeout(1200)
    shoot(page, out / "TODO-series-sqlite-tables.png", name="TODO-series-sqlite-tables.png", lang=lang)

    details = modal.locator("summary")
    if details.count():
        details.first.click()
        page.wait_for_timeout(300)
        modal.locator("textarea").first.fill("SELECT name, cena FROM produkty WHERE cena > 20")
        page.wait_for_timeout(200)
        shoot(page, out / "TODO-series-sqlite-sql.png", name="TODO-series-sqlite-sql.png", lang=lang)
    else:
        mark("TODO-series-sqlite-sql.png", lang, "FAIL (advanced panel not found)")
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    ctx.close()

    # series warnings list: overflow-demo template + overflow csv
    if IDS["overflow"]:
        ctx = new_ctx(DEMO)
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(f"{BASE}/templates/{IDS['overflow']}/edit", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.locator("button", has_text=t["series"]).first.click()
        page.wait_for_timeout(400)
        modal = page.locator("div.fixed.inset-0")
        modal.locator("input[type=file]").first.set_input_files(str(SCRATCH / "overflow-series.csv"))
        page.wait_for_timeout(800)
        page.locator("button", has_text=t["next"]).first.click()  # upload -> map
        page.wait_for_timeout(400)
        page.locator("button", has_text=t["next"]).first.click()  # map -> filter
        page.wait_for_timeout(400)
        page.locator("button", has_text=t["next"]).first.click()  # filter (skipped) -> generate
        page.wait_for_timeout(400)
        page.locator("button", has_text=t["start_series"]).first.click()
        ok = False
        for _ in range(20):
            page.wait_for_timeout(1000)
            if page.locator("text=/warningsTitle|ostrzeżeń tekstu|row.*text overflow|przepełnieniem/i").count() > 0:
                ok = True
                break
            if page.locator("button", has_text=re.compile("Gotowe|Done")).count() > 0:
                break
        page.wait_for_timeout(500)
        shoot(page, out / "TODO-series-warnings-list.png", name="TODO-series-warnings-list.png", lang=lang)
        if not ok:
            mark("TODO-series-warnings-list.png", lang, "ok (best-effort, warnings text not confirmed)")
        page.keyboard.press("Escape")
        ctx.close()

    # ================= import template modal (step1/step2) ==================
    ctx = new_ctx(DEMO)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(BASE + "/templates", wait_until="networkidle")
    page.wait_for_timeout(500)
    page.locator("button", has_text=t["import_tpl"]).first.click()
    page.wait_for_timeout(300)
    shoot(page, out / "TODO-import-step1.png", name="TODO-import-step1.png", lang=lang)
    modal = page.locator("div.fixed.inset-0")
    modal.locator("input[type=file]").first.set_input_files(str(SCRATCH / "rich-export.blg-template.json"))
    page.wait_for_timeout(1200)
    shoot(page, out / "TODO-import-step2.png", name="TODO-import-step2.png", lang=lang)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    ctx.close()

    # ================= devices page: inbox + connector-add-device ===========
    ctx = new_ctx(DEMO)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(BASE + "/devices", wait_until="networkidle")
    page.wait_for_timeout(700)
    shoot(page, out / "TODO-devices-inbox.png", full_page=True, name="TODO-devices-inbox.png", lang=lang)

    page.locator("button", has_text=t["create_advanced"]).first.click()
    page.wait_for_timeout(300)
    modal = page.locator("div.fixed.inset-0")
    modal.locator("input").first.fill(f"Kasa nr 2 ({run_tag})")
    modal.locator("button", has_text=t["create"]).first.click()
    page.wait_for_timeout(700)
    shoot(page, out / "TODO-connector-add-device.png", name="TODO-connector-add-device.png", lang=lang)
    page.locator("div.fixed.inset-0 button", has_text=t["close"]).first.click()
    page.wait_for_timeout(300)

    # ================= F38 connect-printer wizard ============================
    page.locator("button", has_text=t["connect_btn"]).first.click()
    page.wait_for_timeout(400)
    shoot(page, out / "connect-wizard-os.png", name="connect-wizard-os.png", lang=lang)

    page.locator("text=Linux").first.click()
    page.wait_for_timeout(400)
    name_input = page.locator("div.fixed.inset-0 input").first
    name_input.fill(f"Kasa — stanowisko 1 ({run_tag})")
    shoot(page, out / "connect-wizard-name.png", name="connect-wizard-name.png", lang=lang)

    created_token = {}

    def on_response(resp):
        if resp.request.method == "POST" and resp.url.endswith("/api/devices"):
            try:
                created_token["body"] = resp.json()
            except Exception:
                pass

    page.on("response", on_response)
    page.locator("div.fixed.inset-0 button", has_text=re.compile("Utwórz i pobierz|Create and get")).first.click()
    page.wait_for_timeout(1200)
    shoot(page, out / "connect-wizard-download.png", name="connect-wizard-download.png", lang=lang)

    page.locator("div.fixed.inset-0 button", has_text=re.compile(f"^{re.escape(t['next'])} →|{re.escape(t['next'])}")).first.click()
    page.wait_for_timeout(400)
    shoot(page, out / "connect-wizard-run.png", name="connect-wizard-run.png", lang=lang)

    page.locator("div.fixed.inset-0 button", has_text=re.compile("Sprawdź połączenie|Check connection")).first.click()
    page.wait_for_timeout(600)
    shoot(page, out / "connect-wizard-waiting.png", name="connect-wizard-waiting.png", lang=lang)

    # try to bring the freshly-created device online for real, so we can
    # reach the success + printer steps too.
    reached_success = False
    if created_token.get("body"):
        token = created_token["body"].get("token")
        dev = created_token["body"].get("device", {})
        if token:
            cfg = SCRATCH / f"wizard-device-{dev.get('id')}.yaml"
            cfg.write_text(
                f'server_url: "{BASE}"\ntoken: "{token}"\n'
                "poll_interval_seconds: 3\nheartbeat_interval_seconds: 5\n"
                'listen: "127.0.0.1:9111"\nprinters:\n'
                '  - name: "test-plik"\n'
                f'    host: "file://{SCRATCH}/blg-wydruki"\n'
                "    port: 9100\n"
            )
            proc = subprocess.Popen(
                [str(SCRATCH / "blg-connector-linux-amd64"), "-config", str(cfg)],
                stdout=open(SCRATCH / "connector-wizard.log", "a"), stderr=subprocess.STDOUT,
            )
            for _ in range(20):
                page.wait_for_timeout(1000)
                if page.locator("text=/Połączono|Connected/").count() > 0:
                    reached_success = True
                    break
            proc.terminate()

    if reached_success:
        page.wait_for_timeout(300)
        page.locator("div.fixed.inset-0 button", has_text=re.compile("Dodaj drukarkę|Add a printer")).first.click()
        page.wait_for_timeout(400)
        shoot(page, out / "connect-wizard-printer.png", name="connect-wizard-printer.png", lang=lang)
    else:
        mark("connect-wizard-printer.png", lang, "FAIL (device never reported online in time)")
    page.keyboard.press("Escape")
    ctx.close()

    # ================= admin: forced password change, then users ============
    # ChangePasswordPage only requires *a* logged-in user — it isn't gated
    # on must_change_password itself (only the auto-redirect from "/" is).
    # Visiting it directly is therefore a safe, read-only way to capture the
    # screen regardless of the account's current state, with no submission
    # and no mutation required.
    ctx = new_ctx(ADMIN)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(BASE + "/change-password", wait_until="networkidle")
    page.wait_for_timeout(400)
    shoot(page, out / "TODO-set-new-password.png", name="TODO-set-new-password.png", lang=lang)

    # The admin account still needs its *actual* forced change completed
    # once (a normal, expected, one-way setup step — not repeated/looped)
    # before /admin/users and the rest of the admin panel become reachable
    # at all. Only submitted the first time it's still pending.
    page.goto(BASE + "/", wait_until="networkidle")
    page.wait_for_timeout(400)
    if "/change-password" in page.url:
        pw_inputs = page.locator("input[type=password]")
        pw_inputs.nth(0).fill(ADMIN_PASSWORD)
        pw_inputs.nth(1).fill(ADMIN_FINAL_PASSWORD)
        pw_inputs.nth(2).fill(ADMIN_FINAL_PASSWORD)
        page.locator("button[type=submit]").first.click()
        page.wait_for_timeout(1000)
        print(f"[{lang}] completed the admin account's one-time forced password change")

    page.goto(BASE + "/admin/users", wait_until="networkidle")
    page.wait_for_timeout(500)
    mask_emails(page)
    shoot(page, out / "users-admin.png", name="users-admin.png", lang=lang)

    # Stable per-language throwaway account: created once, then reused by
    # later runs (idempotent — a second "Create" attempt would 409 on
    # email_already_exists, so we detect and skip in that case).
    throwaway_email = f"zrzuty.podglad.{lang}@blg.local"
    already_exists = page.locator("tr", has_text=throwaway_email).count() > 0

    page.locator("button", has_text=t["create_account"]).first.click()
    page.wait_for_timeout(300)
    modal = page.locator("div.fixed.inset-0")
    modal.locator("input[type=email]").first.fill(throwaway_email)
    shoot(page, out / "TODO-admin-create-user.png", clip=clip_of(modal.locator("> div").first),
          name="TODO-admin-create-user.png", lang=lang)
    if already_exists:
        page.locator("div.fixed.inset-0 button", has_text=t["cancel"]).first.click()
    else:
        modal.locator("button", has_text=t["create"]).first.click()
        page.wait_for_timeout(700)
        page.locator("div.fixed.inset-0 button", has_text=t["close"]).first.click()
    page.wait_for_timeout(500)
    mask_emails(page)

    # reset password on the throwaway account
    row = page.locator("tr", has_text=throwaway_email).first
    if row.count():
        row.locator("button", has_text=t["reset_password"]).first.click()
        page.wait_for_timeout(300)
        modal = page.locator("div.fixed.inset-0")
        modal.locator("button", has_text=t["reset_password"]).first.click()
        page.wait_for_timeout(600)
        shoot(page, out / "TODO-admin-reset-password.png", clip=clip_of(modal.locator("> div").first),
              name="TODO-admin-reset-password.png", lang=lang)
        page.locator("div.fixed.inset-0 button", has_text=t["close"]).first.click()
        page.wait_for_timeout(400)
    else:
        mark("TODO-admin-reset-password.png", lang, "FAIL (throwaway user row not found)")

    mask_emails(page)
    own_row = page.locator("tr", has_text=ADMIN_EMAIL).first
    other_row = page.locator("tr", has_text=throwaway_email).first
    if own_row.count() and other_row.count():
        b1, b2 = own_row.bounding_box(), other_row.bounding_box()
        top = min(b1["y"], b2["y"])
        bottom = max(b1["y"] + b1["height"], b2["y"] + b2["height"])
        shoot(page, out / "TODO-admin-active-toggle.png",
              clip={"x": b1["x"], "y": top - 4, "width": b1["width"], "height": bottom - top + 8},
              name="TODO-admin-active-toggle.png", lang=lang)
    else:
        mark("TODO-admin-active-toggle.png", lang, "FAIL (rows not found)")

    ctx.close()

    # ================= history page ==========================================
    ctx = new_ctx(DEMO)
    page = ctx.new_page()
    page.goto(BASE + "/history", wait_until="networkidle")
    page.wait_for_timeout(600)
    shoot(page, out / "TODO-generated-history.png", full_page=True, name="TODO-generated-history.png", lang=lang)
    ctx.close()


def main():
    demo = Session(DEMO_JAR, DEMO_EMAIL, DEMO_PASSWORD)
    admin = Session(ADMIN_JAR, ADMIN_EMAIL, ADMIN_PASSWORD)
    demo.ensure_login()
    admin.ensure_login(password_fallbacks=(ADMIN_FINAL_PASSWORD,))
    ensure_setup(demo, admin)

    langs = tuple(sys.argv[1:]) or ("pl", "en")
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        for lang in langs:
            try:
                run_lang(browser, lang)
            except Exception as e:
                print(f"FATAL in run_lang({lang}): {e}")
        browser.close()

    print("\n=== SUMMARY ===")
    for name in sorted(RESULTS):
        row = RESULTS[name]
        print(f"{name}: pl={row.get('pl','-')} en={row.get('en','-')}")
    Path("/tmp/capture-results.json").write_text(json.dumps(RESULTS, indent=2))
    print("DONE")


if __name__ == "__main__":
    main()
