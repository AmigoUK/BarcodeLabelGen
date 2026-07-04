# Design F17: wersjonowanie szablonów

Data: 2026-07-04 · Status: wariant rekomendowany (brainstorming; brak odpowiedzi
na pytanie „co jest wersją" → ręczny zapis tworzy wersję) · P1.

## Decyzja: co tworzy wersję

Edytor autozapisuje co 30 s — gdyby każdy zapis tworzył wersję, historia
zaśmieciłaby się dziesiątkami wpisów na sesję. Dlatego:

- **Autozapis** nadpisuje bieżący `canvas_data` bez tworzenia wersji (jak dziś).
- **Ręczny zapis** (przycisk *Zapisz* / Ctrl+S) zapisuje **migawkę do historii**.

To zgodne z pierwotnym F17 „każdy save = wersja" — user-facing save = ręczny.
Zmiana semantyki pola `Template.version`: rośnie tylko przy migawce (świadomym
zapisie), nie przy autozapisie. Numer wersji = liczba migawek.

## Model danych (alembic 0011)

`template_versions`: id, template_id FK→templates (CASCADE), version (int),
canvas_data (JsonField), width_mm, height_mm (snapshot rozmiaru — restore ma
być kompletny), created_by FK→users (SET NULL), created_at, note (str|null —
np. „przywrócono z v3"). Index (template_id, version desc). UNIQUE(template_id,
version).

**Retencja:** trzymamy ostatnie **30** wersji na szablon; przy zapisie starsze
ponad limit są kasowane (jak `captures`). `log()`/komentarz o limicie w kodzie.

## Serwis (`services/template_versions.py`, bez Flaska)

- `snapshot(session, tpl, *, created_by, note=None)` — tworzy wiersz z bieżącego
  stanu szablonu, przycina do 30. Wołane z `templates.update` gdy `snapshot=True`.
- `list_versions(session, template_id, *, owner_id)` — metadane bez canvas_data.
- `get_version(session, template_id, version, *, owner_id)` — pełny wiersz.
- `restore(session, template_id, version, *, requesting_user_id)` — ustawia
  `canvas_data`/rozmiar szablonu na wersję i **tworzy nową migawkę** „przywrócono
  z vN" (restore odwracalny, sam jest w historii).

## API

- `PUT /api/templates/:id` — nowe opcjonalne `snapshot: bool` (domyślnie false).
  Autozapis wysyła false; ręczny Zapisz/Ctrl+S wysyła true. Gdy true i
  `canvas_data` obecne → `template_versions.snapshot` + bump `version`.
  Gdy false → nadpisanie bez wersji, bez bumpu.
- `GET /api/templates/:id/versions` → `{versions: [{version, note, created_at,
  created_by_email}]}` (owner-only).
- `GET /api/templates/:id/versions/:version` → pełny `canvas_data` + rozmiar
  (podgląd).
- `POST /api/templates/:id/versions/:version/restore` → przywraca, zwraca
  zaktualizowany `TemplatePublic`.

Dostęp: wyłącznie właściciel (historia prywatna nawet dla udostępnionych).

## Frontend

- **Toolbar edytora**: przycisk **🕘 Historia** (obok Zapisz). Otwiera modal.
- **Autosave** (`useAutosave`) → PUT `snapshot:false`. **Ręczny zapis**
  (`saveCanvas` z przycisku i Ctrl+S) → PUT `snapshot:true`. Rozdzielenie
  w `EditorPage.saveCanvas(canvas, {snapshot})`.
- **Modal historii** (`VersionHistoryModal`): lista wersji (v#, data, autor),
  akcje per wiersz: **Podgląd** (miniatura/opis — v1: pokazuje datę+numer,
  „Przywróć" wystarcza) i **Przywróć** (potwierdzenie → restore → przeładowanie
  canvasu w edytorze przez invalidację + `replaceCanvas`). i18n PL/EN.
- Hook `useTemplateVersions(id)` + `useRestoreVersion`.

## Testy / weryfikacja

- pytest: snapshot tylko przy `snapshot=true`; autosave nie tworzy wersji;
  retencja 30; list/get owner-scoped (cudzy → 404); restore ustawia canvas +
  tworzy migawkę „przywrócono z vN"; restore nieistniejącej → 404.
- Frontend: typecheck/lint; e2e GUI na instancji: kilka ręcznych zapisów →
  historia rośnie; autozapis nie dodaje wersji; przywrócenie starszej zmienia
  canvas.
- Docs: HELP/FAQ PL/EN, PROJECT F17 done, UAT wpis. Release 0.14.0.

## Poza zakresem v1

Diff wizualny między wersjami, nazywanie wersji przez użytkownika, wersje dla
autozapisu, gałęzie/tagi, przywracanie do nowego szablonu (klon z wersji).
