"""Render AFX profile artwork from GitHub's contribution calendar."""
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]
DOTS = ["#28252b", "#703142", "#a73d51", "#e6505e", "#ff4257"]
MONO = "ui-monospace, SFMono-Regular, Consolas, monospace"


def label(x, y, value, size, color, anchor="start"):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{MONO}" '
            f'font-size="{size}" fill="{color}">{escape(str(value))}</text>')


def calendar_days(source):
    if source.get("errors"):
        raise ValueError("GitHub returned errors instead of a complete calendar.")
    weeks = source["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = []
    for week in weeks:
        for item in week["contributionDays"]:
            day = date.fromisoformat(item["date"])
            count = item["contributionCount"]
            if not isinstance(count, int) or count < 0:
                raise ValueError(f"Invalid contribution count for {day}")
            days.append((day, count, LEVELS.index(item["contributionLevel"])))
    days.sort()
    if len(days) < 350 or any(b[0] - a[0] != timedelta(days=1) for a, b in zip(days, days[1:])):
        raise ValueError("Calendar is incomplete. Keeping the previous artwork.")
    return days


def document(title, desc, height, elements):
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>',
        f'<rect width="1000" height="{height}" rx="16" fill="#000000"/>',
        *elements, '</svg>', ''
    ])


def locations(days):
    start = days[0][0]
    sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    return {(offset // 7, offset % 7): (day, count, level)
            for day, count, level in days for offset in [(day - sunday).days]}


def month_marks(tiles):
    for (week, row), (day, _, _) in tiles.items():
        if day.day <= 7 and row == 0 and 1 <= week <= max(w for w, _ in tiles) - 1:
            yield week, day.strftime("%b")


def snake_calendar(days, tiles):
    columns = max(w for w, _ in tiles) + 1
    dx = min(16.7, 895 / columns)
    x = lambda week: 75 + dx * week
    y = lambda row: 81 + 16 * row
    path = [(-4, 0)]
    row = 0
    for week in range(-3, columns + 5):
        path.append((week, row))
        if any(tiles.get((week, r), (None, 0, 0))[1] for r in range(7)):
            target = 6 - row
            step = 1 if target > row else -1
            for r in range(row + step, target + step, step):
                path.append((week, r))
            row = target
    arrival = {pos: i for i, pos in enumerate(path)}
    parts = [
        '<defs><clipPath id="field"><rect x="55" y="69" width="920" height="123"/></clipPath></defs>',
        '<style>@media (prefers-reduced-motion:reduce){.motion,.eaten{display:none}}</style>',
        label(34, 35, 'CONTRIBUTION SNAKE', 16, '#ffffff'),
        label(966, 35, f'{sum(n for _, n, _ in days):,} contributions', 14, '#ff435a', 'end'),
        *(label(x(w), 61, name, 11, '#e3e3e3') for w, name in month_marks(tiles)),
        *(label(33, y(r) + 4, s, 10, '#e3e3e3') for r, s in [(1,'M'), (3,'W'), (5,'F')])
    ]
    for pos, (day, count, level) in tiles.items():
        wx, wy = pos
        rect = f'x="{x(wx)-5.8:.2f}" y="{y(wy)-5.8:.2f}" width="11.6" height="11.6" rx="2.5"'
        parts.append(f'<rect {rect} fill="{DOTS[level]}"><title>{day}: {count}</title></rect>')
        if count:
            at = arrival[pos] / (len(path) - 1)
            parts.append(f'<rect class="eaten" {rect} fill="{DOTS[0]}" opacity="0">'
                         f'<animate attributeName="opacity" calcMode="discrete" dur="25s" repeatCount="indefinite" '
                         f'values="0;0.9;0" keyTimes="0;{at:.6f};1"/></rect>')
    parts.append('<g class="motion" clip-path="url(#field)">')
    for lag, color in [(3,'#9c3346'),(2,'#d84553'),(1,'#ff625e'),(0,'#ffffff')]:
        frames = [path[max(i - lag, 0)] for i in range(len(path))]
        coords = ';'.join(f'{x(w):.2f} {y(r):.2f}' for w, r in frames)
        parts.append(f'<g><animateTransform attributeName="transform" type="translate" values="{coords}" '
                     f'dur="25s" repeatCount="indefinite" calcMode="linear"/>'
                     f'<rect x="-6" y="-6" width="12" height="12" rx="4" fill="{color}"/></g>')
    parts.extend(['</g>', label(34, 219, days[0][0].isoformat(), 12, '#e3e3e3'),
                  label(966, 219, days[-1][0].isoformat(), 12, '#e3e3e3', 'end')])
    return document("Contribution snake", "The snake collects squares for days with contributions.", 240, parts)


def skyline(days, tiles):
    columns = max(w for w, _ in tiles) + 1
    step = min(15.1, 815 / columns)
    peak = max(n for _, n, _ in days)
    parts = ['<style>@keyframes light{0%,100%{opacity:0}45%{opacity:.55}}'
             '.glint{opacity:0;animation:light 6s ease-in-out infinite}'
             '@media(prefers-reduced-motion:reduce){.glint{animation:none}}</style>',
             label(34, 35, 'CONTRIBUTION SKYLINE', 16, '#ffffff'),
             label(966, 35, f'Peak day  /  {peak} contributions', 14, '#ff435a', 'end')]
    for (w, r), (day, count, level) in sorted(tiles.items(), key=lambda v: (v[0][1], v[0][0])):
        px, py = 100 + w * step - r * 9, 132 + w * 0.8 + r * 8
        h = 2 + (67 * math.sqrt(count / peak) if peak else 0)
        a = (px, py - h)
        b = (px + step * .9, py + .72 - h)
        c = (b[0] - 8, b[1] + 7)
        d = (px - 8, py + 7 - h)
        def face(points, fill):
            coords = ' '.join(f'{i:.2f},{j:.2f}' for i, j in points)
            return f'<polygon points="{coords}" fill="{fill}"/>'
        parts.extend([f'<g><title>{day}: {count}</title>',
                      face([d, c, (c[0], c[1]+h), (d[0], d[1]+h)], '#71313d' if count else '#1c1b20'),
                      face([c, b, (b[0], b[1]+h), (c[0], c[1]+h)], '#a03c4c' if count else '#26232a'),
                      face([a, b, c, d], DOTS[level])])
        if count:
            delay = w / columns * 4
            parts.append(f'<g class="glint" style="animation-delay:{delay:.2f}s">'
                         + face([a, b, c, d], '#ffe4e8') + '</g>')
        parts.append('</g>')
    parts.extend(label(round(47 + w * step), 254, name, 11, '#e3e3e3') for w, name in month_marks(tiles))
    parts.append(label(34, 283, 'Taller blocks mark days with more contributions.', 13, '#eeeeee'))
    return document('3D contribution graph', 'One block per day. Weeks run left to right.', 305, parts)


if __name__ == '__main__':
    days = calendar_days(json.loads(Path(sys.argv[1]).read_text()))
    tiles = locations(days)
    dest = Path(sys.argv[2])
    dest.mkdir(parents=True, exist_ok=True)
    for name, content in [('snake.svg', snake_calendar(days, tiles)), ('skyline.svg', skyline(days, tiles))]:
        (dest / name).write_text(content, encoding='utf-8')
