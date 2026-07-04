# Design F20: podgląd wydruku PDF

Data: 2026-07-04 · Status: wariant rekomendowany (brainstorming; brak odpowiedzi
→ modal z osadzonym PDF, zakres: pojedyncza etykieta) · P1. Mała funkcja,
głównie frontend.

## Cel

Przycisk **👁 Podgląd** w toolbarze edytora: generuje pojedynczą etykietę i
pokazuje PDF **w oknie aplikacji** (osadzony), z przyciskami **Pobierz** i
**Zamknij** oraz ewentualnymi ostrzeżeniami o przepełnieniu tekstu — bez
opuszczania aplikacji i bez ślepego pobierania.

## Zakres

- **Pojedyncza etykieta** (ten sam endpoint co „Pobierz PDF": `POST /api/generate`
  bez datasetu, zwraca PDF inline). Backend **bez zmian**.
- Seria (kreator) — **poza v1**: kreator już pokazuje status jobu; podgląd
  wielostronicowych plików to osobny, cięższy temat.

## Refaktor `useGeneratePdf`

Dziś hook w jednym kroku fetchuje **i** wymusza download. Rozdzielam
odpowiedzialności (czystsze granice, ta sama maszyneria dla obu przycisków):

- `useGeneratePdf` → zwraca `{ blob, warnings, durationMs }` (bez auto-downloadu).
- `downloadBlob(blob, filename)` — mały helper (albo istniejący `triggerDownload`).
- „Pobierz PDF": generuj → `triggerDownload`. „Podgląd": generuj → otwórz modal
  z blobem; w modalu **Pobierz** woła `triggerDownload` na tym samym blobie
  (jedno wygenerowanie = jeden wpis w Historii F18, bo `/api/generate` zapisuje
  plik).

## `PrintPreviewModal`

Osadza PDF: `<object data={blobUrl} type="application/pdf">` z komunikatem-
fallbackiem (gdy przeglądarka nie umie osadzić — link „otwórz w nowej karcie").
Stopka: **Pobierz** (triggerDownload) + **Zamknij**. Lista ostrzeżeń
(`warnings`) nad podglądem, jeśli niepusta. Blob URL tworzony przy otwarciu,
**zwalniany** (`URL.revokeObjectURL`) przy zamknięciu. i18n PL/EN.

## Toolbar / EditorPage

- `Toolbar`: przycisk `👁 Podgląd` (`onPreview`) obok „Pobierz PDF"; oba
  disabled w trakcie generowania.
- `EditorPage`: stan `previewBlob`; klik Podgląd → `generate.mutateAsync` →
  ustaw blob → render `PrintPreviewModal`.

## Testy / weryfikacja

- Frontend typecheck/lint. Brak testów jednostkowych renderu PDF w przeglądarce
  (celowo — jak reszta frontendu).
- e2e GUI na instancji: klik Podgląd → modal z osadzonym PDF widoczny →
  Pobierz ściąga plik → Zamknij zwalnia. Sprawdzić, że wpis w Historii powstaje
  raz (nie dubluje przy Podgląd+Pobierz).
- Docs HELP/FAQ/PROJECT/UAT; CHANGELOG; release 0.16.0. (Bez zmian backendu →
  bump tylko frontend + wersja aplikacji.)

## Poza zakresem v1

Podgląd serii wielostronicowej, zoom/nawigacja stron ponad natywny czytnik
osadzonego PDF, podgląd na żywo bez klikania (auto-render przy każdej zmianie).
