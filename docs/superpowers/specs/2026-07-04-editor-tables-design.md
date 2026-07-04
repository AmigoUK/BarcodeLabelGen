# Design F7: tabele w edytorze etykiet

Data: 2026-07-04 · Status: wariant rekomendowany (brainstorming; brak odpowiedzi na
pytanie o zakres → edycja w panelu + edytowalne szerokości kolumn) · P1 z MVP.

## Cel

Obiekt „tabela": siatka wierszy×kolumn z tekstem w komórkach (w tym
`{{placeholdery}}` i `{{date+x}}`), drukowana w PDF i emitowana natywnie do ZPL.
Typowe użycia: tabela cecha–wartość (waga, partia, data), wartości odżywcze,
lista pozycji.

## Model danych (frontend `types.ts`, JSON w canvas_data)

```ts
type TableObject = EditorObjectBase & {
  type: "table";
  width: number;        // mm, całość (= suma colWidths, gdy podane)
  height: number;       // mm, całość (wiersze równe: height/rows)
  rows: number;         // 1–20
  cols: number;         // 1–8
  cells: string[][];    // rows × cols; tekst z {{...}}
  colWidths?: number[]; // mm, length == cols; brak → równe
  headerRow?: boolean;  // pogrubiony pierwszy wiersz
  fontSize: number;     // mm
  fontFamily: string;
  fill: string;         // kolor tekstu
  stroke: string;       // kolor siatki
  strokeWidth: number;  // mm
};
```

Padding komórki: stała 0.8 mm (nie w modelu). Wysokości wierszy: równe (v1).

## UX (wariant „panel")

- **Lewy panel**: przycisk `▦ Tabela` — domyślnie 3×2, 40×24 mm, nagłówek wł.,
  komórki przykładowe.
- **Prawy panel (`TableProps`)**: liczba wierszy/kolumn (zmiana zachowuje
  istniejące komórki — dokłada puste / obcina); **siatka inputów** do treści
  komórek (wiersz nagłówka wyróżniony); szerokości kolumn w mm (edycja
  przelicza `width`); fontSize/fontFamily/fill; stroke/strokeWidth; checkbox
  „Pogrubiony nagłówek". `PlaceholderChips` ze wszystkich komórek łącznie
  (chips fioletowe + zielone daty działają jak w tekstach).
- **Canvas (`objects/TableObject.tsx`)**: Konva `Group` (id = object.id →
  wspólny Transformer działa): zewnętrzny `Rect`, wewnętrzne `Line` wg
  granic kolumn/wierszy, `Text` per komórka (wrap do szerokości kolumny,
  ellipsis przy przepełnieniu wysokości wiersza), nagłówek bold.
  Resize: fold scaleX/scaleY → width/height + proporcjonalne przeskalowanie
  `colWidths` (wzór RectObject). Rotacja: Group rotation (Konva obsługuje).
- Klik-w-komórkę na canvasie: **poza zakresem v1** (przyszłość).

## Rendering

- **PDF (`pdf_renderer._draw_table`)**: własne rysowanie (nie delegacja) —
  `saveState` + translate/rotate wokół (x,y) raz dla całej tabeli, potem
  siatka liniami i tekst per komórka (`_wrap_lines` w szerokości kolumny −
  2×padding, obcięcie do wysokości wiersza z wpisem do `warnings` jak
  w `_draw_text`); nagłówek fontem bold (`_resolve_font`). Dispatch w obu
  miejscach: `render_template_pdf` i `batch_render.render_batch_pdf`.
- **ZPL (`generator._emit_table`)**: natywnie — zewnętrzna ramka i linie
  siatki jako `^GB` (poziome: wysokość = grubość; pionowe: szerokość =
  grubość), komórki jako **syntetyczne obiekty text** delegowane do
  istniejącego `_emit_text` (spójne fonty/`^FB`/escape). `rotation != 0` →
  warning „table rotation not supported in ZPL; emitted unrotated".
  **Parser bez zmian** — reimport ZPL degraduje tabelę do rect/line/text
  (naturalna, udokumentowana degradacja).

## Substytucja i wykrywanie placeholderów (komórki)

- `batch_render.substitute_object`: gałąź `table` — kopia z podmianą
  `substitute_string` per komórka (świeża kopia 2D listy — obiekt bywa
  przekazywany bez deepcopy w `zpl/batch.py`).
- `placeholders.substitute_dates_in_canvas`: analogiczna gałąź z
  `substitute_date_string` (pojedynczy PDF i template-ZPL).
- `SeriesWizard.detectTemplatePlaceholders`: zbiera stringi ze wszystkich
  komórek; `templates_io._has_placeholder`: skan komórek;
  `_object_summary`: etykieta „Table r×c".

## Punkt nieoczywisty

`frontend/src/editor/units.ts getBoundsMm` — switch bez default; brak gałęzi
`table` psuje wyrównywanie/rozkładanie. Dodać `case "table"` (x,y,width,height).

## Testy / weryfikacja

- pytest: substytucja komórek (kolumny+daty+kolizja), PDF z tabelą (magic
  bytes + tekst komórek przez pdfplumber, overflow warning), ZPL z tabelą
  (`^GB` liczba linii, `^FD` treści komórek, warning przy rotacji),
  `_has_placeholder` dla tabel.
- Frontend: typecheck/lint; e2e GUI: dodanie tabeli, edycja komórek
  w panelu z `{{date+7d}}` (zielony chip), PDF i eksport ZPL na instancji.
- Starter „Tabela cecha–wartość" dołożony do Biblioteki (7. plik).
- Docs: HELP/FAQ PL/EN sekcja o tabelach; PROJECT F7 done; UAT test 🟡.
- Release 0.13.0.

## Poza zakresem v1

Klik-w-komórkę na canvasie, scalanie komórek, per-komórkowe style,
niejednakowe wysokości wierszy, tło komórek, auto-dopasowanie wysokości.
