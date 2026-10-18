# Ephemeris

![Ephemeris](preview.png)

A Noctalia desktop widget with the current **sidereal** positions of the Sun,
Moon and planets (Mercury to Pluto), updated every 60 seconds. The planets are
shown with their astrological symbols (Saturn, Jupiter and Pluto are drawn by
the widget as vector outlines):

| Column        | Meaning                                                          |
|---------------|------------------------------------------------------------------|
| Planet        | ☉ ☿ ♀ 🜨 ☽ ♂ ♃ ♄ ♅ ♆ ⯓ or 🜨 ☽ ☿ ♀ ☉ ♂ ♃ ♄ ♅ ♆ ⯓ (Planet order setting; 🜨 Earth = opposite the Sun, as seen from the Sun) |
| Fagan/Bradley | sign and degree with the Fagan/Bradley ayanamsa, plus motion     |
| Lahiri        | sign and degree with the Lahiri ayanamsa, plus motion            |
| Dignity       | own sign, exalted, detriment or fall                             |
| Nakshatra     | lunar mansion and pada (1–4), by Lahiri                          |

Motion: **R** retrograde, **SR** stationary turning retrograde, **SD**
stationary turning direct (the planet's speed changes sign within a few days
of now: 1.5 days for Mercury up to 8 days for the outer planets).

Below the table is a short summary of the highlights: dignities, retrograde
and stationary planets, planets in their first or last degrees, and sign
changes coming up soon (the Moon's always, with the time).

Positions are geocentric, computed locally with the Swiss Ephemeris (no
internet needed). Dignities: traditional rulerships and exaltations; Uranus,
Neptune and Pluto rule Aquarius, Pisces and Scorpio and have no exaltation.

## Requirements

- Noctalia v5 (plugin API 24)
- `python3` with **pycairo**, **pyswisseph** and, for Sanskrit names, **PyGObject** (Pango)
- Font: DejaVu Sans (symbols; Saturn, Jupiter and Pluto are drawn by the widget);
  Noto Sans Devanagari for Sanskrit names

Arch / CachyOS:

```sh
sudo pacman -S python-cairo ttf-dejavu
sudo pacman -S python-gobject noto-fonts   # only for Sanskrit names
paru -S pyswisseph               # AUR (or yay)
```

Or, without the AUR, a private environment inside the plugin folder (the
widget uses `.venv/bin/python` when it exists):

```sh
cd ~/noctalia5-widgets/ephemeris   # or wherever the plugin folder is
python3 -m venv --system-site-packages .venv
.venv/bin/pip install pyswisseph
```

## Install

From the repository, as a plugin source:

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

Then open the desktop widget editor and add **Ephemeris** to a monitor.

## Settings

| Setting          | Default       | Notes                                              |
|------------------|---------------|----------------------------------------------------|
| Width            | 680           | the height follows the content                     |
| Update every     | 60            | seconds                                            |
| Primary ayanamsa | Fagan/Bradley | or `Lahiri`; used for dignities and the summary    |
| Font             | 0xProto       | a monospaced font keeps the columns tidy           |
| Font size        | 20            | the table shrinks if it would not fit              |
| Sanskrit names   | off           | nakshatras and the Lahiri/Nakshatra headings in Devanagari |
| Planet order     | Heliocentric  | or Geocentric (Earth, Moon, Mercury, Venus, Sun, Mars…) |

## License

AGPL-3.0-or-later, because the Swiss Ephemeris (Astrodienst AG, via
pyswisseph) is used under the AGPL. See `LICENSE`.
