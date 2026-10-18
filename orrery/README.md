# Orrery

![Orrery](preview.png)

A Noctalia desktop widget that shows the solar system as it is right now,
seen obliquely from the north, with the zodiac on an outer ring and a table of
positions underneath. It is redrawn every minute and needs no internet: all
positions are computed locally with the Swiss Ephemeris.

## What you see

### The picture

| Element | What it shows |
|---------|---------------|
| **Sun** | in the centre, with a soft glow |
| **Planets** | Mercury to Pluto, each on its real orbit, in its own colour and labelled with its astrological symbol (☿ ♀ 🜨 ♂ ♃ ♄ ♅ ♆ ⯓) |
| **Earth** | marked with a ring around it and the symbol 🜨 |
| **Moon** | ☽ on a small circle around Earth, in the direction it is seen from Earth (its real orbit would be invisible at this scale) |
| **Chiron** | ⚷, between Saturn and Uranus |
| **Orbits** | true shape and true inclination to the ecliptic, drawn with the same projection as the bodies |
| **Height markers** | a thin line with a dot under a planet shows how far it is above or below the ecliptic plane (its latitude, see Lat β in the table) |
| **Zodiac ring** | the twelve signs, with a tick every 5° (a longer one at 15°) |
| **Sun's sign** | the sign the Sun is in, as seen from Earth, is highlighted in gold, with a dashed sight line from Earth through the Sun to that sign |
| **Moon's nodes** | ☊ north and ☋ south node (true node, geocentric) as small red diamonds on the inner edge of the ring, at their longitude |
| **Galactic center (GC)** | the centre of the Milky Way (Sgr A\*), a black ball with a faint halo on the ring at its longitude; it is far beyond any scale, so it sits on the ring |
| **Great Attractor (GA)** | the gravitational centre of our supercluster (Laniakea), a white glowing ball on the ring, like the GC |
| **Zodiac label** | top left: **Tropical** or **Sidereal: Fagan/Bradley** |
| **Date and time** | top right |

Saturn, Jupiter and Pluto are drawn by the widget as vector outlines; the other
symbols come from fonts. Every label is placed in the nearest free spot around
its body, clear of other bodies, labels and the sign symbols.

Distances are compressed (the scale shrinks with distance from the Sun) so
that the inner planets stay visible next to Pluto, and Pluto stays inside the
ring.

### The table

One row per body, in heliocentric or geocentric order (see *Table order*):
Mercury, Venus, Earth, Mars, Jupiter, Saturn, Chiron, Uranus, Neptune, Pluto,
then GC, GA and the two nodes when they are shown. Each row starts with a dot
in the body's colour.

| Column   | Meaning |
|----------|---------|
| Planet   | name |
| Lon λ    | ecliptic longitude: heliocentric for the planets (tropical, of date); for the nodes, GC and GA, as seen from Earth |
| Lat β    | ecliptic latitude (0° for the nodes) |
| Sign     | sign and degree of that longitude, tropical or sidereal (see *Zodiac*); Earth's sign is in gold |
| Sun AU   | distance from the Sun in astronomical units |
| Earth AU | distance from Earth |
| Light    | light travel time to Earth: minutes (m), hours (h) or years (y) |

The nodes have no distance (they are points, not bodies), shown as "—".

### Positions and sources

- **Planets:** Swiss Ephemeris, built-in Moshier theory, heliocentric, of date.
- **Chiron:** Swiss Ephemeris data file `ephe/seas_18.se1`.
- **Moon and nodes:** geocentric; the nodes are the *true* node, as in most
  astrology software.
- **Galactic center:** Sgr A\*, J2000 ecliptic position precessed to the date,
  8.18 kpc away (GRAVITY 2019).
- **Great Attractor:** galactic l = 307°, b = +9° (Lynden-Bell et al. 1988),
  converted to ecliptic and precessed to the date; about 62 Mpc (roughly 200
  million light years) away.
- **Sidereal zodiac:** the Fagan/Bradley ayanamsa from the Swiss Ephemeris.

## Tropical or sidereal

The **Zodiac** setting moves only the signs, not the bodies:

- **Tropical** (default) counts the signs from the spring equinox, as in
  Western astrology.
- **Sidereal: Fagan/Bradley** counts them from the stars, about 25° earlier,
  so the ring rotates and the Sign column shifts. The Lon λ column stays the
  true astronomical (tropical) longitude, so it can be compared with a
  planetarium program such as Stellarium.

The zodiac label in the top left corner says which one is in use.

## Requirements

- Noctalia v5 (plugin API 24)
- `python3` with **pycairo** and **pyswisseph** (Swiss Ephemeris)
- Fonts: DejaVu Sans (sign and planet symbols) and Noto Sans Symbols (🜨)

Arch Linux (and Arch-based distributions):

```sh
sudo pacman -S python-cairo ttf-dejavu noto-fonts
paru -S pyswisseph               # AUR (or yay)
```

Or, without the AUR, a private environment inside the plugin folder (the
widget uses `.venv/bin/python` when it exists):

```sh
cd ~/noctalia5-widgets/orrery   # or wherever the plugin folder is
python3 -m venv --system-site-packages .venv
.venv/bin/pip install pyswisseph
```

Check it: `python3 render.py /tmp/orrery.png` should write a PNG.

## Install and use

1. Add this repository as a plugin source and enable the widget:

   ```sh
   noctalia msg plugins source add aha917 git https://github.com/aha917/noctalia5-widgets
   noctalia msg plugins enable traditions/orrery
   ```

   Or from a local copy:

   ```sh
   git clone https://github.com/aha917/noctalia5-widgets ~/noctalia5-widgets
   noctalia msg plugins source add aha917 path ~/noctalia5-widgets
   noctalia msg plugins enable traditions/orrery
   ```

2. Open the desktop widget editor: **Settings → Desktop → Widgets → Toggle
   Editor**, or run `noctalia msg desktop-widgets-edit`.
3. Pick **Orrery** in the drop-down of the editor toolbar and press **+** to
   place it, then drag it where you want it.
4. To change its settings, **click the widget first** (the toolbar buttons
   only work on a selected widget), then press the **gear** button.
5. Press **Done** to leave the editor.

You can place several Orrery widgets, for example one per monitor; each has
its own settings.

## Settings

| Setting | Default | Notes |
|---------|---------|-------|
| Width (px) | 680 | the height follows from the width, the font size and the visible rows |
| Redraw every (seconds) | 60 | Mercury, the fastest, moves about 1 px in 10 minutes |
| Font | 0xProto | labels and the date; any installed font family |
| Table font | 0xProto | a monospaced font keeps the columns tidy |
| Font size | 20 | 8–26; the table shrinks if it would not fit the width |
| Zodiac | Tropical | or Sidereal (Fagan/Bradley), see above |
| Table order | Heliocentric | Mercury, Venus, Earth, Mars… by distance from the Sun; or Geocentric: Earth first, then the Moon's nodes, then Mercury, Venus, Mars… |
| Show: galactic center | on | the GC on the ring and in the table |
| Show: Great Attractor | on | the GA on the ring and in the table |
| Show: Moon's nodes | on | ☊ ☋ on the ring and in the table |
| Show: zodiac label | on | "Tropical" / "Sidereal: Fagan/Bradley" in the top left corner |
| Zodiac label size | 20 | appears only while the label is on; the same number as Font size matches the date |

Hidden elements also leave the table, and the widget gets shorter.

If a font is not installed, cairo falls back to a default font. List the
installed ones with `fc-list : family`.

## Troubleshooting

- **The widget stays empty:** run `python3 render.py /tmp/orrery.png` in the
  plugin folder and read the error; usually pyswisseph or pycairo is missing.
  Noctalia's log (`~/.cache/noctalia/noctalia.log`) shows render errors as
  `orrery: render failed`.
- **A new setting does not appear after an update:** disable and enable the
  plugin (`noctalia msg plugins disable traditions/orrery`, then `enable`).
- **Another moment:** `ORRERY_TIME=<unix time> python3 render.py out.png`
  draws the sky at any date.

## Credits and license

Positions are computed with the Swiss Ephemeris by Astrodienst AG (pyswisseph
by Stanislas Marquis). The Swiss Ephemeris is dual-licensed under the AGPL and
the Swiss Ephemeris Professional License; this plugin uses it under the AGPL
and is therefore licensed under the GNU Affero General Public License v3.0 or
later (see `LICENSE`).
