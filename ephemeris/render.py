#!/usr/bin/env python3
"""Ephemeris: sidereal positions of the Sun, Moon and planets right now, as a
table plus a short summary of the highlights, drawn to a PNG for the Noctalia
desktop widget (desktop.luau).

    render.py <out.png> [scale] [font] [font size] [primary ayanamsa] [sanskrit 0|1]
              [order heliocentric|geocentric]

Prints "height=<px>" (design units, width 900) so the widget can size itself.

Positions: Swiss Ephemeris (pyswisseph, built-in Moshier theory), geocentric,
sidereal with the Fagan/Bradley and the Lahiri ayanamsa. Nakshatras use
Lahiri, as is the Vedic custom. Dignities, motion and the summary follow the
primary ayanamsa (default Fagan/Bradley). EPHEMERIS_TIME=<unix time> renders
another moment.
"""
import hashlib
import json
import math
import os
import random
import sys
import time

import cairo
import swisseph as swe

W = 900                         # design width
FONT = "DejaVu Sans Mono"       # widget setting "font"
GLYPHS = "DejaVu Sans"          # planet and sign symbols
DEVANAGARI = "Noto Sans Devanagari"
DEVA_SCALE = 1.2                # Devanagari looks small next to Latin at the same size
K = 1.0                         # font size setting / 14

#          name       swe id       symbol  symbol font            station window (days)
BODIES = [
    ("Sun",     swe.SUN,     "☉", None,                  0),
    ("Mercury", swe.MERCURY, "☿", None,                  1.5),
    ("Venus",   swe.VENUS,   "♀", None,                  2.5),
    ("Moon",    swe.MOON,    "☽", None,                  0),
    ("Mars",    swe.MARS,    "♂", None,                  3),
    ("Jupiter", swe.JUPITER, "♃", None,                  5),
    ("Saturn",  swe.SATURN,  "♄", None,                  6),
    ("Uranus",  swe.URANUS,  "♅", None,                  8),
    ("Neptune", swe.NEPTUNE, "♆", None,                  8),
    ("Pluto",   swe.PLUTO,   "⯓", None,                  8),
]
# Row (and summary) order, each starting from its centre: heliocentric by
# distance from the Sun as in Orrery, with the Moon after Earth; geocentric
# the Ptolemaic order of the spheres.
ORDERS = {
    "heliocentric": ["Sun", "Mercury", "Venus", "Earth", "Moon", "Mars", "Jupiter",
                     "Saturn", "Uranus", "Neptune", "Pluto"],
    "geocentric":   ["Earth", "Moon", "Mercury", "Venus", "Sun", "Mars", "Jupiter",
                     "Saturn", "Uranus", "Neptune", "Pluto"],
}
# How far ahead a sign change is worth a mention in the summary (days).
INGRESS_AHEAD = {"Sun": 5, "Moon": 3, "Mercury": 4, "Venus": 5, "Mars": 7,
                 "Jupiter": 14, "Saturn": 30, "Uranus": 30, "Neptune": 30, "Pluto": 30}

SIGNS = "♈♉♊♋♌♍♎♏♐♑♒♓"
SIGN_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
              "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# Traditional rulerships (outer planets: their modern signs) and exaltations;
# detriment and fall are the opposite signs.
DOMICILE = {"Sun": [4], "Moon": [3], "Mercury": [2, 5], "Venus": [1, 6], "Mars": [0, 7],
            "Jupiter": [8, 11], "Saturn": [9, 10], "Uranus": [10], "Neptune": [11], "Pluto": [7]}
EXALTATION = {"Sun": 0, "Moon": 1, "Mercury": 5, "Venus": 11, "Mars": 9, "Jupiter": 3, "Saturn": 6}

NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
              "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
              "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
              "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
              "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
NAKSHATRAS_SA = ["अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा", "आर्द्रा",
                 "पुनर्वसु", "पुष्य", "आश्लेषा", "मघा", "पूर्वफाल्गुनी",
                 "उत्तरफाल्गुनी", "हस्त", "चित्रा", "स्वाति", "विशाखा", "अनुराधा",
                 "ज्येष्ठा", "मूल", "पूर्वाषाढा", "उत्तराषाढा", "श्रवण",
                 "धनिष्ठा", "शतभिषा", "पूर्वभाद्रपदा", "उत्तरभाद्रपदा", "रेवती"]

AYANAMSAS = {"fagan-bradley": ("Fagan/Bradley", swe.SIDM_FAGAN_BRADLEY),
             "lahiri": ("Lahiri", swe.SIDM_LAHIRI)}

PALE = (0.85, 0.88, 1.0)
GOLD = (1.0, 0.78, 0.35)
GOOD = (0.55, 0.90, 0.60)       # exalted, own sign
BAD = (1.0, 0.55, 0.50)         # detriment, fall
RETRO = (1.0, 0.55, 0.50)
STATION = (1.0, 0.78, 0.35)


# ---------------------------------------------------------------- astronomy --

def calc(jd, pid, sid):
    swe.set_sid_mode(sid)
    r, _ = swe.calc_ut(jd, pid, swe.FLG_MOSEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL)
    return r[0], r[3]                               # longitude, speed (deg/day)


def motion(jd, pid, window, sid):
    """'' direct, 'R' retrograde, 'SR' stationary turning retrograde,
    'SD' stationary turning direct."""
    if not window:
        return ""
    before = calc(jd - window, pid, sid)[1]
    after = calc(jd + window, pid, sid)[1]
    if (before < 0) != (after < 0):
        return "SR" if after < 0 else "SD"
    return "R" if calc(jd, pid, sid)[1] < 0 else ""


def next_ingress(jd, pid, sid, days):
    """(julian day, new sign) of the next sign change within `days`, or None."""
    sign = int(calc(jd, pid, sid)[0] // 30)
    step = 1 / 24 if pid == swe.MOON else 0.25
    t = jd
    while t < jd + days:
        t2 = t + step
        if int(calc(t2, pid, sid)[0] // 30) != sign:
            lo, hi = t, t2
            while hi - lo > 1 / 1440:               # to the minute
                mid = (lo + hi) / 2
                if int(calc(mid, pid, sid)[0] // 30) != sign:
                    hi = mid
                else:
                    lo = mid
            return hi, int(calc(hi, pid, sid)[0] // 30)
        t = t2
    return None


def jd_to_unix(jd):
    return (jd - 2440587.5) * 86400


def dignity(name, sign):
    if sign in DOMICILE.get(name, []):
        return "own sign"
    if EXALTATION.get(name) == sign:
        return "exalted"
    if (sign + 6) % 12 in DOMICILE.get(name, []):
        return "detriment"
    if EXALTATION.get(name) is not None and (EXALTATION[name] + 6) % 12 == sign:
        return "fall"
    return ""


def nakshatra(lon):
    i = int(lon // (360 / 27))
    pada = int((lon % (360 / 27)) // (360 / 108)) + 1
    return i, pada


def dms(lon):
    d = lon % 30
    deg, mins = int(d), int(round((d - int(d)) * 60))
    if mins == 60:
        deg, mins = deg + 1, 0
    return f"{deg:2d}°{mins:02d}'"


# ------------------------------------------------------------------ drawing --

# ------------------------------------------ drawn Saturn, Jupiter and Pluto --
# Saturn (heavy stem, thin bar, tapering hook), Jupiter (curved "2"-like top)
# and Pluto (ring in a close cup over a cross) are filled outlines rather than
# font glyphs. Coordinates: Saturn in a 340-unit box, Jupiter in a 576-unit
# box, Pluto in a 276 x 250 box, y down; drawn_symbol scales them.


def _bez(p0, p1, p2, p3, t):
    u = 1 - t
    return (u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1])


def _poly(cr, pts):
    """Add a closed polygon, always turning clockwise (y down)."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts = pts[::-1]
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.close_path()


def _rect(cr, x, y, w, h):
    _poly(cr, [(x, y), (x + w, y), (x + w, y + h), (x, y + h)])


def _brush(cr, segments, width, n=48):
    """A stroke along cubic segments whose width follows width(s), s = 0..1."""
    c = [_bez(*seg, i / n) for seg in segments for i in range(n)] + [segments[-1][3]]
    lens = [0.0]
    for a, b in zip(c, c[1:]):
        lens.append(lens[-1] + math.dist(a, b))
    left, right = [], []
    for i, (x, y) in enumerate(c):
        a, b = c[max(i - 1, 0)], c[min(i + 1, len(c) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1
        w = width(lens[i] / lens[-1]) / 2
        left.append((x - dy / d * w, y + dx / d * w))
        right.append((x + dy / d * w, y - dx / d * w))
    _poly(cr, left + right[::-1])


def _flat(cr, build):
    """Flatten a curved outline built by build(cr) and add it, clockwise."""
    cr.save(); cr.new_path(); build(cr)
    pts = [p for kind, p in cr.copy_path_flat() if kind in (0, 1)]
    cr.new_path(); cr.restore()
    return pts


def _saturn_path(cr):
    def hook(c):
        c.move_to(150, 150)
        c.curve_to(178, 112, 240, 105, 266, 158)
        c.curve_to(292, 215, 245, 292, 100, 328)
        c.curve_to(205, 282, 242, 220, 228, 182)
        c.curve_to(218, 155, 188, 150, 163, 178)
        c.line_to(150, 178)
        c.close_path()
    pts = _flat(cr, hook)
    cr.new_path()
    _rect(cr, 120, 12, 43, 188)      # thick stem
    _rect(cr, 60, 50, 202, 12)       # thin cross bar, longer to the right
    _poly(cr, pts)                   # hook, tapering to a point at the lower left


def _jupiter_path(cr):
    # curved top: pointed start, heavy shoulder, a diagonal thinning down to
    # a sharp corner on the bar; the stem stands apart with a slanted top
    def curve(c):
        c.move_to(155, 172)
        c.curve_to(178, 112, 222, 80, 265, 80)
        c.curve_to(322, 80, 364, 120, 361, 180)
        c.curve_to(354, 244, 272, 312, 186, 388)
        c.line_to(145, 405)
        c.curve_to(214, 332, 296, 258, 306, 192)
        c.curve_to(311, 140, 290, 116, 256, 116)
        c.curve_to(216, 116, 182, 136, 155, 172)
        c.close_path()
    pts = _flat(cr, curve)
    cr.new_path()
    _poly(cr, pts)
    _rect(cr, 145, 388, 283, 17)                                 # thin cross bar
    _poly(cr, [(313, 330), (355, 283), (355, 488), (313, 488)])  # stem, slanted top


def _pluto_path(cr):
    # ring, a cup hugging it closely, then the cross below
    t = 20                                            # line weight, as Venus
    cx, cy, ro = 138, 72, 47                          # ring
    ri = ro - t
    ucy, uri = 78, ro + 7                             # cup: centre, inner radius
    uro = uri + t

    def cup(c):
        c.move_to(cx - uro, cy)
        c.line_to(cx - uro, ucy)
        c.arc_negative(cx, ucy, uro, math.pi, 0)
        c.line_to(cx + uro, cy)
        c.line_to(cx + uri, cy)
        c.line_to(cx + uri, ucy)
        c.arc(cx, ucy, uri, 0, math.pi)
        c.line_to(cx - uri, cy)
        c.close_path()
    pts = _flat(cr, cup)
    cr.new_path()
    cr.new_sub_path(); cr.arc(cx, cy, ro, 0, 2 * math.pi); cr.close_path()
    cr.new_sub_path(); cr.arc_negative(cx, cy, ri, 2 * math.pi, 0); cr.close_path()  # hole
    _poly(cr, pts)
    _rect(cr, cx - t / 2, ucy + uro - 4, t, 250 - (ucy + uro - 4))  # stem
    _rect(cr, cx - 34, 196, 68, t)                                   # cross bar


_DRAWN = {"♄": _saturn_path, "♃": _jupiter_path, "⯓": _pluto_path}


def _extents(build):
    c = cairo.Context(cairo.RecordingSurface(cairo.CONTENT_ALPHA, None))
    build(c)
    return c.fill_extents()


_DRAWN_EXT = {s: _extents(f) for s, f in _DRAWN.items()}


def drawn_symbol(cr, sym, x, y, px, col, alpha, align="l", measure=False):
    """Saturn, Jupiter or Pluto at font size px; (x, y) is the baseline start like
    show_text (align "r": x is the right end). Returns the advance."""
    x0, y0, x1, y1 = _DRAWN_EXT[sym]
    k = 0.92 * px / (y1 - y0)                       # cap height plus a short descender
    adv = (x1 - x0) * k + 0.14 * px
    if measure:
        return adv
    if align == "r":
        x -= adv
    for d, c, a in ((1, (0, 0, 0), 0.6 * alpha), (0, col, alpha)):
        cr.save()
        cr.translate(x + 0.07 * px - x0 * k + d, y - 0.76 * px - y0 * k + d)
        cr.scale(k, k)
        _DRAWN[sym](cr)
        cr.restore()
        cr.set_source_rgba(*c, a)
        cr.fill()
    return adv


def text(cr, s, x, y, px, col=PALE, alpha=0.9, font=None, measure=False):
    """Draw s with its baseline at y (px already scaled); returns the advance."""
    if any("\u0900" <= ch <= "\u097f" for ch in s):
        return deva_text(cr, s, x, y, px, col, alpha, font, measure)
    cr.select_font_face(font or FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(px)
    adv = cr.text_extents(s).x_advance
    if not measure:
        cr.set_source_rgba(0, 0, 0, 0.6 * alpha)
        cr.move_to(x + 1, y + 1)
        cr.show_text(s)
        cr.set_source_rgba(*col, alpha)
        cr.move_to(x, y)
        cr.show_text(s)
    return adv


def deva_text(cr, s, x, y, px, col, alpha, font, measure):
    """Like text(), through Pango so Devanagari vowel signs and conjuncts are shaped.
    Imported here so PyGObject is only needed with the Sanskrit names setting."""
    import gi
    gi.require_version("Pango", "1.0")
    gi.require_version("PangoCairo", "1.0")
    from gi.repository import Pango, PangoCairo
    layout = PangoCairo.create_layout(cr)
    desc = Pango.FontDescription.from_string(f"{font or FONT}, {DEVANAGARI}")
    desc.set_absolute_size(px * DEVA_SCALE * Pango.SCALE)
    layout.set_font_description(desc)
    layout.set_text(s, -1)
    adv = layout.get_extents()[1].width / Pango.SCALE
    if not measure:
        top = y - layout.get_baseline() / Pango.SCALE
        for dx, rgba in ((1, (0, 0, 0, 0.6 * alpha)), (0, (*col, alpha))):
            cr.set_source_rgba(*rgba)
            cr.move_to(x + dx, top + dx)
            PangoCairo.show_layout(cr, layout)
        cr.new_path()
    return adv


SYMBOL_FONT = {sym: font for _, _, sym, font, _ in BODIES if font}
EARTH = "🜨"                     # opposite the Sun: Earth as seen from the Sun
SYMBOL_FONT[EARTH] = "Noto Sans Symbols"


# The hand-made symbols shared with the Orrery: filled outlines from
# symbols.json (a 100-unit box, y down, each symbol centred in it); every op
# is M/L/C with absolute coordinates, or Z. Same drawing as the Orrery.
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "symbols.json")) as _f:
    _SYMS = json.load(_f)
SYM_SCALE = {"earth": 0.86, "moon": 0.9, "uranus": 0.8, "neptune": 1.08, "venus": 1.08, "mercury": 1.08, "saturn": 1.02}    # some look heavy or light at full size
SYM_KEY = dict(zip("☉☽☿♀♂♃♄♅♆⯓", ["sun", "moon", "mercury", "venus", "mars", "jupiter",
                                       "saturn", "uranus", "neptune", "pluto"]))
SYM_KEY[EARTH] = "earth"
SYM_KEY.update(zip(SIGNS, ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra",
                           "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]))


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
    x0, y0, x1, y1 = c.fill_extents()
    m = _SYMS[key].get("stroke", 0) / 2       # the stroke widens the outline
    return x0 - m, y0 - m, x1 + m, y1 + m


_SYM_EXT = {key: _sym_extents(key) for key in _SYMS}


def own_symbol(cr, key, x, y, px, col, alpha, measure=False):
    """Symbol `key` in a px-high box; (x, y) is the baseline start like
    show_text. Returns the advance."""
    x0, y0, x1, y1 = _SYM_EXT[key]
    k = SYM_SCALE.get(key, 1) * px / 100
    adv = (x1 - x0) * k + 0.11 * px
    if measure:
        return adv
    ox, oy = x + 0.055 * px - x0 * k, y - 0.27 * px - 50 * k
    rule = cairo.FILL_RULE_EVEN_ODD if _SYMS[key].get("evenodd") else cairo.FILL_RULE_WINDING
    stroke = _SYMS[key].get("stroke", 0)   # extra line weight, in the 100-unit box
    for d, c, a in ((1, (0, 0, 0), 0.6 * alpha), (0, col, alpha)):
        cr.save()
        cr.translate(ox + d, oy + d)
        cr.scale(k, k)
        _sym_path(cr, key)
        cr.restore()
        cr.set_fill_rule(rule)
        cr.set_source_rgba(*c, a)
        if stroke:                          # thicken every line by tracing the outline too
            cr.fill_preserve()
            cr.set_line_width(stroke * k)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            cr.stroke()
        else:
            cr.fill()
    cr.set_fill_rule(cairo.FILL_RULE_WINDING)
    return adv


def glyph(cr, sym, x, y, px, col=PALE, alpha=0.95, measure=False):
    """A planet or sign symbol, drawn from symbols.json (the same symbols as
    the Orrery); anything not in it falls back to the font."""
    if SYM_KEY.get(sym) in _SYMS:
        return own_symbol(cr, SYM_KEY[sym], x, y, px, col, alpha, measure)
    if sym in _DRAWN:
        return drawn_symbol(cr, sym, x, y, px, col, alpha, measure=measure)
    return text(cr, sym, x, y, px, col, alpha, SYMBOL_FONT.get(sym, GLYPHS), measure)


# Sign and planet symbol sizes in px (widget settings "sign_size" and
# "planet_size"): the height of the symbol box, the same units as the Orrery's
# settings, so the same number gives the same size in both widgets.
SIGN_PX = 31.0
PLANET_PX = 32.0


def runs(cr, parts, x, y, px, measure=False):
    """Draw a list of ("t", text, colour) / ("g", planet, colour) /
    ("s", sign, colour) runs. Symbols scale with px like the text, so they
    shrink with the table when it would not fit."""
    rel = px / (14 * K)
    for kind, s, col in parts:
        if kind == "s":
            x += glyph(cr, s, x, y, SIGN_PX * rel, col, measure=measure)
        elif kind == "g":
            x += glyph(cr, s, x, y, PLANET_PX * rel, col, measure=measure)
        else:
            x += text(cr, s, x, y, px, col, measure=measure)
    return x


def wrap(cr, parts, width, px):
    """Split runs into lines no wider than width (breaking text at spaces)."""
    words = []
    for kind, s, col in parts:
        if kind in ("g", "s"):
            words.append((kind, s, col))
        else:
            for i, w in enumerate(s.split(" ")):
                if i:
                    words.append(("t", " ", col))
                if w:
                    words.append(("t", w, col))
    lines, line = [], []
    for w in words:
        trial = line + [w]
        if line and runs(cr, trial, 0, 0, px, measure=True) > width and w[1] != " ":
            carry = [w]
            if w[1][0] in ".,;:)" and line[-1][1] != " ":     # keep punctuation with its word
                carry.insert(0, line.pop())
            while line and line[-1][1] == " ":
                line.pop()
            lines.append(line)
            line = carry
        elif not (not line and w[1] == " "):
            line = trial
    if line:
        lines.append(line)
    return lines


# --------------------------------------------------------------------- main --

def when(jd, now, moon):
    t = time.localtime(jd_to_unix(jd))
    today = time.localtime(now)
    days = (time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1)) -
            time.mktime((today.tm_year, today.tm_mon, today.tm_mday, 0, 0, 0, 0, 0, -1))) / 86400
    if moon:
        day = {0: "today", 1: "tomorrow"}.get(round(days), time.strftime("on %A", t))
        return f"{day} at {time.strftime('%H:%M', t)}"
    if round(days) == 0:
        return "today"
    if round(days) == 1:
        return "tomorrow"
    return f"around {t.tm_mday} {time.strftime('%B', t)}"


def summary(name, sym, lon, sign, mot, dig, ingress, now, moon_nak):
    """One sentence about a body, or None when there is nothing notable."""
    deg = lon % 30
    # "☉ in ♍"; retrograde / stationary planets get a prefix: "R♄ in ♓".
    head = [("t", mot, RETRO if mot == "R" else STATION)] if mot else []
    head += [("g", sym, PALE), ("t", " in ", PALE), ("s", SIGNS[sign], GOLD)]
    if moon_nak:
        head.append(("t", f" ({moon_nak})", PALE))
    clauses = []
    if dig == "exalted":
        clauses.append(("where it is exalted", GOOD))
    elif dig == "fall":
        clauses.append(("where it is in fall", BAD))
    elif dig == "detriment":
        clauses.append(("where it is in detriment", BAD))
    elif dig == "own sign":
        clauses.append(("its own sign", GOOD))
    if name != "Moon" and deg >= 27 and not ingress:
        clauses.append(("in its last degrees", PALE))
    elif name != "Moon" and deg < 1:
        clauses.append(("having just entered it", PALE))
    out = []
    if clauses:
        out.append(("t", ", ", PALE))
        for i, (c, col) in enumerate(clauses):
            if i:
                out.append(("t", " and ", PALE))
            out.append(("t", c, col))
    if ingress:
        jd_in, new = ingress
        back = (new - sign) % 12 == 11
        out += [("t", ", and will " + ("move back into " if back else "enter "), PALE),
                ("s", SIGNS[new], GOLD), ("t", " " + when(jd_in, now, name == "Moon"), PALE)]
    if not out and not mot:
        return None
    return head + out + [("t", ".", PALE)]


def main():
    global FONT, K, SIGN_PX, PLANET_PX
    out = sys.argv[1]
    scale = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    if len(sys.argv) > 3 and sys.argv[3].strip():
        FONT = sys.argv[3].strip()
    if len(sys.argv) > 4 and sys.argv[4].strip():
        K = float(sys.argv[4]) / 14
    key = (sys.argv[5] if len(sys.argv) > 5 else "").strip().lower().replace(" ", "-").replace("/", "-")
    primary = "lahiri" if key.startswith("lahiri") else "fagan-bradley"
    p_name, p_sid = AYANAMSAS[primary]
    sanskrit = len(sys.argv) > 6 and sys.argv[6].strip().lower() in ("1", "true", "yes", "on")
    order = ORDERS["geocentric" if len(sys.argv) > 7 and sys.argv[7].strip().lower().startswith("geo")
                   else "heliocentric"]
    if len(sys.argv) > 8 and sys.argv[8].strip():
        SIGN_PX = float(sys.argv[8])
    if len(sys.argv) > 9 and sys.argv[9].strip():
        PLANET_PX = float(sys.argv[9])
    fb_sid, la_sid = swe.SIDM_FAGAN_BRADLEY, swe.SIDM_LAHIRI

    # argv[10]: the moment to show: unix time, or local "DD.MM.YYYY HH:MM" typed
    # in the widget's time pop-up; empty: now. argv[13]: whole days to move it
    # (the widget's day buttons), counted on the local calendar so the clock
    # time stays the same across summer time changes.
    when = sys.argv[10].strip() if len(sys.argv) > 10 else ""
    shift = int(sys.argv[13]) if len(sys.argv) > 13 and sys.argv[13].strip() else 0
    if not when:
        now = float(os.environ.get("EPHEMERIS_TIME") or time.time())
    elif "." in when and ":" in when and " " in when:
        try:
            d, hm = when.split()
            day, month, year = (int(v) for v in d.split("."))
            hour, minute = (int(v) for v in hm.split(":"))
            now = time.mktime((year, month, day, hour, minute, 0, 0, 0, -1))
            if time.localtime(now)[:5] != (year, month, day, hour, minute):
                raise ValueError
        except ValueError:
            sys.exit(f"not a date and time: {when!r} (expected DD.MM.YYYY HH:MM)")
    else:
        now = float(when)
    if shift:
        lt = time.localtime(now)
        now = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday + shift, lt.tm_hour, lt.tm_min,
                           lt.tm_sec, 0, 0, -1))
    live = abs(now - time.time()) < 120             # showing the present moment
    tm = time.gmtime(now)
    jd = swe.julday(tm.tm_year, tm.tm_mon, tm.tm_mday,
                    tm.tm_hour + tm.tm_min / 60 + tm.tm_sec / 3600)

    row_of, note_of = {}, {}
    for name, pid, sym, _, window in BODIES:
        fb = calc(jd, pid, fb_sid)[0]
        la = calc(jd, pid, la_sid)[0]
        p_lon = fb if primary == "fagan-bradley" else la
        sign = int(p_lon // 30)
        mot = motion(jd, pid, window, p_sid)
        dig = dignity(name, sign)
        n, pada = nakshatra(la)
        nak = NAKSHATRAS[n]
        row_of[name] = (sym, fb, la, mot, dig, ((NAKSHATRAS_SA if sanskrit else NAKSHATRAS)[n], f" {pada}"))
        ing = next_ingress(jd, pid, p_sid, INGRESS_AHEAD[name])
        note_of[name] = summary(name, sym, p_lon, sign, mot, dig, ing, now, nak if name == "Moon" else None)
        if name == "Sun":                           # Earth: opposite the Sun
            e_fb, e_la = (fb + 180) % 360, (la + 180) % 360
            n, pada = nakshatra(e_la)
            row_of["Earth"] = (EARTH, e_fb, e_la, None, None,
                               ((NAKSHATRAS_SA if sanskrit else NAKSHATRAS)[n], f" {pada}"))
    rows = [row_of[name] for name in order]
    notes = [note_of[name] for name in order if note_of.get(name)]

    # Draw on an unbounded recording surface first: the height depends on the
    # wrapped summary. Then replay it, scaled, onto the PNG.
    rec = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
    cr = cairo.Context(rec)
    # exact (unrounded) letter widths, so text is the same size in the Orrery and
    # the Ephemeris whatever resolution each lays its text out at
    fo = cairo.FontOptions()
    fo.set_hint_metrics(cairo.HINT_METRICS_OFF)
    cr.set_font_options(fo)
    k = K
    px = 14 * k
    loc = time.localtime(now)
    y = 16 + 14 * k
    date_s = time.strftime("%d.%m.%Y %H:%M", loc)
    date_w = text(cr, date_s, 0, 0, px, measure=True)
    # another day than today's: the date in red (as R and fall), so it is not mistaken for now
    text(cr, date_s, W - 16 - date_w, y, px, PALE if live else RETRO, alpha=0.75 if live else 0.95)

    # ayanamsa values, small, in the top left corner beside the date
    swe.set_sid_mode(fb_sid)
    fb_a = swe.get_ayanamsa_ut(jd)
    swe.set_sid_mode(la_sid)
    la_a = swe.get_ayanamsa_ut(jd)

    def deg_s(a):
        return f"{int(a)}°{int((a - int(a)) * 60):02d}'"
    note = [("t", f"Ayanamsa: Fagan/Bradley {deg_s(fb_a)}, Lahiri {deg_s(la_a)}. "
                  f"Nakshatras by Lahiri; dignities and highlights by {p_name}.", (0.6, 0.64, 0.75))]
    ny = y
    for line in wrap(cr, note, W - 16 - date_w - 24 - 16, 11 * K):
        runs(cr, line, 16, ny, 11 * K)
        ny += 16 * K
    y = max(y, ny - 16 * K)
    cut = y + 9 * K                                 # bottom of the header
    # The widget's day buttons go under the date, right of the ayanamsa note:
    # leave them at least NAV_PX (displayed px; the PNG is drawn at 2x) of height.
    NAV_PX = 26
    date_x = W - 16 - date_w - 8                    # left edge of the date corner
    date_y = 16 + 14 * k + 6 * K                    # just under the date
    cut = max(cut, date_y + NAV_PX * 2 / scale)

    heads = ["Planet", "Fagan/Bradley", "लाहिड़ी" if sanskrit else "Lahiri", "Dignity",
             "नक्षत्र" if sanskrit else "Nakshatra"]

    def pos_parts(lon, mot):
        p = [("s", SIGNS[int(lon // 30)], PALE), ("t", " " + dms(lon), PALE)]
        if mot:
            p.append(("t", " " + mot, RETRO if mot == "R" else STATION))
        return p

    def cells(r):
        sym, fb, la, mot, dig, nak = r
        return [[("g", sym, PALE)], pos_parts(fb, mot), pos_parts(la, mot),
                [("t", dig or "—", GOOD if dig in ("exalted", "own sign") else BAD if dig else PALE)],
                [("t", nak[0], PALE), ("t", nak[1], PALE)]]

    def measure(kk):
        ws = []
        for i, h in enumerate(heads):
            w = max([runs(cr, cells(r)[i], 0, 0, 14 * kk, measure=True) for r in rows] +
                    [text(cr, h, 0, 0, 13 * kk, measure=True)])
            ws.append(w)
        return ws

    widths = measure(k)
    need = sum(widths) + (len(widths) - 1) * 18 * k
    if need > W - 80:                               # font too large for the width: shrink the table
        k *= (W - 80) / need
        widths = measure(k)
    gap = (W - 80 - sum(widths)) / (len(widths) - 1)
    xs, x = [], 40
    for w in widths:
        xs.append(x)
        x += w + gap

    y += 34 * k
    for i, h in enumerate(heads):
        text(cr, h, xs[i], y, 13 * k, (0.75, 0.80, 0.95), 0.6)
    y += 8 * k
    cr.set_source_rgba(0.75, 0.80, 0.95, 0.25)
    cr.set_line_width(1)
    cr.move_to(40, y)
    cr.line_to(W - 40, y)
    cr.stroke()
    y += 26 * k
    for r in rows:
        for i, c in enumerate(cells(r)):
            runs(cr, c, xs[i], y, 14 * k)
        y += 28 * k

    # summary
    y += 20 * k
    spx = 14 * K
    for parts in notes:
        for line in wrap(cr, parts, W - 80, spx):
            runs(cr, line, 40, y, spx)
            y += 24 * K
        y += 4 * K
    height = math.ceil(y + 10 * K)
    # Keep the tallest height drawn so far (per set of widget settings): the
    # host centres the widget on its position, so a changing height would move
    # the top too. The extra space stays at the bottom, under the summary.
    sig = hashlib.md5(repr((round(scale, 3), FONT, K, primary, sanskrit, order, SIGN_PX, PLANET_PX))
                      .encode()).hexdigest()[:12]
    keep = os.path.join(os.path.dirname(os.path.abspath(out)), f"height-{sig}")
    try:
        with open(keep) as f:
            tallest = int(f.read().strip() or 0)
    except (OSError, ValueError):
        tallest = 0
    if height > tallest:
        try:
            with open(keep, "w") as f:
                f.write(str(height))
        except OSError:
            pass
    height = max(height, tallest)

    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, math.ceil(W * scale), math.ceil(height * scale))
    c2 = cairo.Context(surf)
    c2.scale(scale, scale)
    rnd = random.Random(11)                         # faint fixed stars, like the Orrery
    for _ in range(int(height / 6)):
        c2.set_source_rgba(1, 1, 1, rnd.uniform(0.06, 0.25))
        c2.arc(rnd.uniform(10, W - 10), rnd.uniform(10, height - 10), rnd.uniform(0.4, 1.0), 0, 2 * math.pi)
        c2.fill()
    c2.set_source_surface(rec, 0, 0)
    c2.paint()

    # argv[11] and argv[12]: with these, the picture is saved in three parts so
    # the widget can put its day buttons in the space under the date:
    #   out       the header left of the date corner
    #   argv[12]  the date corner, above the buttons
    #   argv[11]  everything below the header
    def save(img, path):
        tmp = f"{path}.{os.getpid()}.tmp"
        img.write_to_png(tmp)
        os.replace(tmp, path)

    if len(sys.argv) > 12 and sys.argv[12].strip():
        cut_px, x_px, dy_px = round(cut * scale), round(date_x * scale), round(date_y * scale)
        full_w = surf.get_width()
        parts = ((out, 0, 0, x_px, cut_px),
                 (sys.argv[12].strip(), x_px, 0, full_w - x_px, dy_px),
                 (sys.argv[11].strip(), 0, cut_px, full_w, surf.get_height() - cut_px))
        for path, x0, y0, w, h in parts:
            part = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
            pc = cairo.Context(part)
            pc.set_source_surface(surf, -x0, -y0)
            pc.paint()
            save(part, path)
        print(f"cut={cut_px / scale:.3f} datex={x_px / scale:.3f} datey={dy_px / scale:.3f}")
    else:
        save(surf, out)
    print(f"height={height}")
    print(f"time={now:.0f}")
    print(f"date={date_s}")


if __name__ == "__main__":
    main()
