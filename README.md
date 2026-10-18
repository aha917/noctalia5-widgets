# Noctalia 5 widgets

Astronomy and astrology desktop widgets for [Noctalia](https://github.com/noctalia-dev) v5.

| Widget | What it shows |
|--------|---------------|
| [Orrery](orrery/) | The solar system right now: planets, Moon, Chiron, the Moon's nodes and the galactic center over a tropical or sidereal (Fagan/Bradley) zodiac, with a table of positions. |
| [Ephemeris](ephemeris/) | Sidereal positions (Fagan/Bradley and Lahiri) with retrograde and stationary planets, dignities, nakshatras (optionally in Sanskrit) and a short summary of the highlights. |

<p>
  <img src="orrery/preview.png" alt="Orrery" width="49%">
  <img src="ephemeris/preview.png" alt="Ephemeris" width="42%">
</p>

## Install

Add this repository as a plugin source, then enable the widgets you want:

```sh
noctalia msg plugins source add aha917 git https://github.com/aha917/noctalia5-widgets
noctalia msg plugins enable traditions/orrery
noctalia msg plugins enable traditions/ephemeris
```

Then open the desktop widget editor and add the widgets to a monitor. Both need
`python3` with **pycairo** and **pyswisseph** (Ephemeris's Sanskrit names also
need **PyGObject** and Noto Sans Devanagari); each widget's README lists the
details and its settings.

## License

Both widgets are AGPL-3.0-or-later, because they use the Swiss Ephemeris
(Astrodienst AG) under the AGPL. See the `LICENSE` file in each folder.
