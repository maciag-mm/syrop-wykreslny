# Komponenty zewnętrzne / Third-party components

**Syrop Wykreślny** © 2026 Michał Maciąg jest rozpowszechniany na licencji
**GNU General Public License v3.0 lub późniejszej** (`GPL-3.0-or-later`, plik [`LICENSE`](LICENSE)).

*Syrop Wykreślny © 2026 Michał Maciąg is distributed under the **GNU General Public License
v3.0 or later** (`GPL-3.0-or-later`, see [`LICENSE`](LICENSE)).*

Program w wersji dla Windows (instalator i wersja bez instalacji) zawiera poniższe komponenty.
Ich teksty licencji są dołączone do programu w folderze `licencje` (w tym licencje pakietów
Pythona w `licencje\python\…`). Wszystkie licencje są zgodne z GPL-3.0.

*The Windows build (installer and portable version) bundles the components below. Their license
texts ship with the program in the `licencje` folder (Python package licenses in
`licencje\python\…`). All of them are compatible with GPL-3.0.*

| Komponent / Component | Licencja / License | Rola w programie / Role | Źródło / Source |
|---|---|---|---|
| **PyQt6** (Riverbank Computing) | GPL-3.0 (lub komercyjna / or commercial) | interfejs graficzny / GUI bindings | https://www.riverbankcomputing.com/software/pyqt/ · https://pypi.org/project/PyQt6/#files |
| **Qt 6** (The Qt Company), pakiet `PyQt6-Qt6` | LGPL-3.0 | biblioteki GUI / GUI libraries (DLL) | https://download.qt.io/official_releases/qt/ |
| PyQt6-sip | BSD-2-Clause | moduł pomocniczy PyQt6 / PyQt6 support | https://pypi.org/project/PyQt6-sip/ |
| **GDAL / OGR** (pakiet `gdal`, kompilacja Ch. Gohlke) | MIT | odczyt i zapis SHP, GPKG, KML, DXF, DGN | https://gdal.org · https://github.com/cgohlke/geospatial-wheels |
| PROJ (w pakiecie GDAL / bundled with GDAL) | MIT | transformacje układów współrzędnych / CRS transformations | https://proj.org |
| GEOS (w pakiecie GDAL / bundled with GDAL) | LGPL-2.1 | geometria / geometry engine | https://libgeos.org |
| Inne biblioteki w pakiecie GDAL (SQLite, libkml, expat, zlib, libcurl, OpenSSL, HDF5, netCDF i in.) / other libraries bundled with GDAL | licencje liberalne (public domain, BSD, MIT, zlib, curl, Apache-2.0) / permissive | zależności GDAL / GDAL dependencies | https://github.com/cgohlke/geospatial-wheels |
| **LibreDWG** 0.14 (GNU project) | GPL-3.0-or-later | konwersja DWG ⇄ DXF (programy `dwg2dxf.exe`, `dxf2dwg.exe`) | https://www.gnu.org/software/libredwg/ · https://github.com/LibreDWG/libredwg/releases/tag/0.14 |
| libiconv (z LibreDWG / bundled with LibreDWG) | LGPL-2.1 | konwersja kodowania znaków / character encoding | https://www.gnu.org/software/libiconv/ |
| PCRE2 (z LibreDWG / bundled with LibreDWG) | BSD-3-Clause (z wyjątkiem / with exception) | wyrażenia regularne / regular expressions | https://github.com/PCRE2Project/pcre2 |
| ezdxf | MIT | zapis DXF 2000 dla konwersji do DWG / DXF 2000 writer | https://github.com/mozman/ezdxf |
| NumPy (z OpenBLAS) | BSD-3-Clause | zależność ezdxf / ezdxf dependency | https://numpy.org |
| fontTools | MIT | zależność ezdxf / ezdxf dependency | https://github.com/fonttools/fonttools |
| pyparsing | MIT | zależność ezdxf / ezdxf dependency | https://github.com/pyparsing/pyparsing |
| typing_extensions | PSF-2.0 | zależność ezdxf / ezdxf dependency | https://github.com/python/typing_extensions |
| GeographicLib (Python) | MIT | długości geodezyjne na elipsoidzie WGS 84 / geodesic distances | https://geographiclib.sourceforge.io |
| Python 3.12 | PSF-2.0 | środowisko uruchomieniowe / runtime | https://www.python.org |
| PyInstaller (bootloader) | GPL-2.0-or-later z wyjątkiem dla bootloadera / with bootloader exception | uruchamianie spakowanego programu / frozen app launcher | https://pyinstaller.org |
| Microsoft Visual C++ Runtime (`VCRUNTIME140*.dll`, `MSVCP140*.dll`) | licencja redystrybucyjna Microsoft / Microsoft redistributable | biblioteki systemowe / runtime DLLs | https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files |

Narzędzia używane **tylko do budowania** (nie są dołączane do programu) / **build-only** tools
(not shipped): uv, Inno Setup (instalator / installer), Pillow.

## Program opcjonalny / Optional program

**ODA File Converter** (Open Design Alliance) **nie jest** dołączany do programu. Jeśli użytkownik
sam go zainstalował, Syrop Wykreślny uruchamia go jako osobny program do konwersji DWG.

*The **ODA File Converter** (Open Design Alliance) is **not** distributed with this program. If the
user installed it separately, Syrop Wykreślny runs it as a separate program for DWG conversion.*

## Kod źródłowy komponentów GPL / Source code of GPL components

Zgodnie z GPL kod źródłowy komponentów na licencji GPL rozpowszechnianych w postaci binarnej
jest dostępny: kod programu – w tym repozytorium; LibreDWG 0.14 i PyQt6 6.11.0 – pod adresami
podanymi w tabeli, a ich archiwa źródłowe są także dołączane do każdego wydania (Release)
tego projektu na GitHubie.

*As required by the GPL, the source code of GPL-licensed components distributed in binary form is
available: the program's own code in this repository; LibreDWG 0.14 and PyQt6 6.11.0 at the
addresses in the table above, and their source archives are also attached to every GitHub
Release of this project.*

Biblioteki Qt są dołączone jako oddzielne pliki DLL (`_internal\PyQt6\Qt6\bin`) i mogą zostać
zastąpione przez użytkownika innymi, zgodnymi wersjami (wymóg LGPL-3.0).

*Qt libraries are shipped as separate DLL files (`_internal\PyQt6\Qt6\bin`) and can be replaced
by the user with other compatible versions (LGPL-3.0 requirement).*
