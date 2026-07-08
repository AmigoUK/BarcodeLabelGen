# F40b — macOS: instalacja przez „skopiuj 1 komendę" — design

**Data:** 2026-07-08
**Status:** zatwierdzony (wariant A w brainstormie po nieudanym E2E v0.23.1)

## Problem

Dwie kolejne iteracje ścieżki plikowej na macOS poległy na realnym Macu:
1. goły `.command` z bloba — brak bitu wykonywalności („appropriate access
   privileges"),
2. `BLG-Connect.zip` z trybem 0755 w atrybutach — Archive Utility użytkownika
   nie odtworzyło +x (linuksowy `unzip` honoruje; różnica implementacyjna
   niediagnozowalna bez fizycznego Maca).

## Rozwiązanie

macOS przechodzi na **schowek zamiast pliku**: krok „install" kreatora
pokazuje przycisk **Kopiuj** z jedną linią:

```
echo '<base64(skrypt instalatora)>' | base64 -D | bash
```

- Skrypt (z wtopionym tokenem/configiem) jedzie przez schowek — **zero
  pliku, zero bitu wykonywalności, zero kwarantanny/Gatekeepera, zero
  rozpakowywania**. Token nadal nigdy nie występuje w URL.
- Instrukcja: 1. Otwórz Terminal (Cmd+Spacja) → 2. Kliknij Kopiuj →
  3. Wklej i Enter. Kroki samoweryfikacji [1/3–3/3] bez zmian (ten sam
  skrypt).
- `base64 -D` — flaga macOS (ścieżka wyłącznie macowa; Linux zostaje przy
  `bash ~/Pobrane/blg-connect.sh`).
- Wirtualna drukarka (mac): ta sama komenda z argumentami przez
  `bash -s -- --virtual-printer` (skrypt ze stdin dostaje argumenty) —
  generowana dynamicznie w kroku „virtual", bo wymaga base64 z tokenem;
  statyczny klucz i18n `virtualCmdMac` znika.
- Pobieranie `BLG-Connect.zip` zostaje jako **link alternatywny** („wolisz
  plik?") — naprawa zipa pod Archive Utility w backlogu (F40c), podpisany
  .pkg w backlogu (F43).

## Zmiany

- `frontend/src/lib/installerSetup.ts`: `macPasteCommand(opts, extraArgs?)`
  (czysta funkcja; reuse `unixScript` + `toBase64`).
- `ConnectPrinterWizard.tsx`: krok install (mac) — komenda+Kopiuj jako
  primary, zip jako link; krok virtual (mac) — komenda z
  `macPasteCommand(opts, ["--virtual-printer"])`.
- i18n PL/EN: nowy tekst installRun.mac (3 kroki), klucz linku zipa;
  usunięcie `virtualCmdMac`.
- Testy (vitest): komenda dekoduje się z powrotem do skryptu; kończy się
  `| base64 -D | bash`; wariant z argami używa `bash -s -- --virtual-printer`;
  jest jedną linią.

## Wersja

v0.23.2 (patch — naprawa ścieżki instalacji).
