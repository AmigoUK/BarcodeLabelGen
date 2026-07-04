# blg-connector

Lokalny agent druku dla BarcodeLabelGen. Odpytuje serwer o zadania ZPL
i wysyła je do drukarek etykiet po RAW TCP 9100 (Zebra / zgodne z JetDirect).
Jeden statyczny plik wykonywalny — Windows, Linux, Raspberry Pi.

## Szybki start

1. W aplikacji: **Urządzenia → Dodaj urządzenie** — skopiuj token (pokazany raz).
2. Utwórz `config.yaml`:

```yaml
server_url: https://twoj-serwer.example:18003
token: blg_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
poll_interval_seconds: 3        # opcjonalne (domyślnie 3)
heartbeat_interval_seconds: 60  # opcjonalne (domyślnie 60)
listen: 127.0.0.1:9110          # opcjonalne — lokalne API dla przeglądarki
printers:
  - name: Zebra-1
    host: 192.168.1.50          # IP drukarki w LAN
    port: 9100                  # opcjonalne (domyślnie 9100)
  - name: Test                  # drukarka symulowana: zapisuje .zpl do katalogu
    host: file:///var/spool/blg
capture:                        # opcjonalne — wirtualna drukarka (przechwytywanie)
  listen: 127.0.0.1:9101        # nasłuch JetDirect; puste/brak = wyłączone
  # spool_dir: <katalog>        # domyślnie katalog cache użytkownika (0700)
```

3. Uruchom:

```
blg-connector -config config.yaml
```

Urządzenie w aplikacji przejdzie na **Online**, pokaże listę drukarek,
a zadania z kolejki (przycisk **Drukuj** w edytorze) trafią na drukarkę.

## Budowanie

Czyste Go (bez cgo), więc jedna komenda buduje na dowolny system:

```
cd connector
go build -trimpath -ldflags="-s -w" -o blg-connector .                          # bieżący OS
GOOS=windows GOARCH=amd64 go build -trimpath -ldflags="-s -w" -o blg-connector-windows-amd64.exe .
GOOS=darwin  GOARCH=amd64 go build -trimpath -ldflags="-s -w" -o blg-connector-macos-intel .
GOOS=darwin  GOARCH=arm64 go build -trimpath -ldflags="-s -w" -o blg-connector-macos-apple .
GOOS=linux   GOARCH=amd64 go build -trimpath -ldflags="-s -w" -o blg-connector-linux-amd64 .
GOOS=linux   GOARCH=arm64 go build -trimpath -ldflags="-s -w" -o blg-connector-linux-arm64 .   # Raspberry Pi 4/5
GOOS=linux   GOARCH=arm   go build -trimpath -ldflags="-s -w" -o blg-connector-linux-arm .     # Raspberry Pi 2/3
```

Albo od razu wszystkie: `./build-all.sh`. Gotowe binarki: sekcja Assets przy
każdym wydaniu na GitHubie (Windows, macOS Intel/Apple Silicon, Linux
amd64/arm64/arm).

## Jako usługa

**Linux (systemd)** — `/etc/systemd/system/blg-connector.service`:

```ini
[Unit]
Description=BarcodeLabelGen print connector
After=network-online.target

[Service]
ExecStart=/usr/local/bin/blg-connector -config /etc/blg-connector/config.yaml
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**macOS (launchd)** — skopiuj binarkę do `/usr/local/bin/blg-connector`, config
do `/Library/Application Support/blg-connector/config.yaml` (domyślna ścieżka),
a plik `/Library/LaunchDaemons/uk.attv.blg-connector.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>uk.attv.blg-connector</string>
  <key>ProgramArguments</key>
  <array><string>/usr/local/bin/blg-connector</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
```

Załaduj: `sudo launchctl load /Library/LaunchDaemons/uk.attv.blg-connector.plist`.
Pierwszy start Apple Silicon może wymagać zdjęcia kwarantanny:
`xattr -d com.apple.quarantine /usr/local/bin/blg-connector`.

**Windows** — najprościej przez [NSSM](https://nssm.cc/) albo Harmonogram zadań
(uruchom przy starcie, `C:\ProgramData\blg-connector\config.yaml` to domyślna
ścieżka konfiguracji, więc wystarczy `blg-connector.exe` bez argumentów).
Natywna usługa Windows + tray: planowane.

> **Druk RAW TCP 9100 działa identycznie na Windows, macOS i Linux** — konfiguracja
> drukarek w `config.yaml` jest ta sama. Wirtualna drukarka (przechwytywanie) ma
> na razie instrukcję tylko dla Windows; odpowiednik przez CUPS na macOS/Linux to
> pozycja backlogu F35.

## Wirtualna drukarka (przechwytywanie ZPL z innych aplikacji)

Z sekcją `capture` agent nasłuchuje jak drukarka sieciowa (protokół
JetDirect/RAW). Każde odebrane zadanie (jedno połączenie = jedno zadanie)
trafia do **Inboxa** w aplikacji (strona *Urządzenia*), skąd otworzysz je
w edytorze jako edytowalny szablon.

**Konfiguracja na Windows (bez pisania sterownika):**

1. Zainstaluj darmowy sterownik **ZDesigner** (ze strony Zebry) — to on
   generuje ZPL.
2. *Ustawienia → Drukarki → Dodaj drukarkę → ręcznie*: nowy port
   **Standard TCP/IP**, adres `127.0.0.1`, port `9101`, protokół **RAW**,
   **wyłącz SNMP**.
3. Jako sterownik wybierz ZDesigner (dowolny model o rozmiarze twoich
   etykiet). Nazwij drukarkę np. „BarcodeLabelGen (przechwytywanie)".
4. Drukuj na nią z dowolnej aplikacji — zadanie pojawi się w Inboxie.

Ograniczenia: przechwycone zadanie musi zawierać `^XA` (nie-ZPL jest
odrzucany); grafika trybu binarnego (`^GFB`) nie jest wspierana — zostaw
w sterowniku domyślny tryb ASCII/hex (`^GFA`); bitmapy przechodzą jako
passthrough (drukują się, ale nie są edytowalne w edytorze). Nieudane
uploady czekają w lokalnym spoolu i są ponawiane co 30 s.

## Lokalne API (szybka ścieżka przeglądarki)

Agent nasłuchuje na `127.0.0.1:9110` (tylko loopback):

- `GET /status` — wersja, drukarki, czas ostatniego pollingu,
- `GET /printers` — skonfigurowane drukarki,
- `POST /print` `{"printer": "Zebra-1", "zpl": "^XA...^XZ", "copies": 1}` — druk
  bez rundy przez serwer.

CORS otwarty (serwer wiąże się wyłącznie z loopbackiem); preflight Chrome
Private Network Access obsłużony (`Access-Control-Allow-Private-Network: true`).

## Bezpieczeństwo

- Token urządzenia (`blg_…`) trzymaj jak hasło — serwer przechowuje tylko jego
  skrót SHA-256; zgubiony token = usuń urządzenie i utwórz nowe.
- Agent nawiązuje wyłącznie połączenia wychodzące (HTTPS do serwera, TCP do
  drukarek w LAN). Nie otwiera żadnego portu poza loopbackiem.
