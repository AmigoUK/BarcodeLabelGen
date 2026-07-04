# BarcodeLabelGen — Dokumentacja Projektowa

> **Status**: Specyfikacja MVP v1.0 · **Data**: 2026-05-11 · **Język UI**: PL + EN (od dnia 1)

---

## Context

Pracownicy biurowi nie mają obecnie narzędzia, które pozwoliłoby im samodzielnie projektować etykiety i generować je masowo na podstawie arkuszy Excel/CSV (mail-merge dla etykiet). Komercyjne narzędzia (Bartender, NiceLabel) są drogie, technicznie skomplikowane i desktopowe. Canva nie obsługuje kodów kreskowych ani serii z danych. Celem projektu jest **zlikwidowanie tej luki** poprzez prostą, przeglądarkową aplikację z UX na poziomie Canvy, zoptymalizowaną pod biurowego użytkownika nietechnicznego, działającą w sieci firmowej (LAN), z naciskiem na **szybkość dostarczenia MVP** i **jakość UX**.

---

## 1. Przegląd Projektu

**Nazwa robocza**: BarcodeLabelGen
**Typ**: Web SPA (LAN-internal)
**Użytkownik docelowy**: pracownik biurowy, nietechniczny, polskojęzyczny lub anglojęzyczny
**Wartość**: jedyne wewnętrzne narzędzie pozwalające zaprojektować etykietę raz i wygenerować z niej do **1000 unikalnych etykiet** w jednym PDF na podstawie kolumn z XLS/CSV — bez znajomości DTP, bez instalacji oprogramowania, bez kontaktu z IT poza założeniem konta.

### Zakres MVP
- ✅ Online edytor etykiet (Canva-like)
- ✅ Katalog szablonów (osobisty + współdzielony)
- ✅ Generator PDF (pojedynczy + batch z XLS/CSV, do 1000 wierszy)
- ✅ Konta zarządzane przez admina (brak self-registration)
- ✅ Multilanguage UI (PL/EN)
- ⚠️ Integracja Zebra/Toshiba przez Browser Print SDK — **P1**, po MVP

---

## 2. Wymagania Funkcjonalne

### 2.1 Priorytety
- **P0** = MVP (must-have, blokuje wydanie)
- **P1** = Pierwszy update post-MVP (ważne, ale nie blokuje)
- **P2** = Backlog (nice-to-have)

### 2.2 Funkcje

| # | Funkcja | Priorytet |
|---|---|---|
| F1 | Logowanie email + hasło, wylogowanie, reset hasła przez admina | P0 |
| F2 | Panel admina: tworzenie/blokowanie/usuwanie kont, przypisywanie roli | P0 |
| F3 | Dashboard: lista moich szablonów, ostatnio używane, szybki dostęp do "Nowa etykieta" | P0 |
| F4 | Edytor canvas: tekst (font/size/bold/italic/align/color), prostokąty, linie, obrazy (upload PNG/JPG/SVG) | P0 |
| F5 | Edytor: kody kreskowe EAN-13, EAN-14, EAN-128, GTIN, Code 128, QR — z **automatyczną kontrolą sumy kontrolnej** i walidacją | P0 |
| F6 | Edytor: pola dynamiczne `{{nazwa_kolumny}}` z podpowiedziami i podświetleniem | P0 |
| F7 | Edytor: tabele (siatka komórek z konfiguracją wierszy/kolumn, możliwość bindowania komórek do pól dynamicznych) — **zrealizowane w v0.13.0**; spec: `docs/superpowers/specs/2026-07-04-editor-tables-design.md` | P1 |
| F8 | Format etykiety: predefiniowane rozmiary (A4, A5, A6, Zebra: 4×6", 4×4", 3×2", 2×1", custom mm) | P0 |
| F9 | Save/load szablonu (autosave co 30s, manual save) | P0 |
| F10 | Upload XLS/XLSX/CSV (max 10MB, 1000 wierszy) | P0 |
| F11 | Wizard mail-merge: mapowanie kolumn → pól dynamicznych (drag&drop), live preview pierwszego wiersza | P0 |
| F12 | Filtrowanie wierszy przed generowaniem (po wartości kolumny) | P0 |
| F13 | Generowanie PDF (single label / batch wielostronicowy) | P0 |
| F14 | Multilanguage UI (PL, EN) — przełącznik per-user, zapamiętywany w profilu | P0 |
| F15 | Katalogi szablonów + tagi + wyszukiwanie tekstowe — **foldery + wyszukiwanie zrealizowane w v0.11.0 (F31); tagi porzucone na rzecz folderów** | P0.5 |
| F16 | Współdzielenie szablonów między użytkownikami / w zespole (read-only lub clone) — **zrealizowane w v0.11.0 (F31): Biblioteka, read-only + klon** | P1 |
| F17 | Wersjonowanie szablonów (każdy save = nowa wersja, możliwość przywrócenia) — **zrealizowane w v0.14.0** (migawki przy ręcznym zapisie); spec: `docs/superpowers/specs/2026-07-04-template-versioning-design.md` | P1 |
| F18 | Historia wygenerowanych PDF (lista, ponowne pobranie do 30 dni) — **zrealizowane w v0.15.0**; spec: `docs/superpowers/specs/2026-07-04-generated-files-history-design.md` | P1 |
| F19 | Export/import szablonów (JSON) | P1 |
| F20 | Print preview (podgląd PDF w przeglądarce przed pobraniem) — **zrealizowane w v0.16.0** (osadzony podgląd pojedynczej etykiety); spec: `docs/superpowers/specs/2026-07-04-print-preview-design.md` | P1 |
| F21 | Integracja Zebra Browser Print (bezpośredni druk ZPL) — **zrealizowane w v0.10.0** własnym konektorem: szybka ścieżka localhost w dialogu druku | P1 |
| F22 | Integracja Toshiba (TSPL przez agenta lub Browser Print) | P2 |
| F23 | Dodatkowe języki UI (DE, ES, FR — tłumaczenie społecznościowe) | P2 |
| F24 | Placeholdery dynamicznej daty `{{date±Nd/m/y:FORMAT}}` obliczane przy generowaniu (PDF/ZPL) | P0 |
| F25 | Konektor lokalny (Go): print server — druk ZPL bezpośrednio na drukarki sieciowe (rozszerza F21) — **zrealizowane w v0.7.0** | P1 |
| F26 | Konektor: kolejka wydruków po stronie serwera + tokeny urządzeń (druk zdalny przez polling agenta) — **zrealizowane w v0.6.0** | P1 |
| F27 | Konektor: wirtualna drukarka Windows — przechwytywanie ZPL z innych aplikacji + „Inbox" w web appce (import do edytora) — **zrealizowane w v0.8.0** | P2 |
| F28 | Dokumentacja użytkownika: instrukcja + FAQ (PL/EN), placeholdery na screenshoty z opisami | P0 |
| F29 | Walidacja ZPL na wejściu (kolejka druku, przechwyty, import): sanity-check `^XA…^XZ`, limity rozmiaru, odrzucanie nie-ZPL (np. omyłkowo wysłanych stron błędów HTML) z czytelnym komunikatem — **zrealizowane w v0.9.0** | P1 |
| F30 | Lista manualnych testów UAT (checklista dla właściciela: sprzęt, Windows, realna drukarka) — warunek decyzji o wdrożeniu na prod; checklist: `docs/UAT.md` | P0 |
| F31 | Struktura folderów/katalogów szablonów + biblioteka gotowych projektów + udostępnianie innym użytkownikom (konsoliduje F15/F16) — **zrealizowane w v0.11.0**; spec: `docs/superpowers/specs/2026-07-04-folders-library-sharing-design.md` | P1 |
| F32 | Kolorowe tagi dla folderów: kolor przypisany do folderu (kropka/obwódka na pasku folderów i na kafelkach szablonów) i/lub kolorowe tagi na szablonach — **zrealizowane w v0.12.0** (kolor folderu; osobne tagi nie weszły w zakres) | P2 |
| F33 | Grafika wyróżniająca (featured image) szablonu: upload własnego obrazka podglądowego pokazywanego na kafelku listy Szablonów i w Bibliotece (krok w stronę miniatur odłożonych w F31) — **zrealizowane w v0.12.0** | P2 |
| F34 | Konektor desktop macOS + Linux: binarki (Intel/ARM/Pi), ścieżka configu na macOS, uruchomienie jako usługa (launchd/systemd) — czyste Go, kompiluje się bez zmian; plan: `docs/superpowers/specs/2026-07-04-connector-cross-platform-plan.md` | P1 |
| F35 | Konektor: wirtualna drukarka na macOS/Linux (CUPS raw backend → nasłuch JetDirect agenta), odpowiednik windowsowego przechwytywania | P2 |
| F36 | Konektor Android: osobna aplikacja mobilna (polling kolejki + druk ZPL po TCP 9100 do drukarki w WiFi); bez fast-path/wirtualnej drukarki — wymaga własnej sesji brainstormingu | P2 |

### 2.3 User Stories (wybrane kluczowe)

**US-1 (Edytor)**
> Jako pracownik biurowy, chcę przeciągnąć element tekstowy na obszar etykiety i zmienić jego font, aby zaprojektować wygląd etykiety bez znajomości narzędzi DTP.

**US-2 (Pole dynamiczne)**
> Jako pracownik biurowy, chcę dodać pole `{{kod_produktu}}` na etykiecie, aby później zostało automatycznie zastąpione wartościami z arkusza Excel.

**US-3 (Mail-merge)**
> Jako pracownik biurowy, chcę wgrać plik XLS z 500 wierszami i wygenerować PDF z 500 unikalnymi etykietami, aby nie musieć ręcznie tworzyć każdej z osobna.

**US-4 (Walidacja kodu)**
> Jako pracownik biurowy, chcę otrzymać czytelny komunikat "Niepoprawny EAN-13 w wierszu 47" przed generowaniem, aby nie wydrukować błędnych etykiet i nie marnować taśmy w drukarce.

**US-5 (Współdzielenie)** *(P1)*
> Jako pracownik biurowy, chcę udostępnić mój szablon całemu zespołowi, aby koledzy nie musieli projektować od zera.

**US-6 (Admin)**
> Jako administrator, chcę utworzyć konto nowemu pracownikowi i przesłać mu hasło tymczasowe, aby mógł zacząć pracę bez interwencji IT.

---

## 3. Wymagania Niefunkcjonalne

| Kategoria | Wymaganie |
|---|---|
| **Wydajność** | Renderowanie edytora ≤16ms/frame (60fps) dla ≤200 obiektów; generowanie batch PDF dla 1000 wierszy ≤30s |
| **Skalowalność** | Wsparcie dla ~50 jednoczesnych użytkowników (LAN), pojedynczy proces Gunicorn z 4 workerami wystarczy |
| **Dostępność** | 99% w godzinach pracy (8:00–18:00), backup DB dziennie |
| **Bezpieczeństwo** | Argon2id dla haseł, sesje w Redis, CSRF tokens, walidacja uploadów, opcjonalnie TLS w LAN |
| **Kompatybilność** | Chrome/Edge/Firefox ostatnie 2 wersje (brak wsparcia IE/Safari < 16) |
| **Lokalizacja** | i18n od pierwszego commita: brak hardkodowanych stringów UI |
| **Dostępność (a11y)** | Skróty klawiszowe w edytorze, aria-labels, kontrast WCAG AA |
| **Maintainability** | TypeScript strict mode, type hints w Pythonie (mypy), pre-commit hooks |

---

## 4. Architektura Systemu

### 4.1 Diagram komponentów

```
┌─────────────────────── BROWSER (LAN client) ─────────────────────────┐
│                                                                       │
│   ┌─────────────────────────────────────────────────────────┐        │
│   │   React SPA (Vite-built static bundle)                  │        │
│   │   ├─ Editor (react-konva canvas)                        │        │
│   │   ├─ Mail-merge wizard                                  │        │
│   │   ├─ Dashboard / Catalog                                │        │
│   │   └─ i18n (react-i18next: PL, EN)                       │        │
│   └─────────────────────────────────────────────────────────┘        │
│   ┌─────────────────────────────────────────────────────────┐        │
│   │   Zebra Browser Print SDK (P1)                          │        │
│   │   └─ ZPL/TSPL → USB/network printer                     │        │
│   └─────────────────────────────────────────────────────────┘        │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ HTTPS (nginx self-signed lub HTTP w LAN)
                           ▼
┌──────────────────── DOCKER HOST (Linux) ─────────────────────────────┐
│                                                                       │
│   ┌────────────┐    ┌──────────────────┐    ┌──────────────┐         │
│   │  nginx     │───▶│  Flask + Gunicorn│───▶│ PostgreSQL16 │         │
│   │  (reverse  │    │  (REST API,      │    │              │         │
│   │   proxy +  │    │   ReportLab,     │    └──────────────┘         │
│   │   statyki) │    │   barcode libs)  │           ▲                 │
│   └────────────┘    └──────────────────┘           │                 │
│                              │                     │                 │
│                              ├────────────────▶┌─────────┐           │
│                              │                 │  Redis  │           │
│                              │                 │ (sesje, │           │
│                              │                 │  cache) │           │
│                              ▼                 └─────────┘           │
│                     ┌─────────────────┐                              │
│                     │ Volumes:        │                              │
│                     │  /uploads (XLS) │                              │
│                     │  /pdfs (out)    │                              │
│                     │  /assets (img)  │                              │
│                     └─────────────────┘                              │
└──────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  Drukarka Zebra/    │ ◀── (P1) bezpośrednio
                │  Toshiba (USB/LAN)  │     z przeglądarki via
                └─────────────────────┘     Browser Print
```

### 4.2 Wzorce architektoniczne
- **Layered architecture** w backendzie: routes → services → repositories → models
- **REST + JSON** (OpenAPI 3 generowane przez Flask-Smorest, swagger UI na `/api/docs`)
- **SPA + API** (separacja frontend/backend, frontend buildowany do statyków serwowanych przez nginx)
- **Repository pattern** (SQLAlchemy 2.0 styl deklaratywny, sesje per-request)
- **Async-ready** (Generator PDF dla batchy >100 wierszy uruchamiany w wątku z polling endpointem statusu — proste rozwiązanie bez Celery dla MVP)

---

## 5. Tech Stack

### 5.1 Frontend
| Warstwa | Technologia | Uzasadnienie |
|---|---|---|
| Framework | **React 18 + TypeScript** | Największy ekosystem, doskonała współpraca z Konva, łatwo zatrudnić/utrzymać |
| Bundler | **Vite 5** | Najszybszy DX, HMR, minimalna konfiguracja |
| Canvas | **Konva.js + react-konva** | Najwydajniejszy silnik 2D dla wielu obiektów, deklaratywny model — kluczowy dla edytora |
| Styling | **TailwindCSS + shadcn/ui** | Szybkie prototypowanie, gotowe komponenty na poziomie produkcyjnym |
| State | **Zustand** | Prosty store, idealny dla stanu edytora (undo/redo, selection) |
| i18n | **react-i18next** | Standard branżowy, lazy-loading języków |
| Forms | **react-hook-form + Zod** | Type-safe walidacja |
| HTTP | **TanStack Query (React Query)** | Cache, refetch, optymistyczne aktualizacje |
| Routing | **React Router 6** | Standard |

### 5.2 Backend
| Warstwa | Technologia | Uzasadnienie |
|---|---|---|
| Runtime | **Python 3.12** | LTS, pełne typowanie |
| Package mgr | **uv** (Astral) | Najszybszy resolver, lock file, zgodne z preferencją usera |
| Framework | **Flask 3.x** | Wybór usera, lekki, elastyczny |
| API | **Flask-Smorest** | Auto-OpenAPI, walidacja, marshmallow |
| ORM | **SQLAlchemy 2.0** | Standard, async-ready |
| Migracje | **Alembic** | Standard dla SQLAlchemy |
| Walidacja | **Pydantic v2** | Type-safe DTOs |
| Auth | **Flask-Login + Argon2** | Sprawdzone, proste |
| Sesje | **Flask-Session + Redis** | Skalowalne, łatwy logout globalny |
| PDF | **ReportLab** | Najpełniejsza kontrola pozycjonowania w mm, idealne dla etykiet |
| Barkody | **treepoem** (BWIPP) + **qrcode** | treepoem obsługuje wszystkie żądane (EAN-13/14/128, GTIN, Code128) z checksum |
| XLS/CSV | **openpyxl + pandas** | openpyxl dla XLSX, pandas dla CSV i filtrowania |
| Obrazy | **Pillow** | Resize, conversion |
| i18n | **Flask-Babel** | Tłumaczenie komunikatów błędów |
| Testy | **pytest + pytest-flask** | Standard |

### 5.3 Infrastruktura
| Warstwa | Technologia |
|---|---|
| Container | Docker + Docker Compose |
| Reverse proxy | nginx (alpine) |
| Database | PostgreSQL 16 |
| Cache/Sessions | Redis 7 |
| WSGI | Gunicorn (4 workers, gthread) |
| Process supervisor | docker compose restart policy |

---

## 6. Model Danych

### 6.1 Encje (uproszczony schemat)

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────┐
│    User      │       │     Template     │       │   Category   │
├──────────────┤       ├──────────────────┤       ├──────────────┤
│ id (PK)      │◀──┐   │ id (PK)          │   ┌──▶│ id (PK)      │
│ email        │   │   │ owner_id (FK)    │───┘   │ owner_id(FK) │
│ password_hash│   ├───│ name             │       │ name         │
│ role         │   │   │ description      │       └──────────────┘
│ language     │   │   │ category_id (FK) │
│ is_active    │   │   │ format_id (FK)   │       ┌──────────────┐
│ created_at   │   │   │ canvas_data JSONB│       │ LabelFormat  │
└──────────────┘   │   │ current_version  │       ├──────────────┤
                   │   │ is_shared        │   ┌──▶│ id (PK)      │
       ┌───────────┘   │ created_at       │───┘   │ name         │
       │               │ updated_at       │       │ width_mm     │
       │               └────────┬─────────┘       │ height_mm    │
       │                        │                 │ type         │ (A4|ZEBRA|CUSTOM)
       │                        │                 └──────────────┘
       │                        ▼
       │               ┌──────────────────┐       ┌──────────────┐
       │               │ TemplateVersion  │       │     Tag      │
       │               ├──────────────────┤       ├──────────────┤
       │               │ id (PK)          │       │ id (PK)      │
       │               │ template_id (FK) │       │ name         │
       │               │ version_number   │       └──────┬───────┘
       │               │ canvas_data JSONB│              │
       │               │ created_by (FK)  │       ┌──────▼───────┐
       │               │ created_at       │       │ TemplateTag  │
       │               └──────────────────┘       ├──────────────┤
       │                                          │ template_id  │
       │               ┌──────────────────┐       │ tag_id       │
       │               │     DataSet      │       └──────────────┘
       └──────────────▶├──────────────────┤
                       │ id (PK)          │       ┌──────────────────┐
                       │ owner_id (FK)    │       │GenerationHistory │
                       │ filename         │       ├──────────────────┤
                       │ columns JSONB    │       │ id (PK)          │
                       │ row_count        │       │ user_id (FK)     │
                       │ file_path        │       │ template_id (FK) │
                       │ uploaded_at      │       │ dataset_id (FK)  │
                       └──────────────────┘       │ pdf_path         │
                                                  │ status           │
                                                  │ row_count        │
                                                  │ error_message    │
                                                  │ generated_at     │
                                                  └──────────────────┘
```

### 6.2 Kluczowe decyzje
- **`canvas_data` jako JSONB** — całość drzewa Konva.Stage serializowanego do JSON. Daje to elastyczność (zmiany w edytorze nie wymagają migracji DB) i łatwy import/export.
- **`TemplateVersion`** — pełna kopia `canvas_data` per wersja (prostsze niż diffy; przy ~50KB/szablon i kilkudziesięciu wersjach to akceptowalne)
- **`role`** — enum (`admin`, `editor`, `viewer`) z RBAC w middleware
- **PDF-y** trzymane na dysku (volume), a nie w DB; `pdf_path` to względna ścieżka

---

## 7. API & Integracje

### 7.1 REST Endpoints (skrót)

```
AUTH
  POST   /api/auth/login              → { token/cookie }
  POST   /api/auth/logout
  POST   /api/auth/change-password

ADMIN (rola: admin)
  GET    /api/admin/users
  POST   /api/admin/users             → tworzy konto
  PATCH  /api/admin/users/:id         → blokada/zmiana roli
  POST   /api/admin/users/:id/reset-password

TEMPLATES
  GET    /api/templates?scope=mine|shared&q=...&tag=...&category=...
  POST   /api/templates
  GET    /api/templates/:id
  PUT    /api/templates/:id
  DELETE /api/templates/:id
  GET    /api/templates/:id/versions               (P1)
  POST   /api/templates/:id/versions/:n/restore    (P1)
  POST   /api/templates/:id/share                  (P1)
  GET    /api/templates/:id/export                 (P1) → JSON
  POST   /api/templates/import                     (P1)

CATEGORIES & TAGS
  GET    /api/categories  /  POST  /api/categories
  GET    /api/tags

DATASETS
  POST   /api/datasets                → upload XLS/CSV (multipart)
  GET    /api/datasets/:id/preview?rows=5
  POST   /api/datasets/:id/filter     → { column, op, value } → liczba pasujących wierszy

GENERATION
  POST   /api/generate                → { template_id, dataset_id?, mapping?, filters?, single_data? }
                                       → { job_id }
  GET    /api/generate/:job_id/status → { status: pending|running|done|error, progress: 0-100 }
  GET    /api/generate/:job_id/download → application/pdf

HISTORY (P1)
  GET    /api/history
  GET    /api/history/:id/download

LABEL FORMATS
  GET    /api/label-formats

ASSETS
  POST   /api/assets/images           → upload obrazu (PNG/JPG/SVG)
  GET    /api/assets/images/:id

META
  GET    /api/me                      → profil zalogowanego
  GET    /api/health
  GET    /api/docs                    → Swagger UI

KONEKTOR (F26 zaimplementowane w v0.6.0; agent auth tokenem urządzenia Bearer, poza sesją/CSRF)
  GET    /api/devices                 → urządzenia użytkownika (status, drukarki, last_seen)
  POST   /api/devices                 → { name } → { device, token }  (token pokazany raz)
  DELETE /api/devices/:id             → odwołanie tokenu
  POST   /api/print-jobs              → { device_id, printer, zpl, copies } → { job }
  GET    /api/print-jobs              → zadania użytkownika (status pending/sent/done/error)
  GET    /api/agent/jobs              → polling agenta: claim oczekujących zadań (pending→sent)
  POST   /api/agent/jobs/:id/status   → done|error (raport agenta)
  POST   /api/agent/state             → heartbeat: wersja agenta + lista drukarek
  POST   /api/agent/captures          → upload ZPL z wirtualnej drukarki (v0.8.0)
  GET    /api/captures                → „Inbox"; GET/DELETE /api/captures/:id (v0.8.0)
```

### 7.2 Integracje zewnętrzne
- **Brak na MVP**
- **P1**: Zebra Browser Print (JS SDK osadzony w SPA, komunikacja przez `localhost:9100` z lokalnym serwisem Zebra)
- **P2**: Toshiba — przez Browser Print kompatybilny lub własny lekki agent (out of MVP scope)
- **P1/P2**: własny konektor `blg-connector` (Go) — hybryda: lokalny HTTP `127.0.0.1:9110` (szybki druk z przeglądarki) + wychodzący polling do API (kolejka, upload przechwyconego ZPL); wirtualna drukarka Windows przez nasłuch JetDirect na `127.0.0.1:9101` + sterownik ZDesigner na porcie Standard TCP/IP. Szczegóły: `docs/superpowers/specs/2026-07-04-date-placeholders-and-connector-design.md`

---

## 8. Przepływy Użytkownika

### 8.1 Pierwsze logowanie
```
Admin → tworzy konto (email, hasło tymczasowe, rola)
  → wysyła hasło użytkownikowi (out-of-band, np. email/teams)
User → /login → wpisuje email + hasło tymczasowe
  → ekran "Wymuś zmianę hasła"
  → Dashboard
```

### 8.2 Tworzenie szablonu
```
Dashboard → "Nowa etykieta"
  → Modal: wybierz format (A4 / Zebra 4×6" / custom mm)
  → Editor (3 panele: biblioteka | canvas | properties)
  → przeciąga elementy: tekst, barcode, image, table, dynamic field
  → autosave co 30s + ręczny "Zapisz"
  → "Zapisz i zamknij" → wraca na Dashboard
```

### 8.3 Generowanie batch PDF (kluczowy flow)
```
Dashboard → wybiera szablon → "Generuj serię"
  ┌─ Krok 1: Upload danych ──┐
  │  Drag&drop XLSX/CSV       │
  │  → walidacja (max 10MB,   │
  │    1000 wierszy, kolumny) │
  └─────────┬─────────────────┘
            ▼
  ┌─ Krok 2: Mapowanie ──────┐
  │  Lista pól dynamicznych  │
  │  szablonu po lewej       │
  │  Kolumny CSV po prawej    │
  │  Drag&drop / select       │
  └─────────┬─────────────────┘
            ▼
  ┌─ Krok 3: Filtr & Preview ┐
  │  Opcjonalny filtr wierszy│
  │  Live preview pierwszego  │
  │  wiersza w canvas         │
  │  Walidacja barkodów →     │
  │  lista błędów per wiersz  │
  └─────────┬─────────────────┘
            ▼
  ┌─ Krok 4: Generuj ─────────┐
  │  Progress bar (polling)   │
  │  → "Pobierz PDF" + opcja  │
  │     "Wyślij do drukarki"  │ (P1)
  └───────────────────────────┘
```

---

## 9. Bezpieczeństwo

### 9.1 Autentykacja i autoryzacja
- **Argon2id** (parametry: memory=64MB, iterations=3, parallelism=4)
- **Sesje** w Redis, cookie HttpOnly + Secure (jeśli TLS) + SameSite=Lax, TTL 8h sliding
- **CSRF tokens** dla wszystkich mutujących endpointów (Flask-WTF)
- **RBAC** — middleware sprawdzające rolę `admin` dla `/api/admin/*`
- **Brak self-registration** — endpoint `/api/auth/register` **nie istnieje**

### 9.2 Ochrona danych
- Walidacja uploadów: MIME-type + extension + content sniff (python-magic)
- Limity: 10MB plik danych, 5MB obraz, max 1000 wierszy
- Sanityzacja wartości z XLS/CSV (escape przy renderowaniu PDF — choć ReportLab jest wektorowy, więc XSS nie dotyczy)
- Hasła nigdy w logach
- Pliki użytkowników w wolumenie izolowanym, nazwane UUID-ami (nie oryginalnymi nazwami)
- LAN-only: aplikacja nie powinna być wystawiona publicznie bez review

### 9.3 RODO/GDPR
- Minimalne dane osobowe: tylko email + hasło + język
- Brak trackingu, brak ciasteczek analitycznych
- Endpoint `/api/me/delete` (P1) usuwa konto + szablony + historię (cascade)

---

## 10. Strategia Wdrożenia

### 10.1 Środowiska
- **dev**: `docker compose -f compose.dev.yml up` — hot-reload Flask, Vite dev server proxowany
- **prod**: `docker compose up -d` — zbudowane statyki, Gunicorn, restart policy `unless-stopped`
- Brak staging dla MVP (LAN-internal, prod = środowisko firmowe)

### 10.1.1 Dostęp przez Tailscale (HTTPS)
- **Host**: dowolny serwer w tailnecie (Linux z Dockerem)
- **URL produkcyjny**: `https://<host>.<tailnet>.ts.net:18003`
- **Port lokalny aplikacji** (nginx w kontenerze): `127.0.0.1:18003`
- **Wybór portu**: `18003` — domyślny dla MVP; zmień jeśli kolizja z innymi usługami serwowanymi przez Tailscale
- **TLS**: automatycznie zarządzany przez Tailscale (cert Let's Encrypt dla `*.ts.net`) — **brak potrzeby self-signed**
- **Komenda ekspozycji** (po starcie kontenera, jednorazowo):
  ```bash
  tailscale serve --bg --https=18003 http://127.0.0.1:18003
  ```
- **Dostęp**: tylko członkowie tailnetu (autoryzowani użytkownicy)
- **Brak Funnel** (nie wystawiamy publicznie do internetu)

### 10.2 docker-compose.yml (struktura)
```yaml
services:
  nginx:        # reverse proxy + static frontend, ports: 127.0.0.1:18003:80
  web:          # Flask + Gunicorn + ReportLab
  db:           # PostgreSQL 16
  redis:        # sesje + cache + (przyszłość) queue

volumes:
  pgdata, redisdata, uploads, pdfs, assets

networks:
  internal     # bridge, brak external dostępu poza nginx
```

**Kluczowe**: nginx publikuje port **tylko na `127.0.0.1:18003`** (nie `0.0.0.0`), żeby aplikacja była dostępna wyłącznie przez Tailscale Serve, a nie przez publiczny IP serwera.

### 10.3 CI/CD (lekkie dla MVP)
- **Pre-commit hooks**: ruff (lint+format), mypy, prettier, eslint
- **GitHub Actions / Gitea Actions** (jeśli on-prem):
  - lint + test on PR
  - build images on tag → push do lokalnego registry
  - deploy: ręczny `docker compose pull && up -d` na hoście
- Brak Kubernetes — overkill dla LAN MVP

### 10.4 Wymagania infrastrukturalne
- 1 host Linux (Debian/Ubuntu LTS), 4 vCPU / 8GB RAM / 50GB SSD
- Docker Engine 24+, Docker Compose v2
- Backup pg_dump → wolumen hosta + opcjonalnie sync na NAS

---

## 11. Strategia Testowania

### 11.1 Piramida testów
| Poziom | Narzędzia | Pokrycie |
|---|---|---|
| **Unit** | pytest (BE), vitest (FE) | logika barkodów, parser CSV, walidatory, utility funkcje, hooki React |
| **Integration** | pytest + Flask test client + testowy PG (testcontainers) | API endpoints, ORM, generowanie PDF |
| **Snapshot** | pytest-regressions | hash bajtów wygenerowanego PDF dla wzorcowych szablonów |
| **E2E** | Playwright | 3 critical paths: login, utwórz szablon, wygeneruj batch PDF |
| **Manual** | Checklista | integracja z fizyczną drukarką (P1, brak automatyzacji) |

### 11.2 Kryteria akceptacji MVP
- ✅ 100% API endpoints ma test integracyjny (happy path + 1 błąd)
- ✅ Snapshot test dla każdego typu kodu kreskowego
- ✅ E2E "happy path" przechodzi w CI
- ✅ Coverage ≥70% dla backendu
- ✅ Lighthouse ≥90 dla głównych stron (SPA, więc CSR)
- ✅ Manual smoke test na rzeczywistym XLS z 1000 wierszy

---

## 12. Ryzyka i Mitygacje

| Ryzyko | Prawd. | Wpływ | Mitygacja |
|---|---|---|---|
| **R1**: Edytor canvas (Canva-like UX) wykracza poza budżet czasowy MVP | Wysoka | Wysoki | Iteracyjne dostarczanie: najpierw tekst+kody, potem obrazy, na końcu tabele. Tabele można przesunąć do P0.5 |
| **R2**: ~~Tabele w canvas~~ — przesunięte do P1 (decyzja usera) | — | — | Nie dotyczy MVP. W P1 implementacja iteracyjna: najpierw tabele o stałej liczbie kolumn z bindowaniem do CSV, potem pełna edycja siatki |
| **R3**: Generowanie 1000 PDF-ów blokuje request HTTP | Pewna | Wysoki | Job w wątku + polling endpoint statusu. Jeśli okaże się za wolne → Celery + Redis broker w P1 |
| **R4**: Zebra Browser Print wymaga instalacji u każdego użytkownika | Średnia | Niski (P1) | Dokumentacja onboarding + IT może pre-zainstalować przez GPO |
| **R5**: Walidacja kodów kreskowych (zwłaszcza GS1/EAN-128 z FNC1) jest skomplikowana | Średnia | Średni | Użycie biblioteki `treepoem` (BWIPP) — jest "ground truth" w branży |
| **R6**: Multilanguage od dnia 1 spowalnia development | Średnia | Niski | Tylko PL+EN na start, użycie `react-i18next` od pierwszego komponentu (taniej niż retrofit) |
| **R7**: Nietechniczny user nie zrozumie pól dynamicznych `{{...}}` | Średnia | Średni | Wizard mail-merge przeprowadza krok po kroku; w edytorze "field picker" zamiast ręcznego wpisywania |
| **R8**: PDF wygenerowany nie wygląda identycznie jak preview w canvas | Średnia | Wysoki | Strict mapping mm→points; snapshot tests; manual review per typ formatu |
| **R9**: Konflikt edycji (dwóch użytkowników edytuje ten sam shared template) | Niska | Niski | Lock optimistyczny (etag/version) + komunikat "Szablon był zmieniony" |
| **R10**: Wzrost rozmiaru DB przez wersje szablonów | Niska | Niski | Limit 50 wersji per szablon (FIFO); compress JSONB |

---

## 13. Następne Kroki

### 13.1 Roadmap implementacyjny (kolejność dla agentów kodujących)

**Sprint 0 — Setup (1–2 dni)**
1. Inicjalizacja repo: `git init`, remote `git@github.com:AmigoUK/BarcodeLabelGen.git`, push pierwszego commita z dokumentacją
2. `pyproject.toml` (uv), `package.json` (Vite+React+TS), `docker-compose.yml`, `Dockerfile` (multi-stage)
3. Setup nginx config (port `127.0.0.1:18003`), Flask skeleton, Vite skeleton, połączenie z PostgreSQL i Redis
4. Pre-commit hooks, ruff, mypy, eslint, prettier
5. Tailscale Serve setup: `tailscale serve --bg --https=18003 http://127.0.0.1:18003`
6. Weryfikacja: otwarcie `https://<host>.<tailnet>.ts.net:18003` zwraca placeholder "Hello from BarcodeLabelGen"
7. CI workflow (lint + test) — opcjonalnie GitHub Actions

**Sprint 1 — Auth + Admin (3–5 dni)**
1. Modele: `User`, `Role` enum
2. Endpoints: login/logout, change-password, admin user management
3. Frontend: strona logowania, layout aplikacji, panel admina (lista/twórz user)
4. i18n setup (PL+EN), language switcher
5. Testy: unit + integration dla auth

**Sprint 2 — Editor Core (7–10 dni)** ← *najtrudniejszy*
1. Setup react-konva, Zustand store dla stanu edytora (selection, undo/redo)
2. Komponenty: Toolbar, LeftPanel (biblioteka), Canvas, RightPanel (properties)
3. Elementy: Text (z formatowaniem), Rectangle, Line, Image (upload)
4. Save/load: serializacja Konva → JSONB; endpoint POST/PUT template
5. Format etykiety: predefiniowane rozmiary + custom mm; konwersja mm↔px
6. Autosave (debounce 30s)

**Sprint 3 — Barcodes + Dynamic Fields (3–5 dni)**
1. Backend: generator obrazów barkodów (treepoem) z endpoint preview
2. Frontend: typ elementu "Barcode" w canvas, properties: typ kodu, dane, walidacja
3. Pola dynamiczne: typ "DynamicField" z placeholder syntax `{{column_name}}`
4. Walidator checksum dla każdego typu kodu

**Sprint 4 — PDF Generator + Catalog (5–7 dni)**
1. Backend: ReportLab renderer z JSONB Konva — pixel-perfect mapping
2. Endpoint: POST /generate (single label), zwraca PDF
3. Dashboard: lista szablonów, wyszukiwanie, kategorie, tagi
4. Snapshot tests dla wzorcowych szablonów

**Sprint 5 — Mail-Merge (5–7 dni)**
1. Backend: upload XLS/CSV (openpyxl/pandas), modele DataSet
2. Endpoint preview, filter
3. Frontend: wizard 4-krokowy (upload → mapping → filter → generate)
4. Live preview pierwszego wiersza w canvas
5. Async generation: job_id + status polling endpoint
6. Walidacja barkodów per wiersz przed generowaniem

**Sprint 6 — Polish + Release (3–4 dni)**
1. Improved UX, error handling, loading states, empty states, toast notifications
2. E2E Playwright testy (3 critical paths)
3. Dokumentacja użytkownika (PL+EN, w aplikacji jako tooltip/help)
4. Seed data: 3 przykładowe szablony (etykieta produktowa, etykieta wysyłkowa, etykieta magazynowa)
5. README projektu + skrypt deploy

**MVP RELEASE** ✅

**Post-MVP (P1)**: wersjonowanie, współdzielenie, historia, export/import, Zebra Browser Print

### 13.2 Decyzje zatwierdzone przez usera
1. ✅ **Tabele**: poza zakresem MVP, implementacja w P1
2. ✅ **Języki**: PL + EN od dnia 1 (infrastruktura i18n gotowa na rozszerzenia)
3. ✅ **Limit obrazów**: 5 MB / obraz (z auto-kompresją po stronie backendu)
4. ✅ **Nazwa**: `BarcodeLabelGen` (zachowana)
5. ✅ **Repo**: `git@github.com:AmigoUK/BarcodeLabelGen.git`
6. ✅ **Workflow**: commit + push po każdym dużym kroku implementacyjnym
7. ✅ **Dostęp**: Tailscale Serve, `https://<host>.<tailnet>.ts.net:18003` (port 18003, tylko tailnet)

---

## Verification — jak przetestować end-to-end

Po zakończeniu Sprint 0–5:

1. **Setup lokalny**: `docker compose up -d` → aplikacja na `http://localhost`
2. **Smoke test**:
   - zaloguj jako admin (seed user) → utwórz konto testowe
   - wyloguj, zaloguj jako test user → wymuś zmianę hasła
   - utwórz szablon: format A6, dodaj tekst "Produkt:", pole dynamiczne `{{nazwa}}`, kod EAN-13 z polem `{{ean}}`
   - zapisz, wróć na dashboard, otwórz ponownie → szablon powinien być identyczny
   - "Generuj serię" → wgraj testowy XLS z 100 wierszami (`nazwa`, `ean`)
   - mapuj kolumny → preview pierwszego wiersza wygląda OK → generuj
   - pobierz PDF → otwórz, sprawdź wszystkie 100 etykiet
3. **Performance test**: powtórz z 1000 wierszy → czas generowania ≤30s
4. **Multilanguage test**: przełącz na EN → cały UI w EN → wygeneruj PDF (PDF jest danymi, nie zależny od UI lang)
5. **Snapshot test**: `pytest tests/snapshots/ -v` → wszystkie hash zgodne
6. **E2E test**: `playwright test` → 3 critical paths zielone
7. **Coverage**: `pytest --cov=app --cov-report=term-missing` → ≥70%

---

*Dokumentacja przygotowana przez AI Council (Architect, Product Analyst, UX Strategist, Security Advisor, DevOps Engineer, QA Lead). Po zatwierdzeniu sugeruję przeniesienie do `/var/www/html/BarcodeLabelGen/docs/PROJECT.md`.*
