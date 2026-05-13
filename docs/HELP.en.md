# BarcodeLabelGen — Help

A short guide to the app. Read top-to-bottom for a complete tour, or jump straight to the feature you need.

---

## 1. Getting started

### Signing in

1. Open the app URL in your browser.
2. Enter the email and password your administrator gave you.
3. On your first login, the app will ask you to set your own password (minimum 10 characters). This happens once — afterwards you go straight to the dashboard.

### The dashboard

After signing in you land on the **Dashboard**. It's just a welcome screen — to start working, click **Templates** in the left menu.

### Creating your first template

1. **Templates** → **New template**.
2. Enter a name (e.g. "Product price tags").
3. Pick a label format:
   - **Predefined** — ready-made sizes (A4, Zebra 2×1″, etc.).
   - **Custom size** — type width and height in mm and pick orientation.
4. Click **Create** — the editor opens.

---

## 2. Menus and navigation

### Left sidebar

| Item | What's there |
|---|---|
| **Dashboard** | Welcome screen. |
| **Templates** | Your templates list + the *New template* button. |
| **Data imports** | All the CSV/Excel/SQLite files you've ever uploaded for series generation. |
| **Administration → Users** | (admin only) account management. |

### The editor — screen layout

When you open a template you'll see:

- **Toolbar (top)** — Save, Undo/Redo, autosave indicator, **Download PDF**, **Generate Series**.
- **Left panel (Add)** — buttons for inserting objects onto the label.
- **Canvas (center)** — your label at 1:1 scale (millimetres).
- **Alignment bar (above canvas)** — alignment and z-order controls.
- **Right panel (Properties)** — settings for the selected object.

### Alignment bar — what each group does

- **Page** — aligns objects to a page edge or the page center.
- **Selection** — aligns objects relative to each other (needs ≥2 selected).
- **Layer** — moves selected objects forward/back in the z-stack.
- **Distribute** (3+ objects) — equal spacing horizontally/vertically.

Hover any icon for a tooltip.

---

## 3. Building a label — object guide

Everything below lives in the **left panel**, *Add* section.

### T — Text

**What it does:** A single line of fixed-size text.
**When to use:** Headers, short labels, fixed strings.
**How:** Click **T Text**, then select it on the canvas and edit content in the right panel.

### ¶ — Text block

**What it does:** Multi-line text that wraps inside a frame; optional *auto-fit* scales the font up/down to fit.
**When to use:** Variable-length product descriptions (perfect for `{{description}}` from a spreadsheet).
**How:** Click **¶ Text block**. In the right panel tick **Auto-fit font** and set min/max size.

### ▭ — Rectangle, ╱ — Line

**What it does:** Helper geometry (frames, separators).
**How:** Click → drag on the canvas to size; set fill/stroke in the right panel.

### ▤ — Barcode

**What it does:** Renders a barcode from the value you give it.
**When to use:** Any product catalog with codes.
**How:** Click **▤ Barcode**, in the right panel pick the type (EAN-13, Code128, etc.) and enter the data. You can use `{{sku}}` to pull the value from a spreadsheet column.

### 🖼 — Image

**What it does:** Uploads a PNG/JPG/SVG and places it on the canvas. Prints in the PDF.
**When to use:** Logos, illustrations, icons, product photos.
**How:** Click **🖼 Image** → pick a file. Up to 5 MB.

### 🌄 — Background (reference)

**What it does:** Uploads an image as a **locked, full-canvas background** that's **visible in the editor only and is NOT printed in the PDF**.
**When to use:** Your labels arrived from the print shop with a logo already pre-printed. You scan a sample, upload it as background, position the new text against it, and generate the PDF — the printer overlays only the new text, the logo isn't double-printed.
**How:** Click **🌄 Background**, pick a file. The background drops to the bottom of the stack, locked (no handles). To change: select it, then in the right panel uncheck **Lock position** or check **Print in PDF**.

---

## 4. Working with objects

### Selecting

- Single click = select one.
- **Shift + click** = add to selection (multi-select).
- **Ctrl/Cmd + A** = select everything.

### Moving and resizing

- Drag the selected object with the mouse.
- Corner handles = resize; the handle above the object = rotate.
- A **locked** object has no handles — but you can still click it to unlock from the right panel.

### Undo / redo

- **Ctrl/Cmd + Z** = undo.
- **Ctrl/Cmd + Shift + Z** or **Ctrl/Cmd + Y** = redo.

One operation = one history step (e.g. aligning 5 objects undoes in a single Ctrl+Z).

### Layer order (z-order)

In the **alignment bar**, **Layer** group:

- ⤓ **Send to back** — push selected under everything else.
- ↓ **Send backward** — move down by one neighbour.
- ↑ **Bring forward** — move up by one neighbour.
- ⤒ **Bring to front** — over everything.

Multi-select keeps the relative order of the selected items.

### Lock + Print in PDF (right panel)

Every object's right panel has two checkboxes at the top:

- **🔒 Lock position** — disables drag and resize (you can still edit font, colour, etc.).
- **🖨 Print in PDF** — checked by default. Unchecked = visible only in the editor; the renderer skips it in the PDF. Non-printable objects appear at 50% opacity so you spot them at a glance.

### Autosave

The editor saves every few seconds on its own. Status sits in the toolbar:
- **Unsaved changes** — something is pending.
- **Autosaving…** — sending now.
- **Autosaved at 12:34** — last successful save.

You can also click **Save** manually.

---

## 5. Downloading a PDF — single label

Click **Download PDF** in the editor toolbar. Rendering is synchronous (a few seconds), then the PDF downloads automatically.

If any text didn't fit its block, you'll see an **N warnings** chip — hover it for details.

---

## 6. Generating a series — many labels from one template

This is the app's flagship feature. It lets you generate, say, 200 labels from one template, where each gets different data from a spreadsheet or database.

### Step 0 — prep the template

In a Text or Barcode object, insert a placeholder shaped like `{{column_name}}`, e.g.:
- Text: `{{name}}`
- Barcode data: `{{sku}}`

Each occurrence will be replaced with the value from the matching column.

### Step 1 — Upload data

Toolbar → **Generate Series** → Step 1 (Upload data).

Accepted formats:

| Format | Max size | Max rows |
|---|---|---|
| `.csv` | 10 MB | 1,000 |
| `.xls` / `.xlsx` | 10 MB | 1,000 |
| `.db` / `.sqlite` / `.sqlite3` | 50 MB | 1,000 (per query) |

#### CSV / Excel

The file uploads and is parsed immediately. You'll see the columns and row count. Click **Next**.

#### SQLite

After upload the app shows a **table list** (sorted with most-rows-first). Pick a table that has data and click **Use this source**.

If you need SQL-level filtering (e.g. only products in a specific category, or a JOIN across tables), expand **Show advanced** and write a SELECT, e.g.:

```sql
SELECT sku, name, price
FROM products
WHERE category = 'labels' AND price > 0
```

**Security:** The connection is read-only. Only a single SELECT is accepted — `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ATTACH`, `PRAGMA` are blocked. Up to 1,000 result rows — anything larger is rejected with a request to add `WHERE`/`LIMIT`.

### Step 2 — Map fields

The app detects every `{{...}}` placeholder in the template. If the placeholder name matches a column name exactly, it auto-maps. Otherwise, pick the column manually.

### Step 3 — Filter (optional)

Drop rows before generating, e.g. *price > 10* or *category contains "tea"*. Click **Test filter** to see how many rows match. Skip this step to keep all rows.

### Step 4 — Generate PDF

Click **Generate PDF**. A background job starts; a progress bar updates live. When it's done, the PDF downloads automatically.

If any labels had text overflowing their blocks, you'll see a warning list (which row, which object) — the PDF is still produced.

---

## 7. Data imports

Left menu → **Data imports** — every file you've ever uploaded (CSV/Excel/SQLite). You can delete them to free space. Files are private — each user sees only their own.

---

## 8. Administration (admin only)

Left menu → **Administration → Users**.

### Creating a user

1. Click **Create account**.
2. Enter email + temporary password (minimum 10 characters; you can generate a random one).
3. Pick a role:
   - **Administrator** — full access plus user management.
   - **Editor** — creates/edits their own templates and datasets.
   - **Viewer** — can open and view, but doesn't save.
4. After clicking *Create*, the temporary password is shown **once** — pass it to the user.

### Resetting a password

Click **Reset password** next to the account → generate a new temporary one → hand it over. The user is forced to change it on next login.

### Activating / deactivating

Toggle **Active** on the row. You cannot deactivate your own account (safety check).

---

## 8a. Importing / exporting templates

You can save any template as a single `.blg-template.json` file (label size + every object's position + content + bundled images). The file is portable: archive it, mail it, or import it into another BarcodeLabelGen instance.

### Export

Two entry points:
- **Templates** → hover a template tile → **⬇** icon in the bottom-right corner.
- Editor toolbar → **⬇ Export** button (next to *Download PDF*).

You get a `<name>.blg-template.json` — keep it somewhere safe as a backup.

### Import

**Templates** → **⬆ Import** opens a 2-step modal:

1. **Pick a file** — choose your `.blg-template.json`. The app validates it and shows a preview.
2. **Configure** — you can:
   - change the **name** of the new template (default is the name from the file; on collision a "(kopia)" suffix is appended automatically),
   - **override the size** (leave blank = keep original),
   - **uncheck objects** you don't want to bring in (checklist with type icons + short content preview),
   - for every **duplicate image** decide: *Reuse existing* (save space) or *Create new copy*.

Click **Import** → a new template is created and opens in the editor.

### Typical workflows

- **Backup before a big change** — export, archive the file, edit freely. Something broke → re-import.
- **Clone a layout to a different size** — export, import with size override (e.g. same label for A6 and 100×50 mm).
- **Move a template between instances** (dev → prod) — export on one side, import on the other.
- **Partial import** — take the barcode block + a couple of fields from a finished template and uncheck the rest.

### Limits and safety

- Max 20 MB file, 50 objects, 20 images (5 MB each).
- Images are integrity-checked: sha256 must match the base64 payload. Tampered files are rejected.
- The new template always belongs to your account, regardless of who exported the file.

## 9. Keyboard shortcuts

| Shortcut | Action |
|---|---|
| Ctrl/Cmd + S | Save |
| Ctrl/Cmd + Z | Undo |
| Ctrl/Cmd + Shift + Z | Redo |
| Ctrl/Cmd + A | Select everything (in the canvas) |
| Delete / Backspace | Delete selected |
| Shift + click | Add to selection |

---

## 10. Support

Maintained by **Tomasz "Amigo" Lewandowski** — contact: dev@attv.uk · www.attv.uk.

Source: github.com/AmigoUK/BarcodeLabelGen
