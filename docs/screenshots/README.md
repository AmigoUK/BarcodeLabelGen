# Screenshots

This folder holds the images embedded in the project README. The README references each by filename — drop a PNG with the matching name and it just appears.

Recommended: ~1600 px wide, PNG, slate dark background (matches the app theme), browser chrome cropped out.

## What goes where

| File | What to capture | Where in the app |
|---|---|---|
| `01-editor-hero.png` | Hero — full editor with one selected object, all panels visible (Toolbar / LeftPanel / Canvas / AlignmentBar / RightPanel) | open any template in `/templates/<id>/edit` |
| `02-editor-multiselect.png` | Multi-select via Shift+click; AlignmentBar with Selection group + Layer/Distribute visible | editor with 3 objects selected |
| `03-series-csv-mapping.png` | Generate Series modal at Step 2 (Mapping) with auto-mapped placeholders | toolbar → Generate Series → upload sample CSV → Next |
| `04-series-sqlite-picker.png` | SQLite Step 1 — table dropdown sorted by row count + advanced SELECT editor expanded | upload a `.db`/`.sqlite` file |
| `05-import-modal.png` | ImportTemplateModal Phase 2 (Configure) showing object checklist + duplicate radios + warnings | Templates → ⬆ Import → pick exported `.blg-template.json` |
| `06-templates-list.png` | Templates page grid with hover-revealed Export/Delete actions | `/templates` |
| `07-help-page.png` | `/help` page with the Guide tab selected, sidebar showing "Pomoc" highlighted | `/help` |
| `08-batch-pdf-pages.png` | Generated PDF opened in a viewer, 4–6 page thumbnails showing per-row variation | result of a series generation |
| `09-architecture.png` *(optional)* | Architecture diagram (excalidraw / mermaid render / hand-drawn) | — |

## Tips for capturing

- Use a real template with realistic content (not "Lorem ipsum") so the screenshots show the app doing useful work.
- Use the in-app PL or EN locale — match the audience the README targets.
- Keep mouse cursor out of the frame unless you need to highlight a hover state (06).
- For the PDF page thumbnails (`08`), Acrobat or Preview both render decent multi-page contact-sheet views.
