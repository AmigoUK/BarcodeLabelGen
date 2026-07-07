# BarcodeLabelGen — FAQ

Najczęstsze pytania, od najprostszych do bardziej zaawansowanych. Każda odpowiedź jest krótka — jeśli chcesz zobaczyć konkretne kroki ze zrzutami ekranu, zajrzyj do [przewodnika Pomoc](HELP.pl.md), do sekcji podanej w nawiasie. Nie znalazłaś/eś odpowiedzi? Napisz na **dev@attv.uk**.

---

## Podstawy

### Po co jest ten program?
Tworzysz w nim szablony etykiet — rozmiar w milimetrach, dowolny tekst, kody kreskowe, obrazy — a potem generujesz **wiele etykiet z jednego szablonu naraz**, każdą z innymi danymi pobranymi z arkusza (np. Excela) albo z bazy danych. (Zobacz *Pomoc*, sekcja 6.)

### Czemu po pierwszym logowaniu program kazał mi zmienić hasło?
Administrator dał Ci hasło tymczasowe — czyli takie na start, do jednorazowego użycia. Pierwsze logowanie zawsze wymusza ustawienie własnego hasła (minimum 10 znaków). To zdarza się tylko raz. (Zobacz *Pomoc*, sekcja 1.)

### Gdzie jest przycisk „Nowy szablon"?
Lewe menu → **Szablony** → przycisk **Nowy szablon** w prawym górnym rogu listy.

### Czy mogę zmienić rozmiar etykiety po utworzeniu szablonu?
Tak. W edytorze kliknij przycisk **📐 {szerokość}×{wysokość}** w pasku narzędzi, wpisz nowe wymiary w mm albo wybierz gotowy preset i kliknij **Zastosuj**. Obiekty zachowują swoje pozycje w mm — nie są przeskalowywane. (Zobacz *Pomoc*, sekcja 4.)

### Czy mogę cofnąć się do wcześniejszej wersji szablonu?
Tak — kliknij **🕘 Historia** w edytorze. Każdy ręczny zapis (przycisk Zapisz albo Ctrl+S) tworzy wersję, czyli migawkę tego, jak wyglądał szablon w danym momencie; kliknij **Przywróć** przy tej, do której chcesz wrócić. Autozapis nie tworzy wersji, więc lista jest krótka i czytelna — program trzyma 30 ostatnich. (Zobacz *Pomoc*, sekcja 4.)

### Jak zapisać szablon?
Edytor zapisuje sam — to tzw. autozapis, co kilka sekund; status widać w pasku narzędzi. Możesz też ręcznie nacisnąć **Ctrl/Cmd + S**.

---

## Edytor i obiekty

### Jaka jest różnica między **Tekst** (T) a **Blok tekstu** (¶)?
- **Tekst** — jedna linia, stały rozmiar fontu, nie zawija się.
- **Blok tekstu** — wiele linii, zawija się w ramce o zadanej szerokości. Można dodatkowo włączyć **auto-skalowanie**, które samo dopasowuje rozmiar fontu do długości tekstu — przydatne, gdy z bazy przychodzą raz krótkie, raz długie nazwy.

### Co znaczy `{{nazwa_kolumny}}` w polu tekstowym?
To **placeholder** — miejsce, w które program sam wstawi dane z odpowiedniej kolumny Twojego arkusza lub bazy, ale dopiero podczas generowania serii etykiet. Działa zarówno w polu Tekst, jak i w polu *Dane* obiektu Kod kreskowy. (Zobacz *Pomoc*, sekcja 6.)

### Co znaczy zielony chip pod polem tekstowym?
Zielony „chip" (mały kolorowy znacznik) oznacza **placeholder daty** (np. `{{date+14d}}`) i od razu pokazuje, jaka data z niego wyjdzie. Fioletowe chipy to zwykłe kolumny z arkusza. Szczegóły zapisu dat: *Pomoc*, sekcja 7.

### Jak dodać tabelę?
Lewy panel → **▦ Tabela**. Treść komórek, liczbę wierszy/kolumn i szerokości kolumn ustawiasz w prawym panelu. W komórkach działają placeholdery `{{kolumna}}` i daty `{{date+x}}` — przy generowaniu serii kolumny podmieniają się tak samo jak w zwykłym tekście. (Zobacz *Pomoc*, sekcja 3.)

### Polskie znaki w PDF wychodziły jako kwadraciki — czy to naprawione?
Tak, od wersji v0.13.0. PDF osadza teraz czcionki z pełnym zestawem polskich znaków (ż, ł, ć, ę, ą, ź, ń, ś). Jeśli nadal widzisz kwadraciki, sprawdź na stronie `/api/health`, czy działasz na wersji 0.13.0 lub nowszej.

### Jak wstawić logo, które ma się drukować na każdej etykiecie?
Lewy panel → **🖼 Obraz** → wybierz plik PNG, JPG lub SVG. Logo będzie drukować się na każdej wygenerowanej etykiecie.

### Jaka jest różnica między **🖼 Obraz** a **🌄 Tło (referencja)**?
- **🖼 Obraz** — zwykły obraz, drukuje się w PDF.
- **🌄 Tło** — obraz na cały rozmiar etykiety, **zablokowany** (nie da się go przesunąć) i **NIE drukuje się** w PDF. Używaj go, gdy Twoje etykiety przyszły z drukarni z już wydrukowanym logo, a Ty chcesz tylko poprawnie ustawić nowy tekst — w edytorze widzisz tło jako wzorzec, ale finalny PDF zawiera wyłącznie Twoje dodatki. (Zobacz *Pomoc*, sekcja 3.)

### Jak nie drukować jakiegoś obiektu w PDF?
Zaznacz obiekt → w prawym panelu, na samej górze, odznacz **🖨 Drukuj w PDF**. Obiekt zrobi się wyblakły w edytorze — to sygnał, że jest tylko podglądowy — a program pominie go w wydruku.

### Jak zablokować obiekt, żeby przypadkiem się nie przesunął?
Zaznacz go → w prawym panelu zaznacz **🔒 Zablokuj pozycję**. Uchwyty znikną, nie da się przeciągać ani skalować — ale wciąż można zaznaczyć obiekt i zmienić np. font czy kolor. Żeby odblokować, odznacz ten sam checkbox.

### Jak zmienić kolejność obiektów (co jest na wierzchu)?
Pasek wyrównania nad canvasem, grupa **Warstwa**: ⤓ na sam dół, ↓ niżej, ↑ wyżej, ⤒ na sam wierzch.

### Jak rozłożyć równomiernie kilka obiektów w poziomie?
Zaznacz je wszystkie (Shift + klik) → pasek wyrównania → przycisk **Rozłóż poziomo** (działa od 3 zaznaczonych obiektów wzwyż).

### Cofnąłem/am za dużo. Jak to przywrócić?
**Ctrl/Cmd + Shift + Z** albo **Ctrl/Cmd + Y**.

### Jak szybko zrobić kopię obiektu?
Dwa sposoby:
- **Alt + przeciąganie** — przytrzymaj Alt (na Mac: Option) i przeciągnij zaznaczony obiekt. Oryginał zostaje na miejscu, kopia ląduje pod kursorem. Działa też dla kilku zaznaczonych obiektów naraz.
- **Ctrl/Cmd + D** — robi kopię w miejscu, przesuniętą o 5 mm. Zaznaczenie przeskakuje na kopię, więc kolejne Ctrl+D buduje schodek kopii.

Kopia dziedziczy wszystkie ustawienia (font, kolor, blokadę, *Drukuj w PDF*); obrazy współdzielą jeden plik źródłowy.

---

## Generowanie serii (CSV / Excel)

### Jakie pliki mogę wgrać?
CSV, XLS lub XLSX. Maksymalnie **10 MB** i **1000 wierszy** na plik (limit obecnej wersji programu).

### Czy pierwszy wiersz arkusza musi być nagłówkiem?
Tak — pierwszy wiersz musi zawierać nazwy kolumn. To one stają się dostępne jako `{{nazwa}}` przy mapowaniu w Kroku 2.

### Mam więcej niż 1000 wierszy. Co zrobić?
Podziel arkusz na partie po maksymalnie 1000 wierszy i wygeneruj kilka osobnych PDF-ów.

### Mapowanie nie znalazło mojej kolumny.
Sprawdź, czy nazwa placeholdera (`{{...}}`) odpowiada dokładnie nagłówkowi kolumny — wielkość liter ma znaczenie, a dodatkowe spacje przeszkadzają. Jeśli nazwy się różnią (np. placeholder `{{name}}`, a kolumna `Nazwa produktu`), wybierz mapowanie ręcznie z listy w Kroku 2.

### PDF wyszedł z `{{name}}` w treści zamiast prawdziwej nazwy.
To znaczy, że placeholder się nie zmapował. W Kroku 2 (Mapowanie) musisz dla każdego placeholdera wybrać kolumnę.

### Czy mogę wygenerować etykiety tylko dla niektórych wierszy?
Tak — Krok 3 (Filtr). Wybierz kolumnę, warunek (np. „równe", „zawiera", „większe niż") i wartość. Kliknij **Sprawdź filtr**, żeby zobaczyć, ile wierszy się załapie.

---

## Foldery i Biblioteka

### Jak uporządkować szablony w foldery?
Strona **Szablony** → pasek po lewej → **Nowy folder**. Potem najedź na kafelek szablonu → **⚙** → wybierz folder → **Zapisz**. Foldery są prywatne (każdy ma swoje) i jednopoziomowe.

### Usunęłam/em folder — co się stanie z szablonami w środku?
Nic złego — po prostu wracają do „Bez folderu". Żaden szablon nie znika.

### Jak podzielić się szablonem z innymi w firmie?
Kafelek szablonu → **⚙** → zaznacz **„Udostępnij w Bibliotece"**. Inni zobaczą go w **Bibliotece** i będą mogli sklonować go przyciskiem „Użyj" — edytować oryginał może tylko właściciel. Odznacz pole, żeby wycofać udostępnienie.

### Czy przycisk „Użyj" w Bibliotece zmienia oryginał?
Nie — „Użyj" zawsze tworzy Twoją niezależną kopię (z dopiskiem „(kopia)"). Obrazy z szablonu są kopiowane do Twojej własnej biblioteki plików.

### Skąd się biorą „Gotowe projekty" w Bibliotece?
To gotowe wzory wbudowane w aplikację (aktualizowane razem z nią). Zawierają przykładowe placeholdery `{{...}}` i daty `{{date+x}}` — po sklonowaniu po prostu podmień przykładowe wartości na własne.

---

## Placeholdery daty

### Jak wstawić datę przydatności „dziś + 30 dni"?
W polu tekstowym (albo w danych kodu kreskowego) wpisz `{{date+30d}}`. Podczas generowania PDF-a lub ZPL program wstawi datę 30 dni późniejszą niż dzisiejsza, np. `03.08.2026`.

### Jakie przesunięcia dat mogę używać?
`d` = dni, `m` = miesiące, `y` = lata — z plusem albo minusem: `{{date+14d}}`, `{{date-7d}}`, `{{date+3m}}`, `{{date+1y}}`. Samo `{{date}}` to dzisiejsza data.

### Jak zmienić format wyświetlanej daty?
Dodaj format po dwukropku, z klocków DD/MM/YY/YYYY: `{{date+14d:DD/MM/YY}}` → `18/07/26`, `{{date:YYYY-MM-DD}}` → `2026-07-04`. Bez podanego formatu dostajesz `DD.MM.YYYY`.

### Kiedy dokładnie liczy się data?
W momencie **generowania** (PDF-a albo ZPL), według zegara serwera — nie w momencie, gdy piszesz szablon. Zielony chip w edytorze to tylko podgląd na dziś, żebyś od razu widziała/widział, jak to będzie wyglądać.

### Co się stanie, jeśli do 31 stycznia dodam 1 miesiąc?
Dostaniesz 28 (albo 29) lutego — program nigdy nie tworzy dat, które nie istnieją.

### Mam w arkuszu kolumnę o nazwie `date`. Która wersja wygrywa?
Dla gołego `{{date}}` wygrywa **kolumna z arkusza** (tak jak wcześniej). Formy z przesunięciem lub formatem (`{{date+14d}}`, `{{date:YYYY-MM-DD}}`) zawsze liczą się automatycznie, niezależnie od kolumny.

### Czemu w kreatorze serii pole `{{date}}` nie wymaga mapowania?
Bo bez mapowania program sam podstawi dzisiejszą datę. Mapujesz je tylko wtedy, gdy chcesz brać daty z kolumny w arkuszu.

---

## ZPL i TSPL / drukarki etykiet

### Co to jest ZPL i po co mi to?
**ZPL** to specjalny język, którym rozmawiają drukarki etykiet marki Zebra (i modele zgodne). Jeśli drukujesz na takiej drukarce, albo dostajesz gotowe etykiety w ZPL z innego systemu, program potrafi je **zaimportować do edytora** i **wyeksportować Twój projekt jako ZPL**. (Zobacz *Pomoc*, sekcja 7a.)

### Jak zaimportować etykietę ZPL?
Edytor → pasek narzędzi → **⤓ Importuj ZPL** → wklej kod → **Sprawdź** → **Importuj**. Uwaga: import zastępuje obecną zawartość canvasu.

### Nie znam DPI drukarki, z której pochodzi kod.
Zostaw w oknie importu opcję **Wykryj automatycznie**. **DPI** to gęstość wydruku — liczba kropek na milimetr, jaką drukuje drukarka; program porówna wymiary z kodu (`^PW`/`^LL`) z rozmiarem Twojej etykiety i sam dobierze 203 albo 300 dpi.

### Co się dzieje ze zmiennymi typu `{NAZWA}` w pojedynczych klamrach?
Przechodzą nietknięte w obie strony (import i eksport) — to zmienne drukarkowe Twojego własnego systemu, nie mają nic wspólnego z placeholderami programu. Podwójne klamry `{{...}}` to placeholdery BarcodeLabelGen.

### Czym różni się eksport „Szablon (zmienne)" od „Wsad (dataset)"?
- **Szablon** — jeden kod ZPL; placeholdery kolumn zostają w kodzie (podmienisz je we własnym systemie), a daty są od razu obliczone.
- **Wsad** — wybierasz wcześniej wgrany plik danych i dostajesz jeden plik `.zpl` z osobną etykietą dla każdego wiersza (wszystko już podmienione).

### Czy program obsługuje też drukarki TSC albo Toshiba?
Tak — przez **TSPL**, odpowiednik ZPL dla tych marek. W edytorze kliknij **⤒ TSPL**, wybierz DPI (203 lub 300) i pobierz albo skopiuj wygenerowany kod. To na razie prostsza funkcja niż ZPL: eksport działa tylko dla pojedynczej etykiety (bez trybu Wsad), nie ma jeszcze importu, a druk bezpośredni przez konektor obsługuje na razie tylko ZPL, nie TSPL.

### Czy mogę drukować bezpośrednio na drukarkę Zebra z programu?
Tak — przez **konektor** (`blg-connector`), czyli mały program instalowany na komputerze w tej samej sieci co drukarki, który łączy aplikację z drukarką. Skonfiguruj go raz (strona **Urządzenia** → token, czyli unikalny kod dostępu, + plik `config.yaml`), a potem w edytorze klikasz **🖨 Drukuj**, wybierasz urządzenie i drukarkę — etykieta trafia do kolejki, agent ją odbiera i wysyła na drukarkę. Instrukcja instalacji: plik `connector/README.md` w repozytorium projektu.

### Przycisk Drukuj mówi, że urządzenie jest offline.
Agent (program konektora) na tym komputerze nie zgłosił się od ponad minuty — sprawdź, czy `blg-connector` działa i ma połączenie z serwerem. Zadanie druku możesz mimo to wysłać: poczeka w kolejce, aż agent wróci.

### Zadanie druku skończyło się błędem „printer unreachable" (drukarka nieosiągalna).
Agent nie mógł połączyć się z drukarką przez sieć. Sprawdź adres IP drukarki w pliku `config.yaml` agenta i czy drukarka jest włączona, a potem wyślij zadanie ponownie.

### Jak przenieść etykietę ze starego programu (system magazynowy/Word) do edytora?
Skonfiguruj **wirtualną drukarkę** konektora — krok po kroku opisane w `connector/README.md`. Wydrukuj etykietę ze starego programu na tę wirtualną drukarkę, a pojawi się w **Urządzenia → Inbox**, skąd otworzysz ją w edytorze.

### Przechwycona etykieta nie ma loga/grafiki w edytorze.
Grafika ze sterownika drukarki przechodzi jako nieedytowalny element — wydrukuje się poprawnie, ale edytor pokaże tylko teksty, kody kreskowe i kształty, które potrafi rozpoznać i pozwolić Ci edytować.

### Coś wydrukowałam/em na wirtualną drukarkę i nic nie doszło.
Sprawdź log (dziennik zdarzeń) agenta na komputerze z konektorem. Najczęstsze przyczyny: zadanie nie zawierało poprawnego kodu drukarki, było za duże, albo serwer był chwilowo niedostępny — w tym ostatnim przypadku zadanie czeka lokalnie i wysyła się samo, gdy połączenie wróci.

---

## Generowanie serii (SQLite)

### Jak wgrać bazę SQLite?
**SQLite** to plik z całą bazą danych w jednym pliku. Krok 1 kreatora Generuj Serię — wybierz plik z rozszerzeniem `.db`, `.sqlite` lub `.sqlite3`. Limit rozmiaru: **50 MB**.

### Co zobaczę po wgraniu?
Listę tabel z bazy, posortowaną tak, że tabele z największą liczbą wierszy są na górze. Każda pozycja pokazuje liczbę kolumn i wierszy.

### Wybrałam/em tabelę i dostałam/em komunikat, że ma 0 wierszy.
Wybrałaś/eś pustą tabelę. Musi w niej być co najmniej 1 wiersz danych, żeby było co generować — wybierz inną, sortowanie powinno wypychać tabele z danymi na górę listy.

### Jak napisać własne zapytanie do bazy?
Pod listą tabel rozwiń **Pokaż zaawansowane: własne zapytanie SQL** i wpisz np.:
```sql
SELECT sku, UPPER(name) AS name, price FROM products WHERE price > 10
```
Kliknij **Użyj tego źródła**.

### Jakie zapytania są dozwolone?
Tylko **pojedyncze zapytanie odczytujące dane (SELECT)**. Połączenie z bazą jest tylko do odczytu — żadne polecenie, które mogłoby coś zmienić lub skasować, nie zostanie wykonane, nawet jeśli spróbujesz je wpisać.

### Dostałam/em komunikat, że wynik przekracza limit 1000 wierszy. Co teraz?
Twoje zapytanie zwróciło więcej niż 1000 wierszy. Dodaj warunek `WHERE`, żeby zawęzić wynik, albo dopisz `LIMIT 1000` na końcu.

### Czy mogę łączyć dane z dwóch tabel naraz (JOIN)?
Tak, to standardowa funkcja zapytań SQL. Przykład:
```sql
SELECT p.sku, p.name, c.category_description
FROM products p JOIN categories c ON p.category_id = c.category_id
```

### Czy zmiany, które próbuję zrobić w bazie, są zapisywane?
**Nie.** Połączenie jest tylko do odczytu — żadne polecenie modyfikujące się nie wykona.

### Mój plik .db pokazuje błąd „to nie jest poprawna baza SQLite".
Plik prawdopodobnie nie jest w formacie SQLite (np. ma rozszerzenie `.db`, ale w środku jest coś innego). Sprawdź, skąd pochodzi ten plik.

---

## Import / eksport szablonów

### Po co eksportować szablon do pliku?
Trzy główne powody: **backup** (zachowujesz plik na wypadek, gdyby coś poszło nie tak), **klonowanie** (eksport + import z nadpisanym rozmiarem daje gotowy szablon na inny format etykiety), **przenoszenie** (między instalacjami programu albo między użytkownikami).

### Gdzie jest przycisk eksportu?
- Na liście szablonów: najedź na kafelek, kliknij ikonę **⬇** w prawym dolnym rogu.
- W edytorze: pasek narzędzi → przycisk **⬇ Eksportuj**, obok *Pobierz PDF*.

### Co dokładnie jest w pliku .blg-template.json?
Rozmiar etykiety, każdy obiekt (tekst, kod, prostokąt, linia, obraz) z dokładną pozycją i wszystkimi ustawieniami, oraz wszystkie obrazki zakodowane wprost w pliku. Plik jest samowystarczalny — nie potrzebujesz nic więcej poza tym jednym plikiem.

### Czy mogę zaimportować szablon z innej instalacji BarcodeLabelGen?
Tak, format pliku jest stabilny między wersjami. Jeśli docelowa instalacja nie zna dokładnie takiego samego formatu etykiety jak ta, z której eksportowałaś/eś, dostaniesz ostrzeżenie i program użyje formatu „Własny".

### Czy mogę zaimportować tylko część obiektów z pliku?
Tak — w drugim kroku okna importu jest lista z checkboxami. Domyślnie wszystko jest zaznaczone; odznacz to, czego nie chcesz. Pominięte obrazki nie tworzą zbędnych plików w Twojej bibliotece.

### Co się dzieje, gdy w pliku jest obrazek, który już mam?
Program sprawdza, czy to ten sam plik (porównując jego cyfrowy „odcisk palca") i pyta Cię: **Użyj istniejącego** (zero duplikatów na dysku) albo **Utwórz nową kopię** (przydatne, gdy chcesz mieć osobną, niezależnie edytowalną kopię).

### Czy mogę zaimportować szablon, zmieniając jednocześnie jego rozmiar?
Tak — w drugim kroku są pola Szerokość/Wysokość. Zostaw je puste, żeby zachować oryginalny rozmiar, albo wpisz nowe wartości. Obiekty zachowują swoje pozycje w mm, więc układ zostaje ten sam, tylko na innym formacie.

### Dostaję komunikat „Nie udało się odczytać pliku".
Plik nie jest poprawnym plikiem JSON — być może jest uszkodzony albo został zmieniony ręcznie i zapisany z błędem. Spróbuj ponownie wyeksportować szablon źródłowy.

### Dostaję komunikat o niezgodności sumy kontrolnej (sha256).
Zawartość obrazka w pliku nie zgadza się z zapisaną w nim sumą kontrolną — cyfrowym „odciskiem palca", który potwierdza, że plik nie został zmieniony. Oznacza to, że plik był ręcznie modyfikowany. Program celowo odrzuca takie pliki — mogłoby to ukrywać podmieniony obrazek. Wyeksportuj plik ponownie ze źródła.

### Jakie są limity?
Plik do 20 MB, szablon do 50 obiektów, do 20 obrazków, każdy obrazek do 5 MB.

## Konta i bezpieczeństwo

### Jak administrator dodaje nowego użytkownika?
**Administracja → Użytkownicy → Utwórz konto**. Podaje email, hasło tymczasowe (minimum 10 znaków) i rolę. Po utworzeniu konta hasło wyświetla się **tylko raz** — trzeba je od razu skopiować i przekazać użytkownikowi.

### Jakie są role i co mogą robić?
- **Administrator** — wszystko, w tym zarządzanie kontami.
- **Edytor** — tworzy i edytuje własne szablony i zestawy danych, generuje PDF-y.
- **Tylko podgląd** — może oglądać, ale nie zapisuje zmian.

### Zapomniałam/em hasła.
Poproś administratora o reset hasła (**Administracja → Użytkownicy → Resetuj hasło**). Dostaniesz nowe hasło tymczasowe — przy logowaniu program poprosi Cię o ustawienie własnego.

### Czemu nie mogę dezaktywować własnego konta?
Bo zostałabyś/zostałbyś zablokowana/y poza aplikacją bez możliwości naprawy tego samodzielnie. Drugi administrator może dezaktywować kogoś innego, ale nie samego siebie.

### Gdzie znajdę wcześniej wygenerowane PDF-y?
Menu → **Historia**. Program przechowuje tam wszystkie wygenerowane pliki (pojedyncze etykiety i całe serie, PDF-y i wsadowe pliki ZPL) przez 30 dni — kliknij **Pobierz**, żeby ściągnąć plik ponownie bez generowania go od nowa.

## Problemy techniczne

### „Sesja wygasła — odśwież stronę"
Token bezpieczeństwa (mały, tymczasowy kod, który chroni Twoją sesję) wygasł — zwykle po dłuższej nieaktywności. Odśwież stronę (klawisz F5) i zaloguj się ponownie.

### Edytor pokazuje „Nie udało się wczytać szablonu"
Szablon mógł zostać usunięty, albo nie masz do niego dostępu. Wróć na stronę **Szablony** i sprawdź listę.

### Pobieram PDF i dostaję błąd „pdf_render_failed"
Coś poszło nie tak po stronie serwera — zwykle chodzi o nieprawidłowe dane w jednym z obiektów. Sprawdź, czy nie masz placeholdera kolumny `{{...}}` w pojedynczej etykiecie — kolumny działają tylko przy generowaniu serii, w pojedynczym PDF-ie zostają jako zwykły tekst (placeholdery dat liczą się wszędzie).

### Generuję serię i widzę komunikat, że filtr nie złapał żadnego wiersza.
Filtr w Kroku 3 był zbyt restrykcyjny. Wróć i poluzuj go albo go wyłącz.

### Autozapis utknął na „Niezapisane zmiany" i nic się nie dzieje.
Prawdopodobnie padło połączenie z siecią. Sprawdź internet i kliknij ręcznie **Zapisz**.

### W wygenerowanym PDF brakuje jednego obiektu, choć w edytorze go widzę.
Sprawdź, czy w prawym panelu tego obiektu nie jest odznaczone **🖨 Drukuj w PDF** — wtedy jest on tylko podglądowy.

### Tekst w bloku jest przycięty.
Po wygenerowaniu PDF-a zobaczysz chip **„N ostrzeżeń"**. Masz dwie opcje:
1. Powiększ ramkę bloku tekstu.
2. Włącz **Auto-skalowanie** w prawym panelu i ustaw minimalny rozmiar fontu.

### Program jest po angielsku, a chcę po polsku.
Przełącznik języka **PL/EN** jest w prawym górnym rogu nagłówka (dostępny też na stronie logowania).

### Na etykiecie wyszła data wczorajsza albo jutrzejsza zamiast dzisiejszej.
Data liczy się według zegara **serwera**, na którym działa program. Jeśli ten rozjazd się powtarza, poproś administratora o sprawdzenie ustawień strefy czasowej serwera.

---

## Pytania, których nie ma na liście

Napisz do **dev@attv.uk** — opisz, co próbowałaś/eś zrobić i co zobaczyłaś/eś. Zrzut ekranu bardzo się przyda.
