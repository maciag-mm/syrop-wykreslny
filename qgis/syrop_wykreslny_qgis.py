# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Michał Maciąg
"""
===============================================================================
 SYROP WYKREŚLNY  –  przekroje (profile) z trójwymiarowych linii
===============================================================================
 Skrypt Pythona dla QGIS 4.2 (Qt6 / PyQt6); działa również w QGIS 3.x (Qt5).

 Uruchomienie:
   QGIS → Wtyczki → Konsola Pythona → „Pokaż edytor” → „Otwórz skrypt…”
   → wskaż syrop_wykreslny.py → „Uruchom skrypt”.
   Po pierwszym uruchomieniu na pasku narzędzi wtyczek pojawia się ikona
   „Syrop Wykreślny” (buteleczka) – do ponownego otwierania okna w tej sesji.

 Wejście:  linia / multilinia 3D (Z = wysokość) z pliku KML, DXF, DWG, SHP, GPKG
           w układzie EPSG 4326, 2176, 2177, 2178, 2179 lub 2180.
 Wyjście:  obraz (schowek / PNG) oraz KML, DXF, DWG, SHP, GPKG
           w EPSG 4326, 2176–2180 lub w układzie lokalnym (0,0 = początek wykresu).

 DWG: GDAL/QGIS nie zapisuje DWG, a odczytuje go tylko częściowo. Do obsługi
 DWG skrypt używa darmowego programu „ODA File Converter”
 (https://www.opendesign.com/guestfiles/oda_file_converter) – wykrywa go
 automatycznie lub pyta o ścieżkę (zapamiętywaną w ustawieniach QGIS).

 Autor: Michał Maciąg
===============================================================================
"""

import contextlib
import glob
import math
import os
import shutil
import subprocess
import tempfile
import traceback

from qgis.PyQt.QtCore import Qt, QByteArray, QLineF, QMarginsF, QPointF, QRectF, QSettings, QSize, QSizeF
from qgis.PyQt.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QGuiApplication, QIcon, QIntValidator,
                             QImage, QPageLayout, QPageSize, QPainter, QPen, QPixmap, QPolygonF)
from qgis.PyQt.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                                 QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
                                 QLabel, QLineEdit, QMenu,
                                 QMessageBox, QPushButton, QScrollArea, QToolTip,
                                 QVBoxLayout, QWidget)
try:  # Qt6: QAction w QtGui, Qt5: w QtWidgets
    from qgis.PyQt.QtGui import QAction
except ImportError:  # pragma: no cover
    from qgis.PyQt.QtWidgets import QAction
try:
    from qgis.PyQt.QtPrintSupport import QPrintDialog, QPrinter
except ImportError:  # pragma: no cover
    QPrinter = QPrintDialog = None
try:
    from qgis.PyQt.QtSvg import QSvgRenderer
except ImportError:  # pragma: no cover
    QSvgRenderer = None

from qgis.core import (Qgis, QgsMessageLog, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsDistanceArea,
                       QgsPointXY, QgsProject)
try:
    from qgis.utils import iface
except ImportError:  # pragma: no cover
    iface = None

from osgeo import ogr, osr

SCRIPT_NAME = "Syrop Wykreślny"
SCRIPT_VERSION = "1.05"
SETTINGS = "SyropWykreslny/"
ACTION_NAME = "SyropWykreslnyAction"

# ---------------------------------------------------------------------------
#  Ikona (buteleczka syropu z wykresem na etykiecie) – wbudowana w skrypt
# ---------------------------------------------------------------------------
ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
<defs>
<linearGradient id="glass" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5a2204"/>
<stop offset="0.3" stop-color="#b8560b"/><stop offset="0.55" stop-color="#d8741a"/><stop offset="1" stop-color="#4d1c03"/></linearGradient>
<linearGradient id="cap" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8c1414"/>
<stop offset="0.45" stop-color="#e03a2f"/><stop offset="1" stop-color="#7a1010"/></linearGradient>
<linearGradient id="label" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fffdf5"/><stop offset="1" stop-color="#f1e6c8"/></linearGradient>
</defs>
<rect x="22" y="2.5" width="20" height="10" rx="2.2" fill="url(#cap)" stroke="#5c0b0b" stroke-width="1"/>
<g stroke="#6d0f0f" stroke-width="0.9" opacity="0.8"><line x1="25.5" y1="4" x2="25.5" y2="11"/><line x1="29" y1="4" x2="29" y2="11"/>
<line x1="32.5" y1="4" x2="32.5" y2="11"/><line x1="36" y1="4" x2="36" y2="11"/><line x1="39" y1="4" x2="39" y2="11"/></g>
<rect x="24.5" y="12" width="15" height="6" fill="url(#glass)" stroke="#3a1502" stroke-width="1"/>
<path d="M24.5 18 H39.5 C39.5 22.5 51 22 51 30 V57 Q51 61.5 46.5 61.5 H17.5 Q13 61.5 13 57 V30 C13 22 24.5 22.5 24.5 18 Z" fill="url(#glass)" stroke="#3a1502" stroke-width="1.2"/>
<path d="M16.5 30 C16.5 26 20 24.5 22.5 23.5 C19.5 26 18.8 28 18.8 31 V55 Q18.8 57.5 17.6 57.5 Q16.5 57.5 16.5 55 Z" fill="#ffffff" opacity="0.32"/>
<rect x="17" y="31" width="30" height="24" rx="2" fill="url(#label)" stroke="#b89a5a" stroke-width="0.9"/>
<g stroke="#9cc3e6" stroke-width="0.45"><line x1="21" y1="36" x2="45" y2="36"/><line x1="21" y1="41" x2="45" y2="41"/><line x1="21" y1="46" x2="45" y2="46"/>
<line x1="26" y1="33" x2="26" y2="51"/><line x1="31" y1="33" x2="31" y2="51"/><line x1="36" y1="33" x2="36" y2="51"/><line x1="41" y1="33" x2="41" y2="51"/></g>
<path d="M21 33 V51 H45" fill="none" stroke="#1d2b4f" stroke-width="1.2" stroke-linejoin="round"/>
<path d="M21 48 L25.5 42.5 L29.5 45 L34 36.5 L38.5 40.5 L44 34.5 V51 H21 Z" fill="#d6282b" opacity="0.18"/>
<polyline points="21,48 25.5,42.5 29.5,45 34,36.5 38.5,40.5 44,34.5" fill="none" stroke="#d6282b" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"/>
<path d="M53.5 8 C55.5 11.5 57 13.3 57 15.3 A3.5 3.5 0 0 1 50 15.3 C50 13.3 51.5 11.5 53.5 8 Z" fill="#c9600f" stroke="#5a2204" stroke-width="0.8"/>
</svg>"""


def syrop_icon():
    """Zwraca QIcon zbudowaną z wbudowanego SVG."""
    icon = QIcon()
    data = QByteArray(ICON_SVG.encode("utf-8"))
    if QSvgRenderer is not None:
        rnd = QSvgRenderer(data)
        for s in (16, 24, 32, 48, 64, 128):
            img = QImage(s, s, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            rnd.render(p)
            p.end()
            icon.addPixmap(QPixmap.fromImage(img))
    else:
        pm = QPixmap()
        pm.loadFromData(data, "SVG")
        icon.addPixmap(pm)
    return icon


# ---------------------------------------------------------------------------
#  Stałe
# ---------------------------------------------------------------------------
LOCAL = 0  # „kod EPSG” układu lokalnego
UNITS = [("mm", 1000.0), ("cm", 100.0), ("m", 1.0), ("km", 0.001)]
UNIT_F = dict(UNITS)
EPSG_CHOICES = [
    (4326, "EPSG:4326 – WGS 84 (współrzędne geograficzne)"),
    (2176, "EPSG:2176 – PL-2000 strefa 5 (15°E)"),
    (2177, "EPSG:2177 – PL-2000 strefa 6 (18°E)"),
    (2178, "EPSG:2178 – PL-2000 strefa 7 (21°E)"),
    (2179, "EPSG:2179 – PL-2000 strefa 8 (24°E)"),
    (2180, "EPSG:2180 – PL-1992"),
]
LOCAL_LABEL = "Układ lokalny – początek wykresu (0,0)"

# Mianowniki skal dostępne na suwakach
SCALES = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000,
          10000, 20000, 25000, 50000, 100000, 200000, 250000, 500000]

OUT_FORMATS = [("DXF", "AutoCAD DXF (*.dxf)"), ("DWG", "AutoCAD DWG (*.dwg)"),
               ("DGN", "MicroStation DGN v7 (*.dgn)"),
               ("GPKG", "GeoPackage (*.gpkg)"), ("SHP", "ESRI Shapefile (*.shp)"),
               ("KML", "Google KML (*.kml)")]

NAVY = QColor(10, 22, 51)
GRID_1 = QColor(150, 150, 150, 60)     # siatka 1 mm – szara
GRID_5 = QColor(165, 165, 165, 110)    # siatka 5 mm
GRID_10 = QColor(190, 190, 190, 175)   # siatka 10 mm
AXIS = QColor(255, 255, 255)
TEXT = QColor(255, 255, 255)
PROFILE = QColor(255, 255, 255)

THEMES = {
    # ekran: granatowe tło, szara siatka, biały rysunek
    "screen": dict(bg=NAVY, g1=GRID_1, g5=GRID_5, g10=GRID_10, axis=AXIS, text=TEXT, profile=PROFILE,
                   fill=QColor(255, 255, 255, 38), vtx_out=NAVY, sep=QColor(190, 190, 190, 120)),
    # wydruk: białe tło, szara siatka, czarny rysunek
    "paper": dict(bg=QColor(255, 255, 255), g1=QColor(160, 160, 160, 110), g5=QColor(125, 125, 125, 160),
                  g10=QColor(85, 85, 85, 210), axis=QColor(0, 0, 0), text=QColor(0, 0, 0),
                  profile=QColor(0, 0, 0), fill=QColor(0, 0, 0, 22), vtx_out=QColor(255, 255, 255),
                  sep=QColor(0, 0, 0, 120)),
}
SHEET_RED = QColor(240, 55, 55)
MARGIN_GREEN = QColor(40, 205, 90)

# formaty ISO 216 (krótszy × dłuższy bok, mm)
PAPER = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420),
         "A4": (210, 297), "A5": (148, 210), "A6": (105, 148)}
CUSTOM = "Własny"

# elementy rysunku do eksportu: klucz, opis, domyślnie
EXPORT_ELEMENTS = [("wykres", "Wykres (linia profilu i wierzchołki)", True),
                   ("tytul", "Tytuł", True),
                   ("skale", "Skale", True),
                   ("dane", "Dane liczbowe (wartości na osiach, długość, wysokości)", True),
                   ("etykiety", "Etykiety osi", True),
                   ("osie", "Osie z podziałką", True),
                   ("siatka", "Siatka milimetrowa", True),
                   ("arkusz", "Granice arkusza i marginesy", False)]

MAX_IMAGE_PIXELS = 80_000_000  # ok. 320 MB w pamięci
MAX_IMAGE_SIDE = 30000


# ---------------------------------------------------------------------------
#  Funkcje pomocnicze (czysty Python)
# ---------------------------------------------------------------------------
def decimals_for(step):
    """Liczba miejsc po przecinku potrzebna do opisania wielokrotności kroku."""
    for dec in range(0, 9):
        v = step * 10 ** dec
        if abs(v - round(v)) < 1e-6 * max(1.0, abs(v)):
            return dec
    return 8


def unit_dec(factor):
    """Miejsca po przecinku dla wartości podanej w metrach z dokładnością 1 cm."""
    return max(0, 2 + int(round(-math.log10(factor))))


def fnum(v, dec=2):
    """Liczba w zapisie polskim (przecinek dziesiętny)."""
    s = f"{v:.{dec}f}"
    if s.startswith("-") and float(s) == 0:
        s = s[1:]
    return s.replace(".", ",")


def fden(den):
    """Mianownik skali z odstępami tysięcy (np. 25 000)."""
    return f"{int(den):,}".replace(",", " ")


def nice_first(values, need):
    for v in values:
        if v >= need:
            return v
    return values[-1]


class Layout:
    """
    Geometria arkusza przekroju w milimetrach „papieru”.
    Początek (0,0) = lewy dolny róg siatki = (odległość 0, wysokość h0).
    Linie główne siatki co 10 mm, pośrednie co 5 mm, drobne co 1 mm.
    """

    def __init__(self, length, hmin, hmax, hs, vs, uh="m", uv="m"):
        self.hs, self.vs = int(hs), int(vs)
        self.uh, self.uv = uh, uv
        self.fh, self.fv = UNIT_F[uh], UNIT_F[uv]
        self.mh = hs / 1000.0          # metrów odległości na 1 mm papieru
        self.mv = vs / 1000.0          # metrów wysokości na 1 mm papieru
        self.step_h = 10 * self.mh     # wartość jednej kratki 10 mm (poziomo)
        self.step_v = 10 * self.mv     # wartość jednej kratki 10 mm (pionowo)
        n = max(1, int(math.ceil(length / self.step_h - 1e-9)))
        self.w_mm = 10 * n
        self.d_end = n * self.step_h
        lo = int(math.floor(hmin / self.step_v + 1e-9))
        if hmin - lo * self.step_v < 0.25 * self.step_v:
            lo -= 1
        hi = int(math.ceil(hmax / self.step_v - 1e-9))
        if hi * self.step_v - hmax < 0.25 * self.step_v:
            hi += 1
        self.lo_idx = lo
        self.h0 = lo * self.step_v
        self.h_top = hi * self.step_v
        self.h_mm = 10 * (hi - lo)
        self.exag = hs / float(vs)     # przewyższenie
        self.dec_h = decimals_for(self.step_h * self.fh)
        self.dec_v = decimals_for(self.step_v * self.fv)

    def x_mm(self, d):
        return d / self.mh

    def y_mm(self, h):
        return (h - self.h0) / self.mv

    def d_at_mm(self, xmm):
        return xmm * self.mh

    def h_at_mm(self, ymm):
        return self.h0 + ymm * self.mv

    def h_label(self, i10):
        """Opis i-tej (co 10 mm) linii poziomej osi odległości."""
        return fnum(i10 * self.step_h * self.fh, self.dec_h)

    def v_label(self, j10):
        return fnum((self.lo_idx + j10) * self.step_v * self.fv, self.dec_v)

    def fd(self, d_m):
        """Odległość [m] → tekst w jednostkach osi poziomej."""
        return f"{fnum(d_m * self.fh, unit_dec(self.fh))} {self.uh}"

    def fh_(self, h_m):
        """Wysokość [m] → tekst w jednostkach osi pionowej."""
        return f"{fnum(h_m * self.fv, unit_dec(self.fv))} {self.uv}"


def label_every(space_per_major, text_size, pad):
    for n in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000):
        if n * space_per_major >= text_size + pad:
            return n
    return 10000


# ---------------------------------------------------------------------------
#  Zapis DXF (AutoCAD R12 / AC1009 – otwierany przez każdy współczesny AutoCAD)
# ---------------------------------------------------------------------------
def text_width(s, h):
    """Przybliżona szerokość napisu czcionką Arial o wysokości wersalików h."""
    w = 0.0
    for ch in s:
        if ch == " ":
            w += 0.39
        elif ch in ".,:;|!il'`ıjfrt()[]-":
            w += 0.42
        elif ch.isdigit():
            w += 0.78
        elif ch.isupper() or ch in "mwMW×":
            w += 0.95
        else:
            w += 0.72
    return w * h


def text_baseline_point(x, y, h, w, halign, valign, rot):
    """Punkt lewej linii bazowej napisu wyrównanego względem (x, y)."""
    dxl = {0: 0.0, 1: -w / 2.0, 2: -w}.get(halign, 0.0)
    dyl = {0: 0.0, 1: 0.25 * h, 2: -h / 2.0, 3: -h}.get(valign, 0.0)
    a = math.radians(rot or 0.0)
    return (x + dxl * math.cos(a) - dyl * math.sin(a), y + dxl * math.sin(a) + dyl * math.cos(a))


def cad_text(s):
    """Tekst dla AutoCAD-a: „%” zabezpieczony (%%%), znaki spoza ASCII jako \\U+XXXX."""
    out = []
    for ch in s:
        if ch == "%":
            out.append("%%%")
        elif ord(ch) < 128:
            out.append(ch)
        elif ord(ch) <= 0xFFFF:
            out.append("\\U+%04X" % ord(ch))
        else:
            out.append("?")
    return "".join(out)


class DxfR12:
    """Minimalny, poprawny zapis DXF R12 (LINE, POINT, TEXT, POLYLINE 2D/3D)."""

    def __init__(self):
        self.layers = {"0": 7}
        self.ents = []
        self.items = []  # uproszczona lista: ("L", warstwa, współrzędne) / ("T", warstwa, …)
        self.minx = self.miny = self.minz = float("inf")
        self.maxx = self.maxy = self.maxz = float("-inf")

    # -- pomocnicze
    @staticmethod
    def _f(v):
        s = f"{v:.6f}".rstrip("0").rstrip(".")
        return "0" if s in ("", "-0") else s

    def _ext(self, x, y, z=0.0):
        self.minx, self.miny, self.minz = min(self.minx, x), min(self.miny, y), min(self.minz, z)
        self.maxx, self.maxy, self.maxz = max(self.maxx, x), max(self.maxy, y), max(self.maxz, z)

    def _add(self, *pairs):
        self.ents.extend(pairs)

    def layer(self, name, color=7):
        self.layers[name] = int(color)

    # -- encje
    def line(self, x1, y1, x2, y2, layer, z1=0.0, z2=0.0):
        self._ext(x1, y1, z1)
        self._ext(x2, y2, z2)
        self._add((0, "LINE"), (8, layer), (10, x1), (20, y1), (30, z1), (11, x2), (21, y2), (31, z2))
        self.items.append(("L", layer, (x1, y1, z1, x2, y2, z2)))

    def point(self, x, y, z, layer):
        self._ext(x, y, z)
        self._add((0, "POINT"), (8, layer), (10, x), (20, y), (30, z))
        self.items.append(("O", layer, (x, y, z)))

    def polyline(self, pts, layer, three_d=False):
        if len(pts) < 2:
            return
        self._add((0, "POLYLINE"), (8, layer), (66, 1), (10, 0.0), (20, 0.0), (30, 0.0),
                  (70, 8 if three_d else 0))
        for p in pts:
            x, y = p[0], p[1]
            z = p[2] if three_d else 0.0
            self._ext(x, y, z)
            self._add((0, "VERTEX"), (8, layer), (10, x), (20, y), (30, z), (70, 32 if three_d else 0))
        self._add((0, "SEQEND"), (8, layer))
        self.items.append(("P", layer, [(p[0], p[1], p[2] if three_d else 0.0) for p in pts]))

    def text(self, x, y, h, s, layer, halign=0, valign=0, rot=0.0, z=0.0):
        """
        halign: 0 lewo, 1 środek, 2 prawo; valign: 0 linia bazowa, 1 dół, 2 środek, 3 góra.
        (x, y) = punkt wyrównania. Grupa 10/20 dostaje obliczony punkt lewej linii bazowej,
        więc napis stoi poprawnie także w programach, które ignorują wyrównanie.
        """
        w = text_width(s, h)
        bx, by = text_baseline_point(x, y, h, w, halign, valign, rot)
        a = math.radians(rot or 0.0)
        for px, py in ((bx, by), (bx + w * math.cos(a), by + w * math.sin(a)),
                       (bx - h * math.sin(a), by + h * math.cos(a))):
            self._ext(px, py, z)
        pairs = [(0, "TEXT"), (8, layer), (10, bx), (20, by), (30, z), (40, h), (1, cad_text(s))]
        if rot:
            pairs.append((50, rot))
        pairs.append((7, "STANDARD"))
        if halign or valign:
            pairs += [(72, halign), (11, x), (21, y), (31, z), (73, valign)]
        self._add(*pairs)
        self.items.append(("T", layer, (x, y, z, h, s, rot, halign, valign, bx, by, w)))

    def rect(self, x0, y0, x1, y1, layer):
        for a, b, c, d in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
            self.line(a, b, c, d, layer)

    # -- zapis
    def _pairs(self):
        if self.minx == float("inf"):
            self.minx = self.miny = self.minz = self.maxx = self.maxy = self.maxz = 0.0
        out = [(0, "SECTION"), (2, "HEADER"),
               (9, "$ACADVER"), (1, "AC1009"),
               (9, "$DWGCODEPAGE"), (3, "ANSI_1252"),
               (9, "$INSBASE"), (10, 0.0), (20, 0.0), (30, 0.0),
               (9, "$EXTMIN"), (10, self.minx), (20, self.miny), (30, self.minz),
               (9, "$EXTMAX"), (10, self.maxx), (20, self.maxy), (30, self.maxz),
               (9, "$LIMMIN"), (10, self.minx), (20, self.miny),
               (9, "$LIMMAX"), (10, self.maxx), (20, self.maxy),
               (9, "$TEXTSTYLE"), (7, "STANDARD"),
               (9, "$CLAYER"), (8, "0"),
               (0, "ENDSEC"),
               (0, "SECTION"), (2, "TABLES"),
               (0, "TABLE"), (2, "LTYPE"), (70, 1),
               (0, "LTYPE"), (2, "CONTINUOUS"), (70, 0), (3, "Solid line"), (72, 65), (73, 0), (40, 0.0),
               (0, "ENDTAB"),
               (0, "TABLE"), (2, "LAYER"), (70, len(self.layers))]
        for name, col in self.layers.items():
            out += [(0, "LAYER"), (2, name), (70, 0), (62, col), (6, "CONTINUOUS")]
        out += [(0, "ENDTAB"),
                (0, "TABLE"), (2, "STYLE"), (70, 1),
                (0, "STYLE"), (2, "STANDARD"), (70, 0), (40, 0.0), (41, 1.0), (50, 0.0), (71, 0),
                (42, 2.5), (3, "arial.ttf"), (4, ""),
                (0, "ENDTAB"),
                (0, "ENDSEC"),
                (0, "SECTION"), (2, "ENTITIES")]
        out += self.ents
        out += [(0, "ENDSEC"), (0, "EOF")]
        return out

    def save(self, path):
        lines = []
        for code, val in self._pairs():
            if 10 <= code <= 59 and not isinstance(val, str):
                val = self._f(float(val))
            lines.append(f"{code:>3}")
            lines.append(str(val))
        with open(path, "w", encoding="ascii", errors="replace", newline="\r\n") as fh:
            fh.write("\n".join(lines) + "\n")


def build_local_dxf(profile_parts, layout, header, show_vertices=True, el=None, frames=None):
    """
    Rysunek przekroju w układzie lokalnym:
      X = odległość [m], Y = (H − h0) × przewyższenie [m] → rysunek wydrukowany
      w skali 1:(skala pozioma) odpowiada 1:1 arkuszowi na ekranie.
    profile_parts: lista części, każda to lista (d, h).
    el: zbiór eksportowanych elementów (klucze z EXPORT_ELEMENTS).
    frames: [(x0, y0, x1, y1, warstwa)] – granice arkusza / marginesy w jednostkach rysunku.
    header: słownik z tekstami nagłówka: title, info, cap_h, cap_v (edytowalne przez użytkownika).
    Wszystkie opisy są encjami TEXT; żaden nie nachodzi na osie ani znaczniki podziałki.
    """
    header = header or {}
    el = set(k for k, _l, _d in EXPORT_ELEMENTS) if el is None else set(el)
    L = layout
    u = L.mh                                # jednostek rysunku na 1 mm papieru
    W, H = L.w_mm * u, L.h_mm * u
    dx = DxfR12()
    dx.layer("PRZ_SIATKA_1MM", 251)
    dx.layer("PRZ_SIATKA_5MM", 8)
    dx.layer("PRZ_SIATKA_10MM", 9)
    dx.layer("PRZ_OSIE", 7)
    dx.layer("PRZ_TYTUL", 7)
    dx.layer("PRZ_SKALE", 7)
    dx.layer("PRZ_DANE", 7)
    dx.layer("PRZ_ETYKIETY_OSI", 7)
    dx.layer("PRZ_PROFIL", 7)
    dx.layer("PRZ_WIERZCHOLKI", 7)
    dx.layer("PRZ_ARKUSZ", 1)
    dx.layer("PRZ_MARGINESY", 3)

    if "siatka" in el:
        n_lines = L.w_mm + L.h_mm
        if n_lines > 2_000_000:
            raise RuntimeError("Arkusz jest zbyt duży do eksportu siatki – zmniejsz skalę lub wyłącz siatkę.")
        step = 1 if n_lines <= 60_000 else (5 if n_lines <= 300_000 else 10)
        for i in range(0, L.w_mm + 1, step):
            lay = "PRZ_SIATKA_10MM" if i % 10 == 0 else ("PRZ_SIATKA_5MM" if i % 5 == 0 else "PRZ_SIATKA_1MM")
            dx.line(i * u, 0.0, i * u, H, lay)
        for j in range(0, L.h_mm + 1, step):
            lay = "PRZ_SIATKA_10MM" if j % 10 == 0 else ("PRZ_SIATKA_5MM" if j % 5 == 0 else "PRZ_SIATKA_1MM")
            dx.line(0.0, j * u, W, j * u, lay)

    if "osie" in el:
        dx.line(0.0, 0.0, W, 0.0, "PRZ_OSIE")
        dx.line(0.0, 0.0, 0.0, H, "PRZ_OSIE")
        for i in range(0, L.w_mm + 1, 5):
            t = 2.0 if i % 10 == 0 else 1.0
            dx.line(i * u, 0.0, i * u, -t * u, "PRZ_OSIE")
        for j in range(0, L.h_mm + 1, 5):
            t = 2.0 if j % 10 == 0 else 1.0
            dx.line(0.0, j * u, -t * u, j * u, "PRZ_OSIE")

    th = 2.5 * u                            # wysokość opisów wartości [jedn. rysunku]
    TICK = 2.0                              # długość znacznika podziałki [mm]
    GAP = 1.5                               # odstęp opisu od znacznika [mm]
    v_labels = [(k, L.v_label(k)) for k in range(0, L.h_mm // 10 + 1, label_every(10.0, 2.5, 2.0))]
    wv_max = max(text_width(t, 2.5) for _k, t in v_labels) if v_labels else 0.0   # [mm]
    if "dane" in el:
        wh_max = max(text_width(L.h_label(0), 2.5), text_width(L.h_label(L.w_mm // 10), 2.5))
        nh = label_every(10.0, wh_max, 2.5)
        for k in range(0, L.w_mm // 10 + 1, nh):
            # góra napisu poniżej znacznika podziałki
            dx.text(k * 10 * u, -(TICK + GAP) * u, th, L.h_label(k), "PRZ_DANE", halign=1, valign=3)
        for k, t in v_labels:
            # prawa krawędź napisu na lewo od znacznika
            dx.text(-(TICK + GAP) * u, k * 10 * u, th, t, "PRZ_DANE", halign=2, valign=2)
        info = header.get("info", "")
        if info:
            dx.text(0.0, H + 4.0 * u, 2.5 * u, info, "PRZ_DANE")

    if "etykiety" in el:
        # pod opisami wartości osi X: znacznik + odstęp + wysokość opisu + odstęp
        y_title = -(TICK + GAP + 2.5 + 3.0) * u
        dx.text(W / 2.0, y_title, 3.0 * u, f"Odległość [{L.uh}]", "PRZ_ETYKIETY_OSI", halign=1, valign=3)
        # na lewo od najszerszego opisu osi Y (tekst obrócony o 90°, linia bazowa po prawej)
        x_title = -(TICK + GAP + wv_max + 2.5) * u
        dx.text(x_title, H / 2.0, 3.0 * u, f"Wysokość [{L.uv}]", "PRZ_ETYKIETY_OSI",
                halign=1, valign=0, rot=90.0)

    title = header.get("title", "")
    if "tytul" in el and title:
        dx.text(0.0, H + 15.0 * u, 4.0 * u, title, "PRZ_TYTUL")
    if "skale" in el:
        dx.text(0.0, H + 9.0 * u, 3.0 * u,
                f"{header.get('cap_h', 'Skala pozioma')} 1:{fden(L.hs)}     "
                f"{header.get('cap_v', 'Skala pionowa')} 1:{fden(L.vs)}", "PRZ_SKALE")

    if "wykres" in el:
        for part in profile_parts:
            pts = [(d, (h - L.h0) * L.exag) for d, h in part]
            dx.polyline(pts, "PRZ_PROFIL")
            if show_vertices:
                for x, y in pts:
                    dx.point(x, y, 0.0, "PRZ_WIERZCHOLKI")

    if "arkusz" in el and frames:
        for x0, y0, x1, y1, lay in frames:
            dx.rect(x0, y0, x1, y1, lay)
    return dx


def build_geo_dxf(parts_xyz, stations, label_height, layout, el=None):
    """Przekrój w układzie georeferencyjnym: polilinie 3D + punkty 3D + opisy (TEXT)."""
    el = {"wykres", "dane"} if el is None else set(el)
    dx = DxfR12()
    dx.layer("PRZEKROJ_3D", 7)
    dx.layer("PRZEKROJ_WIERZCHOLKI", 7)
    dx.layer("PRZEKROJ_DANE", 7)
    for part, st in zip(parts_xyz, stations):
        if "wykres" in el:
            dx.polyline(part, "PRZEKROJ_3D", three_d=True)
        for (x, y, z), (d, h) in zip(part, st):
            if "wykres" in el:
                dx.point(x, y, z, "PRZEKROJ_WIERZCHOLKI")
            if "dane" in el:
                dx.text(x, y, label_height, f"{layout.fd(d)} / H={layout.fh_(h)}", "PRZEKROJ_DANE", z=z)
    return dx


# ---------------------------------------------------------------------------
#  GDAL / OGR – odczyt
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def ogr_exceptions():
    mgr = getattr(ogr, "ExceptionMgr", None)
    if mgr is not None:
        with mgr(useExceptions=True):
            yield
    else:
        yield


class LineFeature:
    def __init__(self, layer, fid, label, parts, has_z):
        self.layer, self.fid, self.label, self.parts, self.has_z = layer, fid, label, parts, has_z


def geom_parts(g):
    """Z geometrii OGR wyciąga listę części liniowych [(x, y, z), ...]."""
    if g is None:
        return []
    try:
        if g.HasCurveGeometry():
            g = g.GetLinearGeometry()
    except Exception:
        pass
    t = ogr.GT_Flatten(g.GetGeometryType())
    if t in (ogr.wkbLineString, ogr.wkbLinearRing):
        pts = [(g.GetX(i), g.GetY(i), g.GetZ(i)) for i in range(g.GetPointCount())]
        return [pts] if len(pts) >= 2 else []
    if t in (ogr.wkbMultiLineString, ogr.wkbGeometryCollection, ogr.wkbMultiCurve):
        res = []
        for i in range(g.GetGeometryCount()):
            res += geom_parts(g.GetGeometryRef(i))
        return res
    return []


def srs_to_epsg(srs):
    if srs is None:
        return None
    try:
        s = srs.Clone()
        try:
            s.AutoIdentifyEPSG()
        except Exception:
            pass
        if (s.GetAuthorityName(None) or "").upper() == "EPSG":
            return int(s.GetAuthorityCode(None))
        if hasattr(s, "FindMatches"):
            m = s.FindMatches()
            if m and m[0][1] >= 70:
                c = m[0][0]
                if (c.GetAuthorityName(None) or "").upper() == "EPSG":
                    return int(c.GetAuthorityCode(None))
    except Exception:
        pass
    return None


LABEL_FIELDS = ("Name", "name", "NAME", "nazwa", "Nazwa", "NAZWA", "opis", "Opis",
                "id", "ID", "Id", "Layer", "Text")


def scan_datasource(ds):
    feats, epsg = [], None
    for li in range(ds.GetLayerCount()):
        lyr = ds.GetLayer(li)
        lname = lyr.GetName()
        if epsg is None:
            epsg = srs_to_epsg(lyr.GetSpatialRef())
        defn = lyr.GetLayerDefn()
        fields = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
        lab_f = next((f for f in LABEL_FIELDS if f in fields), None)
        lyr.ResetReading()
        f = lyr.GetNextFeature()
        while f is not None:
            g = f.GetGeometryRef()
            parts = geom_parts(g)
            if parts:
                try:
                    has_z = bool(g.Is3D())
                except Exception:
                    has_z = g.GetCoordinateDimension() >= 3
                val = ""
                if lab_f:
                    try:
                        val = f.GetFieldAsString(lab_f) or ""
                    except Exception:
                        val = ""
                lab = f"{lname} • obiekt {f.GetFID()}" + (f" • {val}" if val else "")
                if len(parts) > 1:
                    lab += f" • {len(parts)} części"
                feats.append(LineFeature(lname, f.GetFID(), lab, parts, has_z))
            f = lyr.GetNextFeature()
    return feats, epsg


# ---------------------------------------------------------------------------
#  ODA File Converter (DWG ⇄ DXF)
# ---------------------------------------------------------------------------
def find_oda():
    s = QSettings().value(SETTINGS + "oda_path", "", type=str)
    if s and os.path.isfile(s):
        return s
    cands = []
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                     os.environ.get("ProgramW6432")):
            if base:
                cands += glob.glob(os.path.join(base, "ODA", "ODAFileConverter*", "ODAFileConverter.exe"))
    else:
        cands += glob.glob("/Applications/ODAFileConverter*.app/Contents/MacOS/ODAFileConverter")
        cands += ["/usr/bin/ODAFileConverter", "/usr/local/bin/ODAFileConverter",
                  "/opt/ODAFileConverter/ODAFileConverter"]
        cands += glob.glob("/opt/ODAFileConverter*/ODAFileConverter")
    w = shutil.which("ODAFileConverter")
    if w:
        cands.append(w)
    cands = [c for c in cands if os.path.isfile(c)]
    return sorted(cands, reverse=True)[0] if cands else None


def ask_oda(parent):
    exe = find_oda()
    if exe:
        return exe
    QMessageBox.information(
        parent, SCRIPT_NAME,
        "Do obsługi plików DWG potrzebny jest darmowy program „ODA File Converter”\n"
        "(https://www.opendesign.com/guestfiles/oda_file_converter).\n\n"
        "Nie znaleziono go automatycznie – wskaż plik ODAFileConverter(.exe).")
    flt = "ODAFileConverter (ODAFileConverter.exe)" if os.name == "nt" else "ODAFileConverter (ODAFileConverter*)"
    exe, _ = QFileDialog.getOpenFileName(parent, "Wskaż ODA File Converter", "", flt)
    if exe and os.path.isfile(exe):
        QSettings().setValue(SETTINGS + "oda_path", exe)
        return exe
    return None


def oda_convert(exe, src, out_type, out_ver="ACAD2018"):
    """Konwertuje pojedynczy plik (DXF↔DWG). Zwraca ścieżkę wyniku w katalogu tymczasowym."""
    in_dir = tempfile.mkdtemp(prefix="syrop_in_")
    out_dir = tempfile.mkdtemp(prefix="syrop_out_")
    shutil.copy2(src, in_dir)
    ext = os.path.splitext(src)[1]
    args = [exe, in_dir, out_dir, out_ver, out_type, "0", "1", "*" + ext]
    kw = {"timeout": 300, "capture_output": True}
    if os.name == "nt":
        kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    subprocess.run(args, **kw)
    base = os.path.splitext(os.path.basename(src))[0].lower()
    for fn in os.listdir(out_dir):
        b, e = os.path.splitext(fn)
        if b.lower() == base and e.lower() == "." + out_type.lower():
            return os.path.join(out_dir, fn)
    raise RuntimeError("ODA File Converter nie utworzył pliku wynikowego.\n"
                       "Sprawdź, czy program działa poprawnie (uruchom go ręcznie).")


def open_ogr(path):
    with ogr_exceptions():
        try:
            return ogr.Open(path, 0)
        except Exception:
            return None


def read_lines(path, parent):
    """Zwraca (lista LineFeature, wykryty EPSG lub None, uwaga)."""
    ext = os.path.splitext(path)[1].lower()
    note = ""
    feats, epsg = [], None
    ds = open_ogr(path)
    if ds is not None:
        with ogr_exceptions():
            try:
                feats, epsg = scan_datasource(ds)
            except Exception:
                feats, epsg = [], None
        ds = None
    if ext == ".dwg" and not feats:
        exe = ask_oda(parent)
        if not exe:
            raise RuntimeError("Bez ODA File Converter nie można odczytać tego pliku DWG.")
        dxf = oda_convert(exe, path, "DXF")
        ds = open_ogr(dxf)
        if ds is None:
            raise RuntimeError("Nie udało się odczytać DXF przekonwertowanego z DWG.")
        with ogr_exceptions():
            feats, epsg = scan_datasource(ds)
        ds = None
        note = "DWG odczytano przez ODA File Converter."
    if ext in (".kml", ".kmz"):
        epsg = 4326  # KML jest zawsze w WGS 84
    return feats, epsg, note


# ---------------------------------------------------------------------------
#  Model przekroju
# ---------------------------------------------------------------------------
class Profile:
    """parts: lista części; wierzchołek = (x, y, z, d) – x,y w układzie źródłowym, d = odległość."""

    def __init__(self, name, epsg, parts_xyz):
        self.name = name
        self.epsg = epsg
        self.crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")
        da = QgsDistanceArea()
        da.setSourceCrs(self.crs, QgsProject.instance().transformContext())
        da.setEllipsoid("WGS84" if self.crs.isGeographic() else "NONE")
        self.parts = []
        d, prev = 0.0, None
        for part in parts_xyz:
            pp = []
            for x, y, z in part:
                if z is None or (isinstance(z, float) and math.isnan(z)):
                    continue
                if prev is not None:
                    d += da.measureLine(QgsPointXY(prev[0], prev[1]), QgsPointXY(x, y))
                pp.append((x, y, float(z), d))
                prev = (x, y)
            if len(pp) >= 2:
                self.parts.append(pp)
        if not self.parts:
            raise ValueError("Linia nie zawiera co najmniej dwóch wierzchołków.")
        hs = [v[2] for p in self.parts for v in p]
        self.hmin, self.hmax = min(hs), max(hs)
        self.length = self.parts[-1][-1][3]
        self.nverts = len(hs)
        if self.length <= 0:
            raise ValueError("Długość linii przekroju wynosi 0.")

    def dh_parts(self):
        return [[(v[3], v[2]) for v in p] for p in self.parts]

    def height_at(self, d):
        for p in self.parts:
            for a, b in zip(p, p[1:]):
                if a[3] <= d <= b[3]:
                    if b[3] - a[3] < 1e-12:
                        return a[2]
                    t = (d - a[3]) / (b[3] - a[3])
                    return a[2] + t * (b[2] - a[2])
        return None


def auto_scales(prof):
    hs = nice_first(SCALES, prof.length * 1000.0 / 260.0)
    rng = max(prof.hmax - prof.hmin, 1e-3)
    vs = nice_first(SCALES, rng * 1000.0 / 90.0)
    return hs, min(vs, hs)


def screen_px_per_mm(widget):
    scr = None
    try:
        scr = widget.screen()
    except Exception:
        pass
    if scr is None:
        scr = QGuiApplication.primaryScreen()
    dpi = scr.physicalDotsPerInch() if scr is not None else 96.0
    if not 50.0 <= dpi <= 400.0:
        dpi = 96.0
    return dpi / 25.4


# ---------------------------------------------------------------------------
#  Tekst bez flag wyrównania (zgodne z każdą wersją PyQt5/PyQt6)
# ---------------------------------------------------------------------------
def text_at(p, fm, x, y, s, ha="l", va="base"):
    """ha: l/c/r, va: base/top/mid/bottom – punkt kotwiczenia (x, y)."""
    w = fm.horizontalAdvance(s)
    if ha == "c":
        x -= w / 2.0
    elif ha == "r":
        x -= w
    if va == "top":
        y += fm.ascent()
    elif va == "mid":
        y += (fm.ascent() - fm.descent()) / 2.0
    elif va == "bottom":
        y -= fm.descent()
    p.drawText(QPointF(x, y), s)


_LAST_ERR = [None]


def report_error(where):
    tb = traceback.format_exc()
    if tb != _LAST_ERR[0]:
        _LAST_ERR[0] = tb
        try:
            QgsMessageLog.logMessage(f"{where}:\n{tb}", SCRIPT_NAME, Qgis.MessageLevel.Critical)
        except Exception:
            pass
        print(f"[{SCRIPT_NAME}] {where}:\n{tb}")


# ---------------------------------------------------------------------------
#  Rysowanie ułamka skali (1 nad kreską, mianownik pod kreską)
# ---------------------------------------------------------------------------
def draw_fraction(p, x, cy, den, font, color):
    fm = QFontMetricsF(font)
    num, dens = "1", fden(den)
    w = max(fm.horizontalAdvance(num), fm.horizontalAdvance(dens)) + 8
    fh = fm.height()
    p.setFont(font)
    p.setPen(QPen(color, 1.3))
    text_at(p, fm, x + w / 2.0, cy - 2, num, "c", "bottom")
    p.drawLine(QPointF(x + 1, cy), QPointF(x + w - 1, cy))
    text_at(p, fm, x + w / 2.0, cy + 1, dens, "c", "top")
    return w


def fraction_width(den, font):
    fm = QFontMetricsF(font)
    return max(fm.horizontalAdvance("1"), fm.horizontalAdvance(fden(den))) + 8


# ---------------------------------------------------------------------------
#  Płótno przekroju – kalka milimetrowa na granatowym tle
# ---------------------------------------------------------------------------
class TooBig(Exception):
    pass


class Sheet:
    """Ustawienia arkusza (format, orientacja, marginesy) i jego położenie względem rysunku."""

    def __init__(self):
        st = QSettings()
        self.enabled = st.value(SETTINGS + "sheet_on", False, type=bool)
        self.fmt = st.value(SETTINGS + "sheet_fmt", "A3", type=str)
        if self.fmt not in PAPER and self.fmt != CUSTOM:
            self.fmt = "A3"
        self.landscape = st.value(SETTINGS + "sheet_land", True, type=bool)
        self.cw = st.value(SETTINGS + "sheet_w", 500.0, type=float)
        self.ch = st.value(SETTINGS + "sheet_h", 300.0, type=float)
        self.margins = [st.value(SETTINGS + f"sheet_m{i}", 20.0, type=float) for i in range(4)]  # l, g, p, d
        self.pos = None  # (x, y) [mm] lewego górnego rogu arkusza w układzie rysunku; None = domyślnie

    def size(self):
        if self.fmt in PAPER:
            a, b = PAPER[self.fmt]
            return (float(b), float(a)) if self.landscape else (float(a), float(b))
        return float(self.cw), float(self.ch)

    def label(self):
        w, h = self.size()
        if self.fmt in PAPER:
            return f"{self.fmt} {'poziomo' if self.landscape else 'pionowo'} ({fnum(w, 0)} × {fnum(h, 0)} mm)"
        return f"arkusz {fnum(w, 0)} × {fnum(h, 0)} mm"

    def save(self):
        st = QSettings()
        st.setValue(SETTINGS + "sheet_on", self.enabled)
        st.setValue(SETTINGS + "sheet_fmt", self.fmt)
        st.setValue(SETTINGS + "sheet_land", self.landscape)
        st.setValue(SETTINGS + "sheet_w", self.cw)
        st.setValue(SETTINGS + "sheet_h", self.ch)
        for i, m in enumerate(self.margins):
            st.setValue(SETTINGS + f"sheet_m{i}", m)


class ProfileCanvas(QWidget):
    """
    Arkusz przekroju. Współrzędne „rysunku” w pikselach przy powiększeniu 100 %;
    zoom = powiększenie widoku (nie zmienia skali), off = przesunięcie rysunku w płótnie
    (miejsce na granice arkusza wystające poza rysunek).
    """
    ML, MR, MT, MB = 92, 40, 84, 70

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.hs, self.vs = auto_scales(profile)
        self.uh = self.uv = "m"
        self.show_vertices = True
        self.hover_d = None
        self._hover_pos = None
        self.zoom = 1.0
        self._draw_zoom = 1.0
        self._cosmetic = True
        self._drag = None
        self._sheet_drag = None
        self.zoom_request = None   # funkcja(czynnik, QPointF w układzie płótna)
        self.pan_request = None    # funkcja(dx, dy)
        self.sheet_moved = None    # funkcja() – po przesunięciu arkusza
        self.header_request = None  # funkcja() – dwuklik w nagłówek
        # nagłówek: None = tekst automatyczny
        self.header = {"title": None, "info": None, "cap_h": "Skala pozioma", "cap_v": "Skala pionowa"}
        self.default_scales = auto_scales(profile)
        self.sheet = Sheet()
        self.ppm = screen_px_per_mm(self)
        self.f_small = QFont()
        self.f_small.setPixelSize(11)
        self.f_axis = QFont()
        self.f_axis.setPixelSize(12)
        self.f_axis.setBold(True)
        self.f_title = QFont()
        self.f_title.setPixelSize(15)
        self.f_title.setBold(True)
        self.f_frac = QFont()
        self.f_frac.setPixelSize(13)
        self.f_frac.setBold(True)
        self.f_hover = QFont()
        self.f_hover.setPixelSize(12)
        self.f_hover.setBold(True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._w, self._h = 100, 100
        self.offx = self.offy = 0.0
        self.tw, self.th = 100.0, 100.0
        self.relayout()

    # --- pióra: kosmetyczne na ekranie (stała grubość), zwykłe przy wydruku
    def pen(self, color, width=1.0):
        pen = QPen(color, width)
        pen.setCosmetic(self._cosmetic)
        return pen

    # --- geometria
    def relayout(self):
        self.lay = Layout(self.profile.length, self.profile.hmin, self.profile.hmax,
                          self.hs, self.vs, self.uh, self.uv)
        w = self.ML + self.lay.w_mm * self.ppm + self.MR
        h = self.MT + self.lay.h_mm * self.ppm + self.MB
        w = max(w, self.header_width() + 30)
        self._w, self._h = int(math.ceil(w)), int(math.ceil(h))
        self.update_extent()

    def content_rect(self):
        """Zasięg treści rysunku [px] (bez pustych marginesów płótna)."""
        return QRectF(10.0, 8.0, self._w - 24.0, self._h - 32.0)

    def sheet_pos(self):
        """Lewy górny róg arkusza [mm] w układzie rysunku (0,0 = lewy górny róg płótna rysunku)."""
        if self.sheet.pos is not None:
            return self.sheet.pos
        c = self.content_rect()
        ml, mt = self.sheet.margins[0], self.sheet.margins[1]
        return (c.left() / self.ppm - ml, c.top() / self.ppm - mt)

    def sheet_rect(self):
        sx, sy = self.sheet_pos()
        w, h = self.sheet.size()
        k = self.ppm
        return QRectF(sx * k, sy * k, w * k, h * k)

    def margin_rect(self):
        r = self.sheet_rect()
        ml, mt, mr, mb = [m * self.ppm for m in self.sheet.margins]
        return QRectF(r.left() + ml, r.top() + mt, max(0.0, r.width() - ml - mr), max(0.0, r.height() - mt - mb))

    def fits_sheet(self):
        m = self.margin_rect()
        c = self.content_rect()
        return (m.left() <= c.left() + 0.5 and m.top() <= c.top() + 0.5 and
                m.right() >= c.right() - 0.5 and m.bottom() >= c.bottom() - 0.5)

    def update_extent(self):
        x0, y0, x1, y1 = 0.0, 0.0, float(self._w), float(self._h)
        pad = 0.0
        if self.sheet.enabled:
            r = self.sheet_rect()
            x0, y0 = min(x0, r.left()), min(y0, r.top())
            x1, y1 = max(x1, r.right()), max(y1, r.bottom())
            pad = 30.0
        self.offx, self.offy = pad - x0, pad - y0
        self.tw, self.th = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
        self.apply_zoom()

    def max_zoom(self):
        return max(0.01, min(40.0, 16_000_000 / max(self.tw, self.th)))

    def apply_zoom(self):
        self.zoom = max(0.02, min(self.zoom, self.max_zoom()))
        self.setFixedSize(max(1, int(math.ceil(self.tw * self.zoom))),
                          max(1, int(math.ceil(self.th * self.zoom))))
        self.update()

    def set_scales(self, hs, vs):
        self.hs, self.vs = int(hs), int(vs)
        self.relayout()

    def set_units(self, uh, uv):
        self.uh, self.uv = uh, uv
        self.relayout()

    def to_drawing(self, pos):
        """Punkt widżetu → współrzędne rysunku [px przy 100 %]."""
        return pos.x() / self.zoom - self.offx, pos.y() / self.zoom - self.offy

    def ox(self):
        return float(self.ML)

    def oy(self):
        return self.MT + self.lay.h_mm * self.ppm

    def X(self, xmm):
        return self.ML + xmm * self.ppm

    def Y(self, ymm):
        return self.oy() - ymm * self.ppm

    def auto_title(self):
        return f"Przekrój: {self.profile.name}"

    def auto_info(self):
        L, pr = self.lay, self.profile
        return (f"Długość {L.fd(pr.length)}   •   Hmin {L.fh_(pr.hmin)}   •   "
                f"Hmax {L.fh_(pr.hmax)}   •   przewyższenie {fnum(L.exag, decimals_for(L.exag))}×")

    def header_texts(self):
        hd = self.header
        t1 = self.auto_title() if hd["title"] is None else hd["title"]
        t2 = self.auto_info() if hd["info"] is None else hd["info"]
        return t1, t2

    def header_export(self):
        t1, t2 = self.header_texts()
        return {"title": t1, "info": t2, "cap_h": self.header["cap_h"], "cap_v": self.header["cap_v"]}

    def set_header(self, title, info, cap_h, cap_v):
        self.header = {"title": title, "info": info, "cap_h": cap_h, "cap_v": cap_v}
        self.relayout()

    def header_width(self):
        t1, t2 = self.header_texts()
        a = max(QFontMetricsF(self.f_title).horizontalAdvance(t1), QFontMetricsF(self.f_small).horizontalAdvance(t2))
        fm = QFontMetricsF(self.f_small)
        b = (fm.horizontalAdvance(self.header["cap_h"]) + fraction_width(self.hs, self.f_frac) +
             fm.horizontalAdvance(self.header["cap_v"]) + fraction_width(self.vs, self.f_frac) + 40)
        return self.ML + a + 30 + b

    # --- rysowanie na ekranie
    def paintEvent(self, e):
        p = QPainter(self)
        try:
            z = self.zoom
            r = QRectF(e.rect())
            p.fillRect(r, NAVY)
            p.scale(z, z)
            p.translate(self.offx, self.offy)
            self._draw_zoom = z
            self._cosmetic = True
            clip = QRectF(r.left() / z - self.offx, r.top() / z - self.offy, r.width() / z, r.height() / z)
            self.draw(p, clip, "screen")
            self.draw_hover_marks(p)
            if self.sheet.enabled:
                self.draw_sheet(p)
            p.resetTransform()
            if self.sheet.enabled:
                self.draw_sheet_label(p)
            self.draw_hover_box(p)
        except Exception:
            report_error("Rysowanie przekroju")
            try:
                p.resetTransform()
                p.setPen(QColor(255, 150, 150))
                p.drawText(QPointF(20, 30), "Błąd rysowania – szczegóły: Widok › Panele › "
                                            "Komunikaty dziennika › Syrop Wykreślny")
            except Exception:
                pass
        finally:
            p.end()

    def draw(self, p, clip, theme="screen"):
        """Rysuje cały przekrój (w układzie rysunku) – ekran, obraz i wydruk."""
        T = THEMES[theme]
        L = self.lay
        ppm = self.ppm
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.fillRect(clip, T["bg"])
        ox, oy = self.ox(), self.oy()
        top = float(self.MT)
        right = self.X(L.w_mm)

        # --- siatka milimetrowa (tylko widoczny fragment, z zapasem na opisy osi)
        clip = QRectF(clip).adjusted(-90, -40, 90, 40)
        i0 = max(0, int(math.floor((clip.left() - ox) / ppm)))
        i1 = min(L.w_mm, int(math.ceil((clip.right() - ox) / ppm)))
        j0 = max(0, int(math.floor((oy - clip.bottom()) / ppm)))
        j1 = min(L.h_mm, int(math.ceil((oy - clip.top()) / ppm)))
        show1 = ppm * self._draw_zoom >= 2.2
        groups = {1: [], 5: [], 10: []}
        for i in range(i0, i1 + 1):
            k = 10 if i % 10 == 0 else (5 if i % 5 == 0 else 1)
            if k == 1 and not show1:
                continue
            x = ox + i * ppm
            groups[k].append(QLineF(x, top, x, oy))
        for j in range(j0, j1 + 1):
            k = 10 if j % 10 == 0 else (5 if j % 5 == 0 else 1)
            if k == 1 and not show1:
                continue
            y = oy - j * ppm
            groups[k].append(QLineF(ox, y, right, y))
        for k, col, wd in ((1, T["g1"], 1.0), (5, T["g5"], 1.0), (10, T["g10"], 1.3)):
            if groups[k]:
                p.setPen(self.pen(col, wd if self._cosmetic else wd * 0.5))
                for ln in groups[k]:
                    p.drawLine(ln)

        # --- profil
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for part in self.profile.dh_parts():
            pts = [QPointF(self.X(L.x_mm(d)), self.Y(L.y_mm(h))) for d, h in part]
            poly = QPolygonF(pts)
            area = QPolygonF(pts + [QPointF(pts[-1].x(), oy), QPointF(pts[0].x(), oy)])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(T["fill"]))
            p.drawPolygon(area)
            p.setBrush(Qt.BrushStyle.NoBrush)
            pen = self.pen(T["profile"], 2.4 if self._cosmetic else 1.6)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawPolyline(poly)
            if self.show_vertices:
                p.setPen(self.pen(T["vtx_out"], 1.0 if self._cosmetic else 0.6))
                p.setBrush(QBrush(T["profile"]))
                rv = 2.6 / self._draw_zoom if self._cosmetic else 2.0
                for pt in pts:
                    p.drawEllipse(pt, rv, rv)
                p.setBrush(Qt.BrushStyle.NoBrush)

        # --- osie
        p.setPen(self.pen(T["axis"], 1.6 if self._cosmetic else 1.0))
        p.drawLine(QPointF(ox, top - 4), QPointF(ox, oy))
        p.drawLine(QPointF(ox, oy), QPointF(right + 4, oy))
        p.setPen(self.pen(T["axis"], 1.2 if self._cosmetic else 0.8))
        for i in range(i0 - i0 % 5, i1 + 1, 5):
            t = 7 if i % 10 == 0 else 4
            p.drawLine(QLineF(ox + i * ppm, oy, ox + i * ppm, oy + t))
        for j in range(j0 - j0 % 5, j1 + 1, 5):
            t = 7 if j % 10 == 0 else 4
            p.drawLine(QLineF(ox, oy - j * ppm, ox - t, oy - j * ppm))

        fm = QFontMetricsF(self.f_small)
        p.setFont(self.f_small)
        p.setPen(T["text"])
        nmaj_h = L.w_mm // 10
        wmax = max(fm.horizontalAdvance(L.h_label(k)) for k in (0, nmaj_h))
        nh = label_every(10 * ppm, wmax, 10)
        k_first = max(0, (i0 // 10 - 1) // nh * nh)
        for k in range(k_first, min(nmaj_h, i1 // 10 + 1) + 1, nh):
            x = ox + k * 10 * ppm
            text_at(p, fm, x, oy + 9, L.h_label(k), "c", "top")
        nv = label_every(10 * ppm, fm.height(), 4)
        vw = max(fm.horizontalAdvance(L.v_label(0)), fm.horizontalAdvance(L.v_label(L.h_mm // 10)))
        k_first = max(0, (j0 // 10 - 1) // nv * nv)
        for k in range(k_first, min(L.h_mm // 10, j1 // 10 + 1) + 1, nv):
            y = oy - k * 10 * ppm
            text_at(p, fm, ox - 10, y, L.v_label(k), "r", "mid")

        p.setFont(self.f_axis)
        fa = QFontMetricsF(self.f_axis)
        text_at(p, fa, (ox + right) / 2.0, oy + 14 + fm.height(), f"Odległość [{L.uh}]", "c", "top")
        p.save()
        p.translate(max(14.0, ox - 16 - vw - fa.height()), (top + oy) / 2.0)
        p.rotate(-90)
        text_at(p, fa, 0.0, 0.0, f"Wysokość [{L.uv}]", "c", "top")
        p.restore()

        # --- nagłówek ze skalami w postaci ułamków
        t1, t2 = self.header_texts()
        p.setFont(self.f_title)
        p.setPen(T["text"])
        p.drawText(QPointF(ox, 26), t1)
        p.setFont(self.f_small)
        p.drawText(QPointF(ox, 46), t2)
        x = float(self._w) - 16
        cy = 38.0
        for cap, den in ((self.header["cap_v"], self.vs), (self.header["cap_h"], self.hs)):
            fw = fraction_width(den, self.f_frac)
            x -= fw
            draw_fraction(p, x, cy, den, self.f_frac, T["text"])
            p.setFont(self.f_small)
            p.setPen(T["text"])
            cw = fm.horizontalAdvance(cap)
            x -= cw + 6
            p.drawText(QPointF(x, cy + fm.ascent() / 2 - 1), cap)
            x -= 22
        p.setPen(self.pen(T["sep"], 1 if self._cosmetic else 0.5))
        p.drawLine(QPointF(ox, 62), QPointF(self._w - 16, 62))

    def draw_hover_marks(self, p):
        if self.hover_d is None:
            return
        L = self.lay
        h = self.profile.height_at(self.hover_d)
        X = self.X(L.x_mm(self.hover_d))
        pen = self.pen(QColor(255, 255, 255, 170), 1)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawLine(QPointF(X, float(self.MT)), QPointF(X, self.oy()))
        if h is not None:
            Yh = self.Y(L.y_mm(h))
            p.drawLine(QPointF(self.ox(), Yh), QPointF(self.X(L.w_mm), Yh))
            p.setPen(self.pen(NAVY, 1.5))
            p.setBrush(QBrush(QColor(255, 255, 255)))
            r = 4.5 / self.zoom
            p.drawEllipse(QPointF(X, Yh), r, r)
            p.setBrush(Qt.BrushStyle.NoBrush)

    def draw_hover_box(self, p):
        """Odczyt odległości i wysokości – białe litery na granatowym tle (współrzędne widżetu)."""
        if self.hover_d is None or self._hover_pos is None:
            return
        L = self.lay
        h = self.profile.height_at(self.hover_d)
        lines = [f"odległość: {L.fd(self.hover_d)}",
                 "wysokość: " + (L.fh_(h) if h is not None else "– (przerwa)")]
        fm = QFontMetricsF(self.f_hover)
        w = max(fm.horizontalAdvance(t) for t in lines) + 16
        hh = fm.height() * len(lines) + 10
        x, y = self._hover_pos.x() + 16, self._hover_pos.y() + 16
        if x + w > self.width() - 2:
            x = self._hover_pos.x() - 16 - w
        if y + hh > self.height() - 2:
            y = self._hover_pos.y() - 16 - hh
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(QColor(255, 255, 255), 1))
        p.setBrush(QBrush(QColor(10, 22, 51, 235)))
        p.drawRoundedRect(QRectF(x, y, w, hh), 4, 4)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setFont(self.f_hover)
        p.setPen(QPen(QColor(255, 255, 255), 1.0))
        p.setBrush(QBrush(QColor(255, 255, 255)))
        for i, t in enumerate(lines):
            p.drawText(QPointF(x + 8, y + 5 + fm.ascent() + i * fm.height()), t)

    def draw_sheet(self, p):
        r, m = self.sheet_rect(), self.margin_rect()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = self.pen(MARGIN_GREEN, 1.5)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawRect(m)
        p.setPen(self.pen(SHEET_RED, 2.0))
        p.drawRect(r)

    def draw_sheet_label(self, p):
        """Opis formatu nad ramką arkusza – w pikselach widżetu (stały rozmiar)."""
        r = self.sheet_rect()
        x = (r.left() + self.offx) * self.zoom
        y = (r.top() + self.offy) * self.zoom - 6
        f = QFont()
        f.setPixelSize(12)
        f.setBold(True)
        p.setFont(f)
        p.setPen(SHEET_RED)
        txt = self.sheet.label() + ("" if self.fits_sheet() else "  –  RYSUNEK WYCHODZI POZA MARGINESY")
        p.drawText(QPointF(x, y), txt)

    # --- mysz: kółko = powiększenie, przeciąganie = przesuwanie (lub przesuwanie arkusza)
    @staticmethod
    def _pos(e):
        return e.position() if hasattr(e, "position") else QPointF(e.pos())

    @staticmethod
    def _gpos(e):
        return e.globalPosition() if hasattr(e, "globalPosition") else QPointF(e.globalPos())

    def near_sheet_frame(self, pos):
        if not self.sheet.enabled:
            return False
        x, y = self.to_drawing(pos)
        tol = 7.0 / self.zoom
        for r in (self.sheet_rect(), self.margin_rect()):
            outer = r.adjusted(-tol, -tol, tol, tol)
            inner = r.adjusted(tol, tol, -tol, -tol)
            inside_outer = outer.left() <= x <= outer.right() and outer.top() <= y <= outer.bottom()
            inside_inner = (inner.width() > 0 and inner.height() > 0 and
                            inner.left() <= x <= inner.right() and inner.top() <= y <= inner.bottom())
            if inside_outer and not inside_inner:
                return True
        return False

    def wheelEvent(self, e):
        dy = e.angleDelta().y()
        if dy == 0 or self.zoom_request is None:
            e.ignore()
            return
        self.zoom_request(1.25 if dy > 0 else 0.8, self._pos(e))
        e.accept()

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if self.near_sheet_frame(self._pos(e)):
            self._sheet_drag = (self._gpos(e), self.sheet_pos())
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self._drag = self._gpos(e)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        e.accept()

    def mouseReleaseEvent(self, e):
        if self._sheet_drag is not None:
            self._sheet_drag = None
            ox0, oy0 = self.offx, self.offy
            self.update_extent()
            if self.pan_request is not None:
                self.pan_request((self.offx - ox0) * self.zoom, (self.offy - oy0) * self.zoom)
            if self.sheet_moved is not None:
                self.sheet_moved()
        self._drag = None
        self.setCursor(Qt.CursorShape.SizeAllCursor if self.near_sheet_frame(self._pos(e))
                       else Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, e):
        x, y = self.to_drawing(self._pos(e))
        if 0 <= y <= 64 and 0 <= x <= self._w and self.header_request is not None:
            self.header_request()          # dwuklik w nagłówek = edycja opisu
            return
        if self.zoom_request is not None:
            self.zoom_request(2.0, self._pos(e))

    def mouseMoveEvent(self, e):
        if self._sheet_drag is not None:
            g0, (sx, sy) = self._sheet_drag
            g = self._gpos(e)
            k = self.zoom * self.ppm
            self.sheet.pos = (sx + (g.x() - g0.x()) / k, sy + (g.y() - g0.y()) / k)
            self.update()
            return
        if self._drag is not None and self.pan_request is not None:
            g = self._gpos(e)
            self.pan_request(self._drag.x() - g.x(), self._drag.y() - g.y())
            self._drag = g
            return
        pos = self._pos(e)
        self.setCursor(Qt.CursorShape.SizeAllCursor if self.near_sheet_frame(pos)
                       else Qt.CursorShape.OpenHandCursor)
        x, y = self.to_drawing(pos)
        L = self.lay
        d = L.d_at_mm((x - self.ox()) / self.ppm)
        if 0.0 <= d <= self.profile.length and self.MT <= y <= self.oy():
            self.hover_d = d
            self._hover_pos = QPointF(pos)
        else:
            self.hover_d = None
            self._hover_pos = None
        self.update()

    def leaveEvent(self, _e):
        self.hover_d = None
        self._hover_pos = None
        self.update()

    # --- obraz całego rysunku (schowek / plik) – zawsze w powiększeniu 100 %
    def render_image(self):
        w, h = self._w, self._h
        if w * h > MAX_IMAGE_PIXELS or max(w, h) > MAX_IMAGE_SIDE:
            raise TooBig(f"Arkusz w tej skali byłby zbyt dużym obrazem ({w} × {h} px).\n"
                         "Zwiększ mianowniki skali (mniejsza skala).")
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(NAVY)
        p = QPainter(img)
        try:
            p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            self._draw_zoom = 1.0
            self._cosmetic = True
            self.draw(p, QRectF(0, 0, w, h), "screen")
        finally:
            p.end()
            self._draw_zoom = self.zoom
        dpm = int(round(self.ppm * 1000))
        img.setDotsPerMeterX(dpm)
        img.setDotsPerMeterY(dpm)
        return img

    # --- wydruk arkusza (drukarka lub PDF)
    def print_sheet(self, printer, theme="paper"):
        w, h = self.sheet.size()
        sx, sy = self.sheet_pos()
        k = self.ppm
        p = QPainter()
        if not p.begin(printer):
            raise RuntimeError("Nie udało się rozpocząć drukowania (drukarka lub plik PDF niedostępne).")
        try:
            dpmm = printer.resolution() / 25.4
            p.scale(dpmm / k, dpmm / k)
            p.translate(-sx * k, -sy * k)
            clip = self.margin_rect()
            if theme == "paper":
                p.fillRect(self.sheet_rect(), QColor(255, 255, 255))
            p.setClipRect(clip)
            self._cosmetic = False
            self._draw_zoom = 1.0
            self.draw(p, clip, theme)
        finally:
            self._cosmetic = True
            self._draw_zoom = self.zoom
            p.end()


# ---------------------------------------------------------------------------
#  Okno 1: plik wejściowy i parametry
# ---------------------------------------------------------------------------
class InputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{SCRIPT_NAME} – dane wejściowe")
        self.setWindowIcon(syrop_icon())
        self.setMinimumWidth(620)
        self.feats = []
        self.profile = None
        self._last_path = None

        head = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(syrop_icon().pixmap(48, 48))
        head.addWidget(ico)
        t = QLabel(f"<b style='font-size:15px'>{SCRIPT_NAME}</b><br>"
                   "Przekrój z trójwymiarowej linii (Z = wysokość)")
        head.addWidget(t, 1)

        self.ed_path = QLineEdit()
        self.ed_path.setPlaceholderText("KML, DXF, DWG, SHP lub GPKG z linią / multilinią 3D")
        self.ed_path.editingFinished.connect(self.load_file)
        bt = QPushButton("Wybierz…")
        bt.clicked.connect(self.browse)
        row = QHBoxLayout()
        row.addWidget(self.ed_path, 1)
        row.addWidget(bt)

        self.cb_feat = QComboBox()
        self.cb_feat.setMinimumContentsLength(40)
        self.cb_crs = QComboBox()
        for code, lab in EPSG_CHOICES:
            self.cb_crs.addItem(lab, code)
        self.cb_crs.setCurrentIndex(max(0, self.cb_crs.findData(int(QSettings().value(SETTINGS + "in_epsg", 2180)))))
        self.lb_info = QLabel("")
        self.lb_info.setWordWrap(True)
        self.lb_info.setStyleSheet("color:#666")

        form = QFormLayout()
        form.addRow("Plik wejściowy:", row)
        form.addRow("Linia przekroju:", self.cb_feat)
        form.addRow("Układ współrzędnych pliku:", self.cb_crs)
        form.addRow("", self.lb_info)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Rysuj przekrój")
        bb.accepted.connect(self.on_ok)
        bb.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(head)
        lay.addLayout(form)
        lay.addWidget(bb)

    def browse(self):
        start = QSettings().value(SETTINGS + "in_dir", "", type=str)
        path, _ = QFileDialog.getOpenFileName(
            self, "Plik z linią przekroju", start,
            "Pliki z liniami (*.kml *.kmz *.dxf *.dwg *.shp *.gpkg);;KML (*.kml *.kmz);;DXF (*.dxf);;"
            "DWG (*.dwg);;Shapefile (*.shp);;GeoPackage (*.gpkg);;Wszystkie pliki (*)")
        if path:
            QSettings().setValue(SETTINGS + "in_dir", os.path.dirname(path))
            self.ed_path.setText(path)
            self.load_file()

    def load_file(self):
        path = self.ed_path.text().strip().strip('"')
        if not path or path == self._last_path:
            return
        self._last_path = path
        self.cb_feat.clear()
        self.feats = []
        if not os.path.isfile(path):
            self.lb_info.setText("Plik nie istnieje.")
            return
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            feats, epsg, note = read_lines(path, self)
        except Exception as ex:
            QGuiApplication.restoreOverrideCursor()
            self.lb_info.setText(f"Błąd odczytu: {ex}")
            return
        QGuiApplication.restoreOverrideCursor()
        self.feats = feats
        if not feats:
            self.lb_info.setText("W pliku nie znaleziono linii ani multilinii.")
            return
        if len(feats) > 1:
            self.cb_feat.addItem(f"Wszystkie linie jako jeden przekrój (kolejno, {len(feats)} obiekty)", -1)
        for i, f in enumerate(feats):
            self.cb_feat.addItem(("" if f.has_z else "[brak Z] ") + f.label, i)
        if len(feats) > 1:
            self.cb_feat.setCurrentIndex(1)
        info = [f"Znaleziono linii: {len(feats)}."]
        if epsg is not None:
            idx = self.cb_crs.findData(epsg)
            if idx >= 0:
                self.cb_crs.setCurrentIndex(idx)
                info.append(f"Wykryto układ EPSG:{epsg}.")
            else:
                info.append(f"Plik ma układ EPSG:{epsg}, spoza listy – wybierz właściwy ręcznie.")
        else:
            info.append("Plik nie zawiera informacji o układzie – wybierz go z listy.")
        if note:
            info.append(note)
        self.lb_info.setText(" ".join(info))

    def on_ok(self):
        self.load_file()
        if not self.feats:
            QMessageBox.warning(self, SCRIPT_NAME, "Wskaż plik zawierający linię przekroju.")
            return
        idx = self.cb_feat.currentData()
        chosen = self.feats if idx == -1 else [self.feats[idx]]
        parts = [pt for f in chosen for pt in f.parts]
        zs = [v[2] for pt in parts for v in pt]
        if not any(f.has_z for f in chosen) or all(abs(z) < 1e-12 for z in zs):
            r = QMessageBox.question(
                self, SCRIPT_NAME,
                "Wybrana geometria nie zawiera wysokości (Z) albo wszystkie Z = 0.\n"
                "Przekrój będzie płaski. Kontynuować?")
            if r != QMessageBox.StandardButton.Yes:
                return
        epsg = self.cb_crs.currentData()
        QSettings().setValue(SETTINGS + "in_epsg", epsg)
        base = os.path.splitext(os.path.basename(self.ed_path.text().strip().strip('"')))[0]
        name = base if idx == -1 or len(self.feats) == 1 else f"{base} ({chosen[0].layer} #{chosen[0].fid})"
        try:
            self.profile = Profile(name, epsg, parts)
        except Exception as ex:
            QMessageBox.critical(self, SCRIPT_NAME, f"Nie można utworzyć przekroju:\n{ex}")
            return
        self.accept()


# ---------------------------------------------------------------------------
#  Okno edycji nagłówka (opisu)
# ---------------------------------------------------------------------------
class HeaderDialog(QDialog):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{SCRIPT_NAME} – opis przekroju")
        self.setWindowIcon(syrop_icon())
        self.setMinimumWidth(640)
        self.canvas = canvas
        hd = canvas.header
        t1, t2 = canvas.header_texts()
        self.ed_title = QLineEdit(t1)
        self.ed_info = QLineEdit(t2)
        self.chk_auto = QCheckBox("Linia z danymi uzupełniana automatycznie (długość, wysokości, przewyższenie)")
        self.chk_auto.setChecked(hd["info"] is None)
        self.chk_auto.toggled.connect(self.refresh)
        self.ed_cap_h = QLineEdit(hd["cap_h"])
        self.ed_cap_v = QLineEdit(hd["cap_v"])
        b_def = QPushButton("Przywróć domyślne")
        b_def.clicked.connect(self.defaults)
        form = QFormLayout()
        form.addRow("Tytuł:", self.ed_title)
        form.addRow("Linia z danymi:", self.ed_info)
        form.addRow("", self.chk_auto)
        form.addRow("Podpis skali poziomej:", self.ed_cap_h)
        form.addRow("Podpis skali pionowej:", self.ed_cap_v)
        hint = QLabel("Pusty tytuł lub pusta linia z danymi = element niewidoczny. "
                      "Opis otworzysz też dwuklikiem w nagłówek rysunku.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#666")
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(b_def)
        row.addStretch(1)
        row.addWidget(bb)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(hint)
        lay.addLayout(row)
        self.refresh()

    def refresh(self):
        auto = self.chk_auto.isChecked()
        self.ed_info.setEnabled(not auto)
        if auto:
            self.ed_info.setText(self.canvas.auto_info())

    def defaults(self):
        self.ed_title.setText(self.canvas.auto_title())
        self.chk_auto.setChecked(True)
        self.refresh()
        self.ed_cap_h.setText("Skala pozioma")
        self.ed_cap_v.setText("Skala pionowa")

    def apply(self):
        c = self.canvas
        title = self.ed_title.text()
        c.set_header(None if title == c.auto_title() else title,
                     None if self.chk_auto.isChecked() else self.ed_info.text(),
                     self.ed_cap_h.text(), self.ed_cap_v.text())


# ---------------------------------------------------------------------------
#  Okno ustawień arkusza
# ---------------------------------------------------------------------------
class SheetDialog(QDialog):
    def __init__(self, sheet, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{SCRIPT_NAME} – arkusz")
        self.setWindowIcon(syrop_icon())
        self.sheet = sheet

        self.chk_on = QCheckBox("Pokaż granice arkusza (czerwone) i marginesy (zielone)")
        self.chk_on.setChecked(sheet.enabled)
        self.cb_fmt = QComboBox()
        for k in PAPER:
            self.cb_fmt.addItem(f"{k}  ({PAPER[k][0]} × {PAPER[k][1]} mm)", k)
        self.cb_fmt.addItem("Własny – wpisz wymiary", CUSTOM)
        self.cb_fmt.setCurrentIndex(max(0, self.cb_fmt.findData(sheet.fmt)))
        self.cb_or = QComboBox()
        self.cb_or.addItem("poziomo", True)
        self.cb_or.addItem("pionowo", False)
        self.cb_or.setCurrentIndex(0 if sheet.landscape else 1)
        self.sp_w = QDoubleSpinBox()
        self.sp_h = QDoubleSpinBox()
        for sp in (self.sp_w, self.sp_h):
            sp.setRange(10.0, 20000.0)
            sp.setDecimals(1)
            sp.setSuffix(" mm")
        self.sp_w.setValue(sheet.cw)
        self.sp_h.setValue(sheet.ch)
        self.sp_m = []
        mg = QGridLayout()
        for i, lab in enumerate(("lewy", "górny", "prawy", "dolny")):
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 1000.0)
            sp.setDecimals(1)
            sp.setSuffix(" mm")
            sp.setValue(sheet.margins[i])
            self.sp_m.append(sp)
            mg.addWidget(QLabel(lab + ":"), i // 2, (i % 2) * 2)
            mg.addWidget(sp, i // 2, (i % 2) * 2 + 1)
        self.chk_reset = QCheckBox("Ustaw rysunek w lewym górnym rogu obszaru wydruku (wewnątrz marginesów)")
        self.chk_reset.setChecked(sheet.pos is None)
        hint = QLabel("Położenie arkusza zmienisz też myszą: chwyć czerwoną lub zieloną ramkę "
                      "i przeciągnij ją w oknie przekroju.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#666")

        form = QFormLayout()
        form.addRow("", self.chk_on)
        form.addRow("Format:", self.cb_fmt)
        form.addRow("Orientacja:", self.cb_or)
        form.addRow("Szerokość:", self.sp_w)
        form.addRow("Wysokość:", self.sp_h)
        gb = QGroupBox("Marginesy")
        gb.setLayout(mg)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(gb)
        lay.addWidget(self.chk_reset)
        lay.addWidget(hint)
        lay.addWidget(bb)
        self.cb_fmt.currentIndexChanged.connect(self.refresh)
        self.cb_or.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def refresh(self):
        fmt = self.cb_fmt.currentData()
        custom = fmt == CUSTOM
        self.sp_w.setEnabled(custom)
        self.sp_h.setEnabled(custom)
        self.cb_or.setEnabled(not custom)
        if not custom:
            a, b = PAPER[fmt]
            land = bool(self.cb_or.currentData())
            self.sp_w.setValue(b if land else a)
            self.sp_h.setValue(a if land else b)

    def apply(self):
        sh = self.sheet
        sh.enabled = self.chk_on.isChecked()
        sh.fmt = self.cb_fmt.currentData()
        sh.landscape = bool(self.cb_or.currentData())
        if sh.fmt == CUSTOM:
            sh.cw, sh.ch = self.sp_w.value(), self.sp_h.value()
        sh.margins = [sp.value() for sp in self.sp_m]
        if self.chk_reset.isChecked():
            sh.pos = None
        sh.save()


# ---------------------------------------------------------------------------
#  Okno eksportu
# ---------------------------------------------------------------------------
class ExportDialog(QDialog):
    def __init__(self, profile, parent=None, sheet_on=False):
        super().__init__(parent)
        self.sheet_on = sheet_on
        self.setWindowTitle(f"{SCRIPT_NAME} – eksport przekroju")
        self.setWindowIcon(syrop_icon())
        self.setMinimumWidth(600)
        self.profile = profile

        self.cb_fmt = QComboBox()
        for code, lab in OUT_FORMATS:
            self.cb_fmt.addItem(lab, code)
        self.cb_crs = QComboBox()
        self.cb_crs.addItem(LOCAL_LABEL, LOCAL)
        for code, lab in EPSG_CHOICES:
            self.cb_crs.addItem(lab, code)
        st = QSettings()
        i = self.cb_fmt.findData(st.value(SETTINGS + "out_fmt", "DXF", type=str))
        self.cb_fmt.setCurrentIndex(max(0, i))
        i = self.cb_crs.findData(int(st.value(SETTINGS + "out_epsg", LOCAL)))
        self.cb_crs.setCurrentIndex(max(0, i))

        self.ed_path = QLineEdit()
        bt = QPushButton("Zapisz jako…")
        bt.clicked.connect(self.browse)
        row = QHBoxLayout()
        row.addWidget(self.ed_path, 1)
        row.addWidget(bt)
        self.chk_add = QCheckBox("Dodaj wynik do projektu QGIS")
        self.chk_add.setChecked(True)
        self.lb_desc = QLabel()
        self.lb_desc.setWordWrap(True)
        self.lb_desc.setStyleSheet("color:#555")

        form = QFormLayout()
        form.addRow("Format:", self.cb_fmt)
        form.addRow("Układ współrzędnych:", self.cb_crs)
        form.addRow("Plik wynikowy:", row)
        form.addRow("", self.chk_add)
        form.addRow("", self.lb_desc)

        # --- wybór elementów rysunku
        self.chk_el = {}
        gl = QGridLayout()
        for n, (key, lab, default) in enumerate(EXPORT_ELEMENTS):
            cb = QCheckBox(lab)
            cb.setChecked(st.value(SETTINGS + "el_" + key, default, type=bool))
            self.chk_el[key] = cb
            gl.addWidget(cb, n // 2, n % 2)
        gb = QGroupBox("Elementy rysunku do eksportu")
        gb.setLayout(gl)
        form.addRow(gb)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Eksportuj")
        bb.accepted.connect(self.on_ok)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(bb)
        self.cb_fmt.currentIndexChanged.connect(self.refresh)
        self.cb_crs.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def fmt(self):
        return self.cb_fmt.currentData()

    def epsg(self):
        return self.cb_crs.currentData()

    def refresh(self):
        fmt = self.fmt()
        if fmt == "KML":  # KML jest z definicji w WGS 84
            self.cb_crs.setCurrentIndex(self.cb_crs.findData(4326))
            self.cb_crs.setEnabled(False)
        else:
            self.cb_crs.setEnabled(True)
        ext = "." + fmt.lower()
        p = self.ed_path.text().strip()
        if p:
            self.ed_path.setText(os.path.splitext(p)[0] + ext)
        loc = self.epsg() == LOCAL
        if loc:
            d = ("Układ lokalny: X = odległość [m], Y = (H − poziom porównawczy) × przewyższenie, "
                 "początek (0,0) w lewym dolnym rogu wykresu. Rysunek w skali 1:(skala pozioma) "
                 "odwzorowuje arkusz z ekranu. Prawdziwe odległości i wysokości są w atrybutach.")
        else:
            d = ("Układ georeferencyjny: linia przekroju jako polilinia 3D (X, Y w wybranym układzie, "
                 "Z = wysokość) oraz wierzchołki z odległością i wysokością.")
        if fmt in ("DXF", "DWG"):
            d += " Opisy są zapisywane jako teksty (TEXT, czcionka Arial), każdy rodzaj elementu na osobnej warstwie."
        elif fmt == "DGN":
            d += (" DGN v7 (MicroStation): opisy jako elementy tekstowe, każdy rodzaj elementu na osobnym "
                  "poziomie. Format v7 nie obsługuje polskich znaków – w tekstach zostaną zastąpione łacińskimi.")
        else:
            d += (" Opisy trafiają do warstwy tekstów „opisy” (pole „nazwa” = treść, wysokość, obrót, "
                  "wyrównanie) i po dodaniu do projektu są od razu wyświetlane jako etykiety.")
        if fmt == "SHP":
            d += " Shapefile: każda warstwa w osobnym pliku <nazwa>_linia, _wierzcholki, _elementy, _opisy."
        if fmt == "DWG":
            d += " DWG (AutoCAD 2018) powstaje przez ODA File Converter."
        self.lb_desc.setText(d)
        geo_ok = {"wykres", "dane"}
        for key, cb in self.chk_el.items():
            en = loc or key in geo_ok
            if key == "arkusz":
                en = loc and self.sheet_on
            cb.setEnabled(en)
        self.chk_el["dane"].setText("Dane liczbowe (wartości na osiach, długość, wysokości)" if loc
                                    else "Dane liczbowe (opisy wierzchołków: odległość / wysokość)")

    def elements(self):
        return {k for k, cb in self.chk_el.items() if cb.isChecked() and cb.isEnabled()}

    def browse(self):
        fmt = self.fmt()
        flt = dict(OUT_FORMATS)[fmt]
        start = self.ed_path.text().strip() or os.path.join(
            QSettings().value(SETTINGS + "out_dir", "", type=str), "przekroj." + fmt.lower())
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz przekrój", start, flt)
        if path:
            if not path.lower().endswith("." + fmt.lower()):
                path += "." + fmt.lower()
            self.ed_path.setText(path)

    def on_ok(self):
        if not self.ed_path.text().strip():
            self.browse()
            if not self.ed_path.text().strip():
                return
        st = QSettings()
        st.setValue(SETTINGS + "out_fmt", self.fmt())
        st.setValue(SETTINGS + "out_epsg", self.epsg())
        st.setValue(SETTINGS + "out_dir", os.path.dirname(self.ed_path.text().strip()))
        for key, cb in self.chk_el.items():
            st.setValue(SETTINGS + "el_" + key, cb.isChecked())
        if not self.elements():
            QMessageBox.warning(self, SCRIPT_NAME, "Zaznacz co najmniej jeden element rysunku do eksportu.")
            return
        self.accept()


# ---------------------------------------------------------------------------
#  Zapis GIS (OGR)
# ---------------------------------------------------------------------------
def _srs(epsg):
    if not epsg:
        return None
    s = osr.SpatialReference()
    s.ImportFromEPSG(int(epsg))
    try:
        s.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    except Exception:
        pass
    return s


def _write_line_layer(ds, name, srs, parts, is3d, meta, lco=None):
    lyr = ds.CreateLayer(name, srs, ogr.wkbMultiLineString25D if is3d else ogr.wkbMultiLineString,
                         options=lco or [])
    for fname, ftype, width in (("nazwa", ogr.OFTString, 120), ("dlugosc_m", ogr.OFTReal, 0),
                                ("skala_poz", ogr.OFTString, 20), ("skala_pion", ogr.OFTString, 20),
                                ("przewysz", ogr.OFTReal, 0), ("h_porown", ogr.OFTReal, 0),
                                ("uklad", ogr.OFTString, 60)):
        fd = ogr.FieldDefn(fname, ftype)
        if width:
            fd.SetWidth(width)
        lyr.CreateField(fd)
    g = ogr.Geometry(ogr.wkbMultiLineString25D if is3d else ogr.wkbMultiLineString)
    for part in parts:
        ls = ogr.Geometry(ogr.wkbLineString25D if is3d else ogr.wkbLineString)
        for x, y, z in part:
            if is3d:
                ls.AddPoint(x, y, z)
            else:
                ls.AddPoint_2D(x, y)
        g.AddGeometry(ls)
    f = ogr.Feature(lyr.GetLayerDefn())
    for k, v in meta.items():
        f.SetField(k, v)
    f.SetGeometry(g)
    lyr.CreateFeature(f)


def _write_point_layer(ds, name, srs, pts, is3d, lco=None):
    lyr = ds.CreateLayer(name, srs, ogr.wkbPoint25D if is3d else ogr.wkbPoint, options=lco or [])
    for fname, ftype, width in (("nazwa", ogr.OFTString, 60), ("nr", ogr.OFTInteger, 0),
                                ("odl_m", ogr.OFTReal, 0), ("wys_m", ogr.OFTReal, 0)):
        fd = ogr.FieldDefn(fname, ftype)
        if width:
            fd.SetWidth(width)
        lyr.CreateField(fd)
    for nr, (x, y, z, d, h) in enumerate(pts, 1):
        g = ogr.Geometry(ogr.wkbPoint25D if is3d else ogr.wkbPoint)
        if is3d:
            g.AddPoint(x, y, z)
        else:
            g.AddPoint_2D(x, y)
        f = ogr.Feature(lyr.GetLayerDefn())
        f.SetField("nazwa", f"{fnum(d)} m / H={fnum(h)}")
        f.SetField("nr", nr)
        f.SetField("odl_m", round(d, 4))
        f.SetField("wys_m", round(h, 4))
        f.SetGeometry(g)
        lyr.CreateFeature(f)


def _write_elem_layer(ds, name, srs, items, is3d, lco=None):
    """Linie rysunku (siatka, osie, granice arkusza) z polem „warstwa”."""
    lyr = ds.CreateLayer(name, srs, ogr.wkbLineString25D if is3d else ogr.wkbLineString, options=lco or [])
    fd = ogr.FieldDefn("warstwa", ogr.OFTString)
    fd.SetWidth(40)
    lyr.CreateField(fd)
    for _t, layer, (x1, y1, z1, x2, y2, z2) in items:
        g = ogr.Geometry(ogr.wkbLineString25D if is3d else ogr.wkbLineString)
        if is3d:
            g.AddPoint(x1, y1, z1)
            g.AddPoint(x2, y2, z2)
        else:
            g.AddPoint_2D(x1, y1)
            g.AddPoint_2D(x2, y2)
        f = ogr.Feature(lyr.GetLayerDefn())
        f.SetField("warstwa", layer)
        f.SetGeometry(g)
        lyr.CreateFeature(f)


HALI = {0: "Left", 1: "Center", 2: "Right"}
VALI = {0: "Base", 1: "Bottom", 2: "Half", 3: "Top"}


def _write_text_layer(ds, name, srs, items, is3d, lco=None):
    """Opisy jako teksty: punkt wstawienia + treść, wysokość, obrót i wyrównanie."""
    lyr = ds.CreateLayer(name, srs, ogr.wkbPoint25D if is3d else ogr.wkbPoint, options=lco or [])
    for fname, ftype, width in (("nazwa", ogr.OFTString, 254), ("warstwa", ogr.OFTString, 40),
                                ("wys_txt", ogr.OFTReal, 0), ("obrot", ogr.OFTReal, 0),
                                ("hali", ogr.OFTString, 10), ("vali", ogr.OFTString, 10)):
        fd = ogr.FieldDefn(fname, ftype)
        if width:
            fd.SetWidth(width)
        lyr.CreateField(fd)
    for _t, layer, tt in items:
        x, y, z, h, s, rot, ha, va = tt[:8]
        g = ogr.Geometry(ogr.wkbPoint25D if is3d else ogr.wkbPoint)
        if is3d:
            g.AddPoint(x, y, z)
        else:
            g.AddPoint_2D(x, y)
        f = ogr.Feature(lyr.GetLayerDefn())
        f.SetField("nazwa", s)
        f.SetField("warstwa", layer)
        f.SetField("wys_txt", float(h))
        f.SetField("obrot", float(rot or 0.0))
        f.SetField("hali", HALI.get(ha, "Left"))
        f.SetField("vali", VALI.get(va, "Base"))
        f.SetGeometry(g)
        lyr.CreateFeature(f)


def write_gis(path, fmt, epsg, parts, pts, meta, dx, el):
    """Zwraca listę (ścieżka, nazwa warstwy lub None, rodzaj) utworzonych warstw."""
    is3d = epsg != LOCAL
    srs = _srs(epsg)
    lines = [it for it in dx.items if it[0] == "L"]
    texts = [it for it in dx.items if it[0] == "T"]
    jobs = []  # (sufiks, funkcja(ds, nazwa, lco))
    if "wykres" in el:
        jobs.append(("linia", lambda ds, n, lco: _write_line_layer(ds, n, srs, parts, is3d, meta, lco)))
        jobs.append(("wierzcholki", lambda ds, n, lco: _write_point_layer(ds, n, srs, pts, is3d, lco)))
    if lines:
        jobs.append(("elementy", lambda ds, n, lco: _write_elem_layer(ds, n, srs, lines, is3d, lco)))
    if texts:
        jobs.append(("opisy", lambda ds, n, lco: _write_text_layer(ds, n, srs, texts, is3d, lco)))
    if not jobs:
        raise RuntimeError("Brak elementów do zapisania.")
    outs = []
    with ogr_exceptions():
        if fmt == "SHP":
            drv = ogr.GetDriverByName("ESRI Shapefile")
            base = os.path.splitext(path)[0]
            for suf, fn in jobs:
                pth = f"{base}_{suf}.shp"
                if os.path.exists(pth):
                    drv.DeleteDataSource(pth)
                ds = drv.CreateDataSource(pth)
                fn(ds, os.path.basename(base) + "_" + suf, ["ENCODING=UTF-8"])
                ds = None
                outs.append((pth, None, suf))
            return outs
        if fmt == "GPKG":
            drv = ogr.GetDriverByName("GPKG")
            if os.path.exists(path):
                drv.DeleteDataSource(path)
            ds = drv.CreateDataSource(path)
            for suf, fn in jobs:
                fn(ds, "przekroj_" + suf, [])
                outs.append((path, "przekroj_" + suf, suf))
            ds = None
            return outs
        if fmt == "KML":
            drv = ogr.GetDriverByName("KML")
            if os.path.exists(path):
                os.remove(path)
            ds = drv.CreateDataSource(path, options=["NameField=nazwa", "AltitudeMode=absolute"])
            for suf, fn in jobs:
                fn(ds, "przekroj_" + suf, [])
            ds = None
            return [(path, None, "kml")]
    raise ValueError(fmt)


_PL = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ×•–—„”°", "acelnoszzACELNOSZZx*--\"\"o")

# kolory ACI → indeksy domyślnej tablicy kolorów MicroStation
_ACI_TO_DGN = {1: 3, 3: 2, 5: 1, 2: 4, 7: 0}


def write_dgn(path, dx, is3d):
    """
    MicroStation DGN v7 przez sterownik GDAL/OGR: linie, polilinie i teksty
    (każda warstwa DXF = osobny poziom DGN). DGN v7 nie obsługuje Unicode –
    polskie znaki w tekstach są zamieniane na łacińskie.
    """
    drv = ogr.GetDriverByName("DGN")
    if drv is None:
        raise RuntimeError("Ta instalacja GDAL nie ma sterownika DGN.")
    if os.path.exists(path):
        os.remove(path)
    levels = {name: min(63, i + 1) for i, name in enumerate(n for n in dx.layers if n != "0")}
    cx = (dx.minx + dx.maxx) / 2.0 if dx.minx != float("inf") else 0.0
    cy = (dx.miny + dx.maxy) / 2.0 if dx.miny != float("inf") else 0.0
    cz = (dx.minz + dx.maxz) / 2.0 if (is3d and dx.minz != float("inf")) else 0.0
    opts = ["3D=YES" if is3d else "3D=NO", "MASTER_UNIT_NAME=m", "SUB_UNIT_NAME=mm",
            "SUB_UNITS_PER_MASTER_UNIT=1000", "UOR_PER_SUB_UNIT=10",
            f"ORIGIN={cx:.3f},{cy:.3f},{cz:.3f}"]
    with ogr_exceptions():
        ds = drv.CreateDataSource(path, options=opts)
        lyr = ds.CreateLayer("elements")
        defn = lyr.GetLayerDefn()
        has = {defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())}

        def feat(geom, layer, style=None):
            f = ogr.Feature(defn)
            if "Level" in has:
                f.SetField("Level", levels.get(layer, 0))
            if "ColorIndex" in has:
                f.SetField("ColorIndex", _ACI_TO_DGN.get(dx.layers.get(layer, 7), 0))
            if style:
                f.SetStyleString(style)
            f.SetGeometry(geom)
            lyr.CreateFeature(f)

        def line(pts):
            g = ogr.Geometry(ogr.wkbLineString25D if is3d else ogr.wkbLineString)
            for p in pts:
                if is3d:
                    g.AddPoint(p[0], p[1], p[2])
                else:
                    g.AddPoint_2D(p[0], p[1])
            return g

        for it in dx.items:
            kind, layer, c = it
            if kind == "L":
                feat(line([(c[0], c[1], c[2]), (c[3], c[4], c[5])]), layer)
            elif kind == "P":
                feat(line(c), layer)
            elif kind == "O":
                feat(line([c, c]), layer)
            elif kind == "T":
                x, y, z, h, txt, rot, _ha, _va, bx, by, _w = c
                t = txt.translate(_PL).encode("ascii", "replace").decode("ascii").replace('"', "'")
                g = ogr.Geometry(ogr.wkbPoint25D if is3d else ogr.wkbPoint)
                if is3d:
                    g.AddPoint(bx, by, z)
                else:
                    g.AddPoint_2D(bx, by)
                feat(g, layer, f'LABEL(f:"Arial",t:"{t}",s:{h:.4f}g,a:{float(rot or 0):.2f},p:1)')
        ds = None
    return [(path, None, "cad")]


def apply_text_labels(lyr):
    """Warstwa opisów: etykiety z pola „nazwa”, wysokość/obrót/wyrównanie z atrybutów."""
    try:
        from qgis.core import QgsPalLayerSettings, QgsProperty, QgsTextFormat, QgsVectorLayerSimpleLabeling
        s = QgsPalLayerSettings()
        s.fieldName = "nazwa"
        tf = QgsTextFormat()
        try:
            tf.setSizeUnit(Qgis.RenderUnit.MapUnits)
        except AttributeError:
            from qgis.core import QgsUnitTypes
            tf.setSizeUnit(QgsUnitTypes.RenderMapUnits)
        tf.setSize(1.0)
        tf.setColor(QColor(0, 0, 0))
        s.setFormat(tf)
        P = getattr(QgsPalLayerSettings, "Property", QgsPalLayerSettings)
        dd = s.dataDefinedProperties()
        dd.setProperty(P.Size, QgsProperty.fromExpression('"wys_txt" * 1.4'))
        dd.setProperty(P.LabelRotation, QgsProperty.fromExpression('-"obrot"'))
        dd.setProperty(P.PositionX, QgsProperty.fromExpression("x($geometry)"))
        dd.setProperty(P.PositionY, QgsProperty.fromExpression("y($geometry)"))
        dd.setProperty(P.Hali, QgsProperty.fromField("hali"))
        dd.setProperty(P.Vali, QgsProperty.fromField("vali"))
        s.setDataDefinedProperties(dd)
        lyr.setLabeling(QgsVectorLayerSimpleLabeling(s))
        lyr.setLabelsEnabled(True)
        try:
            lyr.renderer().symbol().setOpacity(0.0)
        except Exception:
            pass
        lyr.triggerRepaint()
    except Exception:
        report_error("Etykiety warstwy opisów")


# ---------------------------------------------------------------------------
#  Okno 2: przekrój
# ---------------------------------------------------------------------------
def _open_windows():
    """Trwały rejestr otwartych okien – chroni obiekty Pythona przed usunięciem
    przez odśmiecacz pamięci (inaczej przyciski i rysowanie przestają działać)."""
    import qgis.utils as _qu
    reg = getattr(_qu, "_syrop_wykreslny_okna", None)
    if reg is None:
        reg = []
        _qu._syrop_wykreslny_okna = reg
    return reg


class ProfileWindow(QDialog):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle(f"{SCRIPT_NAME} {SCRIPT_VERSION} – {profile.name}")
        self.setWindowIcon(syrop_icon())
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinMaxButtonsHint |
                            Qt.WindowType.WindowCloseButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setModal(False)
        _open_windows().append(self)

        self.canvas = ProfileCanvas(profile)
        self.canvas.zoom_request = self.zoom_at
        self.canvas.pan_request = self.pan_by
        self.canvas.sheet_moved = self.update_labels
        self.canvas.header_request = self.edit_header
        # podpowiedzi (tooltipy) w tym oknie: białe litery na granatowym tle
        self.setStyleSheet("QToolTip { color: #ffffff; background-color: #0a1633; "
                           "border: 1px solid #ffffff; padding: 3px; }")

        # --- skale: ręczne wpisanie mianownika
        self.ed_h = QLineEdit(str(self.canvas.hs))
        self.ed_v = QLineEdit(str(self.canvas.vs))
        for ed in (self.ed_h, self.ed_v):
            ed.setValidator(QIntValidator(1, 100_000_000, ed))
            ed.setMaximumWidth(110)
            ed.setToolTip("Wpisz mianownik skali i naciśnij Enter")
            ed.editingFinished.connect(self.apply_scales)
        b_apply = QPushButton("Przerysuj")
        b_apply.clicked.connect(self.apply_scales)
        b_def = QPushButton("Skala domyślna")
        b_def.setToolTip("Przywraca skale dobrane automatycznie przy otwarciu przekroju")
        b_def.clicked.connect(self.default_scales)
        b_def.setAutoDefault(False)

        # --- jednostki osi
        self.cb_uh = QComboBox()
        self.cb_uv = QComboBox()
        for cb in (self.cb_uh, self.cb_uv):
            for u, _f in UNITS:
                cb.addItem(u, u)
            cb.setCurrentIndex(cb.findData("m"))
            cb.currentIndexChanged.connect(self.apply_units)

        self.lb_exag = QLabel()
        self.lb_exag.setMinimumWidth(150)
        self.chk_v = QCheckBox("Wierzchołki")
        self.chk_v.setChecked(True)
        self.chk_v.toggled.connect(self.on_vertices)

        grid = QGridLayout()
        grid.addWidget(QLabel("Skala pozioma  1 :"), 0, 0)
        grid.addWidget(self.ed_h, 0, 1)
        grid.addWidget(QLabel("   jednostki osi poziomej:"), 0, 2)
        grid.addWidget(self.cb_uh, 0, 3)
        grid.addWidget(QLabel("Skala pionowa  1 :"), 1, 0)
        grid.addWidget(self.ed_v, 1, 1)
        grid.addWidget(QLabel("   jednostki osi pionowej:"), 1, 2)
        grid.addWidget(self.cb_uv, 1, 3)
        grid.addWidget(b_apply, 0, 4)
        grid.addWidget(b_def, 1, 4)
        grid.addWidget(self.lb_exag, 0, 5)
        grid.addWidget(self.chk_v, 1, 5)

        # --- powiększenie widoku
        b_out = QPushButton("−")
        b_in = QPushButton("+")
        b_100 = QPushButton("100 %")
        b_fit = QPushButton("Dopasuj")
        for b, w in ((b_out, 34), (b_in, 34), (b_100, 64), (b_fit, 74)):
            b.setFixedWidth(w)
        b_out.clicked.connect(lambda: self.zoom_at(0.8))
        b_in.clicked.connect(lambda: self.zoom_at(1.25))
        b_100.clicked.connect(lambda: self.set_zoom(1.0))
        b_fit.clicked.connect(self.zoom_fit)
        self.lb_zoom = QLabel()
        zrow = QHBoxLayout()
        zrow.addWidget(QLabel("Widok:"))
        for b in (b_out, b_in, b_100, b_fit):
            zrow.addWidget(b)
        zrow.addWidget(self.lb_zoom)
        hint = QLabel("kółko myszy – przybliż / oddal  •  przeciągnij – przesuń widok  •  "
                      "przeciągnij ramkę arkusza – przesuń arkusz  •  dwuklik – przybliż")
        hint.setStyleSheet("color:#666")
        zrow.addSpacing(16)
        zrow.addWidget(hint)
        zrow.addStretch(1)

        left = QVBoxLayout()
        left.addLayout(grid)
        left.addLayout(zrow)

        b_copy = QPushButton("Kopiuj jako obraz")
        b_copy.setToolTip("Kopiuje cały przekrój do schowka (Ctrl+V w Wordzie, Paint, AutoCAD…)")
        b_png = QPushButton("Zapisz obraz…")
        b_exp = QPushButton("Eksportuj…")
        b_exp.setIcon(syrop_icon())
        b_head = QPushButton("Opis…")
        b_head.setToolTip("Edycja nagłówka: tytuł, linia z danymi, podpisy skal (także dwuklik w nagłówek)")
        b_head.clicked.connect(self.edit_header)
        b_sheet = QPushButton("Arkusz…")
        b_sheet.setToolTip("Format arkusza, orientacja, marginesy i położenie rysunku")
        b_print = QPushButton("Drukuj…")
        self.print_menu = QMenu(b_print)
        self.act_pdf = self.print_menu.addAction("Drukuj do pliku PDF…")
        self.act_prn = self.print_menu.addAction("Drukuj na drukarce…")
        self.print_menu.addSeparator()
        self.act_dark = self.print_menu.addAction("Drukuj w kolorystyce ekranowej (granatowe tło) – tylko ten raz")
        self.act_dark.setCheckable(True)
        self.act_dark.setChecked(False)
        self.act_pdf.triggered.connect(lambda: self.print_doc(True))
        self.act_prn.triggered.connect(lambda: self.print_doc(False))
        b_print.setMenu(self.print_menu)
        b_close = QPushButton("Zamknij")
        b_copy.clicked.connect(self.copy_image)
        b_png.clicked.connect(self.save_image)
        b_exp.clicked.connect(self.export)
        b_sheet.clicked.connect(self.sheet_settings)
        b_close.clicked.connect(self.close)
        btns = QGridLayout()
        for n, b in enumerate((b_copy, b_head, b_png, b_sheet, b_exp, b_print, b_close)):
            b.setAutoDefault(False)
            btns.addWidget(b, n // 2, n % 2)
        b_apply.setAutoDefault(False)

        top = QHBoxLayout()
        top.addLayout(left, 1)
        top.addSpacing(12)
        top.addLayout(btns)

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.scroll.viewport().setStyleSheet("background-color:#0a1633;")

        self.lb_status = QLabel()
        self.lb_status.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.scroll, 1)
        lay.addWidget(self.lb_status)

        self.update_labels()
        self.resize(1180, 740)

    # --- zamykanie
    def closeEvent(self, e):
        try:
            _open_windows().remove(self)
        except ValueError:
            pass
        super().closeEvent(e)

    def reject(self):
        self.close()

    # --- skale i jednostki
    def apply_scales(self):
        try:
            hs, vs = int(self.ed_h.text()), int(self.ed_v.text())
        except ValueError:
            self.ed_h.setText(str(self.canvas.hs))
            self.ed_v.setText(str(self.canvas.vs))
            return
        if hs < 1 or vs < 1:
            return
        if (hs, vs) != (self.canvas.hs, self.canvas.vs):
            self.canvas.set_scales(hs, vs)
            self.update_labels()

    def default_scales(self):
        hs, vs = self.canvas.default_scales
        self.canvas.set_scales(hs, vs)
        self.update_labels()

    def edit_header(self):
        dlg = HeaderDialog(self.canvas, self)
        if dlg.exec():
            dlg.apply()
            self.update_labels()

    def apply_units(self):
        self.canvas.set_units(self.cb_uh.currentData(), self.cb_uv.currentData())
        self.update_labels()

    def on_vertices(self, on):
        self.canvas.show_vertices = bool(on)
        self.canvas.update()

    # --- powiększenie / przesuwanie
    def _bars(self):
        return self.scroll.horizontalScrollBar(), self.scroll.verticalScrollBar()

    def zoom_at(self, factor, pos=None):
        c = self.canvas
        hb, vb = self._bars()
        vp = self.scroll.viewport()
        if pos is None:  # środek widoku
            pos = QPointF(hb.value() + vp.width() / 2.0, vb.value() + vp.height() / 2.0)
        vx, vy = pos.x() - hb.value(), pos.y() - vb.value()
        old = c.zoom
        c.zoom = old * factor
        c.apply_zoom()
        k = c.zoom / old
        hb.setValue(int(round(pos.x() * k - vx)))
        vb.setValue(int(round(pos.y() * k - vy)))
        self.update_zoom_label()

    def set_zoom(self, z):
        self.canvas.zoom = z
        self.canvas.apply_zoom()
        self.update_zoom_label()

    def zoom_fit(self):
        vp = self.scroll.viewport()
        c = self.canvas
        self.set_zoom(min((vp.width() - 4) / float(c.tw), (vp.height() - 4) / float(c.th)))

    def pan_by(self, dx, dy):
        hb, vb = self._bars()
        hb.setValue(int(round(hb.value() + dx)))
        vb.setValue(int(round(vb.value() + dy)))

    def update_zoom_label(self):
        self.lb_zoom.setText(f"  powiększenie <b>{fnum(self.canvas.zoom * 100, 0)} %</b>")

    def update_labels(self):
        c = self.canvas
        L = c.lay
        self.ed_h.setText(str(L.hs))
        self.ed_v.setText(str(L.vs))
        self.lb_exag.setText(f"Przewyższenie: <b>{fnum(L.exag, decimals_for(L.exag))}×</b>")
        self.update_zoom_label()
        pr = self.profile
        self.lb_status.setText(
            f"Długość {L.fd(pr.length)}  •  wierzchołków {pr.nverts}  •  części {len(pr.parts)}  •  "
            f"H: {L.fh_(pr.hmin)} – {L.fh_(pr.hmax)}  •  poziom porównawczy {L.fh_(L.h0)}  •  "
            f"wykres {L.w_mm} × {L.h_mm} mm  •  układ źródłowy EPSG:{pr.epsg}  •  "
            f"skala na ekranie dokładna przy powiększeniu 100 % ({fnum(c.ppm * 25.4, 0)} dpi)"
            + (f"  •  {c.sheet.label()}: " + ("rysunek mieści się w marginesach" if c.fits_sheet()
                                              else "<b>rysunek wychodzi poza marginesy</b>")
               if c.sheet.enabled else ""))

    # --- arkusz
    def sheet_settings(self):
        c = self.canvas
        dlg = SheetDialog(c.sheet, self)
        if not dlg.exec():
            return
        dlg.apply()
        c.update_extent()
        self.update_labels()

    # --- wydruk
    def print_doc(self, to_pdf):
        c = self.canvas
        if QPrinter is None:
            QMessageBox.warning(self, SCRIPT_NAME, "Moduł drukowania Qt (QtPrintSupport) jest niedostępny.")
            return
        light = not self.act_dark.isChecked()   # domyślnie zawsze: białe tło, czarna treść
        self.act_dark.setChecked(False)
        if not c.sheet.enabled:
            c.sheet.enabled = True
            c.sheet.save()
            c.update_extent()
            self.update_labels()
        if not c.fits_sheet():
            r = QMessageBox.question(
                self, SCRIPT_NAME,
                f"Rysunek nie mieści się w marginesach arkusza {c.sheet.label()}.\n"
                "Część wychodząca poza marginesy nie zostanie wydrukowana.\n\n"
                "Zmień format w „Arkusz…”, przesuń ramkę arkusza albo zmień skalę.\nDrukować mimo to?")
            if r != QMessageBox.StandardButton.Yes:
                return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(f"{SCRIPT_NAME} – {self.profile.name}")
        self.setup_page(printer)
        if to_pdf:
            start = os.path.join(QSettings().value(SETTINGS + "out_dir", "", type=str), "przekroj.pdf")
            path, _ = QFileDialog.getSaveFileName(self, "Drukuj do PDF", start, "PDF (*.pdf)")
            if not path:
                return
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
        else:
            dlg = QPrintDialog(printer, self)
            dlg.setWindowTitle(f"{SCRIPT_NAME} – drukuj ({c.sheet.label()})")
            if not dlg.exec():
                return
            self.setup_page(printer)  # format arkusza ma pierwszeństwo przed ustawieniem z okna
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            c.print_sheet(printer, "paper" if light else "screen")
        except Exception as ex:
            QGuiApplication.restoreOverrideCursor()
            report_error("Drukowanie")
            QMessageBox.critical(self, SCRIPT_NAME, f"Drukowanie nie powiodło się:\n{ex}")
            return
        QGuiApplication.restoreOverrideCursor()
        if to_pdf:
            QSettings().setValue(SETTINGS + "out_dir", os.path.dirname(path))
            QMessageBox.information(self, SCRIPT_NAME, f"Zapisano PDF ({c.sheet.label()}):\n{path}")
        else:
            QMessageBox.information(self, SCRIPT_NAME, f"Wysłano do drukarki: {printer.printerName()}")

    def setup_page(self, printer):
        sh = self.canvas.sheet
        w, h = sh.size()
        ids = getattr(QPageSize, "PageSizeId", QPageSize)
        if sh.fmt in PAPER:
            ps = QPageSize(getattr(ids, sh.fmt))
        else:
            ps = QPageSize(QSizeF(min(w, h), max(w, h)), QPageSize.Unit.Millimeter, "Syrop – własny",
                           QPageSize.SizeMatchPolicy.ExactMatch)
        orient = QPageLayout.Orientation.Landscape if w > h else QPageLayout.Orientation.Portrait
        printer.setFullPage(True)
        printer.setPageLayout(QPageLayout(ps, orient, QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter))

    # --- obraz
    def copy_image(self):
        try:
            img = self.canvas.render_image()
        except Exception as ex:
            QMessageBox.warning(self, SCRIPT_NAME, str(ex))
            return
        QGuiApplication.clipboard().setImage(img)
        QMessageBox.information(self, SCRIPT_NAME,
                                f"Skopiowano cały przekrój do schowka ({img.width()} × {img.height()} px).")

    def save_image(self):
        start = os.path.join(QSettings().value(SETTINGS + "out_dir", "", type=str), "przekroj.png")
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz obraz przekroju", start,
                                              "PNG (*.png);;JPEG (*.jpg);;TIFF (*.tif)")
        if not path:
            return
        try:
            img = self.canvas.render_image()
        except Exception as ex:
            QMessageBox.warning(self, SCRIPT_NAME, str(ex))
            return
        if not img.save(path):
            QMessageBox.warning(self, SCRIPT_NAME, "Nie udało się zapisać obrazu.")
            return
        QSettings().setValue(SETTINGS + "out_dir", os.path.dirname(path))
        QMessageBox.information(self, SCRIPT_NAME, f"Zapisano obraz:\n{path}")

    # --- eksport
    def export(self):
        dlg = ExportDialog(self.profile, self, self.canvas.sheet.enabled)
        if not dlg.exec():
            return
        fmt, epsg, path = dlg.fmt(), dlg.epsg(), dlg.ed_path.text().strip()
        el = dlg.elements()
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            outs = self.do_export(fmt, epsg, path, el)
        except Exception as ex:
            QGuiApplication.restoreOverrideCursor()
            report_error("Eksport")
            QMessageBox.critical(self, SCRIPT_NAME, f"Eksport nie powiódł się:\n{ex}")
            return
        QGuiApplication.restoreOverrideCursor()
        if outs is None:
            return
        if dlg.chk_add.isChecked() and iface is not None:
            self.add_to_project(outs, epsg)
        QMessageBox.information(self, SCRIPT_NAME, "Zapisano:\n" + "\n".join(sorted({o[0] for o in outs})))

    def sheet_frames_model(self):
        """Granice arkusza i marginesów w jednostkach rysunku lokalnego (Y do góry)."""
        c = self.canvas
        if not c.sheet.enabled:
            return []
        u = c.lay.mh
        ox, oy = c.ox(), c.oy()
        res = []
        for r, lay in ((c.sheet_rect(), "PRZ_ARKUSZ"), (c.margin_rect(), "PRZ_MARGINESY")):
            x0 = (r.left() - ox) / c.ppm * u
            x1 = (r.right() - ox) / c.ppm * u
            y0 = (oy - r.bottom()) / c.ppm * u
            y1 = (oy - r.top()) / c.ppm * u
            res.append((x0, y0, x1, y1, lay))
        return res

    def do_export(self, fmt, epsg, path, el=None):
        el = {k for k, _l, d in EXPORT_ELEMENTS if d} if el is None else el
        pr, L = self.profile, self.canvas.lay
        dh = pr.dh_parts()
        if epsg == LOCAL:
            parts = [[(d, (h - L.h0) * L.exag, 0.0) for d, h in p] for p in dh]
        else:
            dst = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")
            ct = None if dst == pr.crs else QgsCoordinateTransform(pr.crs, dst, QgsProject.instance())
            parts = []
            for p in pr.parts:
                q = []
                for x, y, z, _d in p:
                    if ct is not None:
                        t = ct.transform(QgsPointXY(x, y))
                        x, y = t.x(), t.y()
                    q.append((x, y, z))
                parts.append(q)
        pts = [(x, y, z, d, h) for p, s in zip(parts, dh) for (x, y, z), (d, h) in zip(p, s)]
        uklad = LOCAL_LABEL if epsg == LOCAL else f"EPSG:{epsg}"
        meta = {"nazwa": pr.name, "dlugosc_m": round(pr.length, 4), "skala_poz": f"1:{L.hs}",
                "skala_pion": f"1:{L.vs}", "przewysz": L.exag, "h_porown": L.h0, "uklad": uklad}

        if epsg == LOCAL:
            dx = build_local_dxf(dh, L, self.canvas.header_export(), self.canvas.show_vertices, el,
                                 self.sheet_frames_model())
        else:
            th = 2.0 * L.hs / 1000.0
            if epsg == 4326:
                th /= 111320.0
            dx = build_geo_dxf(parts, dh, th, L, el)

        if fmt in ("SHP", "GPKG", "KML"):
            return write_gis(path, fmt, epsg, parts, pts, meta, dx, el)

        # DGN – przez GDAL
        if fmt == "DGN":
            return write_dgn(path, dx, epsg != LOCAL)

        # DXF / DWG – wszystkie opisy jako encje TEXT
        if fmt == "DXF":
            dx.save(path)
            return [(path, None, "cad")]
        exe = ask_oda(self)
        if not exe:
            return None
        tmp = os.path.join(tempfile.mkdtemp(prefix="syrop_dxf_"),
                           os.path.splitext(os.path.basename(path))[0] + ".dxf")
        dx.save(tmp)
        dwg = oda_convert(exe, tmp, "DWG", "ACAD2018")
        if os.path.exists(path):
            os.remove(path)
        shutil.move(dwg, path)
        return [(path, None, "cad")]

    def add_to_project(self, outs, epsg):
        for pth, lname, kind in outs:
            if pth.lower().endswith((".dwg", ".dgn")):
                continue
            uri = pth if lname is None else f"{pth}|layername={lname}"
            nm = os.path.splitext(os.path.basename(pth))[0] if lname is None else lname
            lyr = iface.addVectorLayer(uri, nm, "ogr")
            if lyr is None:
                continue
            if epsg != LOCAL and pth.lower().endswith(".dxf"):
                lyr.setCrs(QgsCoordinateReferenceSystem(f"EPSG:{epsg}"))
            if kind == "opisy":
                apply_text_labels(lyr)


# ---------------------------------------------------------------------------
#  Uruchomienie
# ---------------------------------------------------------------------------
def syrop_wykreslny():
    parent = iface.mainWindow() if iface is not None else None
    dlg = InputDialog(parent)
    ok = dlg.exec()
    profile = dlg.profile
    dlg.deleteLater()
    if not ok or profile is None:
        return
    win = ProfileWindow(profile, parent)
    win.show()
    win.raise_()
    win.activateWindow()


def install_toolbar_action():
    """Dodaje ikonę buteleczki na pasek wtyczek (na czas bieżącej sesji QGIS)."""
    if iface is None:
        return
    mw = iface.mainWindow()
    act = mw.findChild(QAction, ACTION_NAME)
    if act is None:
        act = QAction(syrop_icon(), SCRIPT_NAME, mw)
        act.setObjectName(ACTION_NAME)
        act.setToolTip(f"{SCRIPT_NAME} {SCRIPT_VERSION} – przekrój z linii 3D")
        iface.addToolBarIcon(act)
    else:
        try:
            act.triggered.disconnect()
        except Exception:
            pass
    act.triggered.connect(syrop_wykreslny)


install_toolbar_action()
syrop_wykreslny()