# BarcodeLabelGen

> Web-based label editor and PDF batch generator for non-technical office users.
> Self-hosted, multilingual (PL + EN), runs on a single Docker host behind Tailscale.

<!--
  📸 SCREENSHOT — docs/screenshots/01-editor-hero.png
  ────────────────────────────────────────────────────
  Hero shot: the editor open on a real label template (e.g. Faktura A6 with
  a barcode + a couple of {{placeholder}} text fields). Capture the WHOLE
  editor — Toolbar at the top, LeftPanel (Add: T / ¶ / ▭ / ╱ / ▤ / 🖼 / 🌄)
  on the left, the Canvas with one object selected (transformer handles
  visible), AlignmentBar above the canvas, RightPanel with LayerProps
  expanded on the right. Browser chrome cropped out. ~1600 px wide.
-->
![Editor hero shot](docs/screenshots/01-editor-hero.png)

---

## What it does

- **Online label editor** — Konva-powered drag-and-drop canvas (text, blocks with auto-fit, rectangles, lines, images, barcodes, dynamic `{{column}}` fields).
- **Lockable + non-printable objects** — pin a logo so it can't be moved; drop a scan of a pre-printed sheet as a layout reference that stays out of the final PDF.
- **Layer order + alignment + distribute** — z-stack controls (front/back/forward/backward), 6 page-relative + 6 selection-relative align operations, equal distribution.
- **Duplicate fast** — Alt+drag a selected object to clone it under the cursor; Ctrl/Cmd+D to duplicate in place. Multi-select supported.
- **Barcodes** — EAN-13, EAN-14, GTIN, Code 128, GS1-128, QR (with checksum validation).
- **Series generation** — upload a CSV, Excel, or **SQLite** file, map placeholders to columns (or write a custom SELECT), optionally filter rows, get a single PDF with one label per row. Up to 1,000 labels per batch.
- **Template import / export** — every template is a single self-contained `.blg-template.json` (size, objects, embedded images). Cross-instance portable; partial import lets you skip objects + override the size.
- **Multilingual UI + in-app docs** — Polish + English from day one, with HELP + FAQ rendered inside the app.
- **Roles** — admin / editor / viewer; admin manages users + temporary password resets.
- **Label formats** — A4, A5, A6, common Zebra sizes (4×6", 4×4", 3×2", 2×1"), plus arbitrary custom mm.

---

## Screens

### The editor

<!--
  📸 SCREENSHOT — docs/screenshots/02-editor-multiselect.png
  ────────────────────────────────────────────────────────
  Same template as the hero, but with 3 objects selected via Shift+click.
  Show the AlignmentBar with the Selection group highlighted and the
  Layer/Distribute buttons visible. Right panel showing "3 objects
  selected — use the alignment bar above the canvas".
-->
![Multi-select alignment](docs/screenshots/02-editor-multiselect.png)

> Multi-select via Shift+click. The alignment bar grows a selection-relative group + a 4-button layer reorder group + horizontal/vertical distribute (3+ objects). One operation = one undo step.

### Series wizard — CSV/Excel

<!--
  📸 SCREENSHOT — docs/screenshots/03-series-csv-mapping.png
  ────────────────────────────────────────────────────────
  Generate Series modal at Step 2 (Mapping). Show the placeholders
  panel with 3-4 dynamic fields (e.g. {{sku}}, {{name}}, {{price}})
  auto-mapped to spreadsheet columns. Show the step indicator at the
  top. Use a real product CSV — readable column names.
-->
![Series wizard — mapping step](docs/screenshots/03-series-csv-mapping.png)

> Step 2 of the Generate Series wizard auto-maps `{{placeholder}}` fields whose names match a spreadsheet column. Otherwise pick the column from the dropdown.

### Series wizard — SQLite source

<!--
  📸 SCREENSHOT — docs/screenshots/04-series-sqlite-picker.png
  ────────────────────────────────────────────────────────
  Generate Series Step 1 after uploading a real .db file (e.g. parana.db
  or any sample SQLite with a few tables). Show the table dropdown
  expanded — sorted by row count, each row with "name (N columns, M
  rows)". Below it, the "Show advanced: custom SQL query" details
  block expanded with a sample SELECT query in the textarea.
-->
![SQLite source picker](docs/screenshots/04-series-sqlite-picker.png)

> Upload a `.db` / `.sqlite` / `.sqlite3` and the wizard offers a table picker (sorted by row count, biggest first) plus an "advanced" SELECT editor. Read-only connection, single-statement validator, 1,000-row cap.

### Template import / export

<!--
  📸 SCREENSHOT — docs/screenshots/05-import-modal.png
  ────────────────────────────────────────────────────────
  ImportTemplateModal at Phase 2 (Configure). Show:
    - the imported template name (editable),
    - width/height override fields (pre-filled),
    - the "Objects to import" checkbox list with 4-5 entries (some
      checked, one unchecked) and a {{…}} chip on the dynamic ones,
    - a "Duplicate images detected" radio row with reuse/copy choice,
    - one yellow warning if format hint missing,
    - the Cancel/Import buttons at the bottom.
-->
![Import template modal](docs/screenshots/05-import-modal.png)

> Each template exports to one `.blg-template.json` (size, objects, embedded images). Re-import with size override + per-object checklist + per-duplicate-image reuse/copy decision.

### Templates page

<!--
  📸 SCREENSHOT — docs/screenshots/06-templates-list.png
  ────────────────────────────────────────────────────────
  Templates page with 6-12 template cards in the grid (real names,
  varied sizes). Hover one card to show the ⬇ Export + ✕ Delete
  icons. Top-right shows the Search box + "⬆ Import" + "+ New
  template" buttons. Sidebar visible on the left.
-->
![Templates list](docs/screenshots/06-templates-list.png)

> Search-filterable grid. Each card hovers to reveal Export (⬇) + Delete (✕). The top-right pair gives Import (from file) and New (create from a format).

### In-app help

<!--
  📸 SCREENSHOT — docs/screenshots/07-help-page.png
  ────────────────────────────────────────────────────────
  /help page in Polish, with the Guide tab selected. Show the markdown
  rendered with proper styling — headings, bullet lists, the keyboard
  shortcuts table. Sidebar visible on the left with "Pomoc" highlighted.
  The two-tab toggle (Przewodnik / FAQ) visible top-right.
-->
![In-app help](docs/screenshots/07-help-page.png)

> The canonical HELP + FAQ Markdown lives in `docs/` and is bundled into the app at build time — one source, both an in-repo doc and an in-app page.

### Batch PDF output

<!--
  📸 SCREENSHOT — docs/screenshots/08-batch-pdf-pages.png
  ────────────────────────────────────────────────────────
  Screenshot of a generated PDF opened in a viewer (Acrobat / Preview /
  Chrome) showing 4-6 thumbnails of consecutive label pages. Each label
  has different data substituted from the spreadsheet, so the variation
  is visible at a glance. PDF info bar visible.
-->
![Generated batch PDF](docs/screenshots/08-batch-pdf-pages.png)

> One PDF, one label per row, ready to print. Up to 1,000 pages per batch.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Konva + TailwindCSS + react-router 7 + react-i18next + react-markdown |
| Backend | Python 3.12 + Flask 3 + uv + SQLAlchemy 2 + Alembic + ReportLab + python-barcode + qrcode + pandas + Pillow + pdfplumber |
| Database | PostgreSQL 16 (production) · SQLite (test fixture) |
| Cache + sessions + job queue | Redis 7 |
| Infrastructure | Docker + Docker Compose + nginx |
| Deployment | Linux host (`HOST`) fronted by Tailscale Serve |
| Tests | pytest (backend, 172 tests) + tsc + eslint (frontend) |

### Architecture overview

<!--
  📸 SCREENSHOT — docs/screenshots/09-architecture.png OR docs/architecture.svg
  ──────────────────────────────────────────────────────────────────────
  Optional: a simple 4-box diagram —
    Browser ─→ nginx (TLS via Tailscale) ─→ {Flask API, static SPA}
                                              ↓        ↑
                                     Postgres + Redis  Konva editor
  Plus uploads/ + assets/ + pdfs/ docker volumes.
  Can be hand-drawn, excalidraw, mermaid-rendered. Skip if too much.
-->

---

## Quick start

```bash
# Clone
git clone https://github.com/AmigoUK/BarcodeLabelGen.git
cd BarcodeLabelGen

# Build + start (Postgres + Redis + Flask + nginx)
docker compose up -d

# First-time DB migration (auto-runs on web container start; explicit form below)
docker compose exec web alembic upgrade head

# Bootstrap an admin account (replace email + password)
docker compose exec web flask create-admin --email you@example.com --password 'change-me-now-please'

# Open in your browser
open http://127.0.0.1:18003
```

### Behind Tailscale (recommended for production)

The service binds to `127.0.0.1:18003` only — to expose it to your tailnet (and get a free `*.ts.net` HTTPS cert):

```bash
tailscale serve --bg --https=18003 http://127.0.0.1:18003
# → https://<your-machine>.<tailnet>.ts.net:18003
```

### Development with hot reload

```bash
docker compose -f compose.dev.yml up
# Vite dev server + Flask debug, proxied through nginx.
```

---

## Documentation

- 📖 **[`docs/HELP.pl.md`](docs/HELP.pl.md)** / **[`docs/HELP.en.md`](docs/HELP.en.md)** — full user guide (onboarding, every feature, troubleshooting). Same content is rendered in-app at `/help`.
- ❓ **[`docs/FAQ.pl.md`](docs/FAQ.pl.md)** / **[`docs/FAQ.en.md`](docs/FAQ.en.md)** — common questions + error message recovery.
- 📐 **[`docs/PROJECT.md`](docs/PROJECT.md)** — original MVP specification (PL).

---

## Project structure

```
BarcodeLabelGen/
├── backend/
│   ├── app/
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routes/        # Flask blueprints (REST endpoints)
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── services/      # Business logic (PDF render, batch, datasets, …)
│   │   └── factory.py     # Flask app factory
│   ├── alembic/           # DB migrations (0001…0006)
│   ├── tests/             # pytest — 172 tests
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/    # Shared UI (Modal, Button, ImportTemplateModal, …)
│   │   ├── editor/        # Konva-based label editor (Canvas, panels, store)
│   │   ├── hooks/         # React-Query data hooks
│   │   ├── pages/         # Route components (Dashboard, Templates, Editor, Help, …)
│   │   ├── i18n/locales/  # PL + EN
│   │   └── lib/           # api client, csrf, download helper
│   └── package.json
├── docs/
│   ├── HELP.{pl,en}.md    # User guide (rendered in-app)
│   ├── FAQ.{pl,en}.md     # FAQ (rendered in-app)
│   ├── PROJECT.md         # MVP specification
│   └── screenshots/       # Images referenced from this README
├── compose.yml            # Production docker-compose
└── README.md              # ← you are here
```

---

## Status

✅ **Production** on `HOST.TAILNET.ts.net:18003` (Tailscale-only).
- Backend: 172 / 172 tests passing.
- QA harness (PDF render geometry checks): all formats ✅.
- Frontend: typecheck + lint + build clean; bundle 153 KB (gzipped 47 KB) main + lazy chunks for editor (Konva) and help (react-markdown).

---

## Credits

**dev@attv.uk · Project & Development: Tomasz 'Amigo' Lewandowski · [www.attv.uk](https://www.attv.uk) · [GitHub](https://github.com/AmigoUK/BarcodeLabelGen)**

## License

GPL-3.0 — see [`LICENSE`](LICENSE).
