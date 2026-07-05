# F22 — Eksport TSPL (drukarki TSC / desktop Toshiba)

Data: 2026-07-05 · Status: **spec zaakceptowany** (wariant A, single-label MVP) · Priorytet: P2

## Cel

Umożliwić eksport etykiety z edytora jako **TSPL** (TSPL2 — język drukarek TSC
oraz wielu desktopowych Toshiba/rebrandów), analogicznie do istniejącego eksportu
ZPL. Użytkownik pobiera plik `.txt`/`.prn` z komendami TSPL i wysyła go na swoją
drukarkę TSC.

## Zakres

**W zakresie (MVP):**

1. Generator `backend/app/services/tspl/` — `generate_tspl(canvas_data, *, dpmm,
   warnings) -> str` obejmujący te same typy obiektów co generator ZPL:
   text, barcode (Code 128 / GS1-128 / EAN-13 / QR), rect, line, table; image
   pomijany z ostrzeżeniem.
2. Endpoint eksportu `POST /api/tspl/generate` (tryb pojedynczej etykiety /
   template — jak gałąź `mode="template"` w `/api/zpl/generate`).
3. Frontend: akcja „Eksportuj TSPL" w edytorze (lustrzana do eksportu ZPL) —
   modal z podglądem tekstu, kopiowaniem i pobraniem, plus lista ostrzeżeń.
4. Dokumentacja + wpis PROJECT.md (F22) + CHANGELOG.

**Poza zakresem (świadomie):**

- **TPCL** (przemysłowe Toshiba B-EX/B-SA) — inny język; osobny przyszły element.
- **Druk przez agenta** — kolejka `print_jobs` niesie pole `zpl`, a agent ma
  bramkę `looksLikeZPL` (wymaga `^XA…^XZ`), która odrzuciłaby TSPL. Druk TSPL
  wymagałby pola „język" w zadaniu + rozluźnienia bramki agenta + fizycznej
  drukarki TSC do weryfikacji — osobny, większy element (przyszłe F).
- **Eksport wsadowy TSPL** (serie, jak `render_batch_zpl`) — szybki follow-up po
  MVP; tu tylko pojedyncza etykieta.
- **Round-trip** (parsowanie TSPL → canvas) — mała wartość, poza zakresem.

## Realia weryfikacji (uczciwość)

Nie ma tutaj fizycznej drukarki TSC. Weryfikowalne w tej sesji: **struktura
generowanego TSPL** (testy jednostkowe każdego emitera + test endpointu).
**Rzeczywisty wydruk** na drukarce TSC weryfikuje użytkownik. Dwa mapowania są z
natury przybliżone i są **udokumentowanymi ograniczeniami**:

- **Czcionki**: edytor używa TrueType (Liberation), TSPL ma wbudowane czcionki
  bitmapowe „1".."8" skalowane całkowitymi mnożnikami. Rozmiar/krój będą
  przybliżone (dobieramy czcionkę + mnożnik najbliższy żądanej wysokości).
- **GAP/DENSITY/SPEED**: zależne od nośnika i modelu; dajemy rozsądne domyślne
  (`GAP 3 mm,0 mm`), które użytkownik może potrzebować dostroić na drukarce.

## Architektura

Nowy pakiet `backend/app/services/tspl/` obok `zpl/`:

```
tspl/
  __init__.py     # eksportuje generate_tspl
  generator.py    # canvas → TSPL (lustro zpl/generator.py)
```

**Reużycie jednostek**: TSPL importuje generyczne `mm_to_dots`, `dpmm_for_dpi`,
`DPMM_BY_DPI`, `DEFAULT_DPMM` z `app.services.zpl.units` (czysta matematyka
mm→dots, ta sama gęstość 203/300 dpi → 8/12 dpmm; bez semantyki ZPL). Rotacja w
TSPL jest liczbowa (0/90/180/270), więc generator TSPL ma własne zaokrąglanie
rotacji (nie letter-based jak ZPL). `zpl/` **nie jest modyfikowany**.

### `generate_tspl(canvas_data, *, dpmm=None, warnings=None) -> str`

Sygnatura i semantyka `dpmm`/`warnings` jak `generate_zpl`. Struktura wyjścia:

```
SIZE <w> mm, <h> mm
GAP 3 mm, 0 mm
DIRECTION 1
REFERENCE 0,0
CLS
<obiekty w kolejności canvasu, printable != False>
PRINT 1
```

Współrzędne obiektów w **dotach** (mm→dots przez `dpmm`), origin lewy-górny.
Liczba kopii z `stage.zpl.pq` jeśli obecna, inaczej 1 (reużycie istniejącego
pola; nazwa `zpl` w stage to historyczny pojemnik hintów — TSPL czyta z niego
tylko `pq`, `dpmm`, wymiary).

### Mapowanie obiektów (synteza z geometrii canvasu)

Hinty `obj["zpl"]` są ZPL-specyficzne — TSPL ich **nie** używa; syntetyzuje z
ogólnych pól (`x,y,width,height,rotation,fontSize,align,text,barcodeType,data,
fill,stroke,strokeWidth`).

| Obiekt | Komenda TSPL |
|---|---|
| text (1 linia) | `TEXT x,y,"<font>",<rot>,<xmul>,<ymul>,"<text>"` |
| text (width>0 / wielolinia) | `BLOCK x,y,<w_dots>,<h_dots>,"<font>",<rot>,<xmul>,<ymul>,"<text>"` |
| barcode code128/gtin/ean14/gs1_128 | `BARCODE x,y,"128",<h_dots>,1,<rot>,2,2,"<data>"` (gs1_128 → `"EAN128"`) |
| barcode ean13 | `BARCODE x,y,"EAN13",<h_dots>,1,<rot>,2,2,"<data>"` |
| barcode qr | `QRCODE x,y,M,<cell>,A,<rot>,"<data>"` (cell 1..10 z wysokości) |
| rect z obrysem | `BOX x,y,<x+w>,<y+h>,<t_dots>` (t = strokeWidth, min 1) |
| rect wypełniony / line | `BAR x,y,<w_dots>,<h_dots>` (line: cieńszy wymiar = strokeWidth) |
| table | siatka `BAR` (linie) + komórki przez ten sam code path co text |
| image | pominięte + `warnings.append({object_id, message})` |

**Czcionka/mnożnik** (`_pick_font`): wybiera bitmapową „1".."8" i całkowity
`xmul=ymul` dający wysokość najbliższą `fontSize` w dotach; przy braku dobrego
dopasowania dokłada ostrzeżenie „TSPL bitmap fonts approximate the editor font".

**Rotacja** (`_snap_rot`): zaokrągla `rotation % 360` do najbliższej z
{0,90,180,270}; przy zaokrągleniu dokłada ostrzeżenie (jak ZPL).

**Escaping**: TSPL treść w cudzysłowach; wewnętrzne `"` zamieniamy sekwencją
`\[22]` (kod TSPL) — funkcja `_esc`. `{{date+x}}` rozwiązywane wcześniej w
endpoint (jak w ZPL), więc do generatora trafia gotowy tekst.

## Dostarczenie (endpoint + UI)

### `POST /api/tspl/generate` (`backend/app/routes/tspl.py`)

Nowy blueprint zarejestrowany w fabryce aplikacji. Body jak ZPL (podzbiór):
`{mode:"template", template_id?|canvas_data?, dpi?}`. Logika = lustro gałęzi
`mode=="template"` z `/api/zpl/generate`:

1. Walidacja (Pydantic `TsplGenerateRequest`, mirror `ZplGenerateRequest` bez
   pól batch).
2. Rozwiązanie canvasu (`template_id` → własność użytkownika, lub `canvas_data`).
3. `substitute_dates_in_canvas(canvas_data)` (rozwiązanie `{{date+x}}`).
4. `generate_tspl(canvas_data, dpmm=dpmm_for_dpi(dpi), warnings=warnings)`.
5. `Response(text, mimetype="text/plain; charset=utf-8")`, nagłówek
   `Content-Disposition: attachment; filename="<name>.txt"`, `Cache-Control:
   no-store`; ostrzeżenia w `X-TSPL-Warnings` (+ `Access-Control-Expose-Headers`).

Rozszerzenie `.txt` (TSPL nie ma kanonicznego rozszerzenia jak `.zpl`; `.prn` też
używane, ale `.txt` jest najbezpieczniejsze do podglądu).

### Frontend

Lustro istniejącego eksportu ZPL: `ExportTsplModal.tsx` (kopia wzorca
`ExportZplModal.tsx` — podgląd tekstu, Kopiuj, Pobierz, lista ostrzeżeń z
nagłówka `X-TSPL-Warnings`) + wpięcie akcji „Eksportuj TSPL" w `Toolbar`/menu
edytora obok „Eksportuj ZPL". i18n PL/EN dla nowych etykiet.

## Obsługa błędów

- Nieobsługiwany obiekt (image) → ostrzeżenie, pominięty (jak ZPL).
- Nieznany `barcodeType` → best-effort `"128"` (Code 128) + ostrzeżenie.
- Brak wymiarów etykiety → `SIZE` z wymiarów canvasu; gdy 0 → pomijamy `SIZE`
  (drukarka użyje własnej kalibracji) + ostrzeżenie.
- Endpoint: brak canvasu/template → 400/404/403 jak ZPL.

## Plan weryfikacji

**W tej sesji (backend, testowalne):**

1. `test_tspl.py` — generator: nagłówek (`SIZE/GAP/DIRECTION/CLS`), stopka
   (`PRINT`), każdy typ obiektu (TEXT, BLOCK, BARCODE 128, BARCODE EAN13, QRCODE,
   BOX, BAR, table→BAR+TEXT), image→warning, nieznany barcode→warning, rotacja
   nie-90°→warning, escaping cudzysłowu.
2. `test_tspl_endpoint.py` — `POST /api/tspl/generate` z `canvas_data`: 200,
   `Content-Disposition` attachment `.txt`, `text/plain`, obecność `SIZE`/`PRINT`
   w treści; wariant z image → nagłówek `X-TSPL-Warnings`.
3. `ruff` + `pytest` zielone.

**Frontend:** `npm run typecheck` + `npm run lint`; weryfikacja akcji eksportu na
żywej instancji (headless Chromium z wstrzykniętą sesją) — pobranie TSPL dla
szablonu, sprawdzenie że treść zaczyna się od `SIZE`.

**Poza tą sesją (użytkownik):** wydruk pliku TSPL na fizycznej drukarce TSC.

## Wersjonowanie

Nowa funkcja użytkowa → **minor**: app `0.19.1 → 0.20.0`. CHANGELOG `[0.20.0]`,
tag `v0.20.0`, GitHub release (bez zmian binarek konektora / APK). PROJECT.md:
F22 → zrealizowane (eksport; druk przez agenta i TPCL poza zakresem).

## Poza zakresem tego spec

TPCL, druk TSPL przez agenta, eksport wsadowy/serie TSPL, round-trip TSPL,
auto-detekcja modelu drukarki.
