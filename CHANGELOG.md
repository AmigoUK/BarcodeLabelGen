# Changelog

All notable changes to **BarcodeLabelGen** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Nothing yet._

## [0.12.1] — 2026-07-04

### Security
- Neutralized stored XSS via user-uploaded SVG: both image-serving
  endpoints (`/api/assets/images/:id`, `/api/templates/:id/featured-image`)
  now respond with `Content-Security-Policy: default-src 'none'; sandbox`
  and `X-Content-Type-Options: nosniff`, blocking script execution on
  direct navigation while leaving `<img>` thumbnails untouched.

## [0.12.0] — 2026-07-04

### Added
- **Folder colors (F32).** The folder ✎ now opens a proper edit dialog
  (replacing the window.prompt rename) with an 8-colour palette; the
  chosen colour shows as a dot next to the folder in the rail and on
  every template card belonging to it.
- **Featured images (F33).** The template ⚙ dialog gains an image
  upload (PNG/JPG/SVG, 5 MB); the thumbnail renders on Templates-page
  cards and in the Library. Served via
  `GET /api/templates/:id/featured-image` with template-level access,
  so library viewers see thumbnails of shared templates; cloning
  copies the image into the cloner's account. Alembic 0010.

## [0.11.0] — 2026-07-04

### Added
- **Template folders, the Library and sharing (F31, consolidating
  F15/F16).** Flat private folders organize the Templates page (rail
  with counts, All / No folder filters; deleting a folder strands its
  templates back to "No folder"; alembic 0009). A per-card
  ⚙ settings dialog moves templates between folders and shares them
  into the new **Library** page, which lists six bundled ready-made
  starters (product EAN-13 with dates, shipping address, shelf price,
  best-before, warehouse QR, inventory sticker — plain
  `.blg-template.json` files under `backend/app/library/`) alongside
  user-shared templates. "Use" always clones into your own templates
  (image assets copied across owners, sha256-deduped) and opens the
  editor. API: `/api/folders` CRUD, `scope=mine|library` +
  `folder_id` filters on the template list, `POST
  /api/templates/:id/clone`, `GET/POST /api/library/starters`.

### Changed
- **BREAKING (API):** `GET /api/templates` now returns only the
  caller's own templates by default; other users' shared templates
  moved to `?scope=library` (previously they were mixed into the main
  list). The UI reflects this: the Templates page is yours, the
  Library is everyone's.

## [0.10.0] — 2026-07-04

### Added
- **Browser fast path for printing (F21).** The print dialog probes the
  loopback connector (`http://127.0.0.1:9110`) when opened; if an agent
  runs on the same machine it appears as a preselected **⚡ This
  computer — instant print** target with its own printer list, and the
  label goes straight over the loopback with an immediate result — no
  server queue round-trip. Verified in real Chromium from the HTTPS
  origin (Private Network Access preflight answered by the agent). Any
  probe failure silently falls back to the queue path.
- **UAT checklist (`docs/UAT.md`, F30)** — owner-run manual tests (real
  Zebra hardware, Windows virtual printer, production data, resilience)
  gating the production go/no-go decision.
- Backlog: F31 — template folders / ready-made project library /
  sharing (to be brainstormed).

## [0.9.0] — 2026-07-04

### Added
- **Inbound ZPL validation (F29).** Every external ZPL entry point —
  the print queue, the import parser, virtual-printer captures and the
  agent's loopback `/print` — now runs a shared sanity gate: empty
  payloads, a missing/reversed `^XA…^XZ` envelope, and recognizable
  wrong formats (HTML error pages, PDF, PostScript, PCL, JSON) are
  rejected as `422 invalid_zpl` with a named reason. The import and
  print dialogs show a readable localized message instead of an error
  code, and the agent logs why it dropped a capture. Closes the gap
  found during v0.7.0 testing where an HTML 500-page could be queued
  and "printed".

## [0.8.0] — 2026-07-04

### Added
- **Connector phase D (F27): virtual printer + captures Inbox.** The
  agent's optional `capture` section opens a JetDirect-style listener —
  point a Windows printer (ZDesigner driver, Standard TCP/IP port →
  `127.0.0.1:9101`) at it and anything other applications print lands
  in the web app. Jobs spool locally (private 0700 dir, offline retries
  every 30 s) and upload to `POST /api/agent/captures` (base64; `^XA`
  sanity gate — the F29 minimum — keeps PCL/HTML noise out; 200 most
  recent kept per device). The **Inbox** on the Devices page lists
  captures with one-click **Open in editor** (ZPL parsed with DPI
  auto-detect, template created at the captured label size), copy-ZPL
  and delete. New table `captures` (alembic `0008`). User guide + FAQ
  updated (PL/EN), Windows setup walkthrough in `connector/README.md`.

### Fixed
- Security-review hardening of the capture spool: user-scoped default
  location (not the world-writable system temp), 0700/0600 permissions,
  and the uploader skips symlinks/non-regular files so a local attacker
  can't exfiltrate files through the agent's device token.

## [0.7.0] — 2026-07-04

### Added
- **Connector phase C (F25): the `blg-connector` Go agent + in-editor
  printing.** Single static binary (Linux amd64/arm64, Windows; release
  assets) that polls the print queue with its device token, sends ZPL to
  printers over RAW TCP 9100 (Zebra / JetDirect) or spools to a
  `file://` directory (simulated-printer mode), reports done/error and
  heartbeats its printer list. Loopback HTTP API on `127.0.0.1:9110`
  (`/status`, `/printers`, `/print`) for the future browser fast path —
  CORS locked to the configured server origin, JSON-only, copies capped.
  New editor **🖨 Print** dialog: pick an online device + reported
  printer + copies + DPI, queue the job and watch it live until the
  agent reports the outcome. User guide + FAQ updated (PL/EN).

### Fixed
- Loopback-API hardening from the automated security review: no
  cross-origin drive-by printing, no printer-topology disclosure to
  foreign sites, bounded `copies` multiplier.

## [0.6.0] — 2026-07-04

### Added
- **Connector phase B (F26): device tokens + server-side print queue.**
  New "Devices" page — register a local print agent and get its Bearer
  token (shown exactly once; only a SHA-256 digest is stored). Session
  API: `GET/POST/DELETE /api/devices`, `POST/GET /api/print-jobs`
  (fully-resolved ZPL, per-device queue, ownership-scoped). Agent API
  (Bearer auth, CSRF-exempt): `GET /api/agent/jobs` (poll-and-claim,
  pending→sent), `POST /api/agent/jobs/:id/status` (done/error),
  `POST /api/agent/state` (printer list + version heartbeat, drives the
  online indicator). New tables `devices`/`print_jobs` (alembic 0007).
  The Go agent itself lands in phase C.

## [0.5.1] — 2026-07-04

### Added
- **Real screenshots in the user guide (PL/EN).** The 20 described
  placeholders in `docs/HELP.{pl,en}.md` are now actual captures
  (login, templates, editor, label size, date chip, series wizard,
  ZPL import/export, admin panel), taken headlessly against a demo
  account. The in-app `/help` page bundles and renders them;
  regeneration script at `tools/capture-help-screenshots.py`.

### Fixed
- **Editor "dynamic fields" hint rendered raw i18next braces**
  (`{{'{{nazwa_kolumny}}'}}`) instead of the example placeholder —
  the hint now interpolates correctly in both languages.
- **Dependency security bumps** resolving all 7 open Dependabot
  alerts: vite 6.4.3 (high: `server.fs.deny` bypass), cryptography
  49.0.0 (high: vulnerable bundled OpenSSL), js-yaml 4.3.0,
  react-router 7.18.1, @babel/core 7.29.7, idna 3.18.

## [0.5.0] — 2026-07-04

### Added
- **Dynamic date placeholders** (`{{date}}`, `{{date+14d}}`, `{{date-7d}}`,
  `{{date+3m}}`, `{{date+1y}}`, optional format suffix like
  `{{date+14d:DD/MM/YY}}`; default `DD.MM.YYYY`). Computed at generation time
  on all output paths — single-label PDF, batch PDF, template ZPL export and
  batch ZPL. Month/year arithmetic clamps to month end (Jan 31 + 1m →
  Feb 28/29). A dataset column literally named `date` still wins for the
  plain `{{date}}` form; offset/format forms always compute. The editor
  inspector shows date placeholders as a green chip with a live preview, and
  the series wizard no longer requires mapping them to a column. Backend
  container now pins `TZ` (default `Europe/London`) so "today" matches the
  users' clock.
- **User guide + FAQ refresh (PL/EN).** In-app help now covers the ZPL
  round-trip, editable label size, DPI auto-detection and date placeholders;
  described screenshot placeholders were added for later capture; the
  never-shipped "Data imports" section was removed.
- **Backlog + design spec** for the local connector (`blg-connector`, Go):
  direct ZPL printing to network printers, server-side print queue with
  device tokens, and a Windows virtual-printer capture flow (F24–F28 in
  `docs/PROJECT.md`, spec in `docs/superpowers/specs/`).

## [0.4.1] — 2026-07-02

### Changed
- The project credit footer now also appears as a slim strip at the bottom
  of the editor workspace (previously shown only on full-shell pages).

## [0.4.0] — 2026-07-02

### Added
- **DPI auto-detection on ZPL import.** The import dialog now has an
  "Analyze" step and an "Auto-detect" DPI option (default): the backend
  infers the authoring density from the label's `^PW`/`^LL` measured against
  the current label size (falling back to a plausibility check, then 203
  dpi). `POST /api/zpl/parse` accepts `dpi: "auto"` with
  `target_width_mm`/`target_height_mm` and returns the `detected_dpi`.
- **Wrong-DPI / oversize hint.** After analyzing, the dialog shows the object
  count, the DPI used, and warns when the imported content extends beyond the
  label — a strong signal the DPI (or label size) needs adjusting before
  importing.

## [0.3.0] — 2026-07-01

### Added
- **Editable label size.** A new size button in the editor toolbar opens a
  dialog to change the label's width × height in millimetres (with common
  presets); the change is undoable and persists to the template, so a label
  can be resized without recreating it. `PUT /api/templates/:id` now accepts
  `width_mm` / `height_mm`, and saving the canvas keeps the template record
  in sync with the on-screen stage.

### Fixed
- **ZPL import no longer overrides the label size.** Importing ZPL brings in
  the elements but keeps the label dimensions you already set, instead of
  resizing the stage to the ZPL's `^PW`/`^LL` (or a 100×150 default when the
  code carried none). Use the new size button to change dimensions
  deliberately.

## [0.2.1] — 2026-07-01

### Fixed
- **White screen after a deploy.** nginx now serves `index.html` (and every
  SPA route) with `Cache-Control: no-cache`, so browsers always revalidate
  the entrypoint instead of holding a stale copy that references hashed JS
  chunks removed by the new build (`Failed to fetch dynamically imported
  module`). Fingerprinted assets stay `immutable`.

## [0.2.0] — 2026-07-01

### Added
- **ZPL / ZPL II round-trip.** Paste an existing ZPL label into the editor,
  adjust element positions visually on the canvas, and export native ZPL
  back out — to copy to the clipboard or download as `.zpl` — for use in
  external software.
  - Backend `services/zpl` engine: a symmetric parser (ZPL → `canvas_data`)
    and generator (`canvas_data` → native ZPL), mm↔dots at 203/300 dpi,
    a fixed bidirectional font map to printer-resident faces
    (`E:ARI000.TTF` / `E:ARI001.TTF`), and `{{column}}` batch rendering that
    reuses the PDF batch substitution.
  - Single-brace template variables (`{NAZWA}`, `{EAN}`), the print quantity
    (`^PQ{NoLabel}`), field blocks, hex-escape and `^FO` justification are
    preserved through the round-trip; unmodelled commands survive verbatim
    as passthrough.
  - Endpoints `POST /api/zpl/parse` and `POST /api/zpl/generate` (template
    sync + batch async via the shared job queue).
  - Editor toolbar gains **Import ZPL** and **Export ZPL**; the export panel
    shows a live preview with Copy / Download and a dataset batch mode.

## [0.1.0] — 2026-06-30

### Added
- Initial BarcodeLabelGen application: Konva-based label editor
  (text, rect, line, image, barcode/QR), PostgreSQL-backed templates and
  label formats, dataset upload (CSV/XLSX/SQLite) with `{{column}}`
  mail-merge, and PDF single-label + batch generation via ReportLab.

[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.12.1...HEAD
[0.12.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.12.1
[0.12.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.12.0
[0.11.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.11.0
[0.10.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.10.0
[0.9.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.9.0
[0.8.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.8.0
[0.7.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.7.0
[0.6.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.6.0
[0.5.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.5.1
[0.5.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.5.0
[0.4.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.4.1
[0.4.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.4.0
[0.3.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.3.0
[0.2.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.2.1
[0.2.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.2.0
[0.1.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.1.0
