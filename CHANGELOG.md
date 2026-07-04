# Changelog

All notable changes to **BarcodeLabelGen** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Nothing yet._

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

[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.5.1
[0.5.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.5.0
[0.4.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.4.1
[0.4.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.4.0
[0.3.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.3.0
[0.2.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.2.1
[0.2.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.2.0
[0.1.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.1.0
