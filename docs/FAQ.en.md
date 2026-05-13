# BarcodeLabelGen — FAQ

The most common questions, ordered from beginner to advanced. Don't see an answer? Check [HELP.en.md](HELP.en.md) or write to dev@attv.uk.

---

## Basics

### What is this app for?
You build label templates here (size in mm, any text, barcodes, images), then generate **many labels from one template** — each with different data pulled from a spreadsheet or SQLite database.

### Why did the app force me to change my password right after I signed in?
The administrator gave you a temporary password. Every first login forces you to set your own (minimum 10 characters). This happens once.

### Where is "New template"?
Left menu → **Templates** → **New template** button in the top-right of the list.

### Can I change the label size after I created the template?
Not in this version. The format is fixed at template creation. If you need a different size, create a new template.

### How do I save a template?
The editor saves on its own (autosave every few seconds — see the toolbar status). You can also press **Ctrl/Cmd + S** manually.

---

## Editor and objects

### What's the difference between **Text** (T) and **Text block** (¶)?
- **Text** — single line, fixed font size, doesn't wrap.
- **Text block** — multi-line, wraps inside a frame of a given width. You can also enable **Auto-fit** which scales the font to fit the content (useful when database names vary in length).

### What does `{{column_name}}` mean in a text field?
It's a **placeholder**. When you generate a series, it'll be replaced with the value from the matching column in your spreadsheet/database. Works in Text **and** in the Barcode object's *Data* field.

### How do I insert a logo that appears on every label?
Left panel → **🖼 Image** → pick a PNG/JPG/SVG. The logo will print on every generated label.

### What's the difference between **🖼 Image** and **🌄 Background (reference)**?
- **🖼 Image** — a regular image. Prints in the PDF.
- **🌄 Background** — full-canvas image, **locked** (can't be moved) and **NOT printed** in the PDF. Use this when your labels came from the print shop with a logo already pre-printed: you upload a scan as a layout reference, position your new text against it, and the final PDF carries only your additions — the printer doesn't double-print the logo.

### How do I keep an object from being printed in the PDF?
Select the object → in the right panel, at the top, uncheck **🖨 Print in PDF**. The object goes to 50% opacity in the editor (so you spot it) and the renderer skips it.

### How do I lock an object so it can't be moved?
Select it → in the right panel, check **🔒 Lock position**. Handles disappear, drag and resize are off — but you can still select the object and edit its font, colour, etc. Uncheck the box to unlock.

### How do I change the order of objects (which one is on top)?
Alignment bar above the canvas, **Layer** group:
- ⤓ to back, ↓ backward, ↑ forward, ⤒ to front.

### How do I distribute 5 objects evenly across the page?
Select all 5 (Shift + click) → alignment bar → **Distribute horizontally** button (works for 3+ objects).

### I undid too much. How do I get it back?
**Ctrl/Cmd + Shift + Z** or **Ctrl/Cmd + Y**.

### How do I quickly duplicate an object?
Two ways:
- **Alt + drag** — hold Alt (Option on Mac) and drag a selected object. The original stays put; the clone lands where you release. Works for multi-select too — relative positions are preserved.
- **Ctrl/Cmd + D** — duplicate in place with a +5 mm offset. Selection jumps to the clones, so a repeated Ctrl+D builds a staircase of copies.

The clone inherits every setting (font, colour, lock, *Print in PDF*); images share the same Asset.

---

## Series generation (CSV / Excel)

### What files can I upload?
CSV, XLS, XLSX. Up to **10 MB** and **1,000 rows** per file (MVP cap).

### Should the first row be column headers?
Yes — the first row must contain column names. Those become the values you can map to as `{{name}}`.

### I have more than 1,000 rows. What now?
Split your spreadsheet into batches of up to 1,000 rows each and generate several PDFs.

### Mapping didn't find my column.
Check that the placeholder name (`{{...}}`) matches the column header exactly — case-sensitive, no extra spaces. If they differ (e.g. placeholder `{{name}}` but column `Product Name`), pick the mapping manually in Step 2.

### My PDF came out with `{{name}}` in the text instead of the actual name.
That means the placeholder didn't get mapped. In Step 2 (Map), every placeholder needs a column.

### Can I include only some of the rows?
Yes — Step 3 (Filter). Pick a column, an operator (equals / contains / greater than / etc.) and a value. Click **Test filter** to see how many rows match.

---

## Series generation (SQLite)

### How do I upload a SQLite database?
Step 1 of the Generate Series wizard — pick a file with the `.db`, `.sqlite` or `.sqlite3` extension. Limit **50 MB**.

### What will I see after the upload?
A list of tables in the database, sorted with the most-rows tables at the top. Each entry shows the column count and row count.

### Why did I pick a table the first time and get `table 'X' returned 0 rows`?
You picked an empty table (e.g. `basket_contents` with 0 rows). The table needs at least one row to generate from. Pick a different one — the sort should put non-empty tables on top.

### How do I write my own SELECT query?
Below the table list, expand **Show advanced: custom SQL query** and type something like:
```sql
SELECT sku, UPPER(name) AS name, price FROM products WHERE price > 10
```
Click **Use this source**.

### Which queries are allowed?
Only a **single SELECT** (optionally prefixed with `WITH ... AS (...)`). The connection is read-only. Blocked: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `ATTACH`, `DETACH`, `PRAGMA`, `VACUUM`, `REINDEX`, transactions.

### I got `result exceeds 1000-row limit`. What now?
Your SELECT returned more than 1,000 rows (MVP cap). Add `WHERE` to narrow it, or `LIMIT 1000` at the end.

### Can I use JOIN?
Yes — JOIN is standard SELECT syntax. Example:
```sql
SELECT p.sku, p.name, c.category_description
FROM products p JOIN categories c ON p.category_id = c.category_id
```

### Are my changes to the database saved?
**No.** The connection is read-only — no modifying statement will run, even if it slipped past the validator.

### My .db file shows "file is not a valid SQLite database".
The file probably isn't actually SQLite (e.g. it has the `.db` extension but is a different format). Check the file's source.

---

## Importing / exporting templates

### Why export a template to a file?
Three main reasons: **backup** (save the file before a big change), **cloning** (export + import with a size override = a ready-made template for another format), **moving** (between instances or between users).

### Where's the export button?
- In the template list (tile) — the **⬇** icon at the bottom-right (appears on hover).
- In the editor toolbar — the **⬇ Export** button next to *Download PDF*.

### What exactly is in the .blg-template.json file?
Label size, every object (text, barcode, rectangle, line, image) with its exact position and all settings, and **every image** base64-encoded inside the file itself. The file is self-contained — you don't need anything else besides this one JSON.

### Can I import a template from a different BarcodeLabelGen instance?
Yes. The file format (`$schema: "blg-template/v1"`) is stable. If the target instance doesn't have the same label format as the source, you get a warning and the program falls back to the "Custom" format.

### Can I import only some of the objects?
Yes — in the second step of the import modal there's a **checklist**. Everything is checked by default; uncheck what you don't want. Skipped `image` objects don't create unused images in your asset library.

### What happens if the file contains an image I already have?
The app detects duplicates by SHA-256 hash and asks you: **Reuse existing** (FK points to the existing image, no disk duplicates) or **Create new copy** (fresh entry with the same content — useful when you want a separately editable copy).

### Can I import a template with a different size?
Yes — the second step has **Width/Height** fields. Leave blank to keep the original, or type new values. Objects keep their positions in mm, so the layout transfers but the format is different.

### I'm getting "Couldn't read the file"
The file is not a valid JSON (e.g. corrupted, opened in an editor and saved with errors). Try re-exporting from the source template.

### I'm getting "sha256 mismatch"
The base64 content doesn't match the declared hash — the file was manually modified. The app deliberately refuses such files (it could hide a swapped image). Re-export from the source.

### Limits?
File ≤ 20 MB, template ≤ 50 objects, ≤ 20 images, each image ≤ 5 MB.

## Accounts and security

### How does an admin add a new user?
**Administration → Users → Create account**. Enter email, a temporary password (minimum 10 characters) and a role. After creation the password is shown **once** — copy it and pass it to the user.

### What are the roles and what can each do?
- **Administrator** — everything, plus user management.
- **Editor** — creates and edits their own templates and datasets, generates PDFs.
- **Viewer** — can browse and view, but cannot save changes.

### I forgot my password.
Ask an admin for a reset (Administration → Users → **Reset password**). You'll get a new temporary password — at login the app will force you to set your own.

### Why can't I deactivate my own account?
Because you'd lock yourself out with no way to undo it. A second administrator can deactivate another administrator.

---

## Technical issues

### "Session expired — please refresh the page"
The CSRF token has expired (usually after a long idle period). Press F5 and sign in again.

### The editor shows "Failed to load template."
The template was probably deleted, or you don't have access. Go back to **Templates** and check the list.

### I downloaded a PDF and got `pdf_render_failed`.
Something went wrong server-side (usually invalid data in an object). Check that you don't have `{{...}}` placeholders in a single-label preview (placeholders only get substituted during series generation; in a single PDF they stay as literal text).

### I generated a series and saw `no_rows: filter matched no rows`
The filter in Step 3 didn't catch any rows. Go back and loosen it or disable it.

### Autosave is stuck on "Unsaved changes" and won't move.
The network probably dropped. Check your connection and click **Save** manually.

### An object I see in the editor is missing in the generated PDF.
Check the right panel — if **🖨 Print in PDF** is unchecked, the object is preview-only.

### Text in a block is getting cut off.
After PDF generation you'll see **N warnings**. Two options:
1. Enlarge the block frame.
2. Enable **Auto-fit font** in the right panel and set a sensible minimum size.

### The app is in Polish but I want English.
The language switcher is in the top-right corner (or in the user menu).

---

## Questions not on the list

Write to **dev@attv.uk** — describe what you were trying to do and what you saw. Screenshots welcome.
