# Design F31: foldery szablonów + Biblioteka (startery i udostępnianie)

Data: 2026-07-04 · Status: zatwierdzony kierunkowo (brainstorming: 3 decyzje użytkownika;
finalne „go" domyślne — wariant rekomendowany, bez miniatur) · Konsoliduje F15/F16.

## Decyzje z brainstormingu

1. **Foldery: płaskie, prywatne per użytkownik.** Jeden poziom; szablon leży w
   dokładnie jednym folderze albo luzem („Bez folderu"). Bez drzewa, bez drag&drop w v1.
2. **Biblioteka = startery wbudowane + szablony udostępnione przez użytkowników.**
   Jedna zakładka w sidebarze, dwie sekcje. Użycie zawsze przez „Użyj" (klon do siebie).
3. **Udostępnianie: dla wszystkich zalogowanych, read-only + klon.** Przełącznik
   „Udostępnij w Bibliotece" na własnym szablonie; edytuje tylko właściciel.
   Wykorzystuje istniejące pole `is_shared` (dziś bez UI).

Decyzje pochodne: lista „Szablony" pokazuje odtąd **wyłącznie własne** (dziś API
miesza cudze `is_shared` do głównej listy — po zmianie cudze żyją tylko w Bibliotece);
miniatury kafelków — poza zakresem v1 (przyszłe rozszerzenie).

## Startery — pliki w repo (wybrane podejście)

Startery to zwykłe pliki `.blg-template.json` (istniejący format eksportu) w
`backend/app/library/` — wersjonowane w gicie, walidowane i klonowane **istniejącą
maszynerią importu** (`templates_io`): zero seedów w bazie, zero użytkownika
systemowego, aktualizacja startera = commit. Odrzucone: seedowane wiersze w DB
(konto-widmo, migracje przy każdej zmianie), hardkod we frontendzie (omija walidację).

Zestaw v1 (6, nazwy PL): etykieta produktu EAN-13 z `{{name}}`/`{{date+x}}`,
adres wysyłki 100×150 (Code128), cena półkowa A6, termin przydatności 50×30,
etykieta magazynowa z QR, inwentarzowa Zebra 2×1".

## Model danych (alembic 0009)

- `folders`: id, owner_id FK→users (CASCADE), name (≤100), created_at,
  UNIQUE(owner_id, name).
- `templates.folder_id`: nullable FK→folders **ON DELETE SET NULL**
  (usunięcie folderu nie kasuje szablonów — wracają do „Bez folderu").

## API

- `GET/POST /api/folders`, `PATCH /api/folders/:id` (rename), `DELETE /api/folders/:id`
  — wszystkie owner-scoped; lista z licznikiem szablonów.
- `GET /api/templates` dostaje `?scope=mine|library` (**domyślnie `mine`** — zmiana
  zachowania) i `?folder_id=<id|none>`; `library` = cudze `is_shared` + własne
  udostępnione (z nazwą właściciela w odpowiedzi).
- `PATCH /api/templates/:id` — istniejące `is_shared` (bez zmian) + nowe `folder_id`
  (walidacja: folder musi należeć do użytkownika).
- `POST /api/templates/:id/clone` — „Użyj": dostęp jak przy odczycie (własny lub
  udostępniony), kopiuje canvas/rozmiar/opis do nowego szablonu klonującego,
  nazwa „<oryginał> (kopia)"; obrazy współdzielone (istniejący mechanizm sha256).
- `GET /api/library/starters` — lista z bundlowanych plików (slug, nazwa, opis,
  rozmiar); `POST /api/library/starters/:slug/use` — import przez `templates_io`
  do szablonów użytkownika.

## Frontend

- **Szablony**: lewy pasek folderów (Wszystkie / foldery z licznikami / Bez
  folderu; dodaj, zmień nazwę, usuń z potwierdzeniem), filtr po kliknięciu;
  na kafelku menu: „Przenieś do folderu…" (select) i checkbox „Udostępnij
  w Bibliotece". Wyszukiwarka działa w obrębie wybranego folderu.
- **Biblioteka** (nowa pozycja sidebar, ikona 📚): sekcja „Startery" i „Od
  użytkowników" (autor przy kafelku); kafelek: nazwa, rozmiar mm, opis,
  przycisk **„Użyj"** → klon → nawigacja do edytora. Własny udostępniony
  szablon ma zamiast „Użyj" dopisek „Twój szablon".
- i18n PL/EN dla całości.

## Testy / weryfikacja

- pytest: CRUD folderów + izolacja właścicieli + unikat nazwy; scope=mine nie
  pokazuje cudzych; scope=library pokazuje cudze tylko is_shared; move do cudzego
  folderu → 404/400; clone własnego/udostępnionego OK, cudzego prywatnego → 404;
  DELETE folderu → szablony folder_id=NULL; startery: lista, use tworzy szablon.
- e2e na instancji + zrzuty GUI (foldery, Biblioteka, Użyj → edytor).
- Docs: HELP/FAQ PL/EN, UAT sekcja F, PROJECT.md F15/F16/F31 statusy. Release 0.11.0.

## Poza zakresem v1 (przyszłość)

Miniatury podglądu kafelków (render PNG serwerowo), drag&drop do folderów,
foldery zagnieżdżone, udostępnianie per-osoba, edycja wspólna.
