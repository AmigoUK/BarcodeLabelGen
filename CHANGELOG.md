# Changelog

All notable changes to **BarcodeLabelGen** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Nothing yet._

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

[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.4.0
[0.3.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.3.0
[0.2.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.2.1
[0.2.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.2.0
[0.1.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.1.0
