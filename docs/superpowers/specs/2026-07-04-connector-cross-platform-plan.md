# Plan: konektor wieloplatformowy (Windows / macOS / Linux / Android)

Data: 2026-07-04 · Status: **plan** (na prośbę „zaplanuj konektor dla mac, linux
i android") — nie implementacja. Rozbicie na realne fazy z priorytetami.

## Punkt wyjścia (fakty, nie założenia)

Agent `blg-connector` (`connector/`) to **czyste Go, zero cgo**. Zweryfikowano
2026-07-04: kompiluje się bez żadnej zmiany kodu na **darwin/amd64, darwin/arm64,
linux/amd64, linux/arm64, linux/arm, android/arm64** (`GOOS/GOARCH`, ~6 MB każda).
Jedyny kod zależny od systemu to domyślna ścieżka `config.yaml` (Windows vs Unix,
`main.go:25`).

Rdzeń jest już przenośny: polling kolejki (HTTPS), druk **RAW TCP 9100**
(JetDirect — identyczny na każdym OS), lokalne API `127.0.0.1:9110`, nasłuch
przechwytywania (TCP). TCP nie zależy od platformy — **druk działa wszędzie tak
samo**.

## Kluczowe rozróżnienie: desktop ≠ Android

- **Desktop (Windows/macOS/Linux)** — ten sam model: proces w tle,
  lokalne API dla przeglądarki, druk po TCP, opcjonalna wirtualna drukarka.
  Rozszerzenie jest **trywialne**.
- **Android** — inny model wykonania. Binarka Go się kompiluje (ELF), ale
  niezrootowany Android nie uruchamia usług w tle jak desktop. Realny produkt =
  **osobna aplikacja mobilna** (Kotlin, foreground service) pollująca kolejkę i
  drukująca po TCP 9100 do drukarki w tej samej sieci WiFi. Fast-path localhost i
  wirtualna drukarka **nie mają sensu** na Androidzie. To osobny, większy projekt.

## Fazy

### F34 — Konektor desktop: macOS + Linux (P1, mały)
Zakres: binarki dla macOS (Intel + Apple Silicon) i Linux (amd64/arm64/arm w tym
Raspberry Pi) w każdym wydaniu; domyślna ścieżka configu dla macOS
(`~/Library/Application Support/blg-connector/config.yaml`); instrukcje
uruchomienia jako usługa: **launchd** (macOS) i **systemd** (Linux — już w
README). Druk i lokalne API bez zmian. Ryzyko: minimalne (już się kompiluje).
Efekt: „pełny konektor" na trzech desktopach.

### F35 — Wirtualna drukarka na macOS/Linux (P2, średni)
Odpowiednik windowsowego przechwytywania (ZDesigner → TCP 9101). Na Unix
naturalny mechanizm to **CUPS z surowym backendem** kierującym na
`socket://127.0.0.1:9101` (agent już nasłuchuje) albo drukarka „raw queue".
Do zaprojektowania: instrukcja konfiguracji CUPS, ewentualnie skrypt
instalacyjny. Sam agent bez zmian — nasłuch JetDirect już działa cross-platform.

### F36 — Konektor Android (P2/P3, duży — osobny projekt)
Aplikacja mobilna: łączy się do serwera tokenem urządzenia, pollowanie kolejki,
druk ZPL po TCP 9100 do drukarki w WiFi. Bez fast-path/wirtualnej drukarki.
Dwie drogi realizacji do rozważenia w osobnym brainstormingu:
1. **Natywna (Kotlin)** — foreground service + prosty klient HTTP/TCP; najlepsza
   integracja z systemem, sklep Google Play, powiadomienia. Najwięcej pracy.
2. **Go + gomobile** — reużycie logiki `client.go`/`printer.go` jako biblioteki
   AAR + cienka warstwa Android (Service). Mniej duplikacji, ale gomobile bywa
   kłopotliwy w utrzymaniu.
Wymaga własnej sesji brainstormingu (model uruchomienia, dystrybucja, discovery
drukarek w sieci). **Nie** rozszerzenie istniejącego agenta — nowy artefakt.

## Zależności / kolejność

F34 najpierw (tanie, natychmiastowa wartość: Mac/Linux/Pi). F35 i F36 niezależne;
F36 to osobny projekt z własnym cyklem spec→plan→impl.

## Poza zakresem tego planu

Toshiba/TSPL (F22 to osobna pozycja), iOS (analogiczny do Androida, gdy zajdzie
potrzeba), auto-discovery drukarek (mDNS/SNMP) — nice-to-have niezależny od OS.
