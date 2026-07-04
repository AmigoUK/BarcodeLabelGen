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
Yes. In the editor, click the **📐 {width}×{height}** button in the toolbar, type new dimensions in mm or pick a preset, and click **Apply**. Objects keep their positions in mm (they are not rescaled).

### How do I save a template?
The editor saves on its own (autosave every few seconds — see the toolbar status). You can also press **Ctrl/Cmd + S** manually.

---

## Editor and objects

### What's the difference between **Text** (T) and **Text block** (¶)?
- **Text** — single line, fixed font size, doesn't wrap.
- **Text block** — multi-line, wraps inside a frame of a given width. You can also enable **Auto-fit** which scales the font to fit the content (useful when database names vary in length).

### What does `{{column_name}}` mean in a text field?
It's a **placeholder**. When you generate a series, it'll be replaced with the value from the matching column in your spreadsheet/database. Works in Text **and** in the Barcode object's *Data* field.

### What does the green chip under a text field mean?
A green chip marks a **date placeholder** (e.g. `{{date+14d}}`) and immediately shows the calculated value. Purple chips are regular spreadsheet columns. For the date syntax details, see the guide, section 7.

### How do I add a table?
Left panel → **▦ Table**. Edit the cell contents, the number of rows/columns and the column widths in the right panel. Placeholders work inside cells — `{{column}}` and dates `{{date+x}}` — and when you generate a series the columns are substituted just like in regular text.

### Polish characters in the PDF used to come out as little boxes — is that fixed?
Yes (since v0.13.0). The PDF now embeds fonts with the full Polish character set (ż, ł, ć, ę, ą, ź, ń, ś). If you still see boxes, make sure you're running version ≥0.13.0 (`/api/health`).

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

## Folders and the Library

### How do I organise templates into folders?
**Templates** page → rail on the left → **New folder**. Then hover a template card → **⚙** → pick a folder → Save. Folders are private (everyone has their own) and single-level.

### I deleted a folder — what happens to its templates?
Nothing bad: they go back to "No folder".

### How do I share a template with others?
Card → **⚙** → **"Share in the Library"**. Others will see it in the **Library** and can clone it with the "Use" button — only the owner can edit it. Untick to withdraw it.

### Does "Use" in the Library change the original?
No — "Use" always creates your own independent copy (with a "(copy)" suffix). Images are copied into your file library.

### Where do the "Ready-made projects" come from?
They're starters built into the app (updated together with it). They contain `{{...}}` fields and `{{date+x}}` dates — after cloning, replace the sample values with your own.

---

## Date placeholders

### How do I insert a best-before date of "today + 30 days"?
In a text field (or in barcode data), type `{{date+30d}}`. When the PDF/ZPL is generated, the app substitutes the date 30 days from today, e.g. `03.08.2026`.

### Which offsets can I use?
`d` = days, `m` = months, `y` = years, with plus or minus: `{{date+14d}}`, `{{date-7d}}`, `{{date+3m}}`, `{{date+1y}}`. A bare `{{date}}` is today's date.

### How do I change the date format?
Add a format after a colon, built from the DD/MM/YY/YYYY blocks: `{{date+14d:DD/MM/YY}}` → `18/07/26`, `{{date:YYYY-MM-DD}}` → `2026-07-04`. Without a format you get `DD.MM.YYYY`.

### When exactly is the date calculated?
At **generation time** (PDF or ZPL), using the server's date — not when you write the template. The green chip in the editor is only a preview for today.

### What if I add 1 month to 31 January?
You get 28 (or 29) February — the app never produces dates that don't exist.

### My spreadsheet has a column called `date`. Which one wins?
For a bare `{{date}}`, the **spreadsheet column** wins (as before). Forms with an offset or format (`{{date+14d}}`, `{{date:YYYY-MM-DD}}`) are always calculated automatically.

### Why doesn't the `{{date}}` field require mapping in the series wizard?
Because when unmapped, the app substitutes today's date. You only map it if you want to take dates from a spreadsheet column.

---

## ZPL / Zebra printers

### What is ZPL and why should I care?
ZPL is the language of label printers (Zebra and compatibles). If you print on such a printer, or receive ready-made ZPL labels from another system, the app can **import them into the editor** and **export your design as ZPL**.

### How do I import a ZPL label?
Editor → toolbar → **⤓ Import ZPL** → paste the code → **Analyze** → **Import**. Careful: the import replaces the current canvas content.

### I don't know the DPI of the printer the code came from.
Leave the **Auto-detect** option in the import dialog — the app compares the dimensions in the code (`^PW`/`^LL`) with your label size and picks 203 or 300 dpi.

### What happens to variables like `{NAZWA}` in single braces?
They pass through untouched in both directions (import and export) — those are your system's printer variables. Double braces `{{...}}` are this app's placeholders.

### What's the difference between the "Template (variables)" and "Batch (dataset)" export?
- **Template** — one ZPL code; column placeholders stay in the code, dates are calculated right away. Made for pasting into your own system.
- **Batch** — you pick an uploaded data file and get one `.zpl` with a label for every row (everything substituted).

### Can I print directly to a Zebra printer from the app?
Yes — through the **connector** (`blg-connector`), a small program you install on a computer on the same network as your printers. Set it up once (**Devices** page → token + `config.yaml` file), then in the editor click **🖨 Print**, pick a device and a printer — the label goes into a queue, the agent picks it up and sends it to the printer. Instructions: `connector/README.md` in the repository.

### The Print button says the device is offline.
The agent on that computer hasn't checked in for over a minute — make sure `blg-connector` is running and can reach the server. You can still submit the job: it will wait in the queue until the agent comes back.

### A print job failed with a "printer unreachable" error.
The agent couldn't connect to the printer over TCP (port 9100). Check the printer's IP in the agent's `config.yaml` and make sure the printer is switched on; then submit the job again.

### How do I move a label from an old program (ERP/Word) into the editor?
Set up the connector's **virtual printer** (the `capture` section in `config.yaml` plus a ZDesigner printer on a "Standard TCP/IP" port pointed at `127.0.0.1:9101` in Windows — step by step in `connector/README.md`). Print the label from the old program to that printer and it will appear in **Devices → Inbox**, from where you can open it in the editor.

### A captured label has no logo/graphics in the editor.
Driver bitmaps (`^GF`) come through as a non-editable passthrough — they will print correctly, but the editor only shows the texts, barcodes and shapes it can model. Binary-mode graphics (`^GFB`) are not supported — leave the driver in ASCII/hex mode.

### I printed something to the virtual printer and nothing arrived.
Check the agent's log. The most common causes: the job contained no `^XA` (the driver isn't producing ZPL — use ZDesigner), the job exceeded 2 MB, or the server was unreachable — in that case the job waits in the agent's local spool and is sent automatically within about 30 s of connectivity coming back.

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
Something went wrong server-side (usually invalid data in an object). Check that you don't have a column placeholder `{{...}}` in a single label (columns only get substituted during series generation; in a single PDF they stay as literal text; date placeholders are calculated everywhere).

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
The **PL/EN** language switcher is in the top-right corner of the header (also on the login page).

### The label came out with yesterday's/tomorrow's date instead of today's.
The date is calculated using the **server's** clock. If the skew keeps happening, ask your administrator to check the server's timezone (the `TZ` variable in the configuration).

---

## Questions not on the list

Write to **dev@attv.uk** — describe what you were trying to do and what you saw. Screenshots welcome.
