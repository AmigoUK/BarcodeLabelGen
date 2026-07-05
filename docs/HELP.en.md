# BarcodeLabelGen — Help

This guide walks you through the app step by step — even if you've never used a similar tool before. Read it top to bottom, or jump straight to the section you need.

If something's missing here, check the [FAQ](FAQ.en.md) or write to **dev@attv.uk**.

---

## 1. Getting started

### Signing in

1. Open the app's web address in your browser (your administrator gives you this).
2. Enter the email and password your administrator gave you.
3. Click **Log in**.

![Login screen](screenshots/help/en/login.png)

*frame: the Email + Password form with the "Log in" button and the PL/EN language switcher in the top-right corner.*

4. If this is your **first** login, the app will ask you to set your own password (minimum 10 characters). This only happens once — on future logins you'll go straight to your panel.

![SCREENSHOT: the forced password-change screen shown on first login — two fields (new password / confirm password), the "minimum 10 characters" hint, and a "Set password" button.](screenshots/help/en/TODO-set-new-password.png)

### The dashboard — your starting screen

After signing in you land on the **Dashboard**. It's just a welcome screen — there's nothing to set up here. To start working, click **Templates** in the menu on the left.

![SCREENSHOT: the Dashboard right after login, with the left sidebar visible; the "Templates" menu item highlighted with an arrow to show where to click next.](screenshots/help/en/TODO-dashboard-empty.png)

### Creating your first template

A **template** is your label design — you build it once, then reuse it as many times as you like (e.g. to print 200 different products in one go).

1. Click **Templates** in the left menu.
2. Click the **New template** button in the top-right corner.

![SCREENSHOT: the Templates page with the "New template" button in the top-right corner clearly highlighted.](screenshots/help/en/TODO-new-template-button.png)

3. Type a name for the template, e.g. "Product price tags".
4. Pick a label format:
   - **Predefined** — ready-made, common sizes (A4, Zebra 2×1″, etc.). Pick this if you're not sure exactly what size you need.
   - **Custom size** — type width and height in millimetres and pick an orientation (portrait/landscape). Pick this if your labels are a non-standard size.

![SCREENSHOT: the "New template" dialog with the name field filled in and the choice between "Predefined" and "Custom size" visible; with "Custom size" selected, the width/height (mm) fields are shown.](screenshots/help/en/TODO-new-template-dialog.png)

5. Click **Create**. The editor opens — you can start designing your label right away.

---

## 2. Menus and navigation

### Left sidebar

| Item | What's there |
|---|---|
| **Dashboard** | Welcome screen. |
| **Templates** | Your templates organised in folders, plus the *New template* and *Import* buttons. |
| **Library** | Ready-made starter projects plus templates shared by other users (section 2a). |
| **Devices** | Print connectors and the inbox of captured labels (section 7a). |
| **Help** | This guide + the FAQ, without leaving the app. |
| **Administration → Users** | (admin only) account management. |

In the header, on the right, you'll find: your email, the **PL/EN** language switcher, and the **Log out** button.

![Templates list](screenshots/help/en/templates.png)

*frame: the Templates page with a few tiles, the search field, and the "Import" and "New template" buttons in the top-right corner.*

### The editor — screen layout

When you open a template you'll see five areas of the screen:

- **Toolbar (top)** — Save, Undo/Redo, an autosave indicator, **Generate series**, **⬇ Export** (template file), **📐 label size**, **⤓ Import ZPL**, **⤒ ZPL** and **⤒ TSPL** (export for label printers — more in section 7a), **Download PDF**.
- **Left panel ("Add")** — buttons for inserting objects onto the label (text, barcode, image, etc.).
- **Canvas (center)** — your label at 1:1 scale, in millimetres — what you see corresponds exactly to the printed size.
- **Alignment bar (above canvas)** — aligning objects and changing their stacking order.
- **Right panel ("Properties")** — settings for whichever object you've just selected.

![The editor — overview](screenshots/help/en/editor-overview.png)

*frame: the whole editor with a template open; arrows labelling the toolbar, the Add panel, the canvas, the alignment bar and the Properties panel.*

### Alignment bar — what each button group does

- **Page** — aligns the selected object to a page edge or the page center.
- **Selection** — aligns objects relative to each other (needs at least 2 selected).
- **Layer** — changes which object sits in front and which sits behind (more in section 4).
- **Distribute** — equal spacing between objects, horizontally or vertically (needs at least 3 selected).

![SCREENSHOT: close-up of the alignment bar above the canvas with the four button groups — Page, Selection, Layer, Distribute — each labelled with an arrow.](screenshots/help/en/TODO-alignment-bar-groups.png)

Every icon has a tooltip — hover over it with your mouse to see what it does.

---

## 2a. Folders, the Library and sharing

### Folders — keeping your own templates tidy

On the **Templates** page, on the left, there's a folder rail: **All**, your folders (with a count of templates in each), and **No folder**. Folders are **private** — every user only sees their own.

![SCREENSHOT: the folder rail on the left side of the Templates page — "All", two example folders with coloured dots and counters, "No folder", and the "New folder" button at the bottom.](screenshots/help/en/TODO-folder-rail.png)

1. To create a new folder, click **New folder** at the bottom of the rail.
2. To move a template into a folder: hover over its card, click the **⚙** icon, pick a folder from the list, and click **Save**.

![SCREENSHOT: a template card with its ⚙ menu open, showing the list of folders to choose from and a "Save" button.](screenshots/help/en/TODO-folder-menu.png)

3. To rename a folder or change its colour, click the **✎** icon next to it. You can pick from 8 colours — a coloured dot then appears next to the folder in the rail and on its template cards.

![SCREENSHOT: the folder edit (✎) dialog with a name field and an 8-colour swatch picker.](screenshots/help/en/TODO-folder-edit.png)

4. Deleting a folder (the **✕** icon) **does not delete its templates** — they simply move back to "No folder".

### The Library — ready-made projects and templates from others

The **Library** menu item has two sections:

- **Ready-made projects** — built-in starters: a product label with an EAN code and a date, a shipping address, a shelf price, a best-before date, a warehouse label with a QR code, an asset sticker.
- **From users** — templates that other users have shared (you can see who the author is).

![SCREENSHOT: the Library page with two sections — "Ready-made projects" at the top and "From users" below — each tile with a "Use" button.](screenshots/help/en/TODO-library-page.png)

The **"Use"** button always creates **your own copy** and opens it in the editor right away — you can't accidentally break the original.

### Sharing your own template

Want colleagues to be able to reuse your template? Share it in the Library:

1. On the **Templates** page, hover over the template's card and click **⚙**.
2. Tick **"Share in the Library"**.
3. Optionally upload a **featured image** — a preview picture that will show up on the list card and in the Library.

![SCREENSHOT: the ⚙ menu of a template card with the "Share in the Library" checkbox ticked and the featured-image upload control visible.](screenshots/help/en/TODO-share-template.png)

From that moment every logged-in user can see the template in the Library and clone it — but **only you can edit the original**. A shared template shows a 📚 icon in the list. Untick the box to withdraw it from the Library.

---

## 3. Building a label — object guide

Everything below lives in the **left panel**, in the *Add* section. Each button inserts a different type of **object** — an element you can freely move and edit on the label.

### T — Text

**What it does:** Inserts a single line of fixed-size text — it does not wrap if the text is too long.
**When to use it:** Headers, short labels, fixed information.
**How:**

1. Click **T Text** in the left panel.
2. Select the new object on the canvas.
3. Type the content into the field in the right panel.

![SCREENSHOT: canvas with a Text object selected; right panel showing the Content field with sample text.](screenshots/help/en/TODO-object-text.png)

### ¶ — Text block

**What it does:** Inserts multi-line text that automatically wraps inside a frame. You can also turn on **auto-fit** — the app will shrink or grow the font on its own so the text fits the frame.
**When to use it:** Product descriptions whose length varies — great together with `{{description}}` pulled from a spreadsheet (see section 6).
**How:**

1. Click **¶ Text block**.
2. In the right panel, tick **Auto-fit** and set a minimum and maximum font size.

![SCREENSHOT: canvas with a Text block object selected; right panel showing the Auto-fit checkbox ticked and the min/max font size fields.](screenshots/help/en/TODO-object-textblock.png)

### ▭ — Rectangle, ╱ — Line

**What it does:** Adds simple shapes — frames, separators, dividing lines.
**How:**

1. Click ▭ or ╱.
2. Drag on the canvas to set its size.
3. In the right panel, set the fill and stroke colour.

![SCREENSHOT: canvas with a drawn rectangle and a line; right panel showing fill and stroke colour pickers.](screenshots/help/en/TODO-object-shapes.png)

### ▤ — Barcode

**What it does:** Generates a **barcode** — a scannable pattern that represents a value, such as a product number — from the data you provide.
**When to use it:** Any product catalog that has codes.
**How:**

1. Click **▤ Barcode**.
2. In the right panel, pick the barcode type (EAN-13, Code128, etc.).
3. Enter the data — or type `{{sku}}` to have the value pulled automatically from a spreadsheet (see section 6).

![SCREENSHOT: canvas with a Barcode object selected; right panel showing the barcode type list (EAN-13, Code128) and a Data field with an example value.](screenshots/help/en/TODO-object-barcode.png)

### ▦ — Table

**What it does:** Inserts a grid of rows and columns with text in each cell — useful for property–value labels, nutrition-fact tables, or a short list of items.
**How:**

1. Click **▦ Table**.
2. In the right panel, set the number of rows and columns.
3. Type the content of each cell — you can use `{{column}}` placeholders and `{{date+x}}` dates (see sections 6 and 7); coloured chips previewing them appear below the grid.
4. Set the column widths (in mm), the font, and the border.
5. Tick **Bold header** if you want to emphasise the first row.

![SCREENSHOT: canvas with a Table object selected; right panel showing row/column count fields, a cell being edited that contains `{{column}}`, and the Bold header checkbox ticked.](screenshots/help/en/TODO-object-table.png)

**Good to know about printing:** the table prints correctly both in the PDF and in a ZPL export (see section 7a). One limitation: a rotated table is not supported in ZPL — it exports without rotation.

### 🖼 — Image

**What it does:** Uploads an image file (PNG, JPG or SVG) and places it on the canvas. It prints normally in the PDF.
**When to use it:** A company logo, icons, product photos.
**How:**

1. Click **🖼 Image**.
2. Pick a file from your computer (up to 5 MB).

![SCREENSHOT: canvas with an uploaded logo as an Image object; right panel showing basic file info.](screenshots/help/en/TODO-object-image.png)

### 🌄 — Background (reference)

**What it does:** Uploads an image as a **locked, full-canvas background** — visible in the editor only, as a visual guide. The background **does not print** in the PDF.
**When to use it:** Your labels came from the print shop with a logo already pre-printed. You scan a sample of that label, upload it as the background, position your new text exactly where it should go, and generate the PDF — the printer overlays only the new text, and the logo doesn't get printed twice.
**How:**

1. Click **🌄 Background**.
2. Pick a file. The background drops to the very bottom of the object stack and is locked — it has no handles for moving.
3. To change it: select it, then in the right panel uncheck **Lock position**, or check **Print in PDF** if you actually want it to print after all.

![SCREENSHOT: canvas with a Background image filling the entire label, looking locked/dimmed; right panel showing the Lock position and Print in PDF checkboxes near the top.](screenshots/help/en/TODO-object-background.png)

---

## 4. Working with objects

### Selecting

- Single click = select one object.
- **Shift + click** = add another object to the selection (multi-select — selecting several at once).
- **Ctrl/Cmd + A** = select every object on the label.

![SCREENSHOT: canvas with three objects selected at the same time (blue selection outlines), demonstrating multi-select via Shift+click.](screenshots/help/en/TODO-multiselect.png)

### Moving and resizing

- Drag the selected object with the mouse to move it.
- The corner handles resize it; the handle above the object rotates it.
- A **locked** object has no handles — but you can still select it and unlock it from the right panel.

![SCREENSHOT: a selected object on the canvas with visible corner resize handles and a rotate handle above it.](screenshots/help/en/TODO-resize-handles.png)

### Undoing changes

- **Ctrl/Cmd + Z** = undo the last change.
- **Ctrl/Cmd + Shift + Z** or **Ctrl/Cmd + Y** = redo an undone change.

One operation is one history step — e.g. aligning 5 objects at once undoes with a single Ctrl+Z.

![SCREENSHOT: close-up of the Undo and Redo buttons in the toolbar.](screenshots/help/en/TODO-undo-redo-buttons.png)

### Duplicating (making copies)

Two quick ways to copy the selected object (or a whole multi-selection):

- **Alt + drag** — hold **Alt** (on Mac: **Option**) and drag a selected object. The original stays in place; the copy lands wherever you release the mouse.
- **Ctrl/Cmd + D** — creates a copy "in place", offset by 5 mm right and down. The selection jumps to the new copy right away, so a follow-up Ctrl+D builds a staircase of copies.

![SCREENSHOT: canvas mid-drag with Alt held down — the original object visible at its starting position and a copy being created under the cursor.](screenshots/help/en/TODO-duplicate-altdrag.png)

The copy inherits everything: font, colour, rotation, the *Lock* and *Print in PDF* settings. Images share the same source file, so they don't take up extra space.

### Layer order (what's on top)

In the **alignment bar**, **Layer** group:

- ⤓ **Send to back** — pushes the selected object under everything else.
- ↓ **Send backward** — moves it down by one position.
- ↑ **Bring forward** — moves it up by one position.
- ⤒ **Bring to front** — puts the object above everything else.

![SCREENSHOT: close-up of the Layer group in the alignment bar with the four icons each labelled by an arrow.](screenshots/help/en/TODO-layer-buttons.png)

### Lock and printing (right panel)

At the very top of the right panel, every object has two checkboxes:

- **🔒 Lock position** — disables dragging and resizing (you can still edit its font, colour, etc.).
- **🖨 Print in PDF** — checked by default. If you uncheck it, the object stays visible only in the editor and won't appear in the generated PDF. Such objects appear faded on the canvas, so you can spot at a glance that they won't print.

![SCREENSHOT: top of the right panel showing the 🔒 Lock position and 🖨 Print in PDF checkboxes; Print in PDF unchecked, with the matching object faded on the canvas.](screenshots/help/en/TODO-lock-print-checkboxes.png)

### Autosave

The editor saves your work on its own every few seconds. The status shows in the toolbar:

- **Unsaved changes** — something is pending.
- **Autosaving…** — currently sending.
- **Autosaved at 12:34** — last successful save.

![SCREENSHOT: close-up of the autosave status area in the toolbar, showing the three states in sequence: "Unsaved changes", "Autosaving…", "Autosaved at 12:34".](screenshots/help/en/TODO-autosave-status.png)

You can also click **Save** manually at any time.

### Version history

Every **manual** save (the **Save** button or **Ctrl+S**) creates a new **version** of the template — a snapshot of how it looked at that moment. Autosave overwrites the current state and does not create extra versions, which keeps the list short and easy to read.

1. Click **🕘 History** in the toolbar.
2. You'll see a list of versions: number, date and author.
3. Click **Restore** next to the one you want to go back to.

![SCREENSHOT: the History panel open, listing a few versions (number, date, author) with a Restore button next to one of them.](screenshots/help/en/TODO-version-history.png)

Restoring saves the current state as a new version, so nothing is ever lost for good — the app keeps the last 30 versions per template.

### Changing the label size

The size you picked when creating the template **can be changed at any time**.

1. Click the **📐 {width}×{height}** button in the toolbar.
2. Type a new width and height in mm (1 to 1000), or click one of the ready-made presets (40×100, 50×30, 100×150, 105×148, 210×297).
3. Click **Apply**.

![The "Label size" dialog](screenshots/help/en/label-size.png)

*frame: the modal with the Width/Height fields and the row of preset chips; cursor hovering the "Apply" button.*

Objects are **not rescaled** — they keep their positions in millimetres. If you shrink the label, just drag back in any elements that ended up past the new edge.

---

## 5. Downloading a PDF — single label

Want to see the result first? Click **👁 Preview** — the PDF shows up embedded in the app together with a **Download PDF** button.

![SCREENSHOT: the in-app PDF preview window with the rendered label and a Download PDF button underneath.](screenshots/help/en/TODO-preview-pdf.png)

Or click **Download PDF** in the toolbar directly — the file starts downloading after a few seconds.

If any text didn't fit its block, you'll see an **"N warnings"** chip in the toolbar. Hover over it to see the details.

![SCREENSHOT: toolbar showing the "N warnings" chip with an open tooltip listing the details of the clipped text.](screenshots/help/en/TODO-warnings-chip.png)

Note: column placeholders (`{{name}}` — a placeholder, meaning a spot where the app will automatically insert data from your spreadsheet) stay as plain text in a single PDF — the real data is only substituted during **series generation** (section 6). Date placeholders (`{{date+14d}}`, section 7), on the other hand, are calculated right away, here too.

---

## 6. Generating a series — many labels from one template

This is the app's **flagship feature**. It lets you generate, say, 200 labels from one template, where each one gets different data — a different product name and a different barcode, for instance — pulled from a spreadsheet or a database.

### Step 0 — prep the template

In a Text or Barcode object, insert a **placeholder** — a spot where the app will automatically insert data from your spreadsheet — shaped like `{{column_name}}`, e.g.:

- Text: `{{name}}`
- Barcode data: `{{sku}}`

Every occurrence gets replaced with the value from the matching column.

![Detected dynamic fields](screenshots/help/en/dynamic-fields.png)

*frame: the right Properties panel with a text field containing `{{name}}` and `{{date+14d}}`; below it two chips — a purple `{{name}}` and a green `{{date+14d}} → 18.07.2026`.*

### Step 1 — upload your data

1. Click **Generate Series** in the toolbar.
2. In Step 1, pick the file with your data.

![SCREENSHOT: Step 1 of the Generate Series wizard with a file picker/drop area and a table of accepted formats.](screenshots/help/en/TODO-series-step1-upload.png)

Accepted formats:

| Format | Max file size | Max rows |
|---|---|---|
| `.csv` | 10 MB | 1,000 |
| `.xls` / `.xlsx` | 10 MB | 1,000 |
| `.db` / `.sqlite` / `.sqlite3` | 50 MB | 1,000 (per query) |

#### If you upload CSV or Excel

The file uploads to the server and is read right away. You'll see the detected columns and the row count.

![SCREENSHOT: preview after uploading a CSV file — the detected columns shown as a small table, the row count, and a "Next" button.](screenshots/help/en/TODO-series-csv-preview.png)

Click **Next**.

#### If you upload SQLite (a database file)

**SQLite** is a file that stores a database — if someone at work exports data from a warehouse system into a file like this, you can use it directly, without converting it to CSV first.

1. After the upload, the app shows a **list of tables** in the database, sorted so the tables with the most rows appear at the top.
2. Pick the table that has the data you need.
3. Click **Use this source**.

![SCREENSHOT: the list of tables after uploading a SQLite file, sorted by row count, with a "Use this source" button on one of the rows.](screenshots/help/en/TODO-series-sqlite-tables.png)

If you need a narrower selection of data (e.g. only products in one category), expand **Show advanced** and write a SELECT query — a database-language command that tells the app exactly what data to fetch, e.g.:

```sql
SELECT sku, name, price
FROM products
WHERE category = 'labels' AND price > 0
```

![SCREENSHOT: the expanded "Show advanced" panel with a SQL query typed into a text box and a "Use this source" button.](screenshots/help/en/TODO-series-sqlite-sql.png)

**Data safety:** the database connection is read-only. The app only accepts data-reading commands (SELECT) — nothing that could change or delete anything will ever run. The result can contain at most 1,000 rows.

### Step 2 — map the fields

The app automatically detects every `{{...}}` placeholder in your template. If a placeholder's name matches a column name exactly, the mapping is set automatically. If the names differ, pick the column manually from the list.

![Series wizard — mapping](screenshots/help/en/series-map.png)

*frame: step 2 of the wizard with the placeholder list on the left and column selects on the right; next to `{{date}}` a green hint reading "Optional — today's date is used when unmapped".*

### Step 3 — filter (optional)

If you don't want to print every row from the spreadsheet, you can filter them out — e.g. only products priced above 10, or only ones whose name contains "tea".

1. Pick a column, a condition (e.g. "greater than"), and a value.
2. Click **Test filter** to see how many rows match.

![SCREENSHOT: Step 3 Filter screen with a column, condition and value selected (e.g. price > 10) and the result after clicking "Test filter" showing the number of matching rows.](screenshots/help/en/TODO-series-filter.png)

You can also skip this step if you want to generate labels for every row.

### Step 4 — generate the PDF

Click **Generate PDF**. The app starts working in the background, and a progress bar shows how much is left. Once it's done, the PDF starts downloading automatically.

![SCREENSHOT: Step 4 with a progress bar mid-generation and a status message.](screenshots/help/en/TODO-series-progress.png)

If some labels had text that didn't fit its block, you'll see a list of warnings — which rows, which objects. The PDF is still generated for every label regardless.

![SCREENSHOT: the warnings list shown after series generation, listing specific rows and objects with clipped text.](screenshots/help/en/TODO-series-warnings-list.png)

---

## 7. Date placeholders — `{{date+…}}`

Besides spreadsheet columns, you can insert **dates that are calculated automatically at the moment the label is generated** — perfect for best-before ("use by") dates and production dates. They work everywhere: in a single PDF, in a series, and in the ZPL export.

### How to write them

| You type | You get (when generating on 04.07.2026) |
|---|---|
| `{{date}}` | 04.07.2026 (today's date) |
| `{{date+14d}}` | 18.07.2026 (+14 days) |
| `{{date-7d}}` | 27.06.2026 (−7 days) |
| `{{date+3m}}` | 04.10.2026 (+3 months) |
| `{{date+1y}}` | 04.07.2027 (+1 year) |
| `{{date+14d:DD/MM/YY}}` | 18/07/26 (custom format) |
| `{{date+3m:YYYY-MM-DD}}` | 2026-10-04 |

- Offset units: **d** = days, **m** = months, **y** = years. Both `+` and `-` work.
- The date format (optional, after a colon) is built from the **DD**, **MM**, **YY**, **YYYY** building blocks — separators (dots, slashes, dashes, spaces) pass through unchanged. Without a format you get `DD.MM.YYYY`.
- Month ends are handled safely: 31 January + 1 month gives 28 or 29 February — the app never invents a date that doesn't exist, like "31 February".

### How do you know it will work?

Once you type the placeholder, a **green chip previewing the calculated date** appears in the right panel (purple chips are regular spreadsheet columns). Hover over the chip — a tooltip reminds you the final value is calculated only at generation time.

![Green date chip](screenshots/help/en/date-chip.png)

*frame: close-up of the right panel; the Content field with `{{date+14d}}` and the green chip `{{date+14d}} → 18.07.2026` underneath.*

### Good to know

- If your spreadsheet has a **column named `date`**, it wins for a bare `{{date}}`. Forms with an offset (`{{date+14d}}`) are always calculated automatically, regardless of any spreadsheet column.
- The date is calculated **at generation time** for the PDF or ZPL, using the server's clock — not when you save the template.
- In the series wizard, date fields **don't need to be mapped** to any column.

---

## 7a. Printing on label printers (ZPL and TSPL)

Labels printed on specialised label printers (like Zebra, TSC, Toshiba) don't use an ordinary PDF — they speak their own command language. The app can both **read** that language (import) and **write** it (export), so you don't need to learn it yourself.

### ZPL — Zebra and compatible printers

**ZPL** is a special language that Zebra-brand label printers (and compatible models) speak. The app can import an existing label written in ZPL into the editor, and export your design as ZPL code.

#### Importing ZPL

1. Click **⤓ Import ZPL** in the toolbar.
2. Paste the ZPL code — e.g. one you received from a label supplier or another system.
3. Pick the **Printer DPI** — this is the print density, i.e. how many dots per millimetre the printer produces. If you don't know your printer's DPI, leave **Auto-detect** on — the app compares the dimensions in the code with your label size and works it out for you.
4. Click **Analyze** — you'll see the number of recognised objects and the detected DPI. If the label in the code is larger than yours, you'll get a hint.
5. Click **Import** — the objects land on the canvas.

![ZPL import dialog](screenshots/help/en/zpl-import.png)

*frame: the modal with ZPL code pasted in, the DPI select set to "Auto-detect" and the analysis result "12 objects · 203 dpi".*

**Careful:** the import replaces the label's current content — if you've already designed something, make a copy first (section 8a).

#### Exporting ZPL

Click **⤒ ZPL** in the toolbar. You get two modes to choose from:

- **Template (variables)** — one ZPL code built from your design. Column placeholders `{{...}}` stay in the code as text (you substitute them in your own system), while date placeholders are calculated right away. You get **Copy** and **Download .zpl** buttons.
- **Batch (dataset)** — pick a previously uploaded data file and the app generates one `.zpl` file with a separate label for every row (both columns and dates substituted).

![ZPL export dialog](screenshots/help/en/zpl-export.png)

*frame: the modal in "Template (variables)" mode with a preview of the generated code and the Copy / Download .zpl buttons.*

Pick the DPI that matches your printer (usually 203 or 300).

### TSPL — TSC and Toshiba printers

**TSPL** is the equivalent of ZPL for TSC and Toshiba-brand printers — a different dialect of the same idea: a command language the label printer understands.

1. Click **⤒ TSPL** in the toolbar.
2. Pick the printer's DPI (203 or 300).
3. You'll see a live preview of the generated code.
4. Click **Copy** or **Download .txt**.

![SCREENSHOT: the "Export TSPL" dialog with a DPI choice (203/300), a live preview of the generated TSPL code, and Copy / Download .txt buttons.](screenshots/help/en/TODO-tspl-export.png)

TSPL export only works for a single label (there's no Batch mode yet) and there isn't an import in the other direction yet — this feature is at an earlier stage than ZPL.

### Direct printing — the connector

Instead of downloading a file, you can print **straight from the editor** (this applies to ZPL — not TSPL) thanks to the **connector** — a small program installed on a computer on the same network as your printers, which links the app to the printer.

1. Install the **blg-connector** agent on a computer connected to the network your printers are on (the download is in the Assets section of every GitHub release; setup instructions: `connector/README.md`).
2. In the app, go to **Devices → Add device**.

![SCREENSHOT: the "Add device" dialog with a generated token (access code) to copy into the agent's config.yaml file.](screenshots/help/en/TODO-connector-add-device.png)

3. Copy the generated **token** (a unique access code) into the agent's `config.yaml` file. The device switches to **Online** and reports its list of connected printers.
4. In the editor, click **🖨 Print**, pick the device, the printer, the number of copies and the DPI, then click **Print**.

![SCREENSHOT: the print dialog in the editor with device, printer, copies and DPI selections, a "Print" button, and a visible progress bar (queued → picked up by agent → printed).](screenshots/help/en/TODO-connector-print-dialog.png)

The dialog shows live progress: *queued → picked up by the agent → printed* (or an error with the reason).

**Fast path:** if the connector is running **on the same computer** where your browser is open, the app detects it automatically and offers a **⚡ This computer — instant print** option. The label then goes straight to the printer, skipping the round trip through the server.

![SCREENSHOT: the print dialog with the "⚡ This computer — instant print" option pre-selected by default.](screenshots/help/en/TODO-connector-fastpath.png)

Date placeholders are calculated at print time; column placeholders stay in the code (this prints a single label, not a series).

### Virtual printer — capture labels from other programs

The connector can also work **the other way round**: it pretends to be an ordinary network printer, and anything other applications (a warehouse system, Word, a legacy program) print to it lands in the **Inbox** on the **Devices** page.

1. In the agent's `config.yaml`, enable the `capture` section (step-by-step instructions, together with the Windows printer setup, are in `connector/README.md`).
2. Print something from any application to that virtual printer.
3. Go to **Devices → Inbox** and click **Open in editor** — the label becomes a regular template: size detected from the code, texts and barcodes editable right away.

![SCREENSHOT: the Devices → Inbox page with a list of a few captured labels (thumbnails, timestamps) and an "Open in editor" button.](screenshots/help/en/TODO-devices-inbox.png)

From the Inbox you can also copy the raw ZPL code or delete an entry. The app keeps at most the 200 most recent captures per device.

---

## 7c. Generated-file history

Click **History** in the menu. Every generation — a single label (**Download PDF**) and a whole series (PDF or batch ZPL) — is added to a list: template name, type, label count, size, date.

![SCREENSHOT: the History page with a list of generated files — columns for template name, type, label count, size, date — and Download and Delete buttons on each row.](screenshots/help/en/TODO-generated-history.png)

Click **Download** to fetch the file again without regenerating it, or **Delete** to remove the entry. Files stay available for **30 days**, after which they are deleted automatically.

---

## 8. Administration (admin only)

Left menu → **Administration → Users**.

![Users panel](screenshots/help/en/users-admin.png)

*frame: the users table with the Email / Role / Active / Last login columns and the "Create account" button at the top.*

### Creating a user

1. Click **Create account**.
2. Enter an email and a temporary password (minimum 10 characters; you can also generate a random one).
3. Pick a role:
   - **Administrator** — full access, including user management.
   - **Editor** — creates and edits their own templates and datasets.
   - **Viewer** — can open and view, but doesn't save changes.

![SCREENSHOT: the "Create account" dialog with Email, temporary password (with a "Generate" button), and a Role dropdown (Administrator/Editor/Viewer).](screenshots/help/en/TODO-admin-create-user.png)

4. After clicking **Create**, the app shows the temporary password **once** — pass it to the new user right away.

### Resetting a password

1. Click **Reset password** next to the user's account.
2. The app generates a new temporary password — hand it over to the user.

![SCREENSHOT: a user row with "Reset password" clicked, and a dialog showing the newly generated temporary password, displayed only once.](screenshots/help/en/TODO-admin-reset-password.png)

The user will be asked to set their own password at their next login.

### Activating / deactivating an account

The **Active** toggle in a user's row switches account access on or off. You can't deactivate your own account — a safeguard against accidentally locking yourself out.

![SCREENSHOT: close-up of the "Active" toggle in a user row, switched on (green); for the current user's own row the toggle is greyed out/disabled.](screenshots/help/en/TODO-admin-active-toggle.png)

---

## 8a. Importing / exporting templates

You can save any template as a single `.blg-template.json` file — it contains the label size, every object's position and content, and images encoded right inside the file. A file like this is portable: archive it, mail it, or import it into another BarcodeLabelGen installation.

### Export

You have two options:

- On the **Templates** page: hover over a template's card and click the **⬇** icon in the bottom-right corner.
- In the editor: click **⬇ Export** in the toolbar (next to *Download PDF*).

![SCREENSHOT: close-up of the ⬇ Export button in the editor toolbar, next to the Download PDF button.](screenshots/help/en/TODO-editor-export-button.png)

This downloads a `<name>.blg-template.json` file — keep it in a backup folder for safety.

### Import

On the **Templates** page, click **⬆ Import** — a 2-step dialog opens:

1. **Pick a file** — choose your `.blg-template.json` file. The app validates it and shows a preview.

![SCREENSHOT: Step 1 of the import dialog with a .blg-template.json file selected, a validity checkmark, and a content preview.](screenshots/help/en/TODO-import-step1.png)

2. **Configure** — here you can:
   - change the new template's name (default is the name from the file; on a naming clash the app adds a "(copy)" suffix),
   - override the label size (leave blank to keep the original),
   - uncheck objects you don't want to import (a checklist with a type icon and a content preview for each one),
   - for every duplicate image, choose: **Reuse existing** (saves space) or **Create new copy**.

![SCREENSHOT: Step 2 of the import dialog with a name field, width/height override fields, an object checklist with checkboxes, and the Reuse existing / Create new copy choice for a duplicate image.](screenshots/help/en/TODO-import-step2.png)

3. Click **Import** — the app creates a new template and opens it in the editor.

### Typical situations where this comes in handy

- **Backup before a big change** — export it, keep the file archived, edit freely. If something goes wrong, import it back.
- **Cloning a layout to a different size** — export, then import with a size override (e.g. the same label design for A6 and for 100×50 mm).
- **Moving a template between installations** (e.g. test → production) — export on one side, import on the other.
- **Partial import** — take just the barcode layout and 2-3 fields from a finished template and uncheck the rest.

### Limits and safety

- Up to 20 MB per file, 50 objects, 20 images (5 MB each).
- Images are checked with a special checksum (**SHA-256** — a digital "fingerprint" of the file that confirms it hasn't been altered). Files someone has manually modified are rejected.
- The new template always lands in your own account, no matter who exported the file.

## 9. Keyboard shortcuts

| Shortcut | Action |
|---|---|
| Ctrl/Cmd + S | Save |
| Ctrl/Cmd + Z | Undo |
| Ctrl/Cmd + Shift + Z | Redo |
| Ctrl/Cmd + A | Select everything (in the canvas) |
| Ctrl/Cmd + D | Duplicate selection (+5 mm offset) |
| Alt + drag | Duplicate selection at the drop point |
| Delete / Backspace | Delete selected |
| Shift + click | Add to selection |

---

## 10. Support

Maintained by **Tomasz "Amigo" Lewandowski** — contact: dev@attv.uk · www.attv.uk.

Source: github.com/AmigoUK/BarcodeLabelGen
