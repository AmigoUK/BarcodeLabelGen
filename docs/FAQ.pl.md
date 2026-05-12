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
Nie w tej wersji. Format ustawiasz raz przy tworzeniu szablonu. Jeśli musisz zmienić rozmiar — utwórz nowy szablon.

### Jak zapisać szablon?
Edytor zapisuje sam (autozapis co kilka sekund — status widać w toolbarze). Możesz też ręcznie **Ctrl/Cmd + S**.

---

## Edytor i obiekty

### Jaka jest różnica między **Tekst** (T) a **Blok tekstu** (¶)?
- **Tekst** — jedna linia, stały rozmiar fontu, nie zawija.
- **Blok tekstu** — wieloliniowy, zawija się w ramce o zadanej szerokości. Dodatkowo można włączyć **Auto-skalowanie**, które dopasowuje font do długości tekstu (potrzebne gdy z bazy przychodzą krótkie i długie nazwy).

### Co znaczy `{{nazwa_kolumny}}` w polu tekstowym?
To **placeholder**. Przy generowaniu serii zostanie podmieniony wartością z odpowiedniej kolumny w arkuszu/bazie. Działa w polu Text **i** w polu *Dane* obiektu Barcode.

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
Coś poszło nie tak po stronie serwera (zwykle nieprawidłowe dane w obiekcie). Sprawdź czy nie masz placeholdera `{{...}}` w pojedynczym podglądzie pojedynczej etykiety (placeholdery działają tylko w generowaniu serii, w pojedynczym PDF zostają jako tekst).

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
Przełącznik języka jest w prawym górnym rogu (lub w menu użytkownika).

---

## Pytania, których nie ma na liście

Napisz do **dev@attv.uk** — opisz co próbujesz zrobić i co zobaczyłeś. Zrzut ekranu mile widziany.
