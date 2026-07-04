# Design: dynamiczne placeholdery daty + konektor lokalny (print server / wirtualna drukarka)

Data: 2026-07-04 · Status: zatwierdzony (brainstorming z użytkownikiem) · Backlog: F24–F28

## Część A — Placeholdery daty `{{date+x}}` (F24, implementowane teraz)

### Cel

Etykiety z terminami przydatności i datami produkcji: data obliczana w momencie
generowania (PDF lub ZPL), przesunięta względem „dziś".

### Składnia

```
{{date}}                  → 04.07.2026        (dziś, format domyślny DD.MM.YYYY)
{{date+14d}}              → 18.07.2026        (+14 dni)
{{date-7d}}               → 27.06.2026        (−7 dni)
{{date+3m}}               → 04.10.2026        (+3 miesiące)
{{date+1y}}               → 04.07.2027        (+1 rok)
{{date+14d:DD/MM/YY}}     → 18/07/26          (format po dwukropku)
{{date+3m:YYYY-MM-DD}}    → 2026-10-04
```

- Jednostki: `d` (dni), `m` (miesiące), `y` (lata); znak `+`/`-`; liczba całkowita.
- Tokeny formatu: `DD`, `MM`, `YY`, `YYYY` (YYYY ma pierwszeństwo przed YY);
  pozostałe znaki przechodzą literalnie (separatory `.`, `/`, `-`, spacje).
- Arytmetyka miesięcy/lat klampuje koniec miesiąca (31.01 + 1m → 28/29.02) —
  `dateutil.relativedelta`.

### Semantyka

- **Reguła kolizji**: gołe `{{date}}` — jeśli dataset ma kolumnę `date`, wygrywa
  wartość z wiersza (kompatybilność wsteczna); bez kolumny → obliczona dzisiejsza
  data. Formy z offsetem/formatem (`{{date+14d}}` itd.) są **zawsze** obliczane.
- **Fallthrough**: niepoprawna składnia (`{{date+xyz}}`, `{{date+14w}}`, spacje
  wewnętrzne) traktowana jak zwykły klucz kolumny (dotychczasowe zachowanie:
  wartość z wiersza lub pusty string w batch; verbatim w single).
- Zmienne drukarkowe ZPL w pojedynczych klamrach `{NAZWA}` — nietknięte.

### Punkty wpięcia

| Ścieżka | Miejsce | Zachowanie |
|---|---|---|
| Batch PDF | `substitute_string` w `backend/app/services/batch_render.py` | daty + kolumny |
| Batch ZPL | j.w. (przez `zpl/batch.py`) | daty + kolumny |
| Single PDF | `backend/app/routes/generate.py` (przed `render_template_pdf`) | **tylko daty**, `{{kolumny}}` verbatim |
| Template ZPL | `backend/app/routes/zpl.py` (przed `generate_zpl`) | **tylko daty** |
| Podgląd w edytorze | chip w inspektorze (`RightPanel.tsx`) | obliczona wartość po stronie przeglądarki |

Nowy moduł: `backend/app/services/placeholders.py` (evaluacja + `substitute_dates_in_canvas`),
lustro TS: `frontend/src/lib/datePlaceholder.ts`.

### Strefa czasowa

„Dziś" = data lokalna serwera; kontener backendu dostaje `TZ=Europe/London`
w `compose.yml` (bez tego kontener liczy w UTC → ryzyko przesunięcia ±1 dzień
względem oczekiwań użytkownika). Podgląd w przeglądarce używa daty lokalnej
przeglądarki. Przyszły druk przez konektor: ewaluacja dat następuje po stronie
serwera w momencie utworzenia zadania druku.

### Kreator serii

Formy z offsetem/formatem nie pojawiają się na liście kolumn do zmapowania.
Gołe `date` pojawia się, auto-mapuje się na kolumnę `date` jeśli istnieje,
ale mapowanie jest opcjonalne (bez niego — dzisiejsza data).

---

## Część B — Konektor lokalny `blg-connector` (F25–F27, projekt — implementacja w kolejnych sesjach)

### Problem

Web app jest hostowana poza siecią lokalną użytkownika; drukarki ZPL (Zebra i
kompatybilne) stoją w LAN. Potrzebne: (1) druk z web appki na te drukarki,
(2) przechwytywanie wydruku ZPL z innych aplikacji Windows do edycji w web appce.

### Architektura: hybryda (zatwierdzona)

```
DRUK — szybka ścieżka (przeglądarka w tym samym LAN co drukarka):
  przeglądarka ──POST /print──▶ agent http://127.0.0.1:9110 ──RAW TCP 9100──▶ drukarka

DRUK — kolejka (przeglądarka gdziekolwiek, np. telefon):
  przeglądarka ──▶ web app POST /api/print-jobs
  agent ──polling GET /api/agent/jobs (HTTPS, token urządzenia)──▶ drukarka

PRZECHWYT — wirtualna drukarka Windows:
  Word/ERP ──▶ sterownik ZDesigner ──port TCP/IP 127.0.0.1:9101──▶ agent (nasłuch JetDirect)
  agent ──POST /api/agent/captures──▶ web app („Inbox" → edytor przez /api/zpl/parse)
```

Zero portów otwieranych z internetu — agent wyłącznie inicjuje połączenia wychodzące;
lokalny HTTP związany tylko z `127.0.0.1`.

### Agent (Go)

- Jeden statyczny `.exe`; tryb usługi Windows **lub** ikona w trayu; config w
  `%ProgramData%\blg-connector\config.yaml` (URL serwera, token, lista drukarek).
- Endpointy lokalne (`127.0.0.1:9110`): `GET /status` (wersja, drukarki, stan),
  `GET /printers`, `POST /print` `{ zpl, printer, copies }`.
- Transport do drukarek: RAW TCP 9100 (JetDirect); drukarki definiowane ręcznie
  (IP:port, nazwa); auto-discovery (mDNS/SNMP) = nice-to-have, poza pierwszą iteracją.
- Wirtualna drukarka **bez własnego sterownika**: agent nasłuchuje na
  `127.0.0.1:9101`; użytkownik instaluje darmowy sterownik ZDesigner i dodaje
  drukarkę na porcie Standard TCP/IP → `127.0.0.1:9101`. Sterownik produkuje ZPL,
  agent zapisuje strumień (podział zadań po timeoutach/`^XZ`) i uploaduje.
- Polling: `GET /api/agent/jobs` co 2–5 s (docelowo long-poll); raport statusu
  po druku.
- Cross-compile: ten sam agent na Linux/Raspberry Pi jako czysty print server.

### Strona serwera (Flask)

- **Tokeny urządzeń**: tabela `devices` (id, nazwa, token-hash, user/zespół,
  last_seen); token generowany w UI (Ustawienia → Urządzenia), pokazywany raz.
  Ścieżki `/api/agent/*` uwierzytelniane nagłówkiem tokenu, **poza** sesją
  i CSRF (osobny dekorator, analogicznie do `admin_required`).
- **Kolejka druku**: tabela `print_jobs` (zpl, printer, copies, status, device,
  created_by); endpointy jak w PROJECT.md §7.1 (sekcja KONEKTOR).
- **Inbox przechwytów**: `captures` (zpl, device, created_at) + widok listy
  w UI; „Otwórz w edytorze" → istniejące `POST /api/zpl/parse` (DPI auto).

### Frontend

- Dialog druku: wybór agenta/drukarki/liczby kopii; najpierw próba szybkiej
  ścieżki (`fetch http://127.0.0.1:9110/status`), przy braku agenta lokalnego —
  fallback na kolejkę serwerową.
- Wskaźnik stanu agenta + strona Ustawienia → Urządzenia (tokeny, last_seen).

### Ryzyka do walidacji w fazie implementacji

1. **Private Network Access / mixed content**: strona HTTPS → `http://127.0.0.1`.
   Chrome traktuje localhost jako potentially trustworthy, ale PNA wymaga
   preflight (`Access-Control-Allow-Private-Network: true` w agencie). Plan B:
   self-signed cert na localhost (wzorzec Zebra Browser Print) lub wyłącznie
   ścieżka przez kolejkę.
2. Sklejanie/rozdzielanie zadań na porcie 9101 (strumień JetDirect nie ma ramek) —
   heurystyka `^XZ` + timeout.
3. Sterownik ZDesigner generuje ZPL z bitmapami (`^GF`) dla treści nie-tekstowych —
   import do edytora pokaże je jako passthrough; edycja pełna tylko dla etykiet
   źródłowo ZPL-owych. Komunikować w UI.

### Fazy wdrożenia

- **Faza B** (serwer): tokeny urządzeń + kolejka + endpointy + UI urządzeń.
- **Faza C** (agent Go): druk — localhost + polling + RAW 9100 + instalator/usługa.
- **Faza D**: wirtualna drukarka (nasłuch 9101) + Inbox + import do edytora.

---

## Część C — Dokumentacja użytkownika (F28, w tej sesji po implementacji)

Instrukcja użytkownika + FAQ generowane skillem UXDocs, **PL i EN**
(`docs/user-guide/pl/`, `docs/user-guide/en/`), wyłącznie na bazie realnych
funkcji aplikacji. Screenshoty jako placeholdery
`![SCREENSHOT: <tytuł>](TODO-screenshot)` z jednozdaniowym opisem kadru,
do późniejszego podmienienia na realne zrzuty. Link z README.
