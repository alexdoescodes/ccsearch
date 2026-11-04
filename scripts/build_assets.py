#!/usr/bin/env python3
"""Generate the animated SVGs in docs/assets/ used by the README.

Everything is plain SVG + SMIL so it animates when GitHub renders it as an
<img> (no JS, no external fonts). All sample sessions are made up.

    python scripts/build_assets.py
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent.parent / "docs" / "assets"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


# ---------------------------------------------------------------- helpers

def kt(t, dur):
    return f"{min(max(t / dur, 0), 1):.4f}"


def visible(a, b, dur):
    """Discrete opacity: hidden, shown from a to b seconds, hidden again; loops."""
    if a <= 0:
        return (f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
                f'calcMode="discrete" values="1;0" keyTimes="0;{kt(b, dur)}"/>')
    return (f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
            f'calcMode="discrete" values="0;1;0" keyTimes="0;{kt(a, dur)};{kt(b, dur)}"/>')


def fade(a, b, dur, ramp=0.35):
    """Smooth opacity in at a, out at b; loops."""
    pts = [(0, 0), (a, 0), (a + ramp, 1), (b - ramp, 1), (b, 0), (dur, 0)]
    return (f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
            f'values="{";".join(str(v) for _, v in pts)}" '
            f'keyTimes="{";".join(kt(t, dur) for t, _ in pts)}"/>')


def typed(text, x, y, start, per_char, end, dur, attrs=""):
    """Text that appears one character at a time, then vanishes at `end`."""
    spans = []
    for i, ch in enumerate(text):
        t = start + i * per_char
        spans.append(f'<tspan opacity="0">{escape(ch)}{visible(t, end, dur)}</tspan>')
    return f'<text x="{x}" y="{y}" xml:space="preserve" {attrs}>{"".join(spans)}</text>'


def svg(w, h, body, title, desc):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d">\n<title id="t">{escape(title)}</title>\n'
            f'<desc id="d">{escape(desc)}</desc>\n{body}\n</svg>\n')


# ---------------------------------------------------------------- hero

CHIPS_MAX_X = 540  # left column ends here; the results panel starts at 600


def chips():
    """Feature chips. Widths assume a wide sans (8 px/char at 12 px) so fonts that
    render wider than the build machine's still fit inside the left column."""
    out, x = [], 56
    for label, color in (("typo-tolerant", "#f0a35e"), ("incremental index", "#39c5cf"),
                         ("resumes anywhere", "#f778ba")):
        w = 26 + len(label) * 8
        out.append(f'<rect x="{x}" y="258" width="{w}" height="24" rx="12" fill="{color}" fill-opacity=".10" '
                   f'stroke="{color}" stroke-opacity=".35"/>'
                   f'<text x="{x + w / 2:.0f}" y="274" text-anchor="middle" font-size="12" fill="{color}">{label}</text>')
        x += w + 10
    assert x - 10 <= CHIPS_MAX_X, f"chips overflow the left column ({x - 10} > {CHIPS_MAX_X})"
    return "".join(out)

def hero():
    W, H, D = 960, 340, 9  # content spans y 58..282: equal top/bottom margins
    rows = [("Restic backups for Docker volumes", 94),
            ("Backup sidecar healthcheck", 81),
            ("Postgres dump script cleanup", 74),
            ("Dockerfile slim-down", 69),
            ("NAS snapshot schedule", 63)]
    cards = []
    for i, (name, sc) in enumerate(rows):
        y = 118 + i * 34
        t0 = 2.3 + i * 0.12
        top = i == 0
        cards.append(f'''
  <g opacity="0">{fade(t0, D - 0.4, D, 0.3)}
    <animateTransform attributeName="transform" type="translate" dur="{D}s" repeatCount="indefinite"
      values="18 0;18 0;0 0;0 0" keyTimes="0;{kt(t0, D)};{kt(t0 + 0.35, D)};1"/>
    <rect x="600" y="{y}" width="316" height="28" rx="7" fill="{'url(#cardTop)' if top else '#ffffff'}"
      fill-opacity="{1 if top else 0.045}" stroke="{'#f0a35e' if top else '#ffffff'}" stroke-opacity="{0.9 if top else 0.08}"/>
    <text x="614" y="{y + 18.5}" font-family="{MONO}" font-size="12.5" fill="{'#fff4e8' if top else '#c9d1d9'}"
      font-weight="{700 if top else 400}">{'❯ ' if top else '  '}{escape(name)}</text>
    <text x="904" y="{y + 18.5}" text-anchor="end" font-family="{MONO}" font-size="11.5"
      fill="{'#ffd3a8' if top else '#6e7781'}">{sc}</text>
  </g>''')
    body = f'''
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#0a0e1a"/><stop offset="1" stop-color="#171126"/>
  </linearGradient>
  <radialGradient id="glowA"><stop offset="0" stop-color="#f0883e" stop-opacity=".55"/><stop offset="1" stop-color="#f0883e" stop-opacity="0"/></radialGradient>
  <radialGradient id="glowB"><stop offset="0" stop-color="#39c5cf" stop-opacity=".40"/><stop offset="1" stop-color="#39c5cf" stop-opacity="0"/></radialGradient>
  <linearGradient id="word" x1="0" y1="0" x2="1" y2="0" gradientUnits="objectBoundingBox">
    <stop offset="0" stop-color="#ffb070"/><stop offset=".45" stop-color="#ff7b72"/>
    <stop offset=".55" stop-color="#ffe2c4"/><stop offset="1" stop-color="#f778ba"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-1 0;1 0" dur="6s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="cardTop" x1="0" x2="1"><stop offset="0" stop-color="#f0883e" stop-opacity=".35"/><stop offset="1" stop-color="#f778ba" stop-opacity=".12"/></linearGradient>
  <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
    <path d="M28 0H0V28" fill="none" stroke="#ffffff" stroke-opacity=".035"/>
  </pattern>
  <clipPath id="frame"><rect width="{W}" height="{H}" rx="20"/></clipPath>
</defs>
<g clip-path="url(#frame)">
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  <rect width="{W}" height="{H}" fill="url(#grid)"/>
  <circle cx="180" cy="40" r="260" fill="url(#glowA)">
    <animateTransform attributeName="transform" type="translate" values="0 0;60 40;0 0" dur="14s" repeatCount="indefinite"/>
  </circle>
  <circle cx="820" cy="300" r="280" fill="url(#glowB)">
    <animateTransform attributeName="transform" type="translate" values="0 0;-70 -30;0 0" dur="16s" repeatCount="indefinite"/>
  </circle>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="#ffffff" stroke-opacity=".08"/>

<g font-family="{SANS}">
  <rect x="56" y="58" width="236" height="26" rx="13" fill="#ffffff" fill-opacity=".06" stroke="#ffffff" stroke-opacity=".12"/>
  <circle cx="72" cy="71" r="4" fill="#3fb950"><animate attributeName="opacity" values="1;.35;1" dur="2.4s" repeatCount="indefinite"/></circle>
  <text x="84" y="75.5" font-size="12.5" fill="#c9d1d9" letter-spacing=".4">CLI for Claude Code sessions</text>
  <text x="52" y="160" font-family="{MONO}" font-size="78" font-weight="800" fill="url(#word)" letter-spacing="-2">csearch</text>
  <text x="56" y="203" font-size="19" fill="#e6edf3">Fuzzy-find any session by what it was about.</text>
  <text x="56" y="232" font-size="19" fill="#8b949e">Arrow keys to pick. Enter to resume — from anywhere.</text>
  {chips()}
</g>

<g>
  <rect x="600" y="62" width="316" height="40" rx="10" fill="#0d1117" fill-opacity=".75" stroke="#ffffff" stroke-opacity=".14"/>
  <circle cx="622" cy="81" r="6" fill="none" stroke="#8b949e" stroke-width="2"/>
  <path d="M626.5 85.5l5 5" stroke="#8b949e" stroke-width="2" stroke-linecap="round"/>
  {typed("dokcer backup", 642, 86.5, 0.5, 0.11, D - 0.4, D, f'font-family="{MONO}" font-size="15" fill="#e6edf3"')}
  <text x="904" y="86" text-anchor="end" font-family="{MONO}" font-size="11" fill="#6e7781" opacity="0">
    {visible(2.2, D - 0.4, D)}top 5 · 0.1 s</text>
  {"".join(cards)}
</g>'''
    return svg(W, H, body, "csearch",
               "csearch: fuzzy-find any Claude Code session by what it was about, pick it with the arrow keys "
               "and resume it from anywhere. A search box types 'dokcer backup' and five ranked sessions slide in.")


# ---------------------------------------------------------------- terminal demo

def demo():
    W, H, D = 880, 556, 16
    x0 = 28
    C = {"fg": "#e6edf3", "dim": "#8b949e", "faint": "#6e7781", "accent": "#39c5cf",
         "amber": "#f0a35e", "green": "#3fb950", "pink": "#f778ba"}
    rows = [
        ("Restic backups for Docker volumes", "~/homelab", "2026-11-02 21:14", 94,
         "my docker volume backups keep failing since the restic update"),
        ("Compose healthcheck for the backup sidecar", "~/homelab", "2026-10-28 18:40", 81,
         "add a healthcheck so the backup container waits for postgres"),
        ("Postgres dump script cleanup", "~/Dev/ledger", "2026-10-19 09:02", 74,
         "clean up the nightly pg_dump script, it writes to /tmp"),
        ("Dockerfile slim-down", "~/Dev/api", "2026-09-30 14:55", 69,
         "the docker image is 1.2 GB, make it smaller"),
        ("NAS snapshot schedule", "~", "2026-09-12 22:31", 63,
         "how often should zfs snapshots run for backups"),
    ]
    t_results, t_enter, t_end = 2.9, 9.4, D - 0.5
    # (row, from, to) for the selection bar, and the key pressed when it moves
    sel = [(0, t_results, 5.0), (1, 5.0, 6.0), (2, 6.0, 6.9), (1, 6.9, 7.8), (0, 7.8, t_enter)]
    keys = [("↓", 5.0), ("↓", 6.0), ("↑", 6.9), ("↑", 7.8), ("⏎ Enter", t_enter)]
    # row = 3 lines (baselines +0, +20, +40). The selection box pads ~9 px above the
    # title's cap height and below the italic line's descenders; rows sit 9 px apart.
    top, step = 112, 82
    box_top, box_h = -20, 73

    body_rows = []
    for i, (title, path, when, sc, match) in enumerate(rows):
        y = top + i * step
        t0 = t_results + i * 0.07
        body_rows.append(f'''
    <g opacity="0">{visible(t0, t_enter, D)}
      <text x="{x0 + 22}" y="{y}" font-weight="700" fill="{C['fg']}">{escape(title)}</text>
      <text x="{x0 + 22}" y="{y + 20}" fill="{C['faint']}">{escape(path)}  ·  {when}  ·  score {sc}</text>
      <text x="{x0 + 22}" y="{y + 40}" fill="{C['dim']}" font-style="italic">› {escape(match)}</text>
    </g>''')

    tr = ";".join(f"0 {r * step}" for r, _, _ in sel)
    kts = ";".join(["0"] + [kt(a, D) for _, a, _ in sel[1:]])
    selection = f'''
    <g opacity="0">{visible(t_results, t_enter, D)}
      <g>
        <animateTransform attributeName="transform" type="translate" dur="{D}s" repeatCount="indefinite"
          calcMode="discrete" values="0 0;{tr}" keyTimes="0;{kt(t_results, D)};{kts.split(';', 1)[1]}"/>
        <rect x="{x0 - 10}" y="{top + box_top}" width="{W - 2 * x0 + 20}" height="{box_h}" rx="9"
          fill="{C['accent']}" fill-opacity=".10" stroke="{C['accent']}" stroke-opacity=".45"/>
        <text x="{x0}" y="{top}" fill="{C['accent']}" font-weight="700">❯</text>
      </g>
    </g>'''

    key_badges = []
    for label, t in keys:
        wbadge = 34 + 9 * (len(label) - 1)
        key_badges.append(f'''
    <g opacity="0">{fade(t - 0.05, t + 0.75, D, 0.12)}
      <rect x="{W - x0 - wbadge}" y="58" width="{wbadge}" height="26" rx="6" fill="#21262d" stroke="#30363d"/>
      <text x="{W - x0 - wbadge / 2}" y="76" text-anchor="middle" fill="{C['fg']}" font-size="13">{label}</text>
    </g>''')

    after = t_enter + 0.25
    body = f'''
<defs>
  <linearGradient id="chrome" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#1c2129"/><stop offset="1" stop-color="#161b22"/></linearGradient>
  <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#000" flood-opacity=".35"/></filter>
</defs>
<rect x="8" y="6" width="{W - 16}" height="{H - 22}" rx="14" fill="#0d1117" stroke="#30363d" filter="url(#shadow)"/>
<path d="M8 20a14 14 0 0 1 14-14h{W - 44}a14 14 0 0 1 14 14v18H8z" fill="url(#chrome)"/>
<circle cx="32" cy="23" r="6" fill="#ff5f57"/><circle cx="52" cy="23" r="6" fill="#febc2e"/><circle cx="72" cy="23" r="6" fill="#28c840"/>
<text x="{W / 2}" y="27" text-anchor="middle" font-family="{SANS}" font-size="12.5" fill="{C['faint']}">zsh — ~/anywhere</text>

<g font-family="{MONO}" font-size="14">
  <text x="{x0}" y="74" fill="{C['green']}">~/anywhere</text>
  <text x="{x0 + 92}" y="74" fill="{C['pink']}">❯</text>
  {typed("csearch dokcer backup", x0 + 110, 74, 0.7, 0.085, t_end, D, f'fill="{C["fg"]}"')}
  {"".join(key_badges)}
  {selection}
  {"".join(body_rows)}
  <text x="{x0}" y="{top + 4 * step + box_top + box_h + 22}" fill="{C['faint']}" font-size="12.5" opacity="0">{visible(t_results + 0.4, t_enter, D)}↑/↓ move · Enter resume · 1-9 jump · Esc quit</text>

  <g opacity="0">{visible(after, t_end, D)}
    <text x="{x0}" y="{top}" fill="{C['dim']}">→ /home/you/homelab</text>
  </g>
  <g opacity="0">{visible(after + 0.3, t_end, D)}
    <text x="{x0}" y="{top + 22}" fill="{C['dim']}">→ claude --resume 7f3c9a2e-41d8-4b6a-9c1e-2b5d8f0a7e13</text>
  </g>
  <g opacity="0">{fade(after + 1.0, t_end, D, 0.3)}
    <rect x="{x0 - 4}" y="{top + 48}" width="{W - 2 * x0 + 8}" height="96" rx="10" fill="#161b22" stroke="{C['amber']}" stroke-opacity=".6"/>
    <text x="{x0 + 16}" y="{top + 78}" fill="{C['amber']}" font-weight="700">✓ Session restored</text>
    <text x="{x0 + 16}" y="{top + 102}" fill="{C['fg']}">Restic backups for Docker volumes</text>
    <text x="{x0 + 16}" y="{top + 124}" fill="{C['faint']}">~/homelab · picked up right where you left off</text>
  </g>
  <g opacity="0">{visible(after + 1.6, t_end, D)}
    <text x="{x0}" y="{top + 182}" fill="{C['pink']}">&gt;</text>
    <rect x="{x0 + 18}" y="{top + 168}" width="9" height="18" fill="{C['fg']}">
      <animate attributeName="opacity" values="1;0;1" dur="1s" calcMode="discrete" keyTimes="0;.5;1" repeatCount="indefinite"/>
    </rect>
  </g>
</g>'''
    return svg(W, H, body, "csearch demo",
               "Terminal recording: typing 'csearch dokcer backup' (with a typo) lists the five best-matching "
               "Claude Code sessions. The selection moves with the arrow keys, Enter switches to ~/homelab and "
               "runs claude --resume on the chosen session.")


# ---------------------------------------------------------------- how it works

def how(theme):
    dark = theme == "dark"
    c = {
        "card": "#161b22" if dark else "#ffffff",
        "stroke": "#30363d" if dark else "#d0d7de",
        "fg": "#e6edf3" if dark else "#1f2328",
        "dim": "#8b949e" if dark else "#59636e",
        "accent": "#39c5cf" if dark else "#0a7ea4",
        "amber": "#f0a35e" if dark else "#bc4c00",
    }
    W, H, D = 912, 176, 4
    nodes = [("01  READ", "Transcripts", "~/.claude/projects/*.jsonl"),
             ("02  INDEX", "Cached index", "re-reads changed files only"),
             ("03  RANK", "Fuzzy match", "title · prompts · path"),
             ("04  RESUME", "claude --resume", "in the session's own dir")]
    bw, gap, y = 206, 20, 34
    parts = []
    for i, (kicker, head, sub) in enumerate(nodes):
        x = 12 + i * (bw + gap)
        a = i * (D / 4)
        parts.append(f'''
  <g>
    <rect x="{x}" y="{y}" width="{bw}" height="104" rx="12" fill="{c['card']}" stroke="{c['stroke']}"/>
    <rect x="{x}" y="{y}" width="{bw}" height="104" rx="12" fill="none" stroke="{c['accent']}" stroke-width="2" opacity="0">
      <animate attributeName="opacity" dur="{D}s" repeatCount="indefinite"
        values="0;0;1;0;0" keyTimes="0;{kt(a, D)};{kt(a + 0.35, D)};{kt(a + 1.2, D)};1"/>
    </rect>
    <text x="{x + 18}" y="{y + 30}" font-family="{MONO}" font-size="11" letter-spacing="1.5" fill="{c['amber']}" font-weight="700">{kicker}</text>
    <text x="{x + 18}" y="{y + 58}" font-family="{SANS}" font-size="17" font-weight="700" fill="{c['fg']}">{escape(head)}</text>
    <text x="{x + 18}" y="{y + 82}" font-family="{MONO}" font-size="10.5" fill="{c['dim']}">{escape(sub)}</text>
  </g>''')
        if i < len(nodes) - 1:
            x1, x2 = x + bw + 3, x + bw + gap - 3
            parts.append(f'''
  <path d="M{x1} {y + 52}H{x2 - 5}" stroke="{c['accent']}" stroke-width="2" stroke-dasharray="4 4">
    <animate attributeName="stroke-dashoffset" values="8;0" dur=".6s" repeatCount="indefinite"/>
  </path>
  <path d="M{x2 - 6} {y + 47}l6 5-6 5" fill="none" stroke="{c['accent']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>''')
    body = "".join(parts)
    return svg(W, H, body, "How csearch works",
               "Four steps: read Claude Code transcripts, keep a cached index that only re-reads changed files, "
               "fuzzy-match on title, prompts and project path, then run claude --resume in the session's own directory.")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {"hero.svg": hero(), "demo.svg": demo(),
             "how-it-works-dark.svg": how("dark"), "how-it-works-light.svg": how("light")}
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
        print(f"wrote docs/assets/{name} ({len(content) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
