# Changelog

All notable changes to **BarcodeLabelGen** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Nothing yet._

## [0.23.1] — 2026-07-08

### Fixed
- **macOS installer failed with "you do not have appropriate access
  privileges" on double-click** (found in the user's live E2E). A browser
  blob download can never carry the executable bit, so the bare `.command`
  could not be launched from Finder at all. The wizard now downloads
  **`BLG-Connect.zip`** — a minimal stored ZIP written in the browser with
  unix mode 0755 in its external attributes; Archive Utility restores the
  +x on extraction, so double-click works (after the one-time
  Privacy & Security "Open Anyway" approval). Verified end-to-end: the
  extracted file carries `-rwxr-xr-x`.

### Changed
- **Installer filenames are English/universal** (user feedback):
  `BLG-Connect.command` / `BLG-Connect.bat` / `blg-connect.sh` (macOS
  artifact: `BLG-Connect.zip`).
- **Installers self-verify in numbered steps** (AnyDesk-style guidance):
  [1/3] download+checksum → [2/3] background service + autostart →
  [3/3] the installer polls the connector's local status endpoint for up
  to 30 s and prints a clear success line or a where-to-look log hint.

## [0.23.0] — 2026-07-07

### Added
- **One-file connector installer + wizard v2 (F40).** The connect-a-printer
  wizard now generates a single personalized installer per OS
  (`Podlacz-BLG.command` / `Podlacz-BLG.bat` / `podlacz-blg.sh`) with the
  token and config embedded — no more separate binary + config.yaml download
  and no terminal commands to type. The installer autodetects the CPU
  architecture (the Apple/Intel question is gone), downloads the right binary
  from GitHub Releases, **verifies its SHA256 checksum**, and registers the
  connector as a background service with autostart: macOS LaunchAgent,
  Windows Task Scheduler (hidden window, log to file), Linux systemd --user
  (+ enable-linger). Re-running the installer updates/repairs the install
  (it preserves a previously enabled capture section). A new printers step
  lists the F39-discovered local printers live ("Zebra_ZD421 — local"), with
  network-IP as a collapsed advanced option that regenerates the installer;
  a final optional step sets up the virtual printer (one `--virtual-printer`
  command on macOS/Linux; a 4-step ZDesigner guide on Windows). Frontend-only;
  Vitest introduced for the installer generators (11 tests) and wired into CI.

### Changed
- **Wizard flow replaces the manual two-file download** — the old
  binary+config+terminal steps are gone from the UI; `connector/README.md`
  keeps the manual path for advanced users.

## [0.22.0] — 2026-07-07

### Added
- **Local (USB/system) printers via connector discovery (F39).** Every 60 seconds,
  the agent discovers system printer queues (macOS/Linux via CUPS `lpstat -e`,
  Windows via winspool) and reports them alongside configured `config.yaml`
  printers. A USB printer (e.g. Zebra ZD421) appears automatically as "printer
  from this computer" — zero configuration. Print via raw system spooler; name
  conflicts defer to YAML config. Kind badge shows the printer origin. No
  migration needed. Upgrade order: server before connectors — an older server
  rejects local printer entries (empty host) in the state report.
- **`SHA256SUMS` on every release** — the release workflow now generates and
  attaches a checksum file next to the connector binaries so downloads can be
  integrity-checked (added retroactively to v0.21.3 from the published assets).

## [0.21.3] — 2026-07-06

### Changed
- **CI: GitHub Actions bumped off deprecated Node 20 runners** — `checkout`
  v4→v7, `setup-go` v5→v6, `setup-node` v4→v6, `setup-uv` v4→v8.3.0. `release.yml`
  gains a `workflow_dispatch` trigger so binaries can be re-attached to an
  existing release manually.

### Fixed
- **CI on main is green again** (it had been red for 30+ commits, since
  ~v0.13.0). Frontend: Prettier formatting applied to 7 drifted files.
  Backend: all 21 Ruff findings fixed (line wraps, `StrEnum` migration,
  reviewed `noqa` for two S608 false positives on quote-escaped identifiers)
  plus 13 mypy errors (parameterized bare `dict` annotations, literal-typed
  `$schema`/`mime_type` in the template export path). No behavior changes;
  full backend test suite passes.

## [0.21.2] — 2026-07-06

### Fixed
- **Wizard download links 404'd on the latest release.** The connect-a-printer
  wizard points at `releases/latest/download/<connector-binary>`, but v0.21.1
  was published without the six connector binaries, so every download in the
  wizard returned 404. The binaries are re-attached to v0.21.1, and a new
  `release.yml` GitHub Actions workflow now builds and uploads all six
  connector binaries automatically whenever a release is published — the
  manual "remember to upload dist/*" step is gone.

## [0.21.1] — 2026-07-05

### Fixed
- **Connect-a-printer wizard polish (F38).** `buildConfigYaml` now escapes the
  values it writes (via a double-quoted YAML scalar), so an unusual character in
  the printer-IP field can't produce a malformed `config.yaml`. The waiting
  screen's "Keep checking" now re-arms its timeout, so the troubleshooting tips
  reappear if a computer still hasn't connected. The blank-name fallback uses
  the localized placeholder instead of a hardcoded string. Found in the
  whole-branch review.

## [0.21.0] — 2026-07-05

### Added
- **"Connect a printer" wizard (F38).** A guided, non-technical setup flow on
  the Devices page: it detects the user's OS, creates the device + token,
  generates a ready-to-run `config.yaml` (no manual editing, no quotes, no
  terminal heredocs), gives one copy-paste run command (with the macOS
  quarantine/chmod folded in), and detects the connection live ("waiting… →
  connected ✅"). Test-printer mode by default; real printer IP is an optional
  post-success step. Frontend-only — reuses the existing devices API; the
  token never appears in a URL. Built from the real friction of setting the
  connector up by hand.

## [0.20.1] — 2026-07-05

### Fixed
- **App version was stuck at 0.16.0.** `app/version.py` (`APP_VERSION`, what
  the health endpoint and editor footer report) is a hand-kept constant —
  the runtime image ships no `pyproject.toml`, so it can't be read at
  runtime — and it silently drifted from v0.16.0 through v0.20.0. Bumped to
  match, and added `tests/test_version_sync.py` asserting `APP_VERSION` ==
  `pyproject.toml [project] version` so the two can never drift unnoticed again.

### Changed
- **README** documents the features added since the ZPL/label-size docs:
  print preview, TSPL export, the cross-platform connector (Windows / macOS /
  Linux / Raspberry Pi) with CUPS capture, and the in-progress Android
  connector core. New tour entries carry screenshot placeholders
  (`docs/screenshots/TODO-*.png`) to be filled with real captures.

## [0.20.0] — 2026-07-05

### Added
- **TSPL export for TSC / desktop Toshiba printers (F22).** A new "Export
  TSPL" action in the editor renders the label as TSPL/TSPL2 (SIZE/GAP/
  DIRECTION/CLS … PRINT) — text, barcodes (Code 128, GS1-128, EAN-13, QR),
  rectangles, lines and tables; images are skipped with a warning. New
  `app/services/tspl/` generator (reusing the ZPL mm→dots math) and
  `POST /api/tspl/generate` endpoint mirroring ZPL's single-label export.
  Font sizing and GAP are documented approximations (TSPL bitmap fonts vs
  the editor's TrueType); actual printing is verified on a physical TSC
  printer. TPCL, agent-printing and batch TSPL remain out of scope.

## [0.19.1] — 2026-07-05

### Fixed
- **F36 core: `RunOnce` now returns a nil error on a rejected token (401).**
  gomobile binds a Go `(string, error)` return so that a non-nil error throws
  in Java/Kotlin and discards the string — which would have hidden the
  `authError` flag and made the Android shell loop "offline" forever on a bad
  token. The 401 case is now carried only via `authError:true` in the summary
  (nil error); transient/network poll failures still return an error so the
  shell retries. Adds print-failure and transient-poll-error tests. Found in
  the whole-branch review before any APK was built.

## [0.19.0] — 2026-07-05

### Added
- **Android connector core (F36).** New `connector/mobilecore/` — a
  gomobile-friendly Go package (`NewAgent` / `RunOnce` / `ReportState`) that
  polls the job queue with a device token and prints ZPL over RAW TCP 9100,
  mirroring the desktop agent's contract. Fully unit-tested (poll parsing,
  Bearer auth, 401 handling, TCP print with copies/newline, printer-name
  match, non-ZPL rejection, end-to-end RunOnce summary). The Kotlin
  foreground-service shell and the `gomobile bind` AAR build are documented in
  `connector/android/README.md` for a machine with the Android toolchain — the
  APK is built and verified on-device in a later step (not in this release).

## [0.18.0] — 2026-07-04

### Added
- **CUPS virtual printer for macOS and Linux (F35).** Capture ZPL from
  other applications on Unix by routing a CUPS raw queue to the connector's
  capture listener. New `connector/install-capture-cups.sh` creates the
  queue in one command (`socket://127.0.0.1:9101`, `-m raw`, idempotent,
  no auto-sudo). The connector needs no code changes — its capture listener
  was already cross-platform. Works for apps that already emit ZPL; generic
  apps (Word, browsers) still need a Zebra driver (out of scope). README
  gains a Windows / macOS+Linux split; the raw-queue path is verified on
  Linux and documented-but-unverified on macOS (and newer CUPS warns that
  raw queues are deprecated).

## [0.17.0] — 2026-07-04

### Added
- **Desktop connector for macOS and Linux (F34).** `blg-connector` is pure
  Go with no cgo, so it already cross-compiled everywhere; this release
  makes it a first-class desktop agent on all three OSes. Every GitHub
  release now ships prebuilt binaries for Windows, macOS (Intel + Apple
  Silicon) and Linux (amd64/arm64/arm, incl. Raspberry Pi), produced by
  the new `connector/build-all.sh`. RAW TCP 9100 printing and the loopback
  API are byte-for-byte identical across platforms.
- **Per-OS default config path.** `defaultConfigPath()` now resolves the
  system config location by `runtime.GOOS`: `C:\ProgramData\…` on Windows,
  `/Library/Application Support/blg-connector/config.yaml` on macOS,
  `/etc/blg-connector/config.yaml` on Linux/BSD — so a service can run
  without an explicit `-config` flag on any platform.
- **launchd setup guide (macOS).** The connector README gains a
  `uk.attv.blg-connector.plist` LaunchDaemon example plus the Apple Silicon
  quarantine-removal note, alongside the existing systemd and Windows
  instructions.

## [0.16.0] — 2026-07-04

### Added
- **Print preview (F20).** A new 👁 Preview button in the editor toolbar
  renders the single-label PDF and shows it embedded in a modal (with any
  text-overflow warnings) before you commit to downloading — Download and
  Close from there. `useGeneratePdf` was split (fetch returns the blob;
  `downloadPdfBlob` saves it) so Preview and Download PDF share one path
  and preview+download stays a single history entry.

## [0.15.0] — 2026-07-04

### Added
- **Generated-file history (F18).** New History page lists every
  generation — single labels, batch PDFs and batch ZPL — with template
  name, type, label count, size and time, re-downloadable for 30 days.
  Single-label PDFs now also persist to the pdfs volume (alongside the
  inline download); batch entries are recorded up-front and hidden from
  the list until their file exists, so in-flight or failed jobs never
  appear. Endpoints: `GET /api/history`, `GET /api/history/:id/download`
  (410 if gone), `DELETE`. Lazy 30-day retention with orphan pruning on
  every write — the project's first time-based cleanup, no cron. Table
  `generated_files` (alembic 0012).

## [0.14.0] — 2026-07-04

### Added
- **Template version history (F17).** A manual save (Save button /
  Ctrl+S) now records a snapshot; autosave keeps overwriting the live
  canvas without adding a version, so history stays free of 30-second
  noise. New 🕘 History toolbar button lists versions (number, note,
  time, author) and restores any of them — the restore itself becomes a
  new "restored from vN" version, so it's reversible. Retention: last 30
  per template. `PUT /api/templates/:id` gains `snapshot:bool`; new
  `GET .../versions`, `GET .../versions/:n`,
  `POST .../versions/:n/restore` (owner-only). Table `template_versions`
  (alembic 0011).

### Changed
- `Template.version` now increments only on a manual save (previously
  every canvas write, including autosave). The number equals the count
  of deliberate saves.

## [0.13.0] — 2026-07-04

### Added
- **Tables in the editor (F7).** New ▦ Table object: a rows×cols grid
  with per-cell text (supporting `{{column}}` and `{{date+x}}`),
  editable column widths, a bold-header toggle, font and border. Renders
  natively to PDF and emits native ZPL (`^GB` grid + delegated cell
  text; rotation warns and emits unrotated). Cell placeholders take part
  in series substitution, date evaluation and wizard column mapping.
  A "Property–value table" starter joins the Library (7 total). Spec:
  `docs/superpowers/specs/2026-07-04-editor-tables-design.md`.

### Fixed
- **Polish glyphs in PDF no longer render as tofu boxes.** ReportLab's
  base14 Type1 fonts are WinAnsi-only, so ż/ł/ć/ę/ą/ź/ń/ś printed as
  black squares in every PDF — a blocker for a Polish label app. The
  renderer now embeds metric-compatible Liberation Sans/Serif/Mono
  (same family mapping, full Latin Extended-A); `fonts-liberation` is
  installed in the runtime image. Found while verifying F7.

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

[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.23.1...HEAD
[0.23.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.23.1
[0.23.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.23.0
[0.22.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.22.0
[0.21.3]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.21.3
[0.21.2]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.21.2
[0.21.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.21.1
[0.21.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.21.0
[0.20.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.20.1
[0.20.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.20.0
[0.19.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.19.1
[0.19.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.19.0
[0.18.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.18.0
[0.17.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.17.0
[0.16.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.16.0
[0.15.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.15.0
[0.14.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.14.0
[0.13.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.13.0
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
