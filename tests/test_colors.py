import colorsys
import re
from pathlib import Path

CSS = (Path(__file__).parent.parent / "missions/static/missions.css").read_text()
WINDOW = {"light": "#ffffff", "dark": "#1e1e1e"}
LOSS = {"light": "#d70015", "dark": "#ff4245"}
GAIN = {"light": "#248a3d", "dark": "#30d158"}


def block(theme):
    sel = r'html\.hb-apple\s*\{' if theme == "light" else r'html\.hb-apple\[data-theme="dark"\]\s*\{'
    m = re.search(sel + r"([^}]*--mx-lead[^}]*)\}", CSS)
    return dict(re.findall(r"--mx-(\w+):\s*(#[0-9a-fA-F]{6})", m.group(1)))


def rgb(h):
    return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def lum(h):
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = map(f, rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def hue(h):
    return colorsys.rgb_to_hsv(*rgb(h))[0] * 360


def dist(a, b):
    d = abs(hue(a) - hue(b))
    return min(d, 360 - d)


def test_five_workers_both_themes():
    for t in WINDOW:
        assert set(block(t)) == {"lead", "builder", "doubter", "defender", "judge"}


def test_contrast_and_never_money():
    for t in WINDOW:
        for who, c in block(t).items():
            assert contrast(c, WINDOW[t]) >= 4.5, (t, who, c, contrast(c, WINDOW[t]))
            assert dist(c, LOSS[t]) >= 25, (t, who, "near the loss red")
            assert dist(c, GAIN[t]) >= 25, (t, who, "near the gain green")
