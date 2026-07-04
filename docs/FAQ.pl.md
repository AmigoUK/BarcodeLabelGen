# BarcodeLabelGen — FAQ

Najczęstsze pytania pogrupowane od najprostszych do zaawansowanych. Brak odpowiedzi tutaj? Zajrzyj do [HELP.pl.md](HELP.pl.md) albo napisz na dev@attv.uk.

---

## Podstawy

### Po co jest ten program?
Robisz w nim szablony etykiet (rozmiar w mm, dowolny tekst, kody kreskowe, obrazy) i potem generujesz **wiele etykiet z jednego szablonu** — każdą z innymi danymi z arkusza lub bazy SQLite.

### Czemu po pierwszym logowaniu kazano mi zmienić hasło?
Administrator dał ci hasło tymczasowe. Pierwsze logowanie zawsze wymusza zmianę na własne (min. 10 znaków). To jednorazowo.

### Gdzie jest "Nowy szablon"?
Lewe menu → **Szablony** → przycisk **Nowy szablon** w prawym górnym rogu listy.

### Czy mogę zmienić rozmiar etykiety po utworzeniu szablonu?
Tak. W edytorze kliknij w toolbarze przycisk **📐 {szerokość}×{wysokość}**, wpisz nowe wymiary w mm albo wybierz preset i kliknij **Zastosuj**. Obiekty zachowują pozycje w mm (nie są przeskalowywane).

### Jak zapisać szablon?
Edytor zapisuje sam (autozapis co kilka sekund — status widać w toolbarze). Możesz też ręcznie **Ctrl/Cmd + S**.

---

## Edytor i obiekty

### Jaka jest różnica między **Tekst** (T) a **Blok tekstu** (¶)?
- **Tekst** — jedna linia, stały rozmiar fontu, nie zawija.
- **Blok tekstu** — wieloliniowy, zawija się w ramce o zadanej szerokości. Dodatkowo można włączyć **Auto-skalowanie**, które dopasowuje font do długości tekstu (potrzebne gdy z bazy przychodzą krótkie i długie nazwy).

### Co znaczy `{{nazwa_kolumny}}` w polu tekstowym?
To **placeholder**. Przy generowaniu serii zostanie podmieniony wartością z odpowiedniej kolumny w arkuszu/bazie. Działa w polu Text **i** w polu *Dane* obiektu Barcode.

### Co znaczy zielony chip pod polem tekstowym?
Zielony chip oznacza **placeholder daty** (np. `{{date+14d}}`) i od razu pokazuje obliczoną wartość. Fioletowe chipy to zwykłe kolumny z arkusza. Szczegóły składni dat: przewodnik, sekcja 7.

### Jak wstawić logo, które jest na każdej etykiecie?
Lewy panel → **🖼 Obraz** → wybierz plik PNG/JPG/SVG. Logo będzie się drukować na każdej etykiecie.

### Jaka jest różnica między **🖼 Obraz** a **🌄 Tło (referencja)**?
- **🖼 Obraz** — zwykły obraz, drukuje się w PDF.
- **🌄 Tło** — pełnowymiarowy obraz, **zablokowany** (nie da się przesunąć) i **NIE drukuje się** w PDF. Używaj gdy etykiety przyszły z drukarni z już nadrukowanym logo i chcesz tylko pozycjonować nowy tekst — tło widzisz w edytorze jako wzorzec, ale finalny PDF zawiera tylko twoje dodatki.

### Jak nie drukować jakiegoś obiektu w PDF?
Zaznacz obiekt → w prawym panelu, na samej górze, odznacz **🖨 Drukuj w PDF**. Obiekt zostanie wyblakły w edytorze (sygnał że jest tylko podglądowy) i renderer go pominie.

### Jak zablokować obiekt żeby się nie przesuwał?
Zaznacz → w prawym panelu zaznacz **🔒 Zablokuj pozycję**. Uchwyty znikną, nie da się przeciągać ani skalować — ale dalej można zaznaczyć i zmieniać font/kolor. Żeby odblokować — odznacz checkbox.

### Jak zmienić kolejność obiektów (co jest na wierzchu)?
Pasek wyrównania nad canvasem, grupa **Warstwa**:
- ⤓ na sam dół, ↓ niżej, ↑ wyżej, ⤒ na sam wierzch.

### Jak rozłożyć równomiernie 5 obiektów w poziomie?
Zaznacz wszystkie 5 (Shift + klik) → pasek wyrównania → przycisk **Rozłóż poziomo** (działa od 3+ obiektów).

### Cofnąłem za dużo. Jak to przywrócić?
**Ctrl/Cmd + Shift + Z** lub **Ctrl/Cmd + Y**.

### Jak szybko zrobić kopię obiektu?
Dwa sposoby:
- **Alt + przeciąganie** — przytrzymaj Alt (Option na Mac) i przeciągnij zaznaczony obiekt. Oryginał zostaje, klon ląduje pod kursorem. Działa też dla multi-select — zachowuje względne pozycje.
- **Ctrl/Cmd + D** — duplikuje w miejscu z przesunięciem +5 mm. Selekcja przeskakuje na klony, więc kolejne Ctrl+D buduje schodek kopii.

Klon dziedziczy wszystkie ustawienia (font, kolor, lock, *Drukuj w PDF*); obrazy współdzielą Asset.

---

## Generowanie serii (CSV / Excel)

### Jakie pliki mogę wgrać?
CSV, XLS, XLSX. Maksymalnie **10 MB** i **1000 wierszy** na plik (limit MVP).

### Pierwszy wiersz arkusza to nagłówki?
Tak, pierwszy wiersz musi zawierać nazwy kolumn — to one stają się dostępne jako `{{nazwa}}` w mapowaniu.

### Mam więcej niż 1000 wierszy. Co zrobić?
Podziel arkusz na partie po max 1000 wierszy i wygeneruj kilka PDF.

### Mapowanie nie znalazło mojej kolumny.
Sprawdź czy nazwa placeholdera (`{{...}}`) odpowiada dokładnie nagłówkowi kolumny — case-sensitive, bez spacji ekstra. Jeśli nazwy są różne (np. placeholder `{{name}}`, kolumna `Product Name`), wybierz mapowanie ręcznie z listy w Kroku 2.

### PDF wyszedł z `{{name}}` w treści zamiast prawdziwą nazwą.
To znaczy że placeholder się nie zmapował. W Kroku 2 (Mapowanie) musisz dla każdego placeholdera wybrać kolumnę.

### Czy mogę odsiać tylko niektóre wiersze?
Tak — Krok 3 (Filtr). Wybierz kolumnę, operator (równe / zawiera / większe niż / itd.) i wartość. Klik **Sprawdź filtr** żeby zobaczyć ile wierszy się załapie.

---

## Placeholdery daty

### Jak wstawić datę przydatności „dziś + 30 dni"?
W polu tekstowym (albo w danych kodu kreskowego) wpisz `{{date+30d}}`. Przy generowaniu PDF/ZPL program podstawi datę o 30 dni późniejszą od dzisiejszej, np. `03.08.2026`.

### Jakie przesunięcia mogę używać?
`d` = dni, `m` = miesiące, `y` = lata, z plusem lub minusem: `{{date+14d}}`, `{{date-7d}}`, `{{date+3m}}`, `{{date+1y}}`. Samo `{{date}}` to dzisiejsza data.

### Jak zmienić format daty?
Dodaj format po dwukropku, z klocków DD/MM/YY/YYYY: `{{date+14d:DD/MM/YY}}` → `18/07/26`, `{{date:YYYY-MM-DD}}` → `2026-07-04`. Bez formatu dostajesz `DD.MM.YYYY`.

### Kiedy dokładnie liczy się data?
W momencie **generowania** (PDF lub ZPL), według daty serwera — nie w momencie pisania szablonu. Zielony chip w edytorze to tylko podgląd na dziś.

### Co jeśli 31 stycznia dodam 1 miesiąc?
Dostaniesz 28 (lub 29) lutego — program nie tworzy nieistniejących dat.

### Mam w arkuszu kolumnę o nazwie `date`. Co wygra?
Dla gołego `{{date}}` wygrywa **kolumna z arkusza** (jak dotychczas). Formy z przesunięciem lub formatem (`{{date+14d}}`, `{{date:YYYY-MM-DD}}`) zawsze liczą się automatycznie.

### Czemu w kreatorze serii pole `{{date}}` nie wymaga mapowania?
Bo bez mapowania program podstawi dzisiejszą datę. Mapujesz tylko jeśli chcesz brać daty z kolumny arkusza.

---

## ZPL / drukarki Zebra

### Co to jest ZPL i po co mi to?
ZPL to język drukarek etykiet (Zebra i zgodne). Jeśli drukujesz na takiej drukarce albo dostajesz gotowe etykiety w ZPL z innego systemu, program potrafi je **importować do edytora** i **eksportować twój projekt jako ZPL**.

### Jak zaimportować etykietę ZPL?
Edytor → toolbar → **⤓ Importuj ZPL** → wklej kod → **Sprawdź** → **Importuj**. Uwaga: import zastępuje obecną zawartość canvasu.

### Nie znam DPI drukarki, z której pochodzi kod.
Zostaw w oknie importu opcję **Wykryj automatycznie** — program porówna wymiary z kodu (`^PW`/`^LL`) z rozmiarem twojej etykiety i dobierze 203 lub 300 dpi.

### Co się dzieje ze zmiennymi typu `{NAZWA}` w pojedynczych klamrach?
Przechodzą nietknięte w obie strony (import i eksport) — to zmienne drukarkowe twojego systemu. Podwójne klamry `{{...}}` to placeholdery tego programu.

### Czym różni się eksport „Szablon (zmienne)" od „Wsad (dataset)"?
- **Szablon** — jeden kod ZPL; placeholdery kolumn zostają w kodzie, daty są od razu obliczone. Do wklejenia we własny system.
- **Wsad** — wybierasz wgrany plik danych i dostajesz jeden `.zpl` z etykietą na każdy wiersz (wszystko podmienione).

### Czy mogę drukować bezpośrednio na drukarkę Zebra z programu?
Jeszcze nie — dziś eksportujesz `.zpl` i wysyłasz go do drukarki własnym narzędziem. Bezpośredni druk przez lokalny konektor jest w planach (backlog F25–F27).

---

## Generowanie serii (SQLite)

### Jak wgrać bazę SQLite?
Krok 1 wizardu Generuj Serię — wybierz plik z rozszerzeniem `.db`, `.sqlite` lub `.sqlite3`. Limit **50 MB**.

### Co zobaczę po wgraniu?
Listę tabel z bazy, posortowanych: najwięcej wierszy na górze. Każda pozycja pokazuje liczbę kolumn i wierszy.

### Czemu pierwszy raz wybrałem tabelę i dostałem `table 'X' returned 0 rows`?
Wybrałeś tabelę bez danych (np. `basket_contents` z 0 wierszy). W tabeli musi być co najmniej 1 wiersz, żeby było co generować. Wybierz inną — sortowanie powinno wypchnąć tabele z danymi na górę listy.

### Jak napisać własne zapytanie SELECT?
Pod listą tabel rozwiń **Pokaż zaawansowane: własne zapytanie SQL** i wpisz np.:
```sql
SELECT sku, UPPER(name) AS name, price FROM products WHERE price > 10
```
Klik **Użyj tego źródła**.

### Jakie zapytania są dozwolone?
Tylko **pojedynczy SELECT** (opcjonalnie poprzedzony `WITH ... AS (...)`). Połączenie jest read-only. Blokowane są: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `ATTACH`, `DETACH`, `PRAGMA`, `VACUUM`, `REINDEX`, transakcje.

### Dostałem `result exceeds 1000-row limit`. Co teraz?
Wynik twojego SELECT ma więcej niż 1000 wierszy (limit MVP). Dodaj `WHERE`, żeby zawęzić, albo `LIMIT 1000` na końcu.

### Czy mogę używać JOIN?
Tak — JOIN jest standardowym SELECT. Przykład:
```sql
SELECT p.sku, p.name, c.category_description
FROM products p JOIN categories c ON p.category_id = c.category_id
```

### Czy zmiany w bazie są zapisywane?
**Nie.** Połączenie jest read-only — żadne polecenie modyfikujące się nie wykona, nawet jeśli przeszłoby walidator.

### Mój plik .db pokazuje "file is not a valid SQLite database".
Plik prawdopodobnie nie jest SQLite (np. ma rozszerzenie `.db` ale to inny format). Sprawdź źródło pliku.

---

## Import / eksport szablonów

### Po co eksportować szablon do pliku?
Trzy główne powody: **backup** (zachowujesz plik przed dużą zmianą), **klonowanie** (eksport + import z nadpisanym rozmiarem to gotowy szablon na inny format), **przenoszenie** (między instancjami / między userami).

### Gdzie jest przycisk eksportu?
- W liście szablonów (kafelek) — ikona **⬇** w prawym dolnym rogu (pojawia się po najechaniu).
- W edytorze toolbar — przycisk **⬇ Eksportuj** obok *Pobierz PDF*.

### Co dokładnie jest w pliku .blg-template.json?
Rozmiar etykiety, każdy obiekt (tekst, kod, prostokąt, linia, obraz) z dokładną pozycją i wszystkimi ustawieniami, oraz **wszystkie obrazki** zakodowane base64 w samym pliku. Plik jest samowystarczalny — nie potrzebujesz nic poza tym jednym JSON-em.

### Czy mogę zaimportować szablon z innej instancji BarcodeLabelGen?
Tak. Format pliku (`$schema: "blg-template/v1"`) jest stabilny. Jeśli docelowa instancja nie ma takiego samego formatu etykiety jak źródłowa, użytkownik zostanie ostrzeżony i program podstawi format „Custom".

### Czy mogę zaimportować tylko część obiektów?
Tak — w drugim kroku okna importu jest **czeklista**. Domyślnie wszystko jest zaznaczone; odznaczasz to, czego nie chcesz. Pominięte obiekty `image` nie tworzą zbędnych obrazków u Ciebie w bibliotece.

### Co się dzieje gdy w pliku jest obrazek, który już mam?
Program sprawdza duplikat po hashu SHA-256 i pyta Cię: **Użyj istniejącego** (FK pokazuje istniejący obrazek, zero duplikatów na dysku) albo **Utwórz nową kopię** (świeży wpis z tą samą zawartością — przydatne gdy chcesz mieć osobną edytowalną kopię).

### Czy mogę zaimportować szablon zmieniając jego rozmiar?
Tak — w drugim kroku są dwa pola **Szerokość/Wysokość**. Zostaw puste żeby zachować oryginał, albo wpisz nowe wartości. Obiekty zachowują swoje pozycje w mm, więc szablon zachowuje układ ale na innym formacie.

### Dostaję "Couldn't read the file"
Plik nie jest poprawnym JSON-em (np. uszkodzony, otwarty w edytorze i zapisany z błędem). Spróbuj ponownie wyeksportować źródłowy szablon.

### Dostaję "sha256 mismatch"
Treść base64 w pliku nie zgadza się z zadeklarowanym hashem — plik został zmodyfikowany ręcznie. Program odrzuca takie pliki świadomie (mogłoby to ukrywać podmieniony obrazek). Re-eksportuj ze źródła.

### Limity?
Plik ≤ 20 MB, szablon ≤ 50 obiektów, ≤ 20 obrazków, każdy obrazek ≤ 5 MB.

## Konta i bezpieczeństwo

### Jak admin dodaje nowego użytkownika?
**Administracja → Użytkownicy → Utwórz konto**. Podaj email, hasło tymczasowe (min. 10 znaków) i rolę. Po utworzeniu hasło wyświetla się **raz** — skopiuj i przekaż użytkownikowi.

### Jakie są role i co mogą robić?
- **Administrator** — wszystko + zarządzanie kontami.
- **Edytor** — tworzy i edytuje własne szablony i dataset'y, generuje PDF.
- **Tylko podgląd** — może oglądać, ale nie zapisuje zmian.

### Zapomniałem hasła.
Poproś admina o reset (Administracja → Użytkownicy → **Resetuj hasło**). Dostaniesz nowe hasło tymczasowe — przy logowaniu program zmusi cię do ustawienia własnego.

### Czemu nie mogę dezaktywować swojego własnego konta?
Bo zostałbyś zablokowany na zewnątrz aplikacji bez możliwości naprawy. Drugiego administratora może dezaktywować inny administrator.

---

## Problemy techniczne

### "Sesja wygasła — odśwież stronę"
Token CSRF wygasł (zwykle po długiej nieaktywności). Odśwież F5 i zaloguj się ponownie.

### Edytor pokazuje "Nie udało się wczytać szablonu"
Szablon mógł zostać usunięty, albo nie masz do niego dostępu. Wróć na **Szablony** i sprawdź listę.

### Pobieram PDF i dostaję błąd "pdf_render_failed"
Coś poszło nie tak po stronie serwera (zwykle nieprawidłowe dane w obiekcie). Sprawdź czy nie masz placeholdera kolumny `{{...}}` w pojedynczej etykiecie (kolumny działają tylko w generowaniu serii, w pojedynczym PDF zostają jako tekst; placeholdery daty liczą się wszędzie).

### Generuję serię i widzę `no_rows: filter matched no rows`
Filtr w Kroku 3 nie złapał żadnego wiersza. Wróć i poluzuj filtr lub go wyłącz.

### Autozapis się zatrzymał na "Niezapisane zmiany" i nie idzie dalej.
Prawdopodobnie sieć padła. Sprawdź połączenie i kliknij ręcznie **Zapisz**.

### W generowanym PDF brakuje jednego obiektu, choć w edytorze go widzę.
Sprawdź czy w prawym panelu nie ma odznaczonego **🖨 Drukuj w PDF** — wtedy obiekt jest tylko podglądowy.

### Tekst w bloku jest przycięty.
Po wygenerowaniu PDF zobaczysz **N ostrzeżeń**. Dwie opcje:
1. Powiększ ramkę bloku.
2. Włącz **Auto-skalowanie** w prawym panelu i ustaw min. font.

### Strona programu jest po angielsku, a chcę po polsku.
Przełącznik języka **PL/EN** jest w prawym górnym rogu nagłówka (także na stronie logowania).

### Na etykiecie wyszła data wczorajsza/jutrzejsza zamiast dzisiejszej.
Data liczy się według zegara **serwera**. Jeśli rozjazd się powtarza, poproś administratora o sprawdzenie strefy czasowej serwera (zmienna `TZ` w konfiguracji).

---

## Pytania, których nie ma na liście

Napisz do **dev@attv.uk** — opisz co próbujesz zrobić i co zobaczyłeś. Zrzut ekranu mile widziany.
