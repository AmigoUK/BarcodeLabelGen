# BarcodeLabelGen — FAQ

The most common questions, from beginner to more advanced. Each answer is short — if you want step-by-step instructions with screenshots, check the [Help guide](HELP.en.md), the section noted in brackets. Can't find your answer? Write to **dev@attv.uk**.

---

## Basics

### What is this app for?
You build label templates in it — size in millimetres, any text, barcodes, images — then generate **many labels from one template at once**, each with different data pulled from a spreadsheet (like Excel) or a database. (See *Help*, section 6.)

### Why did the app force me to change my password right after I signed in?
The administrator gave you a temporary password — a starter password meant to be used only once. Every first login forces you to set your own password (minimum 10 characters). This only happens once. (See *Help*, section 1.)

### Where is the "New template" button?
Left menu → **Templates** → **New template** button in the top-right of the list.

### Can I change the label size after I've created the template?
Yes. In the editor, click the **📐 {width}×{height}** button in the toolbar, type new dimensions in mm or pick a ready-made preset, and click **Apply**. Objects keep their positions in mm — they are never rescaled. (See *Help*, section 4.)

### Can I go back to an earlier version of a template?
Yes — click **🕘 History** in the editor. Every manual save (the Save button or Ctrl+S) creates a version, a snapshot of what the template looked like at that moment; click **Restore** next to the one you want. Autosave doesn't create a version, so the list stays short and easy to read — the app keeps the last 30. (See *Help*, section 4.)

### How do I save a template?
The editor saves on its own — that's autosave, every few seconds; you can see the status in the toolbar. You can also press **Ctrl/Cmd + S** manually.

---

## Editor and objects

### What's the difference between **Text** (T) and **Text block** (¶)?
- **Text** — a single line, fixed font size, doesn't wrap.
- **Text block** — multiple lines, wraps inside a frame of a given width. You can also turn on **auto-fit**, which adjusts the font size to match the length of the text — useful when names coming from a database vary between short and long.

### What does `{{column_name}}` mean in a text field?
It's a **placeholder** — a spot where the app will automatically insert data from the matching column in your spreadsheet or database, but only when you generate a series of labels. It works both in a Text field and in the Barcode object's *Data* field. (See *Help*, section 6.)

### What does the green chip under a text field mean?
A green "chip" (a small coloured tag) marks a **date placeholder** (e.g. `{{date+14d}}`) and immediately shows you which date it will produce. Purple chips are ordinary spreadsheet columns. For the date syntax details, see *Help*, section 7.

### How do I add a table?
Left panel → **▦ Table**. Set the cell content, the number of rows/columns, and the column widths in the right panel. Placeholders work inside cells too — `{{column}}` and dates `{{date+x}}` — and when you generate a series, the columns get substituted just like in regular text. (See *Help*, section 3.)

### Polish characters in the PDF used to come out as little boxes — is that fixed now?
Yes, since v0.13.0. The PDF now embeds fonts with the full Polish character set (ż, ł, ć, ę, ą, ź, ń, ś). If you still see boxes, check `/api/health` to confirm you're running version 0.13.0 or newer.

### How do I insert a logo that prints on every label?
Left panel → **🖼 Image** → pick a PNG, JPG or SVG file. The logo will print on every generated label.

### What's the difference between **🖼 Image** and **🌄 Background (reference)**?
- **🖼 Image** — a regular image, prints in the PDF.
- **🌄 Background** — a full-size image, **locked** (can't be moved) and **NOT printed** in the PDF. Use it when your labels came from the print shop with a logo already printed, and you just need to position your new text correctly — in the editor you see the background as a visual guide, but the final PDF only contains your additions. (See *Help*, section 3.)

### How do I stop an object from printing in the PDF?
Select the object → in the right panel, at the very top, uncheck **🖨 Print in PDF**. The object turns faded in the editor — a signal that it's preview-only — and the app skips it when printing.

### How do I lock an object so it doesn't get moved by accident?
Select it → in the right panel, check **🔒 Lock position**. The handles disappear, and you can't drag or resize it — but you can still select the object and change its font, colour, and so on. To unlock, uncheck the same box.

### How do I change the order of objects (which one is on top)?
The alignment bar above the canvas, **Layer** group: ⤓ to back, ↓ backward, ↑ forward, ⤒ to front.

### How do I distribute several objects evenly across the page?
Select all of them (Shift + click) → alignment bar → **Distribute horizontally** button (works with 3 or more selected objects).

### I undid too much. How do I get it back?
**Ctrl/Cmd + Shift + Z** or **Ctrl/Cmd + Y**.

### How do I quickly make a copy of an object?
Two ways:
- **Alt + drag** — hold Alt (Option on Mac) and drag a selected object. The original stays put, the copy lands under the cursor. This also works with several objects selected at once.
- **Ctrl/Cmd + D** — makes a copy in place, offset by 5 mm. The selection jumps to the copy, so a repeated Ctrl+D builds a staircase of copies.

The copy inherits every setting (font, colour, lock, *Print in PDF*); images share the same source file.

---

## Series generation (CSV / Excel)

### Which files can I upload?
CSV, XLS or XLSX. Up to **10 MB** and **1,000 rows** per file (the current version's cap).

### Does the first row of the spreadsheet need to be a header?
Yes — the first row must contain column names. Those become available as `{{name}}` when mapping in Step 2.

### I have more than 1,000 rows. What do I do?
Split your spreadsheet into batches of up to 1,000 rows each and generate several separate PDFs.

### Mapping didn't find my column.
Check that the placeholder name (`{{...}}`) matches the column header exactly — capitalisation matters, and extra spaces cause mismatches too. If the names differ (e.g. placeholder `{{name}}` but a column called `Product Name`), pick the mapping manually from the list in Step 2.

### My PDF came out with `{{name}}` in the text instead of the real name.
That means the placeholder didn't get mapped. In Step 2 (Map), every placeholder needs a column assigned to it.

### Can I generate labels for only some of the rows?
Yes — Step 3 (Filter). Pick a column, a condition (e.g. "equals", "contains", "greater than") and a value. Click **Test filter** to see how many rows match.

---

## Folders and the Library

### How do I organise templates into folders?
**Templates** page → the rail on the left → **New folder**. Then hover over a template's card → **⚙** → pick a folder → **Save**. Folders are private (everyone has their own) and single-level.

### I deleted a folder — what happens to the templates inside it?
Nothing bad — they simply move back to "No folder". No template disappears.

### How do I share a template with colleagues?
Template card → **⚙** → tick **"Share in the Library"**. Others will see it in the **Library** and can clone it with the "Use" button — only the owner can edit the original. Untick the box to withdraw the share.

### Does the "Use" button in the Library change the original?
No — "Use" always creates your own independent copy (with a "(copy)" suffix). Images from the template are copied into your own file library.

### Where do the "Ready-made projects" in the Library come from?
They're starter designs built into the app (updated along with it). They contain sample `{{...}}` placeholders and `{{date+x}}` dates — after cloning, just replace the sample values with your own.

---

## Date placeholders

### How do I insert a best-before date of "today + 30 days"?
In a text field (or in barcode data), type `{{date+30d}}`. When the PDF or ZPL is generated, the app substitutes the date 30 days after today, e.g. `03.08.2026`.

### Which date offsets can I use?
`d` = days, `m` = months, `y` = years — with a plus or minus sign: `{{date+14d}}`, `{{date-7d}}`, `{{date+3m}}`, `{{date+1y}}`. A bare `{{date}}` is today's date.

### How do I change the format the date is displayed in?
Add a format after a colon, built from the DD/MM/YY/YYYY blocks: `{{date+14d:DD/MM/YY}}` → `18/07/26`, `{{date:YYYY-MM-DD}}` → `2026-07-04`. Without a format you get `DD.MM.YYYY`.

### When exactly is the date calculated?
At **generation time** (of the PDF or ZPL), using the server's clock — not when you write the template. The green chip in the editor is only a preview for today, so you can see right away how it will look.

### What happens if I add 1 month to 31 January?
You get 28 (or 29) February — the app never creates dates that don't exist.

### My spreadsheet has a column named `date`. Which one wins?
For a bare `{{date}}`, the **spreadsheet column** wins (as before). Forms with an offset or a format (`{{date+14d}}`, `{{date:YYYY-MM-DD}}`) are always calculated automatically, regardless of the column.

### Why doesn't the `{{date}}` field require mapping in the series wizard?
Because when it's unmapped, the app substitutes today's date on its own. You only map it if you want to pull dates from a spreadsheet column instead.

---

## ZPL and TSPL / label printers

### What is ZPL and why should I care?
**ZPL** is a special language that Zebra-brand label printers (and compatible models) speak. If you print on such a printer, or receive ready-made ZPL labels from another system, the app can **import them into the editor** and **export your design as ZPL**. (See *Help*, section 7a.)

### How do I import a ZPL label?
Editor → toolbar → **⤓ Import ZPL** → paste the code → **Analyze** → **Import**. Careful: the import replaces the current canvas content.

### I don't know the DPI of the printer the code came from.
Leave the **Auto-detect** option on in the import dialog. **DPI** is print density — how many dots per millimetre the printer produces; the app compares the dimensions in the code (`^PW`/`^LL`) with your label size and picks 203 or 300 dpi on its own.

### What happens to variables like `{NAZWA}` in single braces?
They pass through untouched in both directions (import and export) — those are your own system's printer variables, unrelated to this app's placeholders. Double braces `{{...}}` are BarcodeLabelGen's placeholders.

### What's the difference between the "Template (variables)" and "Batch (dataset)" export?
- **Template** — one ZPL code; column placeholders stay in the code (you substitute them in your own system), and dates are calculated right away.
- **Batch** — you pick a previously uploaded data file and get one `.zpl` file with a separate label for every row (everything already substituted).

### Does the app also support TSC or Toshiba printers?
Yes — through **TSPL**, the equivalent of ZPL for those brands. In the editor click **⤒ TSPL**, pick a DPI (203 or 300), and download or copy the generated code. This is a simpler feature than ZPL for now: export only works for a single label (no Batch mode), there's no import yet, and direct printing through the connector currently supports ZPL only, not TSPL.

### Can I print directly to a Zebra printer from the app?
Yes — through the **connector** (`blg-connector`), a small program you install on a computer on the same network as your printers, which links the app to the printer. Set it up once (**Devices** page → a token, a unique access code, plus a `config.yaml` file), then in the editor click **🖨 Print**, pick the device and printer — the label goes into a queue, the agent picks it up and sends it to the printer. Setup instructions: the `connector/README.md` file in the project repository.

### The Print button says the device is offline.
The agent (the connector program) on that computer hasn't checked in for over a minute — make sure `blg-connector` is running and can reach the server. You can still submit the print job: it will wait in the queue until the agent comes back.

### A print job failed with a "printer unreachable" error.
The agent couldn't connect to the printer over the network. Check the printer's IP address in the agent's `config.yaml` file and make sure the printer is switched on, then submit the job again.

### How do I move a label from an old program (warehouse system/Word) into the editor?
Set up the connector's **virtual printer** — step-by-step instructions are in `connector/README.md`. Print the label from the old program to that virtual printer, and it will appear in **Devices → Inbox**, from where you can open it in the editor.

### A captured label has no logo/graphics in the editor.
Graphics coming from the printer driver pass through as a non-editable element — they print correctly, but the editor only shows the text, barcodes and shapes it can recognise and let you edit.

### I printed something to the virtual printer and nothing arrived.
Check the log (the activity record) of the agent on the computer running the connector. The most common causes: the job didn't contain valid printer code, it was too large, or the server was briefly unreachable — in that last case, the job waits locally and sends itself automatically once the connection comes back.

---

## Series generation (SQLite)

### How do I upload a SQLite database?
**SQLite** is a file that stores an entire database in one file. Step 1 of the Generate Series wizard — pick a file with the `.db`, `.sqlite` or `.sqlite3` extension. Size limit: **50 MB**.

### What will I see after uploading?
A list of tables from the database, sorted so the tables with the most rows come first. Each entry shows its column count and row count.

### I picked a table and got a message saying it has 0 rows.
You picked an empty table. It needs at least 1 row of data for there to be anything to generate — pick a different one; the sorting should push tables with data to the top of the list.

### How do I write my own query against the database?
Below the table list, expand **Show advanced: custom SQL query** and type something like:
```sql
SELECT sku, UPPER(name) AS name, price FROM products WHERE price > 10
```
Click **Use this source**.

### Which queries are allowed?
Only a **single data-reading query (SELECT)**. The database connection is read-only — no command that could change or delete anything will ever run, even if you try to type one.

### I got a message saying the result exceeds the 1,000-row limit. What now?
Your query returned more than 1,000 rows. Add a `WHERE` condition to narrow it down, or add `LIMIT 1000` at the end.

### Can I combine data from two tables (JOIN)?
Yes, that's a standard SQL query feature. Example:
```sql
SELECT p.sku, p.name, c.category_description
FROM products p JOIN categories c ON p.category_id = c.category_id
```

### Are any changes I try to make to the database saved?
**No.** The connection is read-only — no modifying command will ever run.

### My .db file shows an error saying "this is not a valid SQLite database".
The file probably isn't actually in SQLite format (e.g. it has a `.db` extension but something else inside). Check where the file came from.

---

## Importing / exporting templates

### Why would I export a template to a file?
Three main reasons: **backup** (keep the file in case something goes wrong later), **cloning** (export + import with a size override gives you a ready-made template for a different label format), **moving** (between installations of the app, or between users).

### Where's the export button?
- In the template list: hover over a card, click the **⬇** icon in the bottom-right corner.
- In the editor: toolbar → **⬇ Export** button, next to *Download PDF*.

### What exactly is in the .blg-template.json file?
The label size, every object (text, barcode, rectangle, line, image) with its exact position and all its settings, and every image encoded right inside the file. The file is self-contained — you don't need anything else besides this one file.

### Can I import a template from a different BarcodeLabelGen installation?
Yes, the file format is stable across versions. If the destination installation doesn't have exactly the same label format as the one you exported from, you'll get a warning and the app will use the "Custom" format instead.

### Can I import only some of the objects from a file?
Yes — the second step of the import dialog has a checklist. Everything is checked by default; uncheck what you don't want. Skipped images don't create unused files in your library.

### What happens if the file contains an image I already have?
The app checks whether it's the same file (by comparing its digital "fingerprint") and asks you: **Reuse existing** (no duplicate files on disk) or **Create new copy** (useful when you want a separate, independently editable copy).

### Can I import a template while also changing its size?
Yes — the second step has Width/Height fields. Leave them blank to keep the original size, or type new values. Objects keep their positions in mm, so the layout stays the same, just on a different format.

### I get a "Couldn't read the file" message.
The file isn't a valid JSON file — it may be corrupted, or it was edited manually and saved with an error. Try re-exporting the source template.

### I get a checksum (sha256) mismatch message.
The image content in the file doesn't match the checksum recorded in it — a digital "fingerprint" that confirms the file hasn't been altered. This means the file was manually modified. The app deliberately rejects such files — it could otherwise hide a swapped-in image. Re-export the file from the source.

### What are the limits?
File up to 20 MB, template up to 50 objects, up to 20 images, each image up to 5 MB.

## Accounts and security

### How does an administrator add a new user?
**Administration → Users → Create account**. They enter an email, a temporary password (minimum 10 characters) and a role. Once the account is created, the password is shown **only once** — it needs to be copied and handed to the user right away.

### What are the roles and what can each one do?
- **Administrator** — everything, including account management.
- **Editor** — creates and edits their own templates and datasets, generates PDFs.
- **Viewer** — can browse and view, but cannot save changes.

### I forgot my password.
Ask an administrator to reset it (**Administration → Users → Reset password**). You'll get a new temporary password — at your next login the app will ask you to set your own.

### Why can't I deactivate my own account?
Because you'd lock yourself out of the app with no way to undo it yourself. A second administrator can deactivate someone else, but not themselves.

### Where do I find previously generated PDFs?
Menu → **History**. The app keeps every generated file there (single labels and whole series, PDFs as well as batch ZPL files) for 30 days — click **Download** to fetch the file again without regenerating it.

## Technical issues

### "Session expired — please refresh the page"
A security token (a small, temporary code that protects your session) has expired — usually after a period of inactivity. Refresh the page (F5) and sign in again.

### The editor shows "Failed to load template"
The template may have been deleted, or you don't have access to it. Go back to the **Templates** page and check the list.

### I download a PDF and get a "pdf_render_failed" error
Something went wrong on the server side — usually invalid data in one of the objects. Check that you don't have a column placeholder `{{...}}` in a single label — columns only work during series generation; in a single PDF they stay as plain text (date placeholders are calculated everywhere).

### I generate a series and see a message that the filter matched no rows
The filter in Step 3 was too strict. Go back and loosen it, or turn it off.

### Autosave is stuck on "Unsaved changes" and nothing happens
Your network connection probably dropped. Check your connection and click **Save** manually.

### An object I see in the editor is missing from the generated PDF
Check whether **🖨 Print in PDF** is unchecked for that object in the right panel — if so, it's preview-only.

### Text in a block is getting cut off
After generating the PDF you'll see an **"N warnings"** chip. You have two options:
1. Make the text block's frame bigger.
2. Turn on **Auto-fit** in the right panel and set a sensible minimum font size.

### The app is in English but I want Polish
The **PL/EN** language switcher is in the top-right corner of the header (also available on the login page).

### The label came out with yesterday's or tomorrow's date instead of today's
The date is calculated using the clock of the **server** the app runs on. If this keeps happening, ask your administrator to check the server's timezone settings.

---

## Questions not on the list

Write to **dev@attv.uk** — describe what you were trying to do and what you saw. A screenshot really helps.
