<p align="center">
  <img src="docs/ikona.png" width="112" alt="Syrop Wykreślny">
</p>

<h1 align="center">Syrop Wykreślny</h1>

<p align="center">
  <b>Przekroje (profile) terenu z trójwymiarowych linii – na milimetrowej kalce, w skali, gotowe do druku i do CAD-a.</b><br>
  Program dla Windows 10 / 11 · wersja dla QGIS · GPL-3.0
</p>

<p align="center">
  🇵🇱 Polski · <a href="README.en.md">🇬🇧 English</a>
</p>

---

![Przekrój w programie Syrop Wykreślny](docs/przekroj.png)

## Co robi program

Syrop Wykreślny wczytuje linię lub multilinię 3D (współrzędna Z = wysokość) i rysuje jej przekrój:
odległość wzdłuż linii na osi poziomej, wysokość na osi pionowej. Rysunek powstaje na „papierze
milimetrowym” w zadanych skalach, więc wydrukowany w 100 % odpowiada skalom z opisu.

- **Wejście:** KML/KMZ, DXF, DWG, SHP, GPKG – układy EPSG:4326 (WGS 84), 2176, 2177, 2178, 2179
  (PL-2000) i 2180 (PL-1992). Układ jest rozpoznawany z pliku albo wybierany z listy.
- **Skale:** osobna skala pozioma i pionowa (np. 1:5 000 / 1:200), przewyższenie liczone
  automatycznie, jednostki osi mm / cm / m / km.
- **Widok:** siatka milimetrowa na granatowym tle, powiększanie kółkiem myszy, przesuwanie,
  odczyt odległości i wysokości pod kursorem, edytowalny nagłówek (tytuł, dane, podpisy skal).
- **Arkusz i druk:** formaty A0–A6 lub własny, orientacja, marginesy, przesuwanie arkusza myszą,
  druk na drukarce lub do PDF (białe tło) albo w kolorystyce ekranowej.
- **Obraz:** kopiowanie całego przekroju do schowka, zapis PNG / JPEG / TIFF.
- **Eksport:** DXF, DWG, DGN (MicroStation v7), SHP, GPKG, KML
  - w układzie **lokalnym** – rysunek 1:1 z ekranu (początek wykresu = 0,0), osie, siatka, opisy,
    ramka arkusza – każdy element na osobnej warstwie,
  - w układzie **georeferencyjnym** (EPSG 4326 / 2176–2180) – linia przekroju jako polilinia 3D
    z opisami wierzchołków (w DWG zapisanym bez ODA File Converter – jako ciąg odcinków 3D).
- **AutoCAD:** DXF i DWG otwierają się w każdym współczesnym AutoCAD-zie (także ZWCAD, BricsCAD).
  Opisy są tekstami (TEXT, Arial). Do SHP i GPKG dołączany jest styl etykiet dla QGIS.

Obsługa DWG jest wbudowana (konwerter **LibreDWG**). Jeśli na komputerze jest zainstalowany darmowy
[ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter), program użyje go
automatycznie (zapis DWG w formacie AutoCAD 2018), ale nie jest on wymagany.

## Pobieranie i instalacja

Gotowe pliki są w zakładce **[Releases](../../releases/latest)**:

| Plik | Opis |
|---|---|
| `SyropWykreslny_<wersja>_instalator.exe` | Instalator (menu Start, skrót na pulpicie, deinstalacja). **Nie wymaga uprawnień administratora.** |
| `SyropWykreslny_<wersja>_przenosny.zip` | Wersja bez instalacji – rozpakuj cały folder (np. na pendrive) i uruchom `SyropWykreslny.exe`. |

Wymagania: Windows 10 lub 11, 64-bit. Nie trzeba instalować Pythona, QGIS ani innych programów.

> Program nie ma podpisu cyfrowego, więc przy pierwszym uruchomieniu Windows może pokazać okno
> „System Windows ochronił ten komputer”. Kliknij **Więcej informacji → Uruchom mimo to**.

## Jak używać

1. Uruchom program i wskaż plik z linią (albo przeciągnij go na okno). Plik można też podać
   w wierszu polecenia: `SyropWykreslny.exe sciezka\do\linii.kml`.
2. Wybierz linię (lub „wszystkie linie jako jeden przekrój”) i sprawdź układ współrzędnych.
3. Kliknij **Rysuj przekrój**. W oknie przekroju ustaw skale, jednostki i opis.
4. Użyj **Kopiuj jako obraz**, **Zapisz obraz…**, **Drukuj…** albo **Eksportuj…**.
   Przycisk **Nowy przekrój…** otwiera kolejny plik w nowym oknie.

Dziennik błędów: `%LOCALAPPDATA%\SyropWykreslny\syrop_wykreslny.log`.

## Wersja dla QGIS

W folderze [`qgis/`](qgis/) jest pierwotny skrypt dla **QGIS 4.x** (działa też w 3.x).
Uruchomienie: *Wtyczki → Konsola Pythona → Pokaż edytor → Otwórz skrypt… → Uruchom skrypt*.
Po pierwszym uruchomieniu na pasku narzędzi pojawia się ikona buteleczki.
W tej wersji zapis i odczyt nowych plików DWG wymaga programu ODA File Converter.

## Budowanie ze źródeł

Potrzebny jest tylko Windows 10/11 z dostępem do internetu – Python i narzędzia pobierają się same
do `%LOCALAPPDATA%\SyropWykreslny-build` (nic nie jest instalowane w systemie).

1. Pobierz repozytorium (**Code → Download ZIP** albo `git clone`).
2. Uruchom **`BUDUJ.bat`**.
3. Po kilku minutach w folderze `wynik\` pojawią się: instalator, wersja przenośna ZIP,
   pełna paczka oraz raporty z automatycznych testów (`test_programu*.txt`).

Skrypt budowania (`build/build.ps1`) pobiera: Python 3.12 (przez [uv](https://github.com/astral-sh/uv)),
PyQt6, GDAL, ezdxf, GeographicLib, PyInstaller, LibreDWG i Inno Setup, uruchamia testy programu
(także w folderze z polskimi znakami w ścieżce), buduje exe, instalator i paczki.

Uruchomienie bez budowania (z zainstalowanymi pakietami):
```
pip install PyQt6 gdal ezdxf geographiclib
python src/syrop_wykreslny.py
```

## Struktura repozytorium

```
src/syrop_wykreslny.py      program (Python, PyQt6 + GDAL)
qgis/                       wersja skryptu dla QGIS
build/                      skrypt budowania, instalator (Inno Setup), ikona, opis wersji
BUDUJ.bat                   uruchamia budowanie
licenses/                   teksty licencji komponentów (LGPL, Apache)
THIRD_PARTY_LICENSES.md     lista użytych komponentów i ich licencji
LICENSE                     licencja programu (GNU GPL v3)
```

## Licencja

Copyright © 2026 Michał Maciąg

Program jest wolnym oprogramowaniem na licencji **GNU General Public License w wersji 3 lub
późniejszej** ([`LICENSE`](LICENSE)). Możesz go używać (także komercyjnie), kopiować, zmieniać
i rozpowszechniać, pod warunkiem że dalsze wersje również będą na licencji GPL i razem z nimi
udostępnisz kod źródłowy. Program jest dostarczany **bez jakiejkolwiek gwarancji**.

Licencja GPL wynika z użytych komponentów – PyQt6 i LibreDWG są dostępne na licencji GPL-3.0.
Listę wszystkich komponentów i ich licencji zawiera
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
