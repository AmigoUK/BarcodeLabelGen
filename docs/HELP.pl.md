# BarcodeLabelGen — Pomoc

Krótki przewodnik po programie. Czytaj sekcjami, w kolejności, albo skacz od razu do interesującego cię feature'u.

---

## 1. Pierwsze kroki

### Logowanie

1. Otwórz adres aplikacji w przeglądarce.
2. Wpisz email i hasło, które dał ci administrator.
3. Przy pierwszym logowaniu program poprosi cię o ustawienie własnego hasła (min. 10 znaków). To jednorazowe — kolejne logowania od razu pokazują panel.

### Pulpit

Po zalogowaniu trafiasz na **Pulpit**. To tylko ekran powitalny — żeby zacząć pracę kliknij **Szablony** w lewym menu.

### Tworzenie pierwszego szablonu

1. **Szablony** → **Nowy szablon**.
2. Wpisz nazwę (np. "Cennik produktów").
3. Wybierz format etykiety:
   - **Predefiniowane** — gotowe rozmiary (A4, Zebra 2×1″ itd.).
   - **Własny rozmiar** — wpisz szerokość i wysokość w mm i wybierz orientację.
4. Klik **Utwórz** — otwiera się edytor.

---

## 2. Menu i nawigacja

### Lewe menu (sidebar)

| Pozycja | Co tu znajdziesz |
|---|---|
| **Pulpit** | Ekran startowy. |
| **Szablony** | Lista twoich szablonów + przycisk *Nowy szablon*. |
| **Importy danych** | Wgrane pliki CSV/Excel/SQLite z poprzednich generowań serii. |
| **Administracja → Użytkownicy** | (tylko admin) zarządzanie kontami. |

### Edytor — układ ekranu

Po otwarciu szablonu widzisz:

- **Toolbar (góra)** — Zapisz, Cofnij/Ponów, autozapis, **Pobierz PDF**, **Generuj serię**.
- **Lewy panel (Dodaj)** — przyciski wstawiania obiektów na etykietę.
- **Canvas (środek)** — twoja etykieta w skali 1:1 (mm).
- **Pasek wyrównania (nad canvasem)** — wyrównywanie i kolejność warstw.
- **Prawy panel (Właściwości)** — ustawienia zaznaczonego obiektu.

### Pasek wyrównania — co która grupa robi

- **Strona** — wyrównuje obiekt do krawędzi/środka strony.
- **Zaznaczenie** — wyrównuje obiekty względem siebie (potrzebne ≥2 zaznaczone).
- **Warstwa** — zmienia kolejność (przód/tył) zaznaczonych obiektów.
- **Rozłóż** (3+ obiektów) — równe odstępy w poziomie/pionie.

Każda ikona ma podpowiedź (najedź myszką).

---

## 3. Tworzenie etykiety — przewodnik po obiektach

Wszystkie poniższe są w **lewym panelu**, sekcja *Dodaj*.

### T — Tekst

**Co robi:** Pojedyncza linia tekstu o stałym rozmiarze.
**Kiedy:** Etykiety / nagłówki / krótkie napisy.
**Jak:** Klik **T Tekst**, potem zaznacz na canvasie i edytuj treść w prawym panelu.

### ¶ — Blok tekstu

**Co robi:** Wieloliniowy tekst, który automatycznie zawija się w ramce; opcjonalnie *auto-skalowanie* zmniejsza/zwiększa font żeby się zmieścił.
**Kiedy:** Opisy produktu o zmiennej długości (idealne do `{{description}}` ze spreadsheetu).
**Jak:** Klik **¶ Blok tekstu**. W prawym panelu zaznacz **Auto-skalowanie** i ustaw min/max font.

### ▭ — Prostokąt, ╱ — Linia

**Co robi:** Geometria pomocnicza (ramki, separatory).
**Jak:** Klik → przeciągnij w canvasie żeby zmienić rozmiar; ustaw kolor/obrys w prawym panelu.

### ▤ — Kod kreskowy

**Co robi:** Generuje kod kreskowy z podanej wartości.
**Kiedy:** Każdy katalog produktów z kodem.
**Jak:** Klik **▤ Kod kreskowy**, w prawym panelu wybierz typ (EAN-13, Code128 itd.) i wpisz dane. Możesz wpisać `{{sku}}` żeby wartość pobrać z arkusza.

### 🖼 — Obraz

**Co robi:** Wgrywa PNG/JPG/SVG i wstawia na canvas. Drukuje się w PDF.
**Kiedy:** Logo, ilustracje, ikony, zdjęcia produktu.
**Jak:** Klik **🖼 Obraz** → wybierz plik. Maks 5 MB.

### 🌄 — Tło (referencja)

**Co robi:** Wgrywa obraz jako **zablokowane tło na cały rozmiar etykiety**, które jest **widoczne tylko w edytorze, ale NIE drukuje się w PDF**.
**Kiedy:** Etykiety przyszły z drukarni z już wydrukowanym logo. Skanujesz wzór, wgrywasz jako tło, ustawiasz tekst pasujący do logo, generujesz PDF — drukarka dodrukowuje tylko nowy tekst, logo się nie dubluje.
**Jak:** Klik **🌄 Tło**, wybierz plik. Tło ląduje na samym dole stosu, zablokowane (bez uchwytów). Żeby zmienić: zaznacz, w prawym panelu odznacz **Zablokuj pozycję** lub zaznacz **Drukuj w PDF**.

---

## 4. Praca z obiektami

### Zaznaczanie

- Pojedynczy klik = zaznacz jeden.
- **Shift + klik** = dodaj do zaznaczenia (multi-select).
- **Ctrl/Cmd + A** = zaznacz wszystko.

### Przesuwanie i skalowanie

- Przeciągaj zaznaczony obiekt myszką.
- Uchwyty na rogach = skalowanie; uchwyt nad obiektem = obrót.
- Obiekt **zablokowany** nie ma uchwytów — ale dalej można go zaznaczyć żeby odblokować w prawym panelu.

### Cofanie

- **Ctrl/Cmd + Z** = cofnij.
- **Ctrl/Cmd + Shift + Z** lub **Ctrl/Cmd + Y** = ponów.

Jedna operacja = jeden krok historii (np. wyrównanie 5 obiektów cofa się jednym Ctrl+Z).

### Kolejność warstw (z-order)

W **pasku wyrównania**, grupa **Warstwa**:

- ⤓ **Na sam dół** — wsadź zaznaczone pod resztę.
- ↓ **Niżej** — przesuń o jedno pod sąsiada.
- ↑ **Wyżej** — przesuń o jedno nad sąsiada.
- ⤒ **Na sam wierzch** — nad wszystko.

Multi-select zachowuje względną kolejność zaznaczonych.

### Lock + Drukuj w PDF (prawy panel)

Każdy obiekt ma na górze prawego panelu dwa checkboxy:

- **🔒 Zablokuj pozycję** — wyłącza przesuwanie i skalowanie (ale dalej można edytować font, kolor itd.).
- **🖨 Drukuj w PDF** — domyślnie zaznaczone. Odznaczone = obiekt widać tylko w edytorze, w PDF się nie pojawi (renderer go pomija). Obiekty nie-drukowane są wyblakłe (50% przezroczystości) żebyś od razu widział.

### Autozapis

Edytor sam zapisuje co kilka sekund. Status w toolbarze:
- **Niezapisane zmiany** — coś jest do zapisania.
- **Autozapis…** — w trakcie wysyłania.
- **Autozapisano 12:34** — ostatni zapis.

Możesz też ręcznie kliknąć **Zapisz**.

---

## 5. Pobieranie PDF — pojedyncza etykieta

W toolbarze edytora kliknij **Pobierz PDF**. Renderowanie jest synchroniczne (kilka sekund), plik PDF zaczyna się ściągać.

Jeśli któryś tekst nie zmieścił się w bloku, zobaczysz chip **N ostrzeżeń** — najedź żeby zobaczyć szczegóły.

---

## 6. Generowanie serii — wiele etykiet z jednego szablonu

To główny feature programu. Pozwala wygenerować np. 200 etykiet z jednego szablonu, gdzie każda dostaje inne dane z arkusza/bazy.

### Krok 0 — przygotowanie szablonu

Wstaw w Text lub Barcode placeholder w postaci `{{nazwa_kolumny}}`, np.:
- Text: `{{name}}`
- Barcode data: `{{sku}}`

Każde wystąpienie zostanie podmienione wartością z odpowiedniej kolumny.

### Krok 1 — Wgraj dane

Toolbar → **Generuj serię** → Krok 1 (Wgraj dane).

Akceptowane formaty:

| Format | Maks rozmiar | Maks wierszy |
|---|---|---|
| `.csv` | 10 MB | 1000 |
| `.xls` / `.xlsx` | 10 MB | 1000 |
| `.db` / `.sqlite` / `.sqlite3` | 50 MB | 1000 (na zapytanie) |

#### CSV / Excel

Plik trafia na serwer i od razu jest parsowany. Widzisz kolumny i liczbę wierszy. Klik **Dalej**.

#### SQLite

Po uploadzie program pokazuje **listę tabel** (posortowane: najpierw te z największą liczbą wierszy). Wybierz tabelę z danymi i kliknij **Użyj tego źródła**.

Jeśli potrzebujesz filtrowania na poziomie SQL (np. tylko produkty z konkretnej kategorii, lub JOIN dwóch tabel), rozwiń **Pokaż zaawansowane** i wpisz zapytanie SELECT, np.:

```sql
SELECT sku, name, price
FROM products
WHERE category = 'labels' AND price > 0
```

**Bezpieczeństwo:** Połączenie jest read-only. Akceptowany jest tylko pojedynczy SELECT — `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ATTACH`, `PRAGMA` są blokowane. Maksymalnie 1000 wierszy w wyniku — większe odrzucone z prośbą o `WHERE`/`LIMIT`.

### Krok 2 — Mapowanie pól

Program wykrywa wszystkie placeholdery `{{...}}` z szablonu. Jeśli nazwa placeholdera == nazwa kolumny, mapowanie wstawia się automatycznie. Jeśli różne — wybierz ręcznie z listy.

### Krok 3 — Filtr (opcjonalny)

Możesz odsiać wiersze przed generowaniem, np. *price > 10* albo *category contains "tea"*. Klik **Sprawdź filtr** pokazuje ile wierszy się załapie. Pomiń ten krok jeśli chcesz wszystkie.

### Krok 4 — Generuj PDF

Klik **Generuj PDF**. Powstaje zadanie w tle, pasek pokazuje postęp. Po zakończeniu PDF ściąga się automatycznie.

Jeśli któreś etykiety mają teksty nie mieszczące się w blokach, zobaczysz listę ostrzeżeń (które wiersze, które obiekty) — PDF i tak powstaje.

---

## 7. Importy danych

Lewe menu → **Importy danych** — lista wszystkich plików, które kiedykolwiek wgrałeś (CSV/Excel/SQLite). Możesz je usuwać żeby zwolnić miejsce. Pliki są prywatne — każdy widzi tylko swoje.

---

## 8. Administracja (tylko admin)

Lewe menu → **Administracja → Użytkownicy**.

### Tworzenie użytkownika

1. Klik **Utwórz konto**.
2. Wpisz email + hasło tymczasowe (min. 10 znaków, możesz wygenerować losowe).
3. Wybierz rolę:
   - **Administrator** — pełny dostęp + zarządzanie użytkownikami.
   - **Edytor** — tworzy/edytuje swoje szablony i dataset'y.
   - **Tylko podgląd** — może otwierać i podglądać, ale nie zapisuje.
4. Po kliknięciu *Utwórz* program pokaże hasło tymczasowe **tylko raz** — przekaż je użytkownikowi.

### Reset hasła

Klik **Resetuj hasło** przy koncie → wygeneruj nowe tymczasowe → przekaż użytkownikowi. Przy następnym logowaniu zostanie zmuszony je zmienić.

### Aktywacja / dezaktywacja

Toggle **Aktywne** w wierszu użytkownika. Nie możesz dezaktywować własnego konta (zabezpieczenie).

---

## 8a. Import / eksport szablonów

Każdy szablon możesz zapisać jako jeden plik `.blg-template.json` (rozmiar etykiety + pozycje wszystkich obiektów + ich treść + obrazki zakodowane w pliku). Plik jest przenośny: zarchiwizujesz go, wyślesz mailem albo zaimportujesz na drugiej instancji BarcodeLabelGen.

### Eksport

Dwa miejsca:
- **Szablony** → najedź na kafelek szablonu → ikona **⬇** w prawym dolnym rogu.
- W edytorze → toolbar → przycisk **⬇ Eksportuj** (obok *Pobierz PDF*).

Pobiera się plik `<nazwa>.blg-template.json` — najlepiej trzymaj go w katalogu backupów.

### Import

**Szablony** → **⬆ Importuj** otwiera 2-krokowe okno:

1. **Wybór pliku** — podaj `.blg-template.json`. Program sprawdza poprawność i pokazuje podgląd.
2. **Konfiguracja** — możesz:
   - zmienić **nazwę** nowego szablonu (domyślnie nazwa z pliku; jeśli kolizja → automatyczny suffix „(kopia)"),
   - **nadpisać rozmiar** (puste = oryginalny),
   - **odznaczyć obiekty** które nie mają zostać zaimportowane (czeklista — każdy obiekt z ikoną typu i preview treści),
   - dla każdego **duplikatu obrazka** wybrać: *Użyj istniejącego* (oszczędność miejsca) lub *Utwórz nową kopię*.

Klik **Importuj** → tworzy nowy szablon i otwiera go w edytorze.

### Typowe przypadki użycia

- **Backup przed dużą zmianą** — eksportuj, zostaw plik w archiwum, edytuj swobodnie. Coś poszło źle → reimportuj.
- **Klonowanie układu na inny rozmiar** — eksport, import z nadpisanym rozmiarem (np. ta sama etykieta dla A6 i 100×50 mm).
- **Przeniesienie szablonu między instancjami** (dev → prod) — eksport po jednej stronie, import po drugiej.
- **Wybiórczy import** — bierzesz układ kodu kreskowego + 2-3 pola z gotowego szablonu, resztę odznaczasz.

### Limity i bezpieczeństwo

- Maks. 20 MB plik, 50 obiektów, 20 obrazków (5 MB każdy).
- Obrazki są weryfikowane: sha256 musi się zgadzać z zawartością base64. Pliki manipulowane są odrzucane.
- Nowy szablon zawsze trafia do twojego konta (niezależnie kto wyeksportował plik).

## 9. Skróty klawiaturowe

| Skrót | Akcja |
|---|---|
| Ctrl/Cmd + S | Zapisz |
| Ctrl/Cmd + Z | Cofnij |
| Ctrl/Cmd + Shift + Z | Ponów |
| Ctrl/Cmd + A | Zaznacz wszystko (w canvasie) |
| Delete / Backspace | Usuń zaznaczone |
| Shift + klik | Dodaj do zaznaczenia |

---

## 10. Wsparcie

Programem zarządza **Tomasz "Amigo" Lewandowski** — kontakt: dev@attv.uk · www.attv.uk.

Kod źródłowy: github.com/AmigoUK/BarcodeLabelGen
