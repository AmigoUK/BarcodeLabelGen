# F38 — Kreator „Podłącz drukarkę" (wariant A)

Data: 2026-07-05 · Status: **spec zaakceptowany** · Priorytet: P1

## Cel

Prosty, w pełni prowadzony kreator w aplikacji, który przeprowadza osobę
**nietechniczną** od zera do działającego połączenia z konektorem na jej
lokalnym komputerze — **bez ręcznej edycji plików, bez znajomości terminala,
bez zgadywania która binarka**. Powstał wprost z realnych bólów zaobserwowanych
przy ręcznym uruchamianiu konektora na Macu (zła binarka/HTML, łamiący się URL,
blokada Gatekeepera, heredoc, cudzysłowy w `config.yaml`, brak informacji „czy
zadziałało").

## Kluczowe ustalenia (zaakceptowane)

- **Wariant A**: kreator to niemal wyłącznie **frontend** — reużywa istniejących
  endpointów. `config.yaml` budowany **w przeglądarce** (bez nowego endpointu):
  `server_url` = `window.location.origin` (ten sam adres Tailscale, który
  użytkownik ma w pasku), `token` z odpowiedzi `POST /api/devices` (pokazywany
  raz), drukarka z kroku 6.
- **Tryb testowy domyślnie**: pierwsze połączenie nie wymaga drukarki — config
  zawiera „drukarkę do pliku" (`file://`), tak jak zadziałało w teście na Macu.
- **Drukarka to osobny krok po sukcesie** (krok 6), nie warunek połączenia.
- **Token nigdy nie trafia do URL-a** — tylko do pobieranego pliku (zgodnie z
  zasadami prywatności).

## Zakres

**W zakresie (MVP):**

1. Komponent `ConnectPrinterWizard` — modal wielokrokowy (ekrany 1–5 + osobny
   krok 6 „drukarka"), makieta zaakceptowana:
   `scratchpad/connect-wizard-mockup.html`.
2. Czysta logika pomocnicza `lib/connectorSetup.ts`: budowa `config.yaml`, wybór
   binarki per system/architektura, budowa komendy startu per system.
3. Wykrywanie połączenia na żywo (odpytywanie statusu urządzenia) + ekran błędu
   z podpowiedziami.
4. Wejście do kreatora: przycisk „Podłącz drukarkę" na stronie **Urządzenia**
   (główna ścieżka) oraz zachęta w oknie **Drukuj**, gdy nie ma żadnego
   urządzenia online.
5. i18n PL/EN.
6. **Proces wydania**: dołączać wszystkie 6 binarek konektora do każdego wydania
   (żeby linki `releases/latest/download/<asset>` zawsze działały); dograć
   brakujące do bieżącego wydania.

**Poza zakresem (świadomie):**

- **Natywny instalator do dwukrotnego kliknięcia** (macOS `.app/.pkg`, Windows
  `.exe`) — osobny większy projekt (pakowanie, notaryzacja); to naturalne
  rozwinięcie „natywnej usługi + tray".
- **Zdalny instalator „jedną linią"** — token w URL / skrypt per system, ryzyko
  i utrzymanie; odrzucony w brainstormingu.
- **Autostart** (launchd/systemd/usługa Windows) — możliwy przyszły krok
  kreatora; teraz użytkownik trzyma otwarte okno.
- **Konfiguracja przechwytywania (wirtualna drukarka/CUPS)** — osobny przepływ.
- **Gwarancja trybu testowego na Windows** — ścieżka `file://` na Windows
  niezweryfikowana (patrz Ryzyka); realny druk po IP działa cross-platform.

## Architektura

Frontend-heavy, **zero zmian w backendzie i konektorze**. Reużywa:
`POST /api/devices` (`useCreateDevice` → zwraca `{device, token}`), `GET
/api/devices` (`useDevices` → status online per urządzenie).

```
ConnectPrinterWizard (modal)
  ├─ krok 1  wybór systemu (auto-detekcja) ────────────┐
  ├─ krok 2  nazwa → POST /api/devices → token (w RAM) │  lib/connectorSetup.ts
  ├─ krok 3  Pobierz program (link) + Pobierz config   │   (czysta logika:
  │            (Blob z config.yaml zbudowanym w JS)  ───┤    build/pick/command)
  ├─ krok 4  komenda startu do skopiowania ────────────┘
  ├─ krok 5  odpytywanie GET /api/devices → online? ✅ / błąd
  └─ krok 6  (osobno) drukarka: IP albo tryb testowy → nowy config do pobrania
```

### `lib/connectorSetup.ts` (czysta, testowalna logika)

- `type OS = "mac-apple" | "mac-intel" | "windows" | "linux-amd64" | "linux-arm64" | "linux-arm"`
- `detectOS(): { os: OS | null, macNeedsChipChoice: boolean }` — z `navigator`.
  macOS: wykrywamy „Mac", ale **Apple Silicon vs Intel nie jest wiarygodnie
  wykrywalny w przeglądarce** (Apple Silicon podaje się jako Intel) → dla Maca
  kreator dopytuje o procesor (podpowiedź „menu Apple → O tym Macu"). Windows →
  `windows`. Linux → `linux-amd64` (z opcją arm64/arm dla Raspberry Pi).
- `assetFor(os: OS): string` — nazwa pliku wydania, np. `mac-intel` →
  `blg-connector-macos-intel`, `windows` → `blg-connector-windows-amd64.exe`,
  `linux-arm64` → `blg-connector-linux-arm64`.
- `downloadUrlFor(os: OS): string` —
  `https://github.com/AmigoUK/BarcodeLabelGen/releases/latest/download/<asset>`.
- `buildConfigYaml({ serverUrl, token, printer }): string` — składa `config.yaml`
  (patrz niżej). `printer` = `{ mode: "test" }` (domyślnie) lub
  `{ mode: "ip", ip: string, port?: number }`.
- `runCommandFor(os: OS, asset: string): string` — komenda startu:
  - mac: `cd ~/Downloads && xattr -d com.apple.quarantine <asset> 2>/dev/null; chmod +x <asset> && ./<asset> -config config.yaml`
  - linux: `cd ~/Downloads && chmod +x <asset> && ./<asset> -config config.yaml`
  - windows (PowerShell): `cd $HOME\Downloads; .\<asset> -config config.yaml`

### Postać generowanego `config.yaml`

Tryb testowy (domyślny), ścieżka wg systemu (mac/linux → `/tmp/...`,
windows → `C:/...`):

```yaml
server_url: "https://<origin>"
token: "blg_..."
poll_interval_seconds: 5
heartbeat_interval_seconds: 20
listen: "127.0.0.1:9110"
printers:
  - name: "test-plik"
    host: "file:///tmp/blg-wydruki"   # windows: file://C:/blg-wydruki
    port: 9100
```

Tryb „prawdziwa drukarka" (krok 6): `name: "drukarka"`, `host: "<IP>"`,
`port: 9100`. Konektor wymaga ≥1 drukarki — dlatego tryb testowy zawsze zapewnia
poprawny wpis, a samo połączenie (heartbeat → online) nie zależy od tego, czy
drukarka jest osiągalna.

## Przepływ ekranów (zaakceptowana makieta)

1. **Wybór systemu** — auto-detekcja + potwierdzenie; dla Maca podwybór
   Apple/Intel z podpowiedzią.
2. **Nazwa komputera** → `POST /api/devices` → token trzymany w stanie kreatora
   (tylko w pamięci przeglądarki, nie zapisywany).
3. **Pobierz 2 pliki** — *Pobierz program* (link do binarki) + *Pobierz
   ustawienia* (`Blob` z `config.yaml`). Notka o prywatności klucza.
4. **Uruchom** — jedna komenda do skopiowania (na macOS `xattr`/`chmod` ukryte
   w środku), przycisk „Kopiuj", przypomnienie „zostaw okno otwarte".
5. **Sprawdzam połączenie** — spinner; co ~3 s `GET /api/devices`; gdy **to**
   urządzenie wejdzie online → **„Połączono ✅"**. Po ~75 s bez skutku → ekran
   błędu (3 podpowiedzi: okno terminala otwarte? Tailscale połączony? komenda bez
   czerwonego błędu?) + „Sprawdzaj dalej" / „Zacznij od nowa".
6. **Drukarka (osobno, po sukcesie)** — pole IP albo „na razie testowo"; wybór
   generuje zaktualizowany `config.yaml` do ponownego pobrania i krótką instrukcję
   „podmień plik i uruchom ponownie".

## Obsługa błędów

- Nazwa zajęta → komunikat z `device_name_taken` (jak obecny modal).
- Brak połączenia po timeout → ekran błędu z podpowiedziami; „Zacznij od nowa"
  tworzy nowe urządzenie (świeży token) i wraca do kroku 3.
- Utrata sesji/401 przy odpytywaniu → „Zaloguj się ponownie".
- Kopiowanie do schowka niedostępne → pokaż komendę do ręcznego zaznaczenia.

## Plan weryfikacji

**W tej sesji (weryfikowalne):**

1. `lib/connectorSetup.ts` — sprawdzenie logiki przez `npm run typecheck` +
   `lint`; ręczne wywołanie funkcji budujących (config/asset/komenda) i
   porównanie wyników z oczekiwanymi (mac/win/linux).
2. **Realny test rdzenia**: przejść kreator na żywej instancji (headless
   Chromium z wstrzykniętą sesją), utworzyć urządzenie, pobrać wygenerowany
   `config.yaml`, i **uruchomić nim prawdziwy konektor na serwerze** (serwer gra
   rolę „komputera użytkownika") → potwierdzić, że kreator przełącza się na
   „Połączono" (to samo, co ręcznie udało się dziś na Macu).
3. `npm run typecheck` + `lint` zielone.

**Poza tą sesją (użytkownik):** pobranie i uruchomienie na fizycznym
Macu/Windows/Raspberry Pi.

## Ryzyka

- **Detekcja Apple vs Intel** niepewna w przeglądarce → rozwiązane podwyborem dla
  Maca (nie zgadujemy).
- **`releases/latest/download`** działa tylko, gdy najnowsze wydanie ma daną
  binarkę → wymóg „dołączać 6 binarek do każdego wydania" + dograć brakujące do
  bieżącego (część implementacji). Alternatywa na przyszłość: mały endpoint
  `GET /api/connector/downloads` zwracający mapę linków.
- **Tryb testowy na Windows** (`file://C:/...`) niezweryfikowany — połączenie i
  tak zadziała (config się ładuje), niepewny tylko sam zapis pliku; oznaczone.

## Wersjonowanie

Nowa funkcja użytkowa → **minor**: app `0.20.1 → 0.21.0` (spięte trzy źródła
wersji, `test_version_sync.py` pilnuje). CHANGELOG `[0.21.0]`, tag, release
(z kompletem 6 binarek konektora). PROJECT.md: nowa pozycja **F38** oznaczona
jako zrealizowana.

## Poza zakresem tego spec

Natywny instalator, autostart jako usługa, przechwytywanie/CUPS z poziomu
kreatora, backendowy endpoint linków (na przyszłość), gwarancja trybu testowego
na Windows.
