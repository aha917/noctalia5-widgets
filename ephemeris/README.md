# Ephemeris

![Ephemeris](preview.png)

A Noctalia desktop widget with the current **sidereal** positions of the Sun,
Moon and planets, in both the Fagan/Bradley and the Lahiri zodiac, with motion,
dignities, nakshatras and a short summary of what stands out today. It updates
every minute and needs no internet: all positions are computed locally with the
Swiss Ephemeris.

## What you see

### The table

| Column | Meaning |
|--------|---------|
| **Planet** | the astrological symbol: ☉ Sun, ☿ Mercury, ♀ Venus, 🜨 Earth, ☽ Moon, ♂ Mars, ♃ Jupiter, ♄ Saturn, ♅ Uranus, ♆ Neptune, ⯓ Pluto |
| **Fagan/Bradley** | sign and degree in the sidereal zodiac with the Fagan/Bradley ayanamsa (Western sidereal astrology), plus the motion marker |
| **Lahiri** | sign and degree with the Lahiri (Chitrapaksha) ayanamsa, the standard of Vedic astrology, plus the motion marker |
| **Dignity** | **own sign** or **exalted** (green), **detriment** or **fall** (red), "—" otherwise |
| **Nakshatra** | the lunar mansion (one of 27, each 13°20′) and its **pada**, the quarter 1–4 (each 3°20′), always by Lahiri |

The rows are in heliocentric or geocentric order (see *Planet order*).

**Earth (🜨)** is the point opposite the Sun: where the Earth is as seen from
the Sun. It has no dignity, no motion marker and no line in the summary.

**Motion markers**

| Marker | Meaning |
|--------|---------|
| **R** (red) | retrograde |
| **SR** (amber) | stationary, turning retrograde |
| **SD** (amber) | stationary, turning direct |

A planet counts as stationary when its direction changes within a few days of
now: 1.5 days for Mercury, 2.5 for Venus, 3 for Mars, 5 for Jupiter, 6 for
Saturn and 8 for Uranus, Neptune and Pluto. Other software may use a different
window, which is why one program can show *Rx* where another shows *SD*.

**Dignities** follow the traditional rulerships and exaltations; Uranus,
Neptune and Pluto rule Aquarius, Pisces and Scorpio and have no exaltation.
Detriment and fall are the signs opposite.

### The ayanamsa line

Under the table: the current values of both ayanamsas (for example
"Fagan/Bradley 25°06′, Lahiri 24°13′"), and which one the dignities and the
summary use.

### The summary

One line per planet that has something notable, for example:

- `☉ in ♍, and will enter ♎ tomorrow.`
- `R♀ in ♎, its own sign.`
- `♂ in ♋, where it is in fall.`
- `♃ in ♋, where it is exalted and in its last degrees.`
- `☽ in ♐ (Uttara Ashadha), and will enter ♑ today at 17:50.`
- `SD⯓ in ♑.`

It mentions:

- **dignity:** own sign, exalted, detriment or fall;
- **motion:** retrograde and stationary planets get **R**, **SR** or **SD**
  in front of their symbol;
- **degrees:** a planet in its last degrees (27° or more) or one that has
  just entered its sign (under 1°);
- **sign changes coming up:** within 3 days for the Moon (with the time, and
  its nakshatra), 4 for Mercury, 5 for the Sun and Venus, 7 for Mars, 14 for
  Jupiter and 30 for the outer planets; a retrograde planet "moves back into"
  the previous sign.

The Moon always has a line. The summary uses the *Primary ayanamsa* setting.

## Sanskrit names

With **Sanskrit names** on, the nakshatras and the Lahiri and Nakshatra
column headings are written in Devanagari: लाहिड़ी, नक्षत्र, and अश्विनी,
भरणी, कृत्तिका … रेवती. They are drawn through Pango, so vowel signs and
conjuncts are shaped correctly, and 20% larger than the Latin text so they
read at the same size. The pada numbers stay as they are.

## Requirements

- Noctalia v5 (plugin API 24)
- `python3` with **pycairo** and **pyswisseph** (Swiss Ephemeris)
- Font: DejaVu Sans (sign and planet symbols; Saturn, Jupiter and Pluto are
  drawn by the widget) and Noto Sans Symbols (🜨)
- Only for Sanskrit names: **PyGObject** (Pango) and **Noto Sans Devanagari**

Arch Linux (and Arch-based distributions):

```sh
sudo pacman -S python-cairo ttf-dejavu noto-fonts
sudo pacman -S python-gobject              # only for Sanskrit names
paru -S pyswisseph                         # AUR (or yay)
```

Or, without the AUR, a private environment inside the plugin folder (the
widget uses `.venv/bin/python` when it exists):

```sh
cd ~/noctalia5-widgets/ephemeris   # or wherever the plugin folder is
python3 -m venv --system-site-packages .venv
.venv/bin/pip install pyswisseph
```

Check it: `python3 render.py /tmp/ephemeris.png` should write a PNG.

## Install and use

1. Add this repository as a plugin source and enable the widget:

   ```sh
   noctalia msg plugins source add aha917 git https://github.com/aha917/noctalia5-widgets
   noctalia msg plugins enable traditions/ephemeris
   ```

   Or from a local copy:

   ```sh
   git clone https://github.com/aha917/noctalia5-widgets ~/noctalia5-widgets
   noctalia msg plugins source add aha917 path ~/noctalia5-widgets
   noctalia msg plugins enable traditions/ephemeris
   ```

2. Open the desktop widget editor: **Settings → Desktop → Widgets → Toggle
   Editor**, or run `noctalia msg desktop-widgets-edit`.
3. Pick **Ephemeris** in the drop-down of the editor toolbar and press **+**
   to place it, then drag it where you want it.
4. To change its settings, **click the widget first** (the toolbar buttons
   only work on a selected widget), then press the **gear** button.
5. Press **Done** to leave the editor.

You can place several Ephemeris widgets; each has its own settings.

## Settings

| Setting | Default | Notes |
|---------|---------|-------|
| Width (px) | 680 | the height follows the content |
| Update every (seconds) | 60 | how often positions are recalculated |
| Primary ayanamsa | Fagan/Bradley | or `Lahiri`; used for the dignities and the summary (both are always in the table; nakshatras always use Lahiri) |
| Font | 0xProto | a monospaced font keeps the columns tidy (`fc-list : family` lists the installed ones) |
| Font size | 20 | 8–26; the table shrinks if it would not fit the width |
| Sanskrit names | off | nakshatras and the Lahiri/Nakshatra headings in Devanagari |
| Planet order | Heliocentric | Heliocentric: ☉ ☿ ♀ 🜨 ☽ ♂ ♃ ♄ ♅ ♆ ⯓ (by distance from the Sun, as in Orrery). Geocentric: 🜨 ☽ ☿ ♀ ☉ ♂ ♃ ♄ ♅ ♆ ⯓ (the Ptolemaic order) |

## Troubleshooting

- **The widget stays empty:** run `python3 render.py /tmp/ephemeris.png` in
  the plugin folder and read the error; usually pyswisseph or pycairo is
  missing. Noctalia's log (`~/.cache/noctalia/noctalia.log`) shows render
  errors as `ephemeris: render failed`.
- **Sanskrit names show boxes or broken letters:** install `python-gobject`
  and `noto-fonts` (Noto Sans Devanagari).
- **A new setting does not appear after an update:** disable and enable the
  plugin (`noctalia msg plugins disable traditions/ephemeris`, then `enable`).
- **Another moment:** `EPHEMERIS_TIME=<unix time> python3 render.py out.png`.

## License

AGPL-3.0-or-later, because the Swiss Ephemeris (Astrodienst AG, via
pyswisseph) is used under the AGPL. See `LICENSE`.
