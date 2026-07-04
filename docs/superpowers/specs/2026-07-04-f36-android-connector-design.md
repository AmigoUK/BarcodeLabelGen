# F36 — Konektor na Androida (aplikacja mobilna poll-and-print)

Data: 2026-07-04 · Status: **spec zaakceptowany** (stack B: Go+gomobile) · Priorytet: P2

## Cel

Aplikacja Android, która działa jak konektor `blg-connector`, ale w wersji
mobilnej: łączy się do serwera BarcodeLabelGen tokenem urządzenia, pobiera
zadania z kolejki i drukuje ZPL po RAW TCP 9100 do drukarki w tej samej sieci
WiFi. Bez fast-path localhost i bez wirtualnej drukarki — te nie mają sensu na
telefonie.

## Realia środowiska (uczciwość weryfikacji)

W środowisku, w którym powstaje ten spec, **nie ma toolchainu Android** (brak
Javy, Gradle, Android SDK, Kotlina, gomobile — jest tylko Go 1.22). Wobec tego:

- **Rdzeń Go (`connector/mobilecore/`) — weryfikowalny tutaj.** Powstaje w tej
  sesji wraz z testami jednostkowymi uruchamianymi na tym serwerze.
- **Powłoka Kotlin/Android + AAR z gomobile — niezweryfikowane przez autora
  spec.** Kod i instrukcje powstają w planie; build APK, uruchomienie na
  urządzeniu i test end-to-end wykonuje osoba z Android Studio. Wszędzie
  oznaczone jako „niezweryfikowane na urządzeniu".

## Zakres

**W zakresie (MVP):**

1. **Rdzeń Go `connector/mobilecore/`** — samodzielny, importowalny pakiet
   (nie `main`) z API przyjaznym gomobile (string-in / string-out), pokrywający
   pełny cykl poll → druk → raport statusu → raport stanu. Z testami.
2. **Plan powłoki Android (Kotlin)** — `PrintService` (foreground service z
   trwałym powiadomieniem) wołający rdzeń w pętli; `MainActivity` z formularzem
   konfiguracji (URL serwera, token, IP/port drukarki, interwał) i statusem;
   trwałość ustawień (DataStore).
3. **Plan budowy AAR** przez gomobile i złożenia APK.
4. Dokumentacja: README modułu Android + wpis w PROJECT.md.

**Poza zakresem (świadomie):**

- Auto-discovery drukarek (mDNS/SNMP) — nice-to-have na później; MVP = ręczne
  IP.
- Fast-path localhost i wirtualna drukarka (przechwytywanie) — bez sensu na
  Androidzie.
- Publikacja w Google Play — MVP dystrybuowany jako APK (sideload w LAN);
  Play opcjonalnie później.
- Wiele drukarek per urządzenie w UI — MVP obsługuje jedną skonfigurowaną
  drukarkę (nazwa mapowana na `job.printer`); rozbudowa później.
- iOS (analogiczny, osobny artefakt, gdy zajdzie potrzeba).

## Kontrakt agent↔serwer (do odtworzenia — bez zmian po stronie serwera)

Zweryfikowany w `connector/client.go` i `connector/printer.go`:

- `GET /api/agent/jobs`, nagłówek `Authorization: Bearer <token>` →
  `{"jobs":[{"id":int,"printer":string,"copies":int,"zpl":string}]}`.
  Pobranie oznacza zadania jako `sent` po stronie serwera.
- Druk: TCP `dial drukarka:port` (domyślnie 9100), zapis
  `ensureTrailingNewline(zpl)` powtórzonego `copies` razy, timeout 10 s.
  `copies` klampowane do zakresu `1..1000` (`MaxCopies`).
- `POST /api/agent/jobs/{id}/status` → `{"status":"done"|"error","error":?}`.
- `POST /api/agent/state` → `{"agent_version":string,"printers":[{"name","host",
  "port"}]}` (heartbeat + lista drukarek widocznych w UI serwera).
- 401 = token odrzucony → komunikat „odtwórz token na stronie Urządzenia".

## Architektura

Trzy warstwy:

```
┌───────────────────────────────────────────────┐
│ Kotlin/Android  (plan — niezweryfikowane)      │
│  MainActivity (config + status, DataStore)     │
│  PrintService (foreground, pętla co N s)       │
│        │  wywołania string-in / string-out     │
├────────┼───────────────────────────────────────┤
│ AAR (gomobile bind — build poza tym środow.)   │
├────────┼───────────────────────────────────────┤
│ Go  connector/mobilecore/  (TEN spec, testy)   │
│  Agent{serverURL, token, agentVersion}         │
│   RunOnce(host, port) → JSON podsumowania       │
│   ReportState(name, host, port) → error         │
└───────────────────────────────────────────────┘
```

### Warstwa rdzenia: `connector/mobilecore/`

Samodzielny pakiet (gomobile wymaga importowalnego pakietu, nie `main`).
Odwzorowuje sprawdzoną logikę desktopowego agenta; **desktop pozostaje
nietknięty** (unikamy regresji w wydanym artefakcie). Duplikacja jest mała
(kilka krótkich funkcji) i celowa; przyszła konsolidacja do wspólnego pakietu
`core/` odnotowana jako opcja poza zakresem.

**Ograniczenia gomobile bind** kształtują API: eksportowane funkcje przyjmują/
zwracają tylko typy proste (`string`, `int`, `bool`, `[]byte`) oraz wskaźniki
na struktury/interfejsy z pakietu. **Brak `[]Job` na granicy** — dlatego rdzeń
kapsułkuje cały cykl i zwraca **JSON string**, który Kotlin tylko wyświetla.

**Eksportowane API:**

```go
// NewAgent tworzy klienta rdzenia (gomobile: konstruktor → *Agent).
func NewAgent(serverURL, token, agentVersion string) *Agent

// RunOnce wykonuje jeden cykl: poll kolejki → druk każdego zadania na
// host:port → raport statusu każdego zadania. Zwraca JSON podsumowania:
//   {"polled":int,"printed":int,"failed":int,"messages":[string,...],"authError":bool}
// error zwracany tylko dla błędu całego cyklu (np. sieć przy pollingu);
// błędy pojedynczych zadań lądują w failed/messages i są raportowane serwerowi.
func (a *Agent) RunOnce(printerName, printerHost string, printerPort int) (string, error)

// ReportState wysyła heartbeat z jedną skonfigurowaną drukarką.
func (a *Agent) ReportState(printerName, printerHost string, printerPort int) error
```

Wewnętrznie (nieeksportowane, testowane): `pollJobs()`, `printTCP(host,port,
zpl,copies)` (z `ensureTrailingNewline` + klamp `copies`), `reportStatus(id,
status,errMsg)`, `looksLikeZPL(data)` (lustro `zplcheck.go`), `reportState(...)`.
Timeout HTTP 15 s, timeout druku 10 s — jak desktop.

### Warstwa AAR (plan)

`gomobile bind -target=android -o blgcore.aar ./connector/mobilecore` na maszynie
z Android SDK + NDK. Produkuje `blgcore.aar` konsumowany przez moduł Kotlin.
Instrukcje w README modułu.

### Warstwa Kotlin/Android (plan)

- **`MainActivity`** — formularz: URL serwera, token (pole hasłowe), nazwa
  drukarki, IP drukarki, port (domyślnie 9100), interwał pollingu (domyślnie
  15 s). Zapis w Jetpack DataStore. Przycisk Start/Stop usługi. Pokazuje ostatnie
  podsumowanie (z JSON `RunOnce`) i stan „ostatni poll o…".
- **`PrintService`** — foreground service z trwałym powiadomieniem („BLG drukuje
  — nasłuch zadań"); pętla coroutine: co `interval` woła `Agent.RunOnce(...)`,
  parsuje JSON, aktualizuje powiadomienie/stan; okresowo (rzadziej) `ReportState`.
  Foreground zwalnia z Doze przy aktywnym nasłuchu.
- **Uprawnienia**: `INTERNET`, `FOREGROUND_SERVICE` (+ `FOREGROUND_SERVICE_
  DATA_SYNC` na API 34+), `POST_NOTIFICATIONS` (API 33+). Bez lokalizacji (brak
  discovery w MVP).

## Przepływ danych

Identyczny jak desktop, różnice: konfiguracja z UI (nie `config.yaml`), jedna
drukarka, brak capture. Pętla: `RunOnce` → jeśli `authError` → Stop + komunikat;
w innym wypadku aktualizacja statusu i kolejny cykl po `interval`.

## Obsługa błędów

- **Brak sieci / timeout pollingu** → `RunOnce` zwraca `error`; powłoka pokazuje
  „offline — ponawiam", kolejny cykl po interwale (prosty backoff opcjonalnie).
- **Timeout / odmowa druku** (drukarka poza WiFi / zły IP) → zadanie liczone w
  `failed`, `POST …/status {error}` do serwera, komunikat w podsumowaniu.
- **401** → `authError:true`; powłoka zatrzymuje usługę i pokazuje „odtwórz
  token".
- **Nie-ZPL w zadaniu** → `looksLikeZPL` odrzuca, zadanie `error` (spójne z
  bramką serwera F29 i desktopem).
- **Bateria** → interwał konfigurowalny; foreground service; brak WakeLock w MVP
  (użytkownik trzyma telefon podłączony jako „stacja druku”).

## Plan weryfikacji

**W tej sesji (Go, na tym serwerze) — realne uruchomienie:**

1. `pollJobs` parsuje odpowiedź `httptest` serwera (jobs[] → wewnętrzna forma),
   wysyła nagłówek Bearer, mapuje 401 → authError.
2. `printTCP` do lokalnego `net.Listener`-atrapy: odebrane bajty = ZPL z
   trailing newline powtórzony `copies` razy; klamp `copies` (0→1, 2000→1000).
3. `looksLikeZPL` — te same przypadki co desktop (ZPL ok; PostScript/PDF/HTML/
   pusty → odrzucone).
4. `RunOnce` end-to-end na atrapach (httptest + listener): 2 zadania OK + 1 z
   nieosiągalną drukarką → JSON `{"polled":3,"printed":2,"failed":1,...}`, oraz
   3 wywołania `POST …/status` z właściwymi statusami.
5. `ReportState` wysyła `agent_version` + jedną drukarkę.
6. `go vet`, `gofmt`, `go test ./mobilecore/...` zielone.

**Poza tą sesją (osoba z Android Studio) — udokumentowane w planie:**
`gomobile bind` → AAR; złożenie APK; instalacja na telefonie; test e2e:
wygeneruj zadanie w web appce → pojawia się w kolejce → telefon drukuje na
drukarkę w WiFi → status `done` w UI serwera.

## Wersjonowanie i dystrybucja

Osobny artefakt mobilny: własny `versionName`/`versionCode` startujący od
`0.1.0` (moduł Android). Rdzeń Go `mobilecore` wersjonowany razem z repo
(przekazywany do `NewAgent` jako `agentVersion`, widoczny w heartbeat/UI
serwera). Dystrybucja MVP: APK w GitHub Releases (sideload w LAN). Bump wersji
aplikacji BLG za dodanie rdzenia + planu Androida: `0.18.0 → 0.19.0` (nowa
funkcja użytkowa: rdzeń mobilny). Wydanie APK nastąpi w osobnym kroku, gdy build
powstanie na maszynie z SDK.

## Poza zakresem tego spec

Auto-discovery drukarek, publikacja Play, wiele drukarek w UI mobilnym, iOS,
konsolidacja `mobilecore` z desktopem do wspólnego pakietu `core/`.
