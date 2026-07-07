# F39 — Drukarki lokalne (USB/systemowe) przez connector — design

**Data:** 2026-07-07
**Status:** zatwierdzony w brainstormingu (wariant „systemowy podsystem druku")
**Kontekst użytkownika:** Zebra ZD421 na USB przy Macu; serwer BLG na zewnętrznym
hostingu (drukarki nie da się wpiąć w serwer). Toshiba B-EX4D2 na Ethernecie —
obsłuży ją F42 (natywny TPCL). Priorytety użytkownika: (1) druk na ZD421,
(2) łatwy wizard, (3) import `^GF`, (4) TPCL.

## Problem

Connector drukuje wyłącznie po TCP (JetDirect/9100) albo do pliku (`file://`).
Drukarka podłączona kablem USB do komputera użytkownika jest dla BLG
niewidoczna — a to najczęstszy sposób podłączenia drukarki etykiet w małej
firmie. Dodanie drukarki wymaga ręcznej edycji `config.yaml`.

## Rozwiązanie (zasada: zero konfiguracji)

Connector wykrywa systemowe kolejki druku i drukuje na nie przez podsystem
druku OS. Użytkownik podłącza drukarkę do komputera (jednorazowo dodaje ją w
ustawieniach systemu), a BLG widzi ją automatycznie — bez edycji YAML, bez IP.

### Odrzucone warianty

- **Bezpośredni USB (libusb/gousb):** wymaga cgo (psuje macierz cross-kompilacji
  zero-cgo), uprawnienia USB na macOS, kruche per model drukarki.
- **Udostępnienie drukarki w CUPS po sieci:** zero kodu, ale UX nieakceptowalny
  i nie działa dla użytkowników Windows.

## Architektura / przepływ danych

```
[Mac] ZD421 (USB) ← kolejka CUPS ← `lp -d <queue> -o raw` ← blg-connector
                                        │ discovery: `lpstat -e` (ticker 60 s)
                                        ▼
          POST /api/agent/state { printers: [ {name, kind: "local"}, … ] }
                                        ▼
      serwer: device.printers (JSON — bez migracji DB) → dialog druku (UI)
                                        ▼
      job { printer: "<nazwa>" } → connector: dispatch po kind → lp/winspool
```

- Drukarki z `config.yaml` (TCP/plikowe) działają bez zmian; przy konflikcie
  nazw **wygrywa YAML**, wykryty duplikat jest pomijany.
- Job niesie nadal tylko nazwę drukarki — kontrakt kolejki bez zmian.

## Connector (Go)

### Wykrywanie kolejek

- macOS/Linux: parsowanie wyjścia `lpstat -e` (nazwy wszystkich celów CUPS).
- Windows: `EnumPrinters` przez winspool (biblioteka
  `github.com/alexbrainman/printer` — czysty Go/syscall, **bez cgo**).
- Cache w pamięci; odświeżanie przy starcie i co 60 s (własny ticker —
  heartbeat zostaje przy swoich 20 s; stan drukarek raportowany przy
  najbliższym heartbeat po zmianie).
- Brak `lpstat`/CUPS → discovery zwraca pustą listę (jeden log przy starcie,
  bez błędu, bez retry-spamu).

### Druk

Nowy rodzaj drukarki `local` obok istniejących `tcp` i `file`:

- macOS/Linux: `exec.Command("lp", "-d", queue, "-o", "raw", "-n", copies)`
  z payloadem na **stdin**. Bez shella — argumenty przez exec; nazwa kolejki
  walidowana (dozwolone znaki wg CUPS: bez spacji, `/`, `#`). `-o raw` omija
  filtry CUPS; `-n` realizuje kopie natywnie (bez powielania bufora).
- Windows: `printer.Open(name)` → `StartRawDocument` → `Write` → `Close`
  (winspool RAW).
- Timeout na proces `lp` (10 s, jak printTimeout); zabicie procesu po
  przekroczeniu.

### Raportowanie

`ReportState` wysyła listę scaloną: drukarki z YAML (`kind` wg host:
`network`/`file`) + wykryte (`kind: "local"`).

## Serwer + UI

- **Schemat `/api/agent/state`:** wpis drukarki dostaje opcjonalne pole
  `kind: "network" | "file" | "local"`, default `network` — stare connectory
  nie wysyłają pola i nic się nie psuje. `device.printers` to JSON —
  **bez migracji Alembic**.
- **Dialog druku:** drukarki `local` z badge „z komputera: {nazwa urządzenia}".
  Wybór i wysyłka joba bez zmian (nazwa drukarki).
- **Strona Urządzenia:** lista drukarek urządzenia (w tym wykrytych) ze stanu
  agenta; drukarki lokalne są od razu drukowalne — nie ma kroku „dodaj".
- i18n PL/EN dla nowych tekstów.

## Obsługa błędów

- Niezerowy exit `lp` / błąd winspool → stderr (obcięty do sensownej długości)
  w polu błędu joba — widoczny w UI kolejki jak dzisiejsze błędy TCP.
- Kolejka usunięta z systemu → znika z listy przy następnym odświeżeniu;
  job wysłany na nieistniejącą → czytelny błąd „drukarka niedostępna".
- Discovery nie może wywrócić agenta: błędy parsowania logowane, lista pusta.

## Testy

- Go: fake `lpstat`/`lp` podstawione przez PATH w testach (wzorzec istniejących
  testów connectora); część winspool za interfejsem + build tagi
  (`printer_windows.go` / `printer_unix.go`), mock w testach.
- Backend: test schematu — `kind` przyjęty i odbity w API urządzeń; test
  kompatybilności payloadu bez `kind`.
- E2E ręcznie: Mac + ZD421 (USB, kolejka CUPS) — wydruk etykiety z kolejki BLG.

## Wersja

F39 = nowa funkcja → **v0.22.0** (minor).

---

# Zatwierdzone kierunki kolejnych pod-projektów (backlog)

Kolejność wg priorytetów użytkownika. Każdy dostanie własny spec + plan.

## F40 — Wizard v2: instalator jednoplikowy, tło, wirtualna drukarka

- Serwer generuje **jeden spersonalizowany plik** per OS
  (`Podlacz-BLG.command` / `.bat` / `.sh`) z wtopionym tokenem i configiem;
  skrypt sam wykrywa architekturę (`uname -m` — koniec pytania Apple/Intel),
  pobiera właściwą binarkę z GitHub Releases i instaluje.
- **Wymaganie twarde (od użytkownika):** connector działa **w tle, bez
  otwartego okna terminala** — macOS: LaunchAgent
  (`~/Library/LaunchAgents/uk.attv.blg-connector.plist`, start przy logowaniu,
  restart po padzie); Windows: zadanie Harmonogramu zadań bez okna konsoli;
  Linux: systemd --user. Logi do pliku.
- **Wymaganie twarde: wszystko wstaje po restarcie** — kolejki systemowe
  (wirtualna 9101 i lokalne drukarki) są trwałe z natury; autostart connectora
  załatwia LaunchAgent/Task Scheduler/systemd.
- Wizard prowadzi też przez **instalację wirtualnej drukarki** (kolejka CUPS /
  port Standard TCP/IP na Windows ze sterownikiem ZDesigner) — dziś to tylko
  README.
- Niepodpisane pliki: wizard pokazuje dokładny ekran Gatekeeper/SmartScreen
  ze zrzutem i instrukcją („prawy klik → Otwórz"). Podpisane .pkg/.msi —
  osobny temat w backlogu (wymaga certyfikatów).
- Krok „drukarka po IP/test" przeprojektowany: najpierw lista wykrytych
  drukarek (F39), IP tylko jako opcja zaawansowana.

## F41 — Import `^GF` (bitmapy w ZPL)

- Parser ZPL dekoduje `^GFA` (hex ASCII) **oraz** wariant skompresowany Z64
  (zlib+base64 — tak wysyłają sterowniki, m.in. ZDesigner) → PNG → Asset →
  obiekt obrazka na kanwie we właściwej pozycji i skali.
- Domyka scenariusz „drukuj z dowolnego programu przez ZDesigner na wirtualną
  drukarkę → edytuj wynik w BLG" (dziś bitmapy przepadają — parser zna tylko
  `BC/BE/BQ/BX/FD/FB/GB/GD…`).

## F42 — Natywny TPCL + język per drukarka

- **Decyzja użytkownika:** Toshiba B-EX4D2 ma drukować **natywnym TPCL** —
  bez przełączania drukarki w Z-MODE (emulacja ZPL istnieje, ale odrzucona).
- Generator canvas → TPCL (lustrzany do generatora TSPL z F22).
- Pole `language: "zpl" | "tspl" | "tpcl"` per drukarka przez cały pipeline:
  konfiguracja drukarki, kolejka (serwer renderuje właściwy język), connector
  (walidacja ZPL tylko dla jobów ZPL), dialog druku.
- Bonus: generator TSPL (F22) wpina się w kolejkę tym samym mechanizmem —
  drukarki TSC/B-FV dostają druk z kolejki „za darmo".
- Weryfikacja: wydruk testowy na fizycznej B-EX4D2 (iteracyjnie).
