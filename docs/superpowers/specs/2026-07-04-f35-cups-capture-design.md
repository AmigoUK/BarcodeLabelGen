# F35 — Wirtualna drukarka na macOS/Linux przez CUPS

Data: 2026-07-04 · Status: **spec zaakceptowany** (wariant B) · Priorytet: P2

## Cel

Umożliwić przechwytywanie ZPL z innych aplikacji do **Inboxa** na macOS i Linux,
tak jak na Windows działa to dziś przez sterownik ZDesigner + port Standard
TCP/IP. Efekt: użytkownik na Macu/Linuksie tworzy systemową kolejkę drukarki,
która kieruje surowy ZPL do lokalnego agenta `blg-connector`, a ten wrzuca każde
zadanie do Inboxa (strona *Urządzenia*), skąd otwiera się je w edytorze.

## Punkt wyjścia (fakty, nie założenia)

Zweryfikowano w kodzie 2026-07-04:

- **Agent nie wymaga żadnych zmian.** `Capturer` (`connector/capture.go`) to
  zwykły listener TCP nasłuchujący na `cfg.Capture.Listen`. Jedno połączenie =
  jedno zadanie (`captureIdleTimeout = 30s`, `captureMaxBytes = 2 MB`). Spool
  0700/0600, retry uploadu co 30 s. To już jest cross-platform.
- **Walidacja `looksLikeZPL`** (`connector/zplcheck.go`) odrzuca payloady bez
  `^XA`…`^XZ` oraz rozpoznane formaty (HTML/PDF/PostScript/PCL/JSON) z czytelnym
  komunikatem. Dlatego zwykła aplikacja drukująca PostScript przez raw queue
  dostanie zrozumiały błąd, a nie śmieci w Inboxie.

Wniosek: **F35 to konfiguracja CUPS + skrypt-pomocnik + dokumentacja.** Zero
zmian w kodzie Go.

## Zakres (wariant B — zaakceptowany)

**W zakresie:**

1. `connector/install-capture-cups.sh` — idempotentny skrypt tworzący raw queue
   w CUPS kierującą na agenta.
2. Rozbudowa sekcji „Wirtualna drukarka" w `connector/README.md` o ścieżkę
   macOS/Linux (CUPS), z jawną granicą możliwości.
3. Aktualizacja `docs/PROJECT.md` (F35 → zrealizowane) i CHANGELOG.

**Poza zakresem (świadomie):**

- **Sterownik Zebra/CUPS dla zwykłych aplikacji** (Word, przeglądarka → ZPL).
  Wymaga proprietarnego sterownika Zebry pod Linux/macOS; kruche i niemożliwe do
  rzetelnej weryfikacji bez fizycznej maszyny i drukarki. Udokumentowane jako
  „zaawansowane / na później". Realny użytkownik F35 to aplikacja **już
  emitująca ZPL** (POS, systemy etykietujące, skrypty, sterownik ZDesigner na
  innej maszynie).
- Zmiany w kodzie agenta, serwera i UI Inboxa (Inbox już istnieje z F27).

## Kluczowe rozróżnienie (granica możliwości)

| | Windows (dziś) | macOS/Linux (F35) |
|---|---|---|
| Kto generuje ZPL | sterownik ZDesigner | **aplikacja źródłowa** (musi już emitować ZPL) |
| Transport do agenta | port Standard TCP/IP (RAW) | backend CUPS `socket://` (raw queue) |
| Zwykłe aplikacje (Word…) | działają (sterownik) | **nie** (potrzebny sterownik Zebry — poza zakresem) |

Na Unix „raw queue" oznacza: CUPS przekazuje bajty zadania **bez filtra** do
`socket://127.0.0.1:9101`. Jeśli aplikacja wysyła ZPL — dociera ZPL. Jeśli
wysyła PostScript — agent go odrzuci.

## Architektura i przepływ danych

Bez zmian w agencie. Nowy jest tylko sposób konfiguracji systemowej kolejki:

```
aplikacja  ──lp / dialog druku──▶  CUPS raw queue
                                    (BarcodeLabelGen-Capture)
                                         │  backend socket://127.0.0.1:9101
                                         ▼
                              blg-connector  ── Capturer (TCP :9101)
                                         │  spool 0700 → upload (token urządzenia)
                                         ▼
                              serwer BLG  ── Inbox (strona Urządzenia)
                                         ▼
                                     edytor (^XA parse → szablon)
```

Jedno połączenie TCP = jedno zadanie: backend `socket://` CUPS otwiera nowe
połączenie na zadanie i zamyka je po wysłaniu — dokładnie ten kontrakt, którego
oczekuje `Capturer` (jak windowsowy port monitor).

## Komponent: `connector/install-capture-cups.sh`

**Cel:** jedna komenda zamiast ręcznego `lpadmin`. Wspólny dla Linux i macOS
(oba mają CUPS + `lpadmin`).

**Parametry (zmienne środowiskowe z domyślnymi):**

- `QUEUE` — nazwa kolejki, domyślnie `BarcodeLabelGen-Capture`.
- `TARGET` — cel agenta, domyślnie `127.0.0.1:9101` (musi zgadzać się z
  `capture.listen` w `config.yaml` agenta).

**Kroki:**

1. Sprawdź obecność `lpadmin` (część CUPS). Brak → komunikat z instrukcją
   instalacji (`apt install cups` / CUPS jest wbudowany w macOS) i wyjście ≠ 0.
2. Utwórz/zaktualizuj raw queue:
   `lpadmin -p "$QUEUE" -E -v "socket://$TARGET" -m raw`
   (`-E` włącza i akceptuje zadania; `-m raw` = brak filtra/sterownika).
   Idempotentne: ponowne uruchomienie nadpisuje konfigurację tej samej kolejki.
3. Wypisz jak używać: `lp -d "$QUEUE" etykieta.zpl` oraz jak usunąć:
   `lpadmin -x "$QUEUE"`.

**Świadome decyzje:**

- **Bez `sudo` w środku.** Na wielu systemach `lpadmin` wymaga uprawnień
  (grupa `lpadmin`/`_lpadmin` lub root). Skrypt nie eskaluje sam — jeśli
  `lpadmin` zwróci błąd uprawnień, wypisujemy podpowiedź „uruchom przez sudo lub
  dodaj się do grupy lpadmin". Nie chcemy cicho odpalać sudo.
- **`set -euo pipefail`**, komunikaty na STDERR, kod wyjścia ≠ 0 przy błędzie —
  spójne z `build-all.sh`.
- **Brak twardej zależności od uruchomionego agenta.** Kolejkę można utworzyć
  zanim agent wstanie; zadania po prostu nie połączą się, dopóki agent nie
  nasłuchuje (CUPS pokaże „waiting for printer"). To akceptowalne i
  udokumentowane.

## Dokumentacja (`connector/README.md`)

Sekcję „Wirtualna drukarka (przechwytywanie ZPL…)" rozbić na dwie ścieżki:

- **Windows** — istniejąca treść (ZDesigner + Standard TCP/IP port).
- **macOS / Linux (CUPS)** — nowa: wymagany wpis `capture` w `config.yaml`
  (nasłuch na `127.0.0.1:9101`); jedna komenda `./install-capture-cups.sh` albo
  równoważne `lpadmin` ręcznie; jak drukować (`lp -d …`); **jawna granica**:
  działa dla aplikacji emitujących ZPL, zwykłe aplikacje wymagają sterownika
  Zebry (poza zakresem); uwaga o macOS (nowszy CUPS Apple bywa restrykcyjny
  wobec raw queues — oznaczone jako niezweryfikowane na fizycznym Macu).

Ograniczenia przechwytywania (brak `^GFB`, passthrough bitmap, retry spoola)
zostają wspólne dla obu ścieżek.

## Obsługa błędów

- Brak `lpadmin` → jasny komunikat + instrukcja instalacji CUPS, exit ≠ 0.
- Błąd uprawnień `lpadmin` → podpowiedź o sudo/grupie lpadmin.
- Aplikacja wysyła nie-ZPL → agent odrzuca (`looksLikeZPL`), zadanie nie trafia
  do Inboxa; to celowe. Udokumentowane.
- Agent nie nasłuchuje → CUPS trzyma zadanie („waiting for printer"), wznawia po
  starcie agenta. Udokumentowane.

## Plan weryfikacji (runtime, na tym serwerze — Linux)

1. Zapewnić CUPS lokalnie (zainstalować `cups`/`cups-client` jeśli brak; w razie
   potrzeby uruchomić `cupsd` w tle) — środowisko testowe, nie produkcja.
2. Uruchomić `blg-connector` z minimalnym `config.yaml` zawierającym sekcję
   `capture` nasłuchującą np. na `127.0.0.1:9101` (serwer/token mogą być
   atrapą — testujemy tylko ścieżkę capture → spool).
3. Odpalić `install-capture-cups.sh` → potwierdzić utworzenie raw queue
   (`lpstat -v`, `lpstat -p`).
4. `lp -d BarcodeLabelGen-Capture` z testowym `^XA…^XZ` → potwierdzić w logu
   agenta „virtual printer… job captured" i plik w spoolu (upload do atrapy
   serwera może się nie udać — to OK, sprawdzamy że **capture** działa).
5. Test negatywny: `lp -d …` z plikiem nie-ZPL (np. PostScript) → potwierdzić
   odrzucenie przez agenta.
6. Idempotencja: uruchomić skrypt drugi raz → brak błędu, kolejka bez duplikatu.

macOS: **niezweryfikowane** (brak fizycznej maszyny) — oznaczone w README.

## Wersjonowanie

Nowa funkcja użytkowa → **minor bump**. Aplikacja `0.17.0 → 0.18.0`. Konektor
`0.4.0 → 0.5.0` (nowe narzędzie w pakiecie konektora, choć bez zmian w binarce).
CHANGELOG `[0.18.0]`, tag `v0.18.0`, GitHub release (binarki bez zmian względem
v0.17.0 — dołączyć te same 6 z `build-all.sh` dla spójności Assets).

## Poza zakresem tego spec

Sterownik Zebra/CUPS dla zwykłych aplikacji (przyszły F, jeśli zajdzie potrzeba),
auto-discovery, natywny instalator .pkg/.deb kolejki, iOS/Android (F36).
