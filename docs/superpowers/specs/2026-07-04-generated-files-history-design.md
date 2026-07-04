# Design F18: historia wygenerowanych PDF

Data: 2026-07-04 · Status: zakres zatwierdzony przez użytkownika (serie **i**
pojedyncze) · P1.

## Cel

Strona **Historia** z listą wygenerowanych plików (pojedyncze etykiety, serie
PDF, wsadowy eksport ZPL) i ponownym pobraniem przez **30 dni**. Dziś: serie
lądują na dysku (`pdfs/`) ale rekord Redis wygasa po 24 h i plik nigdy nie jest
kasowany (sieroty); pojedyncze etykiety nie są w ogóle zapisywane.

## Model (`generated_files`, alembic 0012)

id, owner_id FK→users (CASCADE, index), template_id FK→templates (SET NULL —
historia przeżywa usunięcie szablonu), template_name (String, snapshot nazwy),
kind ("pdf"|"zpl"), mode ("single"|"series"), storage_filename (String, plik w
`pdfs_dir()`), row_count (int|null — liczba etykiet w serii), created_at.
Rozmiar **nie** jest kolumną — liczony leniwie z `os.stat` przy listowaniu
(unika rozjazdu, gdy plik batcha powstaje w tle).

## Kluczowa decyzja: bez DB w wątku roboczym

`jobs.run_in_thread` działa poza Flaskiem/DB i **zostaje nietknięty**. Zamiast
pisać wpis z wątku:

- **Batch (PDF/ZPL)**: route tworzy wpis `generated_files` synchronicznie przy
  starcie joba — `storage_filename` jest znany z góry (`{job_id}_{safe}.pdf`).
- **Single**: route zapisuje bajty do `pdfs_dir()/{uuid}_{safe}.pdf` (obok
  dotychczasowego zwrotu inline) + wpis.

**Listowanie pomija wpisy, których plik jeszcze nie istnieje** — batch w toku
lub nieudany job nie zaśmieca historii. „Gotowość" wnioskujemy z obecności
pliku, nie ze statusu Redis. To trzyma `jobs.py` bez zależności od DB.

## Retencja (leniwa, po raz pierwszy czasowa)

Serwis `generated_files.record()` przy każdym zapisie:
1. usuwa wpisy `created_at < now-30d` **i ich pliki** z dysku;
2. usuwa wpisy, których plik nie istnieje i `created_at < now-1h` (osierocone
   nieudane joby) — bez kasowania plików (ich nie ma).

Bez crona — spójne z precedensem `captures`/`template_versions` (trim-on-write).
Retencja to `GENERATED_RETENTION_DAYS = 30` w serwisie.

## Serwis (`services/generated_files.py`, bez Flaska)

- `record(session, *, owner_id, template_id, template_name, kind, mode,
  storage_filename, row_count=None)` — wstawia wpis + odpala retencję.
- `list_for_user(session, *, user_id)` — wpisy z istniejącym plikiem, najnowsze
  pierwsze, z doliczonym `size_bytes` (os.stat).
- `get_for_user(session, file_id, *, user_id)` — jeden wpis (owner-scoped).
- `delete(session, file_id, *, user_id)` — wpis + plik.

## API (`routes/history.py`, session auth, owner-only)

- `GET /api/history` → `{files: [{id, template_name, kind, mode, row_count,
  size_bytes, created_at}]}`.
- `GET /api/history/:id/download` → `send_file` (mimetype wg kind), 410 gdy
  plik zniknął.
- `DELETE /api/history/:id` → 204.

Wpięcia: `routes/generate.py` (single + batch) i `routes/zpl.py` (batch)
wołają `generated_files.record`. Nazwy: batch reużywa `output_filename`; single
generuje własny plik.

## Frontend

- Nowa strona **`/history`** (`HistoryPage`) + pozycja nav **Historia**
  (klucz `nav.history` już istnieje w i18n). Tabela: nazwa szablonu, typ
  (PDF/ZPL), tryb (Pojedyncza/Seria), liczba etykiet, rozmiar, data;
  przyciski **Pobierz** i **Usuń**. Hooki `useHistory` / `useDeleteHistory`.
- Pusta lista → komunikat. Pobieranie przez istniejący `triggerDownload`/blob
  wzorzec.

## Testy / weryfikacja

- pytest: single tworzy wpis+plik; batch tworzy wpis, niewidoczny póki plik nie
  powstanie; ZPL batch → kind=zpl; retencja 30 dni (wpis z podmienionym
  `created_at` znika); download owner-scoped (cudzy → 404); delete usuwa plik;
  410 gdy plik ręcznie skasowany.
- Frontend typecheck/lint; e2e GUI na instancji: wygeneruj pojedynczy + serię,
  Historia pokazuje oba, ponowne pobranie działa, usuwanie działa.
- Docs HELP/FAQ/PROJECT/UAT; CHANGELOG; release 0.15.0.

## Poza zakresem v1

Podgląd miniatury PDF w historii, filtrowanie/szukanie, współdzielenie linku,
konfigurowalny okres retencji przez UI, sprzątanie plików-sierot sprzed F18.
