# UAT — lista testów manualnych przed wdrożeniem na prod (F30)

Testy do wykonania **ręcznie przez właściciela** i potwierdzenia, żebyśmy mogli
podjąć decyzję o wdrożeniu produkcyjnym. Wszystko poniżej zostało już
przetestowane automatycznie lub w środowisku symulowanym — tu chodzi
o potwierdzenie na **realnym sprzęcie i realnych plikach**, których nie da się
zasymulować.

**Jak raportować:** przy każdym teście zaznacz `[x]` i dopisz wynik/uwagi.
Testowana wersja: `v______` (widoczna w `GET /api/health` i CHANGELOG).
Testy oznaczone 🔴 są **blokujące** dla decyzji o prod; 🟡 — ważne, ale nie blokują.

---

## A. Sprzęt — realna drukarka Zebra (nie da się zasymulować)

- [ ] 🔴 **A1. Druk przez kolejkę na fizyczną Zebrę.** Skonfiguruj agenta
  (`connector/README.md`) z prawdziwą drukarką (IP:9100). Edytor → 🖨 Drukuj →
  wybierz urządzenie i drukarkę → Drukuj. *Oczekiwane:* etykieta wychodzi
  z drukarki, wygląda jak na canvasie (pozycje/rozmiary w mm się zgadzają),
  status w oknie przechodzi na „Wydrukowano".
  Wynik: ..................................................
- [ ] 🔴 **A2. Szybka ścieżka na fizyczną Zebrę.** Agent na tym samym
  komputerze co przeglądarka → dialog druku pokazuje „⚡ Ten komputer" →
  Drukuj. *Oczekiwane:* natychmiastowy wydruk, komunikat „Wydrukowano".
  Wynik: ..................................................
- [ ] 🔴 **A3. Kody kreskowe czytelne.** Na wydruku z A1/A2: zeskanuj EAN-13
  i QR czytnikiem/telefonem. *Oczekiwane:* kody skanują się i mają właściwą
  wartość. Sprawdź przy 203 dpi i (jeśli masz taką drukarkę) 300 dpi.
  Wynik: ..................................................
- [ ] 🔴 **A4. Daty na wydruku.** Etykieta z `{{date+14d}}` wydrukowana przez
  konektor. *Oczekiwane:* data = dziś + 14 dni, format DD.MM.YYYY.
  Wynik: ..................................................
- [ ] 🟡 **A5. Kopie.** Druk z liczbą kopii 3. *Oczekiwane:* 3 identyczne etykiety.
  Wynik: ..................................................
- [ ] 🟡 **A6. Drukarka wyłączona.** Wyłącz drukarkę, wyślij zadanie przez
  kolejkę. *Oczekiwane:* status „błąd" z komunikatem o nieosiągalnej drukarce;
  po włączeniu drukarki ponowny wydruk działa.
  Wynik: ..................................................

## B. Windows — wirtualna drukarka (testowane tylko na Linuksie symulacyjnie)

- [ ] 🔴 **B1. Agent jako usługa na Windows.** `blg-connector-windows-amd64.exe`
  z configiem w `C:\ProgramData\blg-connector\config.yaml` (NSSM lub
  Harmonogram zadań). *Oczekiwane:* urządzenie Online po restarcie komputera.
  Wynik: ..................................................
- [ ] 🔴 **B2. Wirtualna drukarka ZDesigner.** Według `connector/README.md`:
  sterownik ZDesigner + port Standard TCP/IP → 127.0.0.1:9101 (RAW, SNMP off).
  Wydrukuj etykietę z dowolnej aplikacji (np. stary program etykiet / Word).
  *Oczekiwane:* wpis w Urządzenia → Inbox w ciągu ~1 min.
  Wynik: ..................................................
- [ ] 🔴 **B3. Przechwycone → edytor.** Inbox → „Otwórz w edytorze" na wpisie
  z B2. *Oczekiwane:* szablon o sensownym rozmiarze etykiety, teksty/kody
  edytowalne (bitmapy ^GF mogą być niewidoczne — to udokumentowane).
  Wynik: ..................................................
- [ ] 🟡 **B4. Przeglądarka na Windows (Chrome i Edge).** Dialog druku
  z agentem lokalnym na Windows — czy pojawia się „⚡ Ten komputer"?
  *Oczekiwane:* tak na Chrome i Edge; na Firefoksie może brakować — zanotuj.
  Wynik: ..................................................

## C. Realne dane produkcyjne

- [ ] 🔴 **C1. Twój prawdziwy arkusz.** Wgraj realny plik CSV/XLSX z produkcji
  (nie testowy) do kreatora serii; zmapuj pola; wygeneruj PDF. *Oczekiwane:*
  wszystkie wiersze, polskie znaki poprawne, żadnych `{{...}}` w wyniku.
  Wynik: ..................................................
- [ ] 🔴 **C2. Realny ZPL z twojego systemu.** Jeśli masz ZPL z innego
  systemu — wklej w Importuj ZPL (auto-DPI). *Oczekiwane:* elementy trafiają
  na canvas we właściwych miejscach; eksport z powrotem drukuje się identycznie.
  Wynik: ..................................................
- [ ] 🟡 **C3. Duża seria.** Batch bliski limitu (~1000 wierszy).
  *Oczekiwane:* PDF gotowy w <30 s, pasek postępu działa.
  Wynik: ..................................................

## D. Codzienna praca w przeglądarce (potwierdzenie na twoim sprzęcie)

- [ ] 🔴 **D1. Pełny przepływ nowego użytkownika.** Admin tworzy konto →
  logowanie hasłem tymczasowym → wymuszona zmiana → nowy szablon → tekst,
  kod kreskowy, `{{date+30d}}` → Pobierz PDF. *Oczekiwane:* zero błędów,
  wszystko po polsku.
  Wynik: ..................................................
- [ ] 🟡 **D2. Telefon/tablet.** Otwórz aplikację na telefonie: zaloguj się,
  obejrzyj listę szablonów, zleć wydruk przez kolejkę (dialog druku).
  *Oczekiwane:* da się użyć; edytor może być niewygodny — zanotuj wrażenia.
  Wynik: ..................................................
- [ ] 🟡 **D3. Dwie osoby naraz.** Dwóch użytkowników edytuje SWOJE szablony
  jednocześnie i generuje serie. *Oczekiwane:* brak wzajemnych zakłóceń.
  Wynik: ..................................................
- [ ] 🟡 **D4. Pomoc i FAQ.** Przeczytaj `/help` (PL i EN) pod kątem
  nieaktualnych treści i screenshotów. *Oczekiwane:* zgodne z aplikacją.
  Wynik: ..................................................

## E. Odporność (przed prod warto znać zachowanie)

- [ ] 🟡 **E1. Restart serwera w trakcie pracy.** `docker compose restart`
  podczas otwartego edytora. *Oczekiwane:* po odświeżeniu sesja albo działa,
  albo czysto prosi o ponowne logowanie; autosave nie zgubił zmian sprzed restartu.
  Wynik: ..................................................
- [ ] 🟡 **E2. Agent traci sieć.** Odłącz komputer z agentem od sieci na
  2 min podczas wysłanego zadania. *Oczekiwane:* zadanie czeka w kolejce,
  po powrocie sieci drukuje się bez duplikatów.
  Wynik: ..................................................
- [ ] 🔴 **E3. Miejsce na dysku serwera.** Sprawdź `df -h` na serwerze przed
  wdrożeniem — dziś dysk bywa >90%. *Oczekiwane:* ustalony plan (czyszczenie /
  powiększenie), bo pełny dysk wyłącza zapisy (patrz incydent z 4.07.2026).
  Wynik: ..................................................

## F. Foldery i Biblioteka (v0.11.0)

- [ ] 🟡 **F1. Foldery.** Utwórz 2 foldery, przenieś szablony (⚙ na kafelku),
  przefiltruj, zmień nazwę folderu, usuń folder. *Oczekiwane:* szablony z
  usuniętego folderu wracają do „Bez folderu".
  Wynik: ..................................................
- [ ] 🟡 **F2. Udostępnienie i klon.** Udostępnij szablon (⚙ → Biblioteka);
  drugi użytkownik klika „Użyj" w Bibliotece. *Oczekiwane:* dostaje własną
  edytowalną kopię (z obrazkami!), oryginał nietknięty.
  Wynik: ..................................................
- [ ] 🟡 **F3. Startery.** Użyj 2–3 gotowych projektów, wydrukuj/wygeneruj PDF.
  *Oczekiwane:* sensowne etykiety bez poprawek technicznych.
  Wynik: ..................................................

## G. Tabele i polskie znaki (v0.13.0)

- [ ] 🟡 **G1. Tabela na realnej drukarce.** Dodaj tabelę cecha–wartość z `{{...}}`,
  wygeneruj serię z arkusza, wydrukuj. *Oczekiwane:* siatka i teksty jak na canvasie,
  kolumny podmienione z arkusza.
  Wynik: ..................................................
- [ ] 🔴 **G2. Polskie znaki w druku.** Wydrukuj etykietę z „zażółć gęślą jaźń ŻŁĆĘĄŹŃŚ"
  na realnej drukarce (PDF i przez konektor). *Oczekiwane:* wszystkie znaki poprawne,
  zero kwadracików.
  Wynik: ..................................................

---

## Decyzja

Wszystkie 🔴 zaliczone: ☐ TAK ☐ NIE
Decyzja o wdrożeniu na prod: ☐ GO ☐ NO-GO — data: .......... podpis: ..........
