# BarcodeLabelGen — konektor Android (F36)

Aplikacja mobilna, która działa jak `blg-connector`, ale na telefonie: pobiera
zadania z kolejki serwera i drukuje ZPL po RAW TCP 9100 do drukarki w tej samej
sieci WiFi. Bez fast-path localhost i bez wirtualnej drukarki (nie mają sensu na
Androidzie).

## Architektura

- **Rdzeń Go** `connector/mobilecore/` — cała logika sieć+druk, przetestowana
  (`go test ./connector/mobilecore/...`). Eksportuje pod gomobile:
  - `NewAgent(serverURL, token, agentVersion string) *Agent`
  - `(*Agent) RunOnce(printerName, printerHost string, printerPort int) (string, error)`
    → JSON `{"polled","printed","failed","messages":[],"authError"}`
  - `(*Agent) ReportState(printerName, printerHost string, printerPort int) error`
- **AAR** — `gomobile bind` pakuje rdzeń dla Androida.
- **Powłoka Kotlin** — `PrintService` (foreground) woła `RunOnce` w pętli;
  `MainActivity` zbiera konfigurację i pokazuje status.

> **Status:** rdzeń Go jest zweryfikowany. Powłoka Kotlin i build AAR **nie były
> zbudowane ani uruchomione** przez autora — poniższe to instrukcje i scaffold do
> zbudowania oraz przetestowania na urządzeniu.

## Budowa AAR (maszyna z Android SDK + NDK)

```
go install golang.org/x/mobile/cmd/gomobile@latest
gomobile init
cd connector
gomobile bind -target=android -androidapi 21 -o blgcore.aar ./mobilecore
```

Skopiuj `blgcore.aar` do `app/libs/` modułu Android i dodaj w `build.gradle`:
`implementation files('libs/blgcore.aar')`. Pakiet Javy: `mobilecore`.

## Uprawnienia (`AndroidManifest.xml`)

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

## Scaffold Kotlin (do zbudowania i weryfikacji na urządzeniu)

Konfiguracja (URL serwera, token, nazwa drukarki, IP, port=9100, interwał=15 s)
trzymana w Jetpack DataStore i czytana przez usługę.

```kotlin
// PrintService.kt — foreground service z pętlą poll-and-print.
import mobilecore.Agent
import mobilecore.Mobilecore  // gomobile: Mobilecore.newAgent(...)

class PrintService : Service() {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(1, buildNotification("Nasłuch zadań…"))
        val cfg = loadConfig() // serverUrl, token, printerName, printerIp, port, intervalSec
        val agent: Agent = Mobilecore.newAgent(cfg.serverUrl, cfg.token, cfg.agentVersion)
        scope.launch {
            while (isActive) {
                try {
                    val summary = agent.runOnce(cfg.printerName, cfg.printerIp, cfg.port.toLong())
                    val s = JSONObject(summary)
                    if (s.getBoolean("authError")) {
                        updateNotification("Token odrzucony — odtwórz na stronie Urządzenia")
                        stopSelf(); break
                    }
                    updateNotification("Wydrukowano ${s.getInt("printed")}, błędy ${s.getInt("failed")}")
                } catch (e: Exception) {
                    updateNotification("Offline — ponawiam…")
                }
                delay(cfg.intervalSec * 1000L)
            }
        }
        return START_STICKY
    }
    // buildNotification / updateNotification / loadConfig / onBind omitted — implement per Android norms.
}
```

`MainActivity` to prosty formularz zapisujący konfigurację do DataStore i
przyciski Start/Stop dla `PrintService`, plus pole na ostatnie podsumowanie.

> **gomobile a typy:** `RunOnce`/`ReportState` przyjmują `int` po stronie Go →
> gomobile mapuje na `long` w Javie/Kotlinie (stąd `cfg.port.toLong()`). Zwrot
> `(string, error)` → Kotlin dostaje `String` i rzuca `Exception` na błąd cyklu.

## Test end-to-end (na urządzeniu)

1. W web appce wygeneruj zadanie druku skierowane na urządzenie/drukarkę.
2. Uruchom usługę w aplikacji (Start).
3. Zadanie powinno wydrukować się na drukarce w WiFi; status `done` widoczny w
   UI serwera (strona Urządzenia).

## Dystrybucja

MVP: APK w GitHub Releases (sideload w LAN). `versionName` startuje od `0.1.0`.
Google Play — opcjonalnie później.
