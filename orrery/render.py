#!/usr/bin/env python3
"""Orrery: the solar system as it is right now, drawn to a PNG for the
Noctalia desktop widget (desktop.luau).

    render.py <out.png> [scale] [font] [table font] [font size] [zodiac]
              [zodiac label 0|1] [zodiac label size] [order heliocentric|geocentric]
              [show GC 0|1] [show GA 0|1] [show nodes 0|1]

zodiac is "fagan-bradley" (default, sidereal signs) or "tropical".

Positions: Swiss Ephemeris (pyswisseph). Planets use the built-in Moshier
theory; Chiron comes from ephe/seas_18.se1. Longitudes are heliocentric,
tropical, of date. ORRERY_TIME=<unix time> renders another moment.

View: the ecliptic seen obliquely from the north, 0 deg Aries on the right,
Cancer at the back. Distances are compressed (piecewise linear through the
planets' mean distances) so the inner planets stay visible; orbits and
bodies are drawn at their true inclination to the ecliptic (HEIGHT_X). The
outer band is the zodiac; the sign the Sun is in as seen from Earth (the one
Earth looks at across the Sun) is highlighted, with a dashed sight line from
Earth through the Sun.
"""
import json
import math
import os
import random
import sys
import time

import cairo
import swisseph as swe

HERE = os.path.dirname(os.path.abspath(__file__))
swe.set_ephe_path(os.path.join(HERE, "ephe"))

W = 900                         # design width; the height grows with the font size
TABLE_Y = 470                   # top of the table (the orrery sits above)
CX, CY = 450, 250               # Sun on screen
R_ZOD = 420                     # outer edge of the zodiac band (x radius)
TILT = 0.40                     # vertical squash of the ecliptic plane
HEIGHT_X = 1                    # exaggeration of heights above the ecliptic (1 = true)
BODY_X = 1.4                    # scale of the drawn Sun, planets and GC
ZOD_SIZE = 26                   # zodiac glyphs (px)
BAND_IN = 0.92                  # inner edge of the zodiac band (fraction of R_ZOD)
BAND_EXTRA = 18                 # extra height of the band's outer edge (px), so the
                                # band is about as wide at the front and back as at the sides
FONT = "DejaVu Sans"            # labels and titles (widget setting "font")
MONO = "DejaVu Sans Mono"       # table (widget setting "table_font")
GLYPHS = "DejaVu Sans"          # Greek letters in the table header: many mono fonts lack them
TEXT_K = 1.0                    # font size setting / 14, the design size of the table text


def canvas_height(k, rows):
    """Must match desktop.luau, which sizes the widget from it."""
    return math.floor(TABLE_Y + (70 + 25 * rows) * k)

#            name        swe id         mean AU  colour (r,g,b)          size  period (days)
PLANETS = [
    ("Mercury", swe.MERCURY, 0.387, (0.80, 0.78, 0.74), 3.5, 87.97),
    ("Venus",   swe.VENUS,   0.723, (0.95, 0.85, 0.55), 5.5, 224.70),
    ("Earth",   swe.EARTH,   1.000, (0.30, 0.55, 1.00), 6.0, 365.26),
    ("Mars",    swe.MARS,    1.524, (0.95, 0.40, 0.20), 4.5, 686.98),
    ("Jupiter", swe.JUPITER, 5.203, (0.93, 0.55, 0.25), 11.0, 4332.6),
    ("Saturn",  swe.SATURN,  9.537, (0.92, 0.80, 0.50), 9.0, 10759.2),
    ("Chiron",  swe.CHIRON,  13.69, (0.75, 0.70, 0.85), 3.5, 18500.0),
    ("Uranus",  swe.URANUS,  19.19, (0.55, 0.90, 0.95), 7.0, 30688.5),
    ("Neptune", swe.NEPTUNE, 30.07, (0.35, 0.50, 1.00), 7.0, 60182.0),
    ("Pluto",   swe.PLUTO,   39.48, (0.80, 0.68, 0.58), 3.0, 90560.0),
]
# Galactic center (Sgr A*): ecliptic J2000 position, distance 8.18 kpc (GRAVITY 2019).
GC_LON, GC_LAT = 266.8517, -5.5361
GC_AU = 8178 * 206264.806
GC_LY = 8178 * 3.26156
GC_SIZE = 3.5                   # drawn like Chiron
# Great Attractor: galactic l = 307, b = +9 (Lynden-Bell et al. 1988) as ecliptic
# J2000, at cz ~ 4350 km/s, about 62 Mpc. Drawn on the band like the GC.
GA_LON, GA_LAT = 222.0406, -41.2807
GA_AU = 62e6 * 206264.806
GA_LY = 62e6 * 3.26156
GA_COL = (1.0, 1.0, 1.0)        # a white, glowing ball

# Picture labels: astrological symbols (keys of symbols.json); GC and GA keep
# their names.
SYMBOLS = {"Moon": "moon", "Mercury": "mercury", "Venus": "venus", "Earth": "earth",
           "Mars": "mars", "Jupiter": "jupiter", "Saturn": "saturn", "Chiron": "chiron",
           "Uranus": "uranus", "Neptune": "neptune", "Pluto": "pluto",
           "North Node": "north-node", "South Node": "south-node"}
# Table Object column: the same symbols plus the Sun; GC and GA keep their names.
TABLE_SYMBOLS = dict(SYMBOLS, Sun="sun")
TABLE_SYM_PX = 18                    # symbol size in the table (text is 14)
TABLE_SYM_K = {"north-node": 0.82, "south-node": 0.82}   # the nodes look big

# The Moon's nodes (true node, geocentric) are marked on the inner edge of the
# zodiac band at their longitude, like the galactic center.
NODES = ("North Node", "South Node")
SUN_COL = (1.0, 0.82, 0.35)
NODE_COL = (0.85, 0.45, 0.40)

# Table order. Heliocentric: the Sun, then by distance from it. Geocentric: Earth
# (the centre) first, then the Sun, then the Moon's nodes in place of the Moon, then the rest.
ORDERS = {
    "heliocentric": ["Sun", "Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Chiron",
                     "Uranus", "Neptune", "Pluto", "GC", "GA", "North Node", "South Node"],
    "geocentric":   ["Earth", "Sun", "North Node", "South Node", "Mercury", "Venus", "Mars", "Jupiter",
                     "Saturn", "Chiron", "Uranus", "Neptune", "Pluto", "GC", "GA"],
}

# The Moon: drawn on a small circle around Earth (its real orbit would be
# invisible at this scale), in the direction it is seen from Earth.
MOON_R = 0.075                  # radius of that circle, fraction of R_ZOD
MOON_COL = (0.82, 0.82, 0.80)
MOON_SIZE = 2.2
SYM_SIZE = 17                   # symbol labels, scaled with the font size like the text

SIGNS = "♈♉♊♋♌♍♎♏♐♑♒♓"            # in table cells; drawn as the symbols below
SIGN_KEYS = dict(zip(SIGNS, ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra",
                             "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]))

# Distance compression: AU -> fraction of the inner radius of the zodiac band.
# Pluto (29.7-49.3 AU) stays inside the band. Chiron is left out of the knots (its orbit is very eccentric) and simply
# follows the curve between Saturn and Uranus.
KNOTS = [(0.0, 0.0), (0.0001, 0.10), (0.387, 0.17), (0.723, 0.25), (1.0, 0.33),
         (1.524, 0.41), (5.203, 0.53), (9.537, 0.64), (19.19, 0.76), (30.07, 0.84),
         (50.0, 0.91)]


def squash(au):
    for (a0, f0), (a1, f1) in zip(KNOTS, KNOTS[1:]):
        if au <= a1:
            return f0 + (f1 - f0) * (au - a0) / (a1 - a0)
    return KNOTS[-1][1]


def project(lon_deg, frac, z_frac=0.0):
    """Ecliptic longitude + compressed radius (+ height) -> screen x, y, depth."""
    a = math.radians(lon_deg)
    x = math.cos(a) * frac * R_ZOD
    y = math.sin(a) * frac * R_ZOD           # positive = towards the back
    return CX + x, CY - y * TILT - z_frac * R_ZOD, y


def helio(jd, pid):
    flags = swe.FLG_HELCTR | (0 if pid == swe.CHIRON else swe.FLG_MOSEPH)
    r, _ = swe.calc_ut(jd, pid, flags)
    return r[0], r[1], r[2]


def geo_distance(jd, pid):
    flags = swe.FLG_TRUEPOS | (0 if pid == swe.CHIRON else swe.FLG_MOSEPH)
    r, _ = swe.calc_ut(jd, pid, flags)
    return r[2]


def sphere(cr, x, y, rad, col, glow=0.0):
    if glow:
        g = cairo.RadialGradient(x, y, rad * 0.5, x, y, rad * (1 + glow))
        g.add_color_stop_rgba(0, *col, 0.35)
        g.add_color_stop_rgba(1, *col, 0.0)
        cr.set_source(g)
        cr.arc(x, y, rad * (1 + glow), 0, 2 * math.pi)
        cr.fill()
    g = cairo.RadialGradient(x - rad * 0.35, y - rad * 0.35, rad * 0.1, x, y, rad)
    g.add_color_stop_rgb(0, *[min(1, c * 1.25 + 0.15) for c in col])
    g.add_color_stop_rgb(0.7, *col)
    g.add_color_stop_rgb(1, *[c * 0.45 for c in col])
    cr.set_source(g)
    cr.arc(x, y, rad, 0, 2 * math.pi)
    cr.fill()


ELEV = math.asin(TILT)          # viewing angle above the ecliptic plane
AMBIENT = 0.20                  # light on the night side, so planets in front of the Sun stay visible


def lit_sphere(cr, x, y, rad, col, light, glow=0.0):
    """A planet lit by the Sun. light = direction to the Sun in the picture's
    3D frame (x right, y towards the back, z up); the disc is shaded per pixel,
    so a planet in front of the Sun shows a crescent, one behind it is full."""
    if glow:
        g = cairo.RadialGradient(x, y, rad * 0.5, x, y, rad * (1 + glow))
        g.add_color_stop_rgba(0, *col, 0.30)
        g.add_color_stop_rgba(1, *col, 0.0)
        cr.set_source(g)
        cr.arc(x, y, rad * (1 + glow), 0, 2 * math.pi)
        cr.fill()
    lx, ly, lz = light
    n = math.sqrt(lx * lx + ly * ly + lz * lz) or 1
    lx, ly, lz = lx / n, ly / n, lz / n
    se, ce = math.sin(ELEV), math.cos(ELEV)
    sx, sy, sz = lx, ly * se + lz * ce, -ly * ce + lz * se   # screen right, up, towards viewer
    hx, hy, hz = sx, sy, sz + 1                              # half vector for the sheen
    hn = math.sqrt(hx * hx + hy * hy + hz * hz) or 1
    hx, hy, hz = hx / hn, hy / hn, hz / hn
    dev = cr.get_matrix().xx                                 # device pixels per unit
    R = rad * dev
    size = int(math.ceil(2 * R)) + 2
    img = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    stride = img.get_stride()
    buf = bytearray(stride * size)
    c0 = size / 2
    for j in range(size):
        v = (c0 - (j + 0.5)) / R
        row = j * stride
        for i in range(size):
            u = ((i + 0.5) - c0) / R
            rr = u * u + v * v
            cov = min(1.0, max(0.0, (1 - math.sqrt(rr)) * R + 0.5))
            if cov <= 0:
                continue
            w = math.sqrt(max(0.0, 1 - min(rr, 1)))
            d = u * sx + v * sy + w * sz
            lit = AMBIENT + (1 - AMBIENT) * max(0.0, (d + 0.12) / 1.12) ** 0.9   # soft terminator
            spec = max(0.0, u * hx + v * hy + w * hz) ** 24 * 0.25 if d > 0 else 0
            limb = 0.85 + 0.15 * w
            px = []
            for c in col:
                px.append(min(1.0, c * lit * limb + spec) * cov)
            o = row + i * 4                                  # BGRA, premultiplied
            buf[o] = int(px[2] * 255)
            buf[o + 1] = int(px[1] * 255)
            buf[o + 2] = int(px[0] * 255)
            buf[o + 3] = int(cov * 255)
    img.get_data()[:] = buf
    img.mark_dirty()
    cr.save()
    cr.translate(x - size / 2 / dev, y - size / 2 / dev)
    cr.scale(1 / dev, 1 / dev)
    cr.set_source_surface(img, 0, 0)
    cr.paint()
    cr.restore()


def sun_sphere(cr, x, y, rad, glow=1.6):
    """The Sun: a soft corona and a disc darkening towards its rim."""
    g = cairo.RadialGradient(x, y, rad * 0.6, x, y, rad * (1 + glow))
    g.add_color_stop_rgba(0, 1.0, 0.82, 0.40, 0.55)
    g.add_color_stop_rgba(0.35, 1.0, 0.70, 0.25, 0.20)
    g.add_color_stop_rgba(1, 1.0, 0.60, 0.20, 0.0)
    cr.set_source(g)
    cr.arc(x, y, rad * (1 + glow), 0, 2 * math.pi)
    cr.fill()
    g = cairo.RadialGradient(x, y, 0, x, y, rad)
    g.add_color_stop_rgb(0, 1.0, 0.98, 0.88)
    g.add_color_stop_rgb(0.55, 1.0, 0.92, 0.62)
    g.add_color_stop_rgb(0.85, 1.0, 0.80, 0.38)
    g.add_color_stop_rgb(1, 0.93, 0.58, 0.18)
    cr.set_source(g)
    cr.arc(x, y, rad, 0, 2 * math.pi)
    cr.fill()


def black_sphere(cr, x, y, rad):
    """The galactic center: a black ball, lit from the upper left like the
    planets, with a faint halo so it stands out against the dark sky."""
    g = cairo.RadialGradient(x, y, rad * 0.8, x, y, rad * 1.9)
    g.add_color_stop_rgba(0, 0.85, 0.88, 1.0, 0.45)
    g.add_color_stop_rgba(1, 0.85, 0.88, 1.0, 0.0)
    cr.set_source(g)
    cr.arc(x, y, rad * 1.9, 0, 2 * math.pi)
    cr.fill()
    g = cairo.RadialGradient(x - rad * 0.4, y - rad * 0.4, rad * 0.05, x, y, rad)
    g.add_color_stop_rgb(0, 0.75, 0.77, 0.82)
    g.add_color_stop_rgb(0.35, 0.22, 0.23, 0.26)
    g.add_color_stop_rgb(1, 0.0, 0.0, 0.0)
    cr.set_source(g)
    cr.arc(x, y, rad, 0, 2 * math.pi)
    cr.fill()


# ------------------------------------------ drawn Saturn, Jupiter and Pluto --
# Astrological symbols are filled outlines from symbols.json (a 100-unit box,
# y down, each symbol centred in it); every op is M/L/C with absolute
# coordinates, or Z.
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "symbols.json")) as _f:
    _SYMS = json.load(_f)
SYM_K = 1.25                    # symbol box size, as a fraction of the font size
SYM_SCALE = {"earth": 0.7, "moon": 0.7, "uranus": 0.8}    # these look heavy at full size


def _sym_path(cr, key):
    for op in _SYMS[key]["ops"]:
        if op[0] == "C":
            cr.curve_to(*op[1:])
        elif op[0] == "L":
            cr.line_to(*op[1:])
        elif op[0] == "M":
            cr.move_to(*op[1:])
        else:
            cr.close_path()


def _sym_extents(key):
    c = cairo.Context(cairo.RecordingSurface(cairo.CONTENT_ALPHA, None))
    _sym_path(c, key)
    return c.fill_extents()


_SYM_EXT = {key: _sym_extents(key) for key in _SYMS}


def symbol(cr, key, x, y, px, col, alpha, align="l", measure=False, centre=False):
    """Draw symbol `key` at font size px. (x, y) is the baseline start like
    show_text (align "r": x is the right end), or with centre=True the middle
    of the symbol. Returns the advance."""
    x0, y0, x1, y1 = _SYM_EXT[key]
    k = SYM_K * SYM_SCALE.get(key, 1) * px / 100
    adv = (x1 - x0) * k + 0.14 * px
    if measure:
        return adv
    if centre:
        ox, oy = x - (x0 + x1) / 2 * k, y - (y0 + y1) / 2 * k
    else:
        if align == "r":
            x -= adv
        ox, oy = x + 0.07 * px - x0 * k, y - 0.34 * px - 50 * k
    rule = cairo.FILL_RULE_EVEN_ODD if _SYMS[key].get("evenodd") else cairo.FILL_RULE_WINDING
    for d, c, a in ((1, (0, 0, 0), 0.6 * alpha), (0, col, alpha)):
        cr.save()
        cr.translate(ox + d, oy + d)
        cr.scale(k, k)
        _sym_path(cr, key)
        cr.restore()
        cr.set_fill_rule(rule)
        cr.set_source_rgba(*c, a)
        cr.fill()
    cr.set_fill_rule(cairo.FILL_RULE_WINDING)
    return adv

def text(cr, s, x, y, size, col=(1, 1, 1), alpha=0.85, font=None, align="l", bold=False, k=None):
    cr.select_font_face(font or FONT, cairo.FONT_SLANT_NORMAL,
                        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size * (TEXT_K if k is None else k))
    ext = cr.text_extents(s)
    if align == "c":
        x -= ext.width / 2 + ext.x_bearing
    elif align == "r":
        x -= ext.x_advance
    cr.set_source_rgba(0, 0, 0, 0.6 * alpha)
    cr.move_to(x + 1, y + 1)
    cr.show_text(s)
    cr.set_source_rgba(*col, alpha)
    cr.move_to(x, y)
    cr.show_text(s)
    return ext.x_advance


def ellipse_path(cr, frac):
    cr.save()
    cr.translate(CX, CY)
    cr.scale(frac * R_ZOD, frac * R_ZOD * TILT)
    cr.arc(0, 0, 1, 0, 2 * math.pi)
    cr.restore()


def band(lon_deg, t):
    """Point across the zodiac band at longitude lon_deg: t = 0 inner edge, 1 outer.
    The outer edge is taller than a true projection (BAND_EXTRA), otherwise the
    tilt would squeeze the band at the front and back below the glyph size."""
    x0, y0, _ = project(lon_deg, BAND_IN)
    a = math.radians(lon_deg)
    x1 = CX + math.cos(a) * R_ZOD
    y1 = CY - math.sin(a) * (R_ZOD * TILT + BAND_EXTRA)
    return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t


def band_outer_path(cr):
    cr.save()
    cr.translate(CX, CY)
    cr.scale(R_ZOD, R_ZOD * TILT + BAND_EXTRA)
    cr.arc(0, 0, 1, 0, 2 * math.pi)
    cr.restore()


def sector_path(cr, lon0, lon1, steps=24):
    """One sign's sector of the zodiac band."""
    pts = [band(lon0 + (lon1 - lon0) * i / steps, 1) for i in range(steps + 1)]
    pts += [band(lon1 - (lon1 - lon0) * i / steps, 0) for i in range(steps + 1)]
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.close_path()


def precess_lon(lon, jd):
    """J2000 ecliptic longitude of a fixed object precessed to the date."""
    t = (jd - 2451545.0) / 36525
    return (lon + (5028.796195 * t + 1.1054348 * t * t) / 3600) % 360


def fmt_light(au):
    minutes = au * 499.004784 / 60
    return f"{minutes:.1f} m" if minutes < 60 else f"{minutes / 60:.1f} h"


def main():
    global FONT, MONO, TEXT_K
    out = sys.argv[1]
    scale = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    if len(sys.argv) > 3 and sys.argv[3].strip():
        FONT = sys.argv[3].strip()
    if len(sys.argv) > 4 and sys.argv[4].strip():
        MONO = sys.argv[4].strip()
    if len(sys.argv) > 5 and sys.argv[5].strip():
        TEXT_K = float(sys.argv[5]) / 14
    sidereal = not (sys.argv[6] if len(sys.argv) > 6 else "").strip().lower().startswith("trop")
    show_zodiac = (sys.argv[7] if len(sys.argv) > 7 else "1").strip() != "0"
    zodiac_px = float(sys.argv[8]) if len(sys.argv) > 8 and sys.argv[8].strip() else 20.0
    order = ORDERS["geocentric" if len(sys.argv) > 9 and sys.argv[9].strip().lower().startswith("geo")
                   else "heliocentric"]
    flag = lambda i: (sys.argv[i] if len(sys.argv) > i else "1").strip() != "0"
    hidden = set()
    if not flag(10):
        hidden.add("GC")
    if not flag(11):
        hidden.add("GA")
    if not flag(12):
        hidden.update(NODES)
    order = [name for name in order if name not in hidden]
    now = float(os.environ.get("ORRERY_TIME") or time.time())
    tm = time.gmtime(now)
    jd = swe.julday(tm.tm_year, tm.tm_mon, tm.tm_mday,
                    tm.tm_hour + tm.tm_min / 60 + tm.tm_sec / 3600)

    H = canvas_height(TEXT_K, len(order))
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, math.ceil(W * scale), math.ceil(H * scale))
    cr = cairo.Context(surf)
    # exact (unrounded) letter widths, so text is the same size in the Orrery and
    # the Ephemeris whatever resolution each lays its text out at
    fo = cairo.FontOptions()
    fo.set_hint_metrics(cairo.HINT_METRICS_OFF)
    cr.set_font_options(fo)
    cr.scale(scale, scale)

    # faint stars (fixed pattern, so they do not flicker between frames)
    rnd = random.Random(7)
    for _ in range(140):
        x, y = rnd.uniform(10, W - 10), rnd.uniform(10, H - 10)
        cr.set_source_rgba(1, 1, 1, rnd.uniform(0.08, 0.35))
        cr.arc(x, y, rnd.uniform(0.4, 1.1), 0, 2 * math.pi)
        cr.fill()

    pos = {}
    for name, pid, _, _, _, _ in PLANETS:
        pos[name] = helio(jd, pid)
    sun = swe.calc_ut(jd, swe.SUN, swe.FLG_MOSEPH)[0]   # as seen from Earth
    pos["Sun"] = (sun[0], sun[1], None)
    pos["GC"] = (precess_lon(GC_LON, jd), GC_LAT, GC_AU)
    pos["GA"] = (precess_lon(GA_LON, jd), GA_LAT, GA_AU)
    nn = swe.calc_ut(jd, swe.TRUE_NODE, swe.FLG_MOSEPH)[0][0]
    pos["North Node"], pos["South Node"] = (nn, 0.0, None), ((nn + 180) % 360, 0.0, None)
    earth_lon = pos["Earth"][0]
    # Signs start at 0 deg tropical Aries, or for the sidereal zodiac at the
    # Fagan/Bradley ayanamsa (bodies stay where they are; only the signs move).
    ayan = 0.0
    if sidereal:
        swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY)
        ayan = swe.get_ayanamsa_ut(jd)
    sun_sign_lon = (earth_lon + 180) % 360            # the Sun's position seen from Earth
    hi = int(((sun_sign_lon - ayan) % 360) // 30)

    # ---- zodiac band ----
    sector_path(cr, hi * 30 + ayan, hi * 30 + 30 + ayan)
    cr.set_source_rgba(0.95, 0.70, 0.25, 0.22)
    cr.fill()
    cr.set_line_width(1)
    for edge in (lambda: ellipse_path(cr, BAND_IN), lambda: band_outer_path(cr)):
        edge()
        cr.set_source_rgba(0.75, 0.80, 0.95, 0.45)
        cr.stroke()
    glyph_boxes = []                                # sign glyphs, kept clear of labels
    for k in range(12):
        x0, y0 = band(k * 30 + ayan, 0)
        x1, y1 = band(k * 30 + ayan, 1)
        cr.move_to(x0, y0)
        cr.line_to(x1, y1)
        cr.set_source_rgba(0.75, 0.80, 0.95, 0.45)
        cr.stroke()
        for d in range(5, 30, 5):
            xa, ya = band(k * 30 + ayan + d, 1)
            xb, yb = band(k * 30 + ayan + d, 1 - (0.3 if d == 15 else 0.18))
            cr.move_to(xa, ya)
            cr.line_to(xb, yb)
            cr.set_source_rgba(0.75, 0.80, 0.95, 0.30)
            cr.stroke()
        gx, gy = band(k * 30 + ayan + 15, 0.5)
        col = (1.0, 0.75, 0.30) if k == hi else (0.80, 0.85, 1.0)
        key = SIGN_KEYS[SIGNS[k]]
        symbol(cr, key, gx, gy, ZOD_SIZE, col, 1.0 if k == hi else 0.7, centre=True)
        ex0, ey0, ex1, ey1 = _SYM_EXT[key]
        hw, hh = (ex1 - ex0) * SYM_K * ZOD_SIZE / 200, (ey1 - ey0) * SYM_K * ZOD_SIZE / 200
        glyph_boxes.append((gx - hw - 2, gx + hw + 2, gy - hh - 2, gy + hh + 2))

    # ---- orbits (true shape and inclination, same projection as the bodies) ----
    for name, pid, au, col, _, period in PLANETS:
        steps = 180
        pts = []
        for i in range(steps + 1):
            lon, lat, r = helio(jd + period * i / steps, pid)
            frac = squash(r)
            pts.append(project(lon, frac, frac * math.sin(math.radians(lat)) * HEIGHT_X)[:2])
        cr.move_to(*pts[0])
        for p in pts[1:]:
            cr.line_to(*p)
        cr.close_path()
        cr.set_line_width(1.6 if name == "Earth" else 1.0)
        cr.set_source_rgba(*col, 0.55 if name == "Earth" else 0.35)
        cr.stroke()

    # ---- sight line Earth -> Sun -> highlighted sign ----
    ex, ey, _ = project(earth_lon, squash(pos["Earth"][2]))
    zx, zy, _ = project(sun_sign_lon, BAND_IN)
    cr.set_dash([4, 5])
    cr.set_line_width(1)
    cr.move_to(ex, ey)
    cr.line_to(zx, zy)
    cr.set_source_rgba(1.0, 0.75, 0.30, 0.45)
    cr.stroke()
    cr.set_dash([])

    # ---- the Moon's (schematic) orbit around Earth ----
    cr.save()
    cr.translate(*project(pos["Earth"][0], squash(pos["Earth"][2]))[:2])
    cr.scale(MOON_R * R_ZOD, MOON_R * R_ZOD * TILT)
    cr.arc(0, 0, 1, 0, 2 * math.pi)
    cr.restore()
    cr.set_source_rgba(*MOON_COL, 0.35)
    cr.set_line_width(0.8)
    cr.stroke()

    # ---- bodies, back to front ----
    bodies = []
    for name, pid, au, col, size, _ in PLANETS:
        lon, lat, r = pos[name]
        frac = squash(r)
        z = frac * math.sin(math.radians(lat)) * HEIGHT_X
        x, y, depth = project(lon, frac, z)
        bx, by, _ = project(lon, frac)
        bodies.append((depth, name, x, y, bx, by, col, size * BODY_X))
    # The galactic center sits on the zodiac band (it is far beyond any scale);
    # its latitude is in the table.
    # On a sign glyph they move toward the band's inner edge (just inside it if need be).
    for name, col in (("GC", (0.0, 0.0, 0.0)), ("GA", GA_COL)):
        if name in hidden:
            continue
        lon = pos[name][0]
        rad = GC_SIZE * BODY_X * 1.4
        for t in (0.5, 0.15, 0.0, -0.15, -0.3):
            gx, gy = band(lon, t)
            if not any(l - rad < gx < r + rad and tp - rad < gy < bt + rad
                       for l, r, tp, bt in glyph_boxes):
                break
        bodies.append((project(lon, BAND_IN)[2], name, gx, gy, gx, gy, col, GC_SIZE * BODY_X))
    bodies.append((0.0, "Sun", CX, CY, CX, CY, SUN_COL, 26 * BODY_X))
    for name in NODES:
        if name in hidden:
            continue
        nx, ny, ndepth = project(pos[name][0], BAND_IN)
        bodies.append((ndepth, name, nx, ny, nx, ny, NODE_COL, 3.2))
    # Moon: geocentric direction, on a circle around Earth (see MOON_R).
    mr, _ = swe.calc_ut(jd, swe.MOON, swe.FLG_MOSEPH)
    e_lon, e_lat, e_r = pos["Earth"]
    e_frac = squash(e_r)
    _, ex0, ey0 = None, *project(e_lon, e_frac)[:2]
    ma = math.radians(mr[0])
    mdx, mdy = math.cos(ma) * MOON_R * R_ZOD, math.sin(ma) * MOON_R * R_ZOD
    mz = MOON_R * math.sin(math.radians(mr[1])) * HEIGHT_X * R_ZOD
    edepth = project(e_lon, e_frac)[2]
    bodies.append((edepth + mdy, "Moon", ex0 + mdx, ey0 - mdy * TILT - mz,
                   ex0 + mdx, ey0 - mdy * TILT, MOON_COL, MOON_SIZE * BODY_X))
    bodies.sort(key=lambda b: -b[0])

    def label_style(name):
        sym = SYMBOLS.get(name)
        return (sym, None, SYM_SIZE) if sym else (name, FONT, 13)

    def label_width(name):
        s, font, px = label_style(name)
        if font is None:
            return symbol(cr, s, 0, 0, px * TEXT_K, None, 0, measure=True)
        cr.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(px * TEXT_K)
        return cr.text_extents(s).x_advance

    labels = []                                     # (name, x, y, align), drawn last
    for depth, name, x, y, bx, by, col, size in bodies:
        if name == "Sun":
            sun_sphere(cr, x, y, size)
            continue
        if name in NODES:                           # small diamond on the band's inner edge
            cr.move_to(x, y - size * 1.3); cr.line_to(x + size, y)
            cr.line_to(x, y + size * 1.3); cr.line_to(x - size, y); cr.close_path()
            cr.set_source_rgba(*col, 0.95); cr.fill_preserve()
            cr.set_source_rgba(0, 0, 0, 0.5); cr.set_line_width(0.8); cr.stroke()
            labels.append((name, x, y, size))
            continue
        if abs(y - by) > 1.5:                       # stalk down to the ecliptic
            cr.move_to(bx, by)
            cr.line_to(x, y)
            cr.set_source_rgba(*col, 0.6)
            cr.set_line_width(1)
            cr.stroke()
            cr.arc(bx, by, 1.5, 0, 2 * math.pi)
            cr.fill()
        if name == "Saturn":                        # ring behind the globe
            cr.save(); cr.translate(x, y); cr.rotate(-0.35); cr.scale(2.2, 0.55)
            cr.arc(0, 0, size, math.pi, 2 * math.pi); cr.restore()
            cr.set_source_rgba(0.95, 0.85, 0.60, 0.8); cr.set_line_width(2.2); cr.stroke()
        if name == "GC":
            black_sphere(cr, x, y, size)
        elif name == "GA":
            sphere(cr, x, y, size, col, glow=2.2)
        else:
            # direction to the Sun: screen x, depth (towards the back) and height
            light = (CX - x, -depth, -(by - y))
            lit_sphere(cr, x, y, size, col, light,
                       glow=0.8 if name in ("Jupiter", "Uranus", "Neptune") else 0)
        if name == "Saturn":                        # ring in front of the globe
            cr.save(); cr.translate(x, y); cr.rotate(-0.35); cr.scale(2.2, 0.55)
            cr.arc(0, 0, size, 0, math.pi); cr.restore()
            cr.set_source_rgba(0.95, 0.85, 0.60, 0.9); cr.set_line_width(2.2); cr.stroke()
        if name == "Earth":
            cr.arc(x, y, size + 3, 0, 2 * math.pi)
            cr.set_source_rgba(0.5, 0.7, 1.0, 0.8); cr.set_line_width(1); cr.stroke()
        labels.append((name, x, y, size * 2.1 if name == "Saturn" else size))   # Saturn: ring

    # Each label takes the first free spot around its body: right, left, above,
    # below, then the diagonals; if all overlap a body or an earlier label (or
    # leave the picture), the same ring is tried a little further out.
    line = SYM_SIZE * TEXT_K * 1.1
    placed = [(x - r, x + r, y - size, y + size)         # (left, right, top, bottom)
              for _, name, x, y, _, _, _, size in bodies if name != "Sun"
              for r in [size * 2.1 if name == "Saturn" else size]] + glyph_boxes

    def spots(bx, by, r, w):
        """Label boxes (left, baseline) around a body, nearest first."""
        up, down = line * 0.2, line * 0.8               # baseline to box bottom / top
        for g in (5, 5 + line * 0.5, 5 + line, 5 + line * 1.5):
            d = (r + g) * 0.75
            yield bx + r + g, by + 13 * TEXT_K * 0.35                # right
            yield bx - r - g - w, by + 13 * TEXT_K * 0.35            # left
            yield bx - w / 2, by - r - g - up                        # above
            yield bx - w / 2, by + r + g + down                      # below
            yield bx + d, by - d - up                                # upper right
            yield bx + d, by + d + down                              # lower right
            yield bx - d - w, by - d - up                            # upper left
            yield bx - d - w, by + d + down                          # lower left

    for name, bx, by, r in labels:
        w = label_width(name)
        box = None
        for x0, y in spots(bx, by, r, w):
            cand = (x0, x0 + w, y - line * 0.8, y + line * 0.2)
            inside = cand[0] >= 8 and cand[1] <= W - 8 and cand[2] >= 8 and cand[3] <= TABLE_Y - 8
            if inside and not any(cand[0] < rr and cand[1] > l and cand[2] < b and cand[3] > t
                                  for l, rr, t, b in placed):
                box = cand
                break
        if box is None:                                   # crowded: right of the body anyway
            x0, y = bx + r + 5, by + 13 * TEXT_K * 0.35
            if x0 + w > W - 8:
                x0 = W - 8 - w
            box = (x0, x0 + w, y - line * 0.8, y + line * 0.2)
        placed.append(box)
        x0, y = box[0], box[3] - line * 0.2
        s, font, px = label_style(name)
        if font is None:
            symbol(cr, s, x0, y, px * TEXT_K, (0.92, 0.94, 1.0), 0.9)
        else:
            text(cr, s, x0, y, px, (0.92, 0.94, 1.0), 0.9, font)

    # ---- table ----
    # Columns are sized to their content, so a large font still fits the width.
    loc = time.localtime(now)
    y0 = TABLE_Y
    k = TEXT_K
    date_w = text(cr, time.strftime("%a %d %b %Y  %H:%M", loc), W - 16, 16 + 14 * k,
                  14, (0.8, 0.84, 0.95), 0.75, align="r")
    if show_zodiac:                                   # size in the same units as "Font size"
        zodiac_s = "Sidereal: Fagan/Bradley" if sidereal else "Tropical"
        cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(zodiac_px)
        room = W - 32 - date_w - 24                   # shrink rather than run into the date
        zodiac_px *= min(1.0, room / cr.text_extents(zodiac_s).x_advance)
        text(cr, zodiac_s, 16, 16 + 14 * k, zodiac_px, (0.8, 0.84, 0.95), 0.75, k=1)
    if HEIGHT_X != 1:
        text(cr, f"heights ×{HEIGHT_X}", W - 40, y0, 13, (0.8, 0.84, 0.95), 0.55, align="r")

    gold, pale = (1.0, 0.75, 0.30), (0.85, 0.88, 1.0)
    rows = []
    for name, pid, au, col, _, _ in ([("Sun", None, 0.0, SUN_COL, 0, 0)] + PLANETS + [("GC", None, GC_AU, (0.0, 0.0, 0.0), GC_SIZE, 0),
                                                ("GA", None, GA_AU, GA_COL, GC_SIZE, 0)]
                                     + [(n, None, None, NODE_COL, 0, 0) for n in NODES]):
        lon, lat, r = pos[name]
        slon = (lon - ayan) % 360
        sign, deg = int(slon // 30), slon % 30
        d, m = int(deg), int(round((deg - int(deg)) * 60))
        if m == 60:
            d, m = d + 1, 0
        if name == "Earth" or name in NODES:
            dist_s, light_s = "—", "—"
        elif name == "Sun":
            dist_s, light_s = f"{sun[2]:.3f}", fmt_light(sun[2])
        elif name == "GC":
            dist_s, light_s = f"{GC_AU:.2e}".replace("e+0", "e"), f"{GC_LY / 1000:.1f}k y"
        elif name == "GA":
            dist_s, light_s = f"{GA_AU:.2e}".replace("e+", "e"), f"{GA_LY / 1e6:.0f}M y"
        else:
            dist = geo_distance(jd, pid)
            dist_s, light_s = f"{dist:.3f}", fmt_light(dist)
        rows.append((name, col, [name, f"{lon:.2f}°", f"{lat:+.2f}°", SIGNS[sign] + f"{d:2d}°{m:02d}'",
                                 "—" if name == "Sun" else dist_s if name in ("GC", "GA") or r is None else f"{r:.3f}",
                                 dist_s, light_s]))
    rows = sorted((row for row in rows if row[0] in order), key=lambda row: order.index(row[0]))
    heads = ["Object", "Lon λ", "Lat β", "Sign", "Sun AU", "Earth AU", "Light"]
    right = [False, True, True, False, True, True, True]

    def width(s, size, font):
        cr.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(size * k)
        return cr.text_extents(s).x_advance

    def cell_width(c, i, size):
        if i == 3:                                   # glyph + gap + degrees
            return (max(symbol(cr, key, 0, 0, (TABLE_SYM_PX - 1) * k, None, 0, measure=True)
                        for key in SIGN_KEYS.values()) + 6 * k + width(c[1:], size, MONO))
        if i == 0 and c in TABLE_SYMBOLS:
            key = TABLE_SYMBOLS[c]
            return symbol(cr, key, 0, 0, TABLE_SYM_PX * TABLE_SYM_K.get(key, 1) * k, None, 0, measure=True)
        return width(c, size, MONO)

    def measure():
        ws = []
        for i, h in enumerate(heads):
            w = max([cell_width(r[2][i], i, 14) for r in rows] + [width(h, 13, MONO)])
            ws.append(w + (22 * k if i == 0 else 0))
        return ws

    widths = measure()
    need = sum(widths) + (len(widths) - 1) * 10 * k
    if need > W - 80:                                # font too large for the width: shrink the table
        k *= (W - 80) / need
        widths = measure()
    dot = 22 * k                                     # coloured dot before the name
    gap = (W - 80 - sum(widths)) / (len(widths) - 1)
    xs, x = [], 40
    for w in widths:
        xs.append((x, x + w))
        x += w + gap

    hy = y0 + 34 * k
    hcol = (0.75, 0.80, 0.95)
    for i, h in enumerate(heads):
        x0, x1 = xs[i]
        if h[-1] in "λβ":                           # Greek from GLYPHS: many mono fonts lack it
            w = text(cr, h[-1], x1, hy, 13, hcol, 0.6, GLYPHS, align="r", k=k)
            text(cr, h[:-1], x1 - w, hy, 13, hcol, 0.6, MONO, align="r", k=k)
        else:
            text(cr, h, x1 if right[i] else x0, hy, 13, hcol, 0.6, MONO, align="r" if right[i] else "l", k=k)
    rowy = hy + 26 * k
    for name, col, cells in rows:
        x0, _ = xs[0]
        if name == "GC":
            black_sphere(cr, x0 + 8 * k, rowy - 5 * k, 4.5 * k)
        elif name == "GA":
            sphere(cr, x0 + 8 * k, rowy - 5 * k, 4.5 * k, GA_COL, glow=1.2)
        else:
            cr.set_source_rgba(*col, 0.95)
            cr.arc(x0 + 8 * k, rowy - 5 * k, 4.5 * k, 0, 2 * math.pi)
            cr.fill()
        if name in TABLE_SYMBOLS:
            key = TABLE_SYMBOLS[name]
            symbol(cr, key, x0 + dot, rowy, TABLE_SYM_PX * TABLE_SYM_K.get(key, 1) * k, pale, 0.9)
        else:
            text(cr, cells[0], x0 + dot, rowy, 14, font=MONO, k=k)
        for i in (1, 2, 4, 5, 6):
            dim = cells[i] == "—"
            text(cr, cells[i], xs[i][1], rowy, 14, font=MONO, align="r", alpha=0.5 if dim else 0.85, k=k)
        sx0, sx1 = xs[3]
        symbol(cr, SIGN_KEYS[cells[3][0]], sx0, rowy, (TABLE_SYM_PX - 1) * k, gold if name == "Earth" else pale, 0.85)
        text(cr, cells[3][1:], sx1, rowy, 14, font=MONO, align="r", k=k)
        rowy += 25 * k

    tmp = f"{out}.{os.getpid()}.tmp"
    surf.write_to_png(tmp)
    os.replace(tmp, out)


if __name__ == "__main__":
    main()
