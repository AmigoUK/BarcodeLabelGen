# Changelog

All notable changes to **BarcodeLabelGen** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Nothing yet._

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

[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.2.1
[0.2.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.2.0
[0.1.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.1.0
