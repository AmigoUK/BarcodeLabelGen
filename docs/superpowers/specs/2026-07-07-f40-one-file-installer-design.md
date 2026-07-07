# F40 — Wizard v2: instalator jednoplikowy, praca w tle, wirtualna drukarka — design

**Data:** 2026-07-07
**Status:** do zatwierdzenia (kierunek zatwierdzony w specu F39)
**Twarde wymagania użytkownika:** (1) JEDEN plik do pobrania zamiast binarki +
config.yaml; (2) connector działa **w tle, bez otwartego okna terminala**,
(3) **wszystko wstaje po restarcie**; (4) wizard prowadzi też przez instalację
wirtualnej drukarki; (5) instrukcje nie mogą być mylące.

## Problem

Wizard F38 wymaga: pobrania dwóch plików (binarka + config.yaml), otwarcia
terminala, wklejenia komendy (cd/chmod/xattr), zostawienia otwartego okna,
a po restarcie — ręcznego ponownego uruchomienia. Instalacja wirtualnej
drukarki istnieje tylko w README. Dla nietechnicznego użytkownika to za dużo.

## Rozwiązanie: spersonalizowany instalator generowany w przeglądarce

**Frontend-only** (jak F38): wizard, mając token świeżo utworzonego urządzenia
w pamięci, składa treść instalatora w JS i pobiera ją jako jeden plik przez
blob. Token nigdy nie trafia do URL-a ani do backendu ponad to, co dziś.
Zero nowych endpointów.

Jeden plik per OS:

| OS | Plik | Autostart | Uwaga bezpieczeństwa przy uruchomieniu |
|---|---|---|---|
| macOS | `Podlacz-BLG.command` | LaunchAgent (`~/Library/LaunchAgents/uk.attv.blg-connector.plist`, `RunAtLoad` + `KeepAlive`) | Gatekeeper: „prawy klik → Otwórz" (wizard pokazuje dokładnie ten ekran) |
| Windows | `Podlacz-BLG.bat` | Harmonogram zadań (`schtasks /create … /sc onlogon`), start przez `powershell -WindowStyle Hidden` | SmartScreen/MOTW: „Więcej informacji → Uruchom mimo to" |
| Linux | `podlacz-blg.sh` | `systemd --user` unit (`~/.config/systemd/user/blg-connector.service`, `enable --now`) | `chmod +x` robi instrukcja `bash podlacz-blg.sh` (bez chmod) |

### Co robi instalator (wspólny szkielet)

1. **Wykrywa architekturę sam** (`uname -m` / `PROCESSOR_ARCHITECTURE`) —
   znika pytanie Apple/Intel i wybór wariantu Linuksa; wizard pyta tylko o OS
   (z auto-detekcją jak dziś).
2. Tworzy katalog aplikacji: macOS `~/Library/Application Support/blg-connector/`,
   Windows `%LOCALAPPDATA%\blg-connector\`, Linux `~/.local/share/blg-connector/`.
3. Zapisuje **wtopiony config.yaml** (heredoc; wartości escapowane jak w F38
   `buildConfigYaml` — reuse tej samej funkcji).
4. Pobiera właściwą binarkę z
   `https://github.com/AmigoUK/BarcodeLabelGen/releases/latest/download/<asset>`
   (`curl -L`; Windows: wbudowany `curl.exe`, jest w Win10 1803+). Weryfikuje
   sumę z `SHA256SUMS` (pobiera plik sum, `shasum -a 256 -c` / certutil).
5. `chmod +x` + zdjęcie kwarantanny (macOS `xattr -d com.apple.quarantine`).
6. Rejestruje autostart (tabela wyżej) i **uruchamia connector w tle od razu**.
7. Wypisuje krótkie „Gotowe — wróć do przeglądarki" i kończy. Log connectora
   idzie do pliku (`…/blg-connector/connector.log`), nie na ekran.
8. **Idempotencja:** ponowne uruchomienie instalatora zatrzymuje starą
   instancję, nadpisuje binarkę/config i startuje nową (ścieżka aktualizacji
   i „napraw instalację" w jednym).

### Wizard v2 — przepływ (przebudowa ConnectPrinterWizard)

1. **OS** — auto-detekcja, jedno potwierdzenie (bez pytania o chip).
2. **Nazwa komputera** — jak dziś (tworzy urządzenie + token).
3. **Pobierz instalator** — JEDEN przycisk. Pod spodem od razu instrukcja
   uruchomienia właściwa dla OS, z zrzutem ekranu ostrzeżenia
   (Gatekeeper / SmartScreen) i tekstem „to normalne — plik nie jest jeszcze
   podpisany cyfrowo".
4. **Czekam na połączenie** — jak dziś (poll online), timeout z podpowiedziami
   (w tym „otwórz plik connector.log").
5. **Połączono ✅ → Drukarki** — nowy krok korzystający z F39: lista
   **wykrytych drukarek** urządzenia („Zebra_ZD421 — lokalna") z odświeżaniem;
   drukarka po IP jako opcja zaawansowana (składana sekcja): po wpisaniu IP
   wizard generuje **nowy instalator z tą drukarką wpiętą w config** — user
   pobiera go i uruchamia ponownie (idempotencja = to jest oficjalna ścieżka
   zmiany konfiguracji; żadnej ręcznej edycji YAML nigdzie).
6. **(Opcjonalnie) Wirtualna drukarka** — krok „Chcę przechwytywać wydruki
   z innych programów": macOS/Linux — instalator obsługuje flagę
   `--virtual-printer`, wizard pokazuje komendę 1-klik-kopiuj
   (`bash Podlacz-BLG.command --virtual-printer` — dodaje sekcję capture do
   config.yaml, restartuje connector, tworzy kolejkę CUPS przez lpadmin);
   Windows — przewodnik krokowy (ZDesigner + port TCP 9101) z zrzutami,
   bo instalacji sterownika nie da się legalnie zautomatyzować.

### Zmiany w connectorze

Minimalne: **brak zmian w Go** poza ewentualnym drobiazgiem — instalator
używa istniejących flag (`-config`). Sekcję capture dopisuje instalator
(tekstowo), nie connector.

## Odrzucone warianty

- **Podpisane .pkg/.msi** — najlepszy UX, ale wymaga certyfikatów (Apple
  Developer 99 USD/rok + cert EV dla Windows); backlog, architektura się nie
  gryzie (instalator skryptowy zostaje jako fallback).
- **Endpoint backendowy generujący instalator** — niepotrzebny (token i tak
  jest w przeglądarce w chwili kreacji; generacja w JS = mniejsza powierzchnia).
- **Elektron/tray-app** — przerost formy nad treścią.

## Bezpieczeństwo

- Token w treści pliku instalatora — jak dziś w config.yaml (ten sam poziom
  zaufania); plik ląduje w Pobranych użytkownika. Wizard przypomina, żeby
  nie przesyłać pliku dalej.
- Weryfikacja SHA256 pobranej binarki (nowość — dziś jej nie ma).
- Instalator pisze wyłącznie w katalogach użytkownika (bez sudo). `lpadmin`
  może wymagać uprawnień — komunikat jak w install-capture-cups.sh.

## Testy

- Jednostkowe (frontend): generatory treści instalatorów (`installerFor(os,
  config)`) — czyste funkcje string → snapshot testy na komplet OS-ów;
  escapowanie tokenu/nazw (quoting w bash/batch).
- Ręczne E2E: macOS (użytkownik, Mac + ZD421) i Linux (na linuxserv1 —
  systemd --user); Windows — na maszynie użytkownika, gdy dostępna.
- Wizard: typecheck/lint/build + ręczny przegląd i18n PL/EN.

## Wersja

F40 = nowa funkcja → **v0.23.0** (minor).
