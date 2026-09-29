"""Renders the profile README's SVG slices into assets/.

Every slice is part of one continuous console frame. Run fetch.py first to refresh
data/*.json; this script only reads those files and draws.

Every slice is W wide, a multiple of 40px tall (so the grid lines up across slices),
and draws the same side rails; only the first slice has the top edge and title bar,
only the last one closes the frame.
"""
import base64, datetime, html, io, json, math, pathlib, re, textwrap

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = HERE / "data"
OUT = ROOT / "assets"
FONT_DIR = HERE / "fonts"
CYAN, MAGENTA, GREEN = "#00d9ff", "#ff2bd6", "#3fb950"
W, M = 880, 16            # slice width, transparent side margin (room for the glow)
FL, FR = M, W - M         # frame left / right
X = 52                    # text left edge
e = html.escape


def faces(text, weights=(400, 700)):
    out = []
    for w in weights:
        f = TTFont(FONT_DIR / f"jetbrains-mono-latin-{w}-normal.woff2", recalcTimestamp=False)  # fixed timestamp keeps output byte-identical between runs
        o = subset.Options(); o.flavor = "woff2"; o.layout_features = []
        s = subset.Subsetter(o); s.populate(text=text); s.subset(f)
        b = io.BytesIO(); f.flavor = "woff2"; f.save(b)
        out.append(f"@font-face{{font-family:'JBM';font-weight:{w};src:url(data:font/woff2;base64,"
                   f"{base64.b64encode(b.getvalue()).decode()}) format('woff2')}}")
    return "".join(out)


BASE_CSS = f"""text{{font-family:'JBM',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:15px}}
.dim{{fill:#8b949e}}.cy{{fill:{CYAN}}}.fg{{fill:#c9d1d9}}.gr{{fill:{GREEN}}}.wh{{fill:#f0fbff}}
@keyframes fadein{{from{{opacity:0;transform:translateX(-6px)}}to{{opacity:1;transform:none}}}}
@keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
.ln{{animation:fadein .35s ease-out both}}
.cursor{{animation:blink 1.05s step-end infinite}}
.dot{{animation:pulse 2s ease-in-out infinite}}"""

DEFS = f"""<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{CYAN}" stroke-opacity=".06"/></pattern>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="g" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="4"/></filter>"""


def slice_svg(h, body, *, title, desc, text, top=False, bottom=False, css="", defs="", weights=(400, 700)):
    assert h % 40 == 0, h
    y0 = M if top else 0
    y1 = h - M if bottom else h
    rails = f"M{FL} {y0}V{y1}M{FR} {y0}V{y1}"
    if top:
        rails += f"M{FL} {y0}H{FR}"
    if bottom:
        rails += f"M{FL} {y1}H{FR}"
    gy0 = y0 if top else -40
    gy1 = y1 if bottom else h + 40
    glow = f"M{FL} {gy0}V{gy1}M{FR} {gy0}V{gy1}" + (f"M{FL} {y0}H{FR}" if top else "") + (f"M{FL} {y1}H{FR}" if bottom else "")
    corners = ""
    if top:
        corners += f'<path d="M{FL-7} {y0+18}V{y0-7}H{FL+18}"/><path d="M{FR-18} {y0-7}H{FR+7}V{y0+18}"/>'
    if bottom:
        corners += f'<path d="M{FL-7} {y1-18}V{y1+7}H{FL+18}"/><path d="M{FR-18} {y1+7}H{FR+7}V{y1-18}"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-labelledby="t d">
<title id="t">{e(title)}</title>
<desc id="d">{e(desc)}</desc>
<style>
{faces(text, weights)}
{BASE_CSS}
{css}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<defs>
{DEFS}
{defs}
</defs>
<path d="{glow}" fill="none" stroke="{CYAN}" stroke-width="3" opacity=".55" filter="url(#glow)"/>
<rect x="{FL}" y="{y0}" width="{FR-FL}" height="{y1-y0}" fill="#03040a"/>
<rect x="{FL}" y="{y0}" width="{FR-FL}" height="{y1-y0}" fill="url(#grid)"/>
{body}
<path d="{rails}" fill="none" stroke="{CYAN}" stroke-width="1.2"/>
<g fill="none" stroke="{CYAN}" stroke-width="2">{corners}</g>
</svg>
'''


def heading(y, name, counter):
    return f'''<text x="{X}" y="{y}" font-weight="700" fill="{CYAN}" filter="url(#g)" opacity=".8" style="font-size:20px">~/</text>
<text x="{X}" y="{y}" font-weight="700" style="font-size:20px"><tspan class="cy">~/</tspan><tspan class="wh">{e(name)}</tspan></text>
<text x="{FR-36}" y="{y}" text-anchor="end" letter-spacing="2" fill="#6e7681" style="font-size:12px">{e(counter)}</text>
<line x1="{X}" y1="{y+14}" x2="{FR-36}" y2="{y+14}" stroke="{CYAN}" stroke-opacity=".4"/>
<line x1="{X}" y1="{y+14}" x2="{X+120}" y2="{y+14}" stroke="{CYAN}" stroke-width="2"/>
<line x1="{X}" y1="{y+14}" x2="{X+120}" y2="{y+14}" stroke="{CYAN}" stroke-width="3" filter="url(#g)"/>'''


def stagger(rows, y0, lh, delay0=0.15, step=0.12):
    """rows: markup strings with {y}, or None for a small spacer. Returns (markup, next_y)."""
    out, y, i = [], y0, 0
    for r in rows:
        if r is None:
            y += 14; continue
        i += 1
        out.append(f'<g class="ln" style="animation-delay:{delay0 + i*step:.2f}s">' + r.replace("{y}", str(y)) + "</g>")
        y += lh
    return "\n".join(out), y


def up40(v):
    return int(math.ceil(v / 40) * 40)


# ─────────────────────────────── header ───────────────────────────────
def build_header():
    bar_left, bar_right = "SYS://PILOTRONICA // NODE:GIORGI", "ONLINE · ALL SYSTEMS NOMINAL"
    name = "GIORGI KOBAIDZE"
    lines = ["software engineer · engineering manager", "10 years of C# / .NET, back-end at heart",
             "building open-source tools under "]
    text = bar_left + bar_right + name + "$ whoami>>" + "".join(lines) + "PILOTRONICA"
    h = 360
    css = f"""@keyframes type{{from{{width:0}}}}
@keyframes flicker{{0%{{opacity:0}}10%{{opacity:1}}14%{{opacity:.2}}22%{{opacity:1}}30%{{opacity:.4}}40%,100%{{opacity:1}}}}
@keyframes gm{{0%,92%,100%{{transform:translate(0,0)}}93%{{transform:translate(5px,-1px)}}95%{{transform:translate(-3px,1px)}}97%{{transform:translate(2px,0)}}}}
@keyframes gc{{0%,92%,100%{{transform:translate(0,0)}}93%{{transform:translate(-5px,1px)}}95%{{transform:translate(4px,-1px)}}97%{{transform:translate(-2px,0)}}}}
.typing{{animation:type .7s steps(8) .3s both}}
.name{{animation:flicker .9s linear 1.1s both}}
.gm{{animation:gm 6s linear 2s infinite}}.gc{{animation:gc 6s linear 2s infinite}}"""
    defs = f"""<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" fill-opacity=".2"/></pattern>
<filter id="tglow" x="-5%" y="-40%" width="110%" height="180%"><feGaussianBlur stdDeviation="9"/></filter>
<filter id="sglow" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="3"/></filter>
<clipPath id="typeclip"><rect class="typing" x="{X}" y="80" width="140" height="30"/></clipPath>"""
    dotx = FR - 20 - len(bar_right) * 8.2 - 16
    rows = [f'<text class="fg" x="{X}" y="{{y}}"><tspan class="cy">&gt;&gt;</tspan> {e(lines[0])}</text>',
            f'<text class="fg" x="{X}" y="{{y}}"><tspan class="cy">&gt;&gt;</tspan> {e(lines[1])}</text>',
            f'<text class="fg" x="{X}" y="{{y}}"><tspan class="cy">&gt;&gt;</tspan> {e(lines[2])}<tspan class="cy" font-weight="700">PILOTRONICA</tspan></text>']
    desc_lines, _ = stagger(rows, 218, 24, delay0=1.75, step=0.25)
    body = f'''<rect x="{FL}" y="{M}" width="{FR-FL}" height="34" fill="{CYAN}" fill-opacity=".08"/>
<line x1="{FL}" y1="{M+34}" x2="{FR}" y2="{M+34}" stroke="{CYAN}" stroke-opacity=".5"/>
<text x="{FL+16}" y="{M+22}" letter-spacing="1" class="cy" style="font-size:12px">{e(bar_left)}</text>
<text x="{FR-20}" y="{M+22}" letter-spacing="1" class="dim" text-anchor="end" style="font-size:12px">{e(bar_right)}</text>
<circle class="dot" cx="{dotx}" cy="{M+18}" r="4" fill="{GREEN}"/>
<circle class="dot" cx="{dotx}" cy="{M+18}" r="4" fill="{GREEN}" filter="url(#sglow)"/>
<g clip-path="url(#typeclip)"><text x="{X}" y="102" class="dim"><tspan class="gr">$</tspan> whoami</text></g>
<g class="name" font-weight="800" letter-spacing="2" style="font-size:56px">
<text x="{X}" y="172" fill="{CYAN}" opacity=".55" filter="url(#tglow)" style="font-size:56px">{name}</text>
<g class="gm"><text x="{X+3}" y="172" fill="{MAGENTA}" opacity=".75" style="font-size:56px">{name}</text></g>
<g class="gc"><text x="{X-3}" y="172" fill="{CYAN}" opacity=".85" style="font-size:56px">{name}</text></g>
<text x="{X}" y="172" fill="#f0fbff" style="font-size:56px">{name}</text>
</g>
{desc_lines}
<g class="ln" style="animation-delay:2.8s">
<text x="{X}" y="304" class="gr">$</text>
<rect class="cursor" x="{X+18}" y="291" width="10" height="17" fill="{CYAN}"/>
<rect class="cursor" x="{X+18}" y="291" width="10" height="17" fill="{CYAN}" filter="url(#sglow)"/>
</g>
<rect x="{FL}" y="{M+35}" width="{FR-FL}" height="{h-M-35}" fill="url(#scan)"/>'''
    return slice_svg(h, body, title="Giorgi Kobaidze",
                     desc="Software engineer and engineering manager. 10 years of C# and .NET, back-end at heart. "
                          "Building open-source tools under Pilotronica.",
                     text=text, top=True, css=css, defs=defs, weights=(400, 700, 800))


# ─────────────────────────────── footer ───────────────────────────────
def build_footer():
    h = 80
    text = "$ exit connection to georgekobaidze closed. // EOF"
    body = f'''<text x="{X}" y="30" class="dim"><tspan class="gr">$</tspan> exit</text>
<text x="{X}" y="52" class="dim">connection to <tspan class="cy">georgekobaidze</tspan> closed. <tspan fill="#484f58">// EOF</tspan></text>'''
    return slice_svg(h, body, title="End of profile", desc="Connection closed.", text=text, bottom=True)



# ────────────────────────────── projects ──────────────────────────────
HW = W // 2   # half-slice width (440, a multiple of 40 so the grid stays aligned)


def half_slice(h, side, body, *, title, desc, text, weights=(400, 700)):
    """Left or right half of a full-width row; only its outer side has a rail."""
    assert h % 40 == 0
    rx = FL if side == "L" else HW - M
    bx0, bx1 = (FL, HW) if side == "L" else (0, HW - M)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{HW}" height="{h}" viewBox="0 0 {HW} {h}" role="img" aria-labelledby="t d">
<title id="t">{e(title)}</title>
<desc id="d">{e(desc)}</desc>
<style>
{faces(text, weights)}
{BASE_CSS}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<defs>
{DEFS}
</defs>
<path d="M{rx} -40V{h+40}" fill="none" stroke="{CYAN}" stroke-width="3" opacity=".55" filter="url(#glow)"/>
<rect x="{bx0}" y="0" width="{bx1-bx0}" height="{h}" fill="#03040a"/>
<rect x="{bx0}" y="0" width="{bx1-bx0}" height="{h}" fill="url(#grid)"/>
{body}
<path d="M{rx} 0V{h}" fill="none" stroke="{CYAN}" stroke-width="1.2"/>
</svg>
'''


PROJECTS = [
    dict(slug="noterunway", name="NoteRunway", url="https://github.com/georgekobaidze/noterunway",
         tag="HACKATHON WINNER", tagc=GREEN, stars=13, stack="Next.js · TypeScript · MCP",
         desc="AI-powered Notion workspace management: clean up and organize your workspace with deterministic scans and AI analysis."),
    dict(slug="metal-birds-watch", name="Metal Birds Watch", url="https://github.com/georgekobaidze/metal-birds-watch",
         tag="HACKATHON WINNER", tagc=GREEN, stars=7, stack="Node.js · Leaflet · JavaScript",
         desc="Real-time notifications when planes fly over your location, with live aircraft data on an interactive map."),
    dict(slug="sunday-dev-drive", name="Sunday DEV Drive", url="https://github.com/georgekobaidze/sunday-dev-drive",
         tag="DEV WEEKEND CHALLENGE", tagc=MAGENTA, stars=9, stack="Three.js · JavaScript · DEV API",
         desc="A synthwave drive through your DEV Community articles, with your posts lit up on neon roadside billboards."),
    dict(slug="neuralhats", name="NeuralHats", url="https://github.com/georgekobaidze/neuralhats",
         tag="GEMMA 4 CHALLENGE", tagc=MAGENTA, stars=4, stack="React · FastAPI · Gemma 4",
         desc="Six AI personas debate any topic using the Six Thinking Hats framework. Runs fully local."),
]
CARD_H = 200


def build_projects_head():
    h = 120
    body = heading(44, "projects", "// 03") + f'''
<g class="ln" style="animation-delay:.2s"><text x="{X}" y="96" class="dim"><tspan class="gr">$</tspan> ls -l ~/projects</text></g>'''
    return slice_svg(h, body, title="Projects", desc="Projects", text="~/projects// 02$ ls -l")


def build_card(p, side, delay, stars=None):
    p = dict(p, stars=stars.get(p["slug"], p["stars"]) if stars else p["stars"])
    x0 = 52 if side == "L" else 10          # card box, 378 wide, 20px gutter between the two cards
    cw, y0, ch = 378, 12, 176
    pad = 18
    tx = x0 + pad
    cut = 16
    box = f"M{x0} {y0}H{x0+cw-cut}L{x0+cw} {y0+cut}V{y0+ch}H{x0+cut}L{x0} {y0+ch-cut}Z"
    lines = textwrap.wrap(p["desc"], 43)
    assert len(lines) <= 3, lines
    tag_w = len(p["tag"]) * 7.6 + 16
    title_w = len(p["name"]) * 10.2
    desc = "\n".join(f'<text x="{tx}" y="{100 + i*20}" class="fg" style="font-size:13px">{e(l)}</text>' for i, l in enumerate(lines))
    sx = x0 + cw - pad
    star = f'<path transform="translate({sx - len(str(p["stars"]))*7.2 - 20} 158) scale(.55)" d="M10 0l2.9 6.6 7.1.6-5.4 4.7 1.6 7L10 15.2 3.8 18.9l1.6-7L0 7.2l7.1-.6z" fill="#e3b341"/>'
    body = f'''<g class="ln" style="animation-delay:{delay:.2f}s">
<path d="{box}" fill="{CYAN}" fill-opacity=".035"/>
<path d="{box}" fill="none" stroke="{CYAN}" stroke-opacity=".4"/>
<path d="M{x0+cw-cut} {y0}L{x0+cw} {y0+cut}" stroke="{CYAN}" stroke-width="2"/>
<text x="{tx}" y="{y0+34}" font-weight="700" fill="{CYAN}" filter="url(#g)" opacity=".6" style="font-size:17px">{e(p["name"])}</text>
<text x="{tx}" y="{y0+34}" font-weight="700" class="cy" style="font-size:17px">{e(p["name"])}</text>
<path d="M{tx+title_w+11} {y0+31}l8-8M{tx+title_w+13} {y0+23}h6v6" fill="none" stroke="{CYAN}" stroke-width="1.6"/>
<rect x="{tx}" y="{y0+46}" width="{tag_w}" height="18" fill="none" stroke="{p["tagc"]}" stroke-opacity=".8"/>
<text x="{tx+8}" y="{y0+59}" letter-spacing="1" fill="{p["tagc"]}" style="font-size:11px">{e(p["tag"])}</text>
{desc}
<text x="{tx}" y="{y0+158}" class="dim" style="font-size:12px">{e(p["stack"])}</text>
{star}
<text x="{sx}" y="{y0+158}" text-anchor="end" class="dim" style="font-size:12px">{p["stars"]}</text>
</g>'''
    text = p["name"] + p["tag"] + p["desc"] + p["stack"] + str(p["stars"])
    return half_slice(CARD_H, side, body, title=p["name"],
                      desc=f'{p["name"]}: {p["desc"]} Built with {p["stack"].replace(" · ", ", ")}. {p["stars"]} stars.', text=text)



# ─────────────────────────────── stats ────────────────────────────────
AMBER, VIOLET = "#e3b341", "#bc8cff"


def fmt(n):
    return "—" if n is None else f"{n:,}"


def tile(x, y, w, h, label, value, sub, delay, pending=False):
    vc = "#484f58" if pending else CYAN
    glow = "" if pending else f'<text x="{x+16}" y="{y+50}" font-weight="700" fill="{CYAN}" filter="url(#g)" opacity=".55" style="font-size:30px">{e(value)}</text>'
    return f'''<g class="ln" style="animation-delay:{delay:.2f}s">
<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{CYAN}" fill-opacity=".035" stroke="{CYAN}" stroke-opacity=".35"/>
<path d="M{x} {y+12}V{y}H{x+12}" fill="none" stroke="{CYAN}" stroke-width="2"/>
<text x="{x+16}" y="{y+22}" letter-spacing="1.5" class="dim" style="font-size:10.5px">{e(label)}</text>
{glow}<text x="{x+16}" y="{y+50}" font-weight="700" fill="{vc}" style="font-size:30px">{e(value)}</text>
<text x="{x+16}" y="{y+h-12}" fill="#6e7681" style="font-size:12px">{e(sub)}</text>
</g>'''


def build_stats(d):
    y = datetime.date.fromisoformat(d["updated"])
    since = datetime.date.fromisoformat(d["created_at"][:10])
    yrs = (y - since).days // 365
    parts = []
    parts.append(heading(44, "stats", "// 02"))
    parts.append(f'<g class="ln" style="animation-delay:.15s"><text x="{X}" y="96" class="dim"><tspan class="gr">$</tspan> gh stats --user georgekobaidze</text></g>')
    # row 1 — big tiles
    tw, gap, ty, th = 182, 16, 118, 92
    t1 = [("TOTAL STARS", fmt(d["stars"]), f"across {d.get('repo_count', 'all')} repos" if d.get("repo_count") else "across all repos"),
          (f"CONTRIBUTIONS {d['year']}", fmt(d["contributions_year"]), f"{fmt(d['contributions_all'])} all time")
          if "contributions_year" in d else   # older data files only have commit counts
          (f"COMMITS {d['year']}", fmt(d["commits_year"]), f"{fmt(d['commits_all'])} all time"),
          ("PULL REQUESTS", fmt(d["prs"]), f"{fmt(d['prs_merged'])} merged"),
          ("CURRENT STREAK", f"{d['streak_current']}d", f"longest: {d['streak_longest']} days")]
    for i, (lab, val, sub) in enumerate(t1):
        parts.append(tile(X + i * (tw + gap), ty, tw, th, lab, val, sub, .25 + i * .08))
    # row 2 — neofetch list + languages
    ry, rh = ty + th + 16, 150
    lw = 300
    kv = [("followers", fmt(d["followers"])), ("forks", fmt(d["forks"])),
          ("member since", f"{since:%b %Y} ({yrs}y)"), ("hackathon wins", f"{d['hackathon_wins']} ★")]
    rows = "\n".join(
        f'<text x="{X+16}" y="{ry+38+i*28}" xml:space="preserve"><tspan class="cy">{e(k)}</tspan><tspan class="dim">{"." * (16 - len(k))}</tspan> <tspan class="fg">{e(v)}</tspan></text>'
        for i, (k, v) in enumerate(kv))
    parts.append(f'''<g class="ln" style="animation-delay:.6s">
<rect x="{X}" y="{ry}" width="{lw}" height="{rh}" fill="{CYAN}" fill-opacity=".035" stroke="{CYAN}" stroke-opacity=".35"/>
<path d="M{X} {ry+12}V{ry}H{X+12}" fill="none" stroke="{CYAN}" stroke-width="2"/>
{rows}
</g>''')
    lx = X + lw + gap
    lwid = (FR - 36) - lx
    langs = sorted(d["languages"].items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in langs)
    top = langs[:5]
    other = total - sum(v for _, v in top)
    items = [(k, v / total) for k, v in top] + ([("Other", other / total)] if other else [])
    cols = [CYAN, MAGENTA, GREEN, AMBER, VIOLET, "#6e7681"]
    bx, by, bw = lx + 16, ry + 42, lwid - 32
    segs, cx = [], bx
    for (k, p), c in zip(items, cols):
        w = bw * p
        segs.append(f'<rect x="{cx:.1f}" y="{by}" width="{max(w-2,1):.1f}" height="8" fill="{c}"/>')
        segs.append(f'<rect x="{cx:.1f}" y="{by}" width="{max(w-2,1):.1f}" height="8" fill="{c}" filter="url(#g)" opacity=".6"/>')
        cx += w
    legend = []
    for i, ((k, p), c) in enumerate(zip(items, cols)):
        col, row = i % 2, i // 2
        lxx = bx + col * (bw / 2)
        lyy = by + 36 + row * 26
        legend.append(f'<rect x="{lxx}" y="{lyy-9}" width="9" height="9" fill="{c}"/>'
                      f'<text x="{lxx+18}" y="{lyy}" class="fg" style="font-size:13px">{e(k)}</text>'
                      f'<text x="{lxx + bw/2 - 24}" y="{lyy}" text-anchor="end" class="dim" style="font-size:13px">{p*100:.1f}%</text>')
    parts.append(f'''<g class="ln" style="animation-delay:.7s">
<rect x="{lx}" y="{ry}" width="{lwid}" height="{rh}" fill="{CYAN}" fill-opacity=".035" stroke="{CYAN}" stroke-opacity=".35"/>
<path d="M{lx} {ry+12}V{ry}H{lx+12}" fill="none" stroke="{CYAN}" stroke-width="2"/>
<text x="{lx+16}" y="{ry+24}" letter-spacing="1.5" class="dim" style="font-size:10.5px">TOP LANGUAGES</text>
<rect x="{bx}" y="{by}" width="{bw}" height="8" fill="#11161d"/>
{"".join(segs)}
{"".join(legend)}
</g>''')
    # row 3 — DEV Community (tiles without data are left out; the row hides if all are missing)
    dv = d.get("dev") or {}
    t3 = [(lab, dv.get(k)) for lab, k in (("ARTICLES", "articles"), ("REACTIONS", "reactions"), ("COMMENTS", "comments"),
                                          ("VIEWS", "views"), ("DEV FOLLOWERS", "followers"))]
    t3 = [(lab, v) for lab, v in t3 if v is not None]
    fy = ry + rh + 30
    if t3:
        dy = ry + rh + 34
        parts.append(f'<g class="ln" style="animation-delay:.8s"><text x="{X}" y="{dy}" class="dim"><tspan class="gr">$</tspan> dev stats --user georgekobaidze</text></g>')
        n = len(t3)
        dw = (FR - 36 - X - (n - 1) * 12) / n
        for i, (lab, val) in enumerate(t3):
            parts.append(tile(X + i * (dw + 12), dy + 16, dw, 76, lab, fmt(val), "", .9 + i * .06))
        fy = dy + 16 + 76 + 30
    parts.append(f'<text x="{FR-36}" y="{fy}" text-anchor="end" fill="#484f58" style="font-size:11px">// last sync {d["updated"]}</text>')
    h = up40(fy + 16)
    text = "".join(str(x) for x in ["~/stats// 02$ gh stats --user georgekobaidze dev stats", "".join(p for p in parts)])
    text = re.sub(r"<[^>]+>", "", text) + "0123456789,—%.★()d"
    activity = (f"{d['contributions_year']} contributions in {d['year']}, {d['contributions_all']} all time"
                if "contributions_year" in d else f"{d['commits_year']} commits in {d['year']}, {d['commits_all']} all time")
    desc = (f"GitHub stats: {d['stars']} total stars; {activity}; "
            f"{d['prs']} pull requests ({d['prs_merged']} merged); current streak {d['streak_current']} days, longest {d['streak_longest']}; "
            f"{d['followers']} followers; {d['forks']} forks; member since {since:%B %Y}; {d['hackathon_wins']} hackathon wins. "
            "Top languages: " + ", ".join(f"{k} {p*100:.1f}%" for k, p in items) + "."
            + ("" if not t3 else " DEV Community: " + ", ".join(f"{fmt(v)} {lab.lower()}" for lab, v in t3) + "."))
    return slice_svg(h, "\n".join(parts), title="Stats", desc=desc, text=html.unescape(text))


# ─────────────────────────────── stack ────────────────────────────────
STACK = [
    ("languages", ["C#", "Java", "TypeScript", "JavaScript", "Python"]),
    ("frameworks", [".NET", "Node.js", "FastAPI"]),
    ("databases", ["PostgreSQL", "MS SQL", "MySQL", "Redis", "MongoDB"]),
    ("cloud", ["AWS", "Azure"]),
    ("front-end", ["React", "Next.js", "Three.js", "Tailwind CSS"]),
]


def build_stack():
    parts = [heading(44, "stack", "// 04"),
             f'<g class="ln" style="animation-delay:.15s"><text x="{X}" y="96" class="dim"><tspan class="gr">$</tspan> scan --loadout --top-level</text></g>']
    y, rowh = 126, 44
    cw = 0.6 * 13          # char advance at 13px
    for r, (cat, items) in enumerate(STACK):
        parts.append(f'<g class="ln" style="animation-delay:{.25 + r*.1:.2f}s">')
        parts.append(f'<text x="{X}" y="{y+20}" class="dim" style="font-size:13px">{e(cat)}</text>')
        parts.append(f'<text x="{X+104}" y="{y+20}" class="cy" style="font-size:13px">›</text>')
        x = X + 124
        for it in items:
            w = len(it) * cw + 26
            parts.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="30" fill="{CYAN}" fill-opacity=".06" stroke="{CYAN}" stroke-opacity=".55"/>')
            parts.append(f'<path d="M{x:.1f} {y+8}V{y}H{x+8:.1f}" fill="none" stroke="{CYAN}" stroke-width="2"/>')
            parts.append(f'<text x="{x+13:.1f}" y="{y+20}" font-weight="700" class="cy" style="font-size:13px">{e(it)}</text>')
            x += w + 10
        parts.append("</g>")
        y += rowh
    h = up40(y + 10)
    text = "~/stack// 04$ scan --loadout --top-level›" + "".join(c + "".join(i) for c, i in STACK)
    desc = "Tech stack. " + " ".join(f"{c}: {', '.join(i)}." for c, i in STACK)
    return slice_svg(h, "\n".join(parts), title="Tech stack", desc=desc, text=text)


# ─────────────────────────────── writing ──────────────────────────────
HEART = "M8 14.2 6.9 13.2C3 9.7.5 7.4.5 4.6.5 2.3 2.3.5 4.6.5c1.3 0 2.5.6 3.4 1.6C8.9 1.1 10.1.5 11.4.5c2.3 0 4.1 1.8 4.1 4.1 0 2.8-2.5 5.1-6.4 8.6z"
BUBBLE = "M1.5 1.5h13v9h-7l-3.5 3v-3h-2.5z"


def build_writing_head():
    body = heading(44, "writing", "// 05") + f'''
<g class="ln" style="animation-delay:.15s"><text x="{X}" y="96" class="dim"><tspan class="gr">$</tspan> tail -n 5 ~/dev.to/posts.log <tspan fill="#484f58"># auto-updated</tspan></text></g>'''
    return slice_svg(120, body, title="Writing", desc="Latest articles on DEV Community",
                     text="~/writing// 05$ tail -n 5 ~/dev.to/posts.log # auto-updated")


def build_article_row(a, i):
    date = a["published_at"][:10]
    title = a["title"]
    maxc = 58
    shown = title if len(title) <= maxc else title[:maxc - 1].rstrip(" .,:;") + "…"
    tx = X + 112
    rx = FR - 36
    rc, cc = str(a["reactions"]), str(a["comments"])
    # right block:  ♥ 169   ▭ 218   ↗
    ax = rx - 10
    cx_num = ax - 18
    cx_icon = cx_num - 3 * 7.8 - 22       # fixed columns (room for 3 digits) so rows line up
    rx_num = cx_icon - 16
    rx_icon = rx_num - 3 * 7.8 - 22
    body = f'''<g class="ln" style="animation-delay:{.2 + i*.08:.2f}s">
<rect x="{X-10}" y="4" width="{rx - X + 20}" height="32" fill="{CYAN}" fill-opacity="{'.04' if i % 2 == 0 else '0'}"/>
<text x="{X}" y="25" class="dim" style="font-size:13px">{date}</text>
<text x="{X+94}" y="25" class="cy" style="font-size:13px">›</text>
<text x="{tx}" y="25" class="fg" style="font-size:14px">{e(shown)}</text>
<path transform="translate({rx_icon:.1f} 13) scale(.8)" d="{HEART}" fill="{MAGENTA}"/>
<text x="{rx_num:.1f}" y="25" text-anchor="end" class="dim" style="font-size:13px">{rc}</text>
<path transform="translate({cx_icon:.1f} 13) scale(.8)" d="{BUBBLE}" fill="none" stroke="{CYAN}" stroke-width="1.5" stroke-linejoin="round"/>
<text x="{cx_num:.1f}" y="25" text-anchor="end" class="dim" style="font-size:13px">{cc}</text>
<path d="M{ax-6} 25l8-8M{ax-4} 17h6v6" fill="none" stroke="{CYAN}" stroke-width="1.5"/>
</g>'''
    text = date + "›" + shown + rc + cc
    return slice_svg(40, body, title=title,
                     desc=f"{title}. Published {date}. {rc} reactions, {cc} comments.", text=text)


def build_writing_more():
    body = f'''<g class="ln" style="animation-delay:.7s">
<text x="{X}" y="26" style="font-size:13px"><tspan class="gr">&gt;&gt;</tspan><tspan class="cy"> read all articles on DEV Community</tspan></text>
<path d="M{X+298} 26l8-8M{X+300} 18h6v6" fill="none" stroke="{CYAN}" stroke-width="1.5"/>
</g>'''
    return slice_svg(40, body, title="All articles", desc="Read all articles on DEV Community",
                     text=">> read all articles on DEV Community")


# ──────────────────────────────── links ───────────────────────────────
LINKS = [
    ("devdotto", "DEV", "@georgekobaidze", "https://dev.to/georgekobaidze"),
    ("linkedin", "LinkedIn", "in/giorgikobaidze", "https://www.linkedin.com/in/giorgikobaidze/"),
    ("x", "X", "@georgekobaidze", "https://x.com/georgekobaidze"),
    ("youtube", "YouTube", "@Pilotronica", "https://www.youtube.com/@Pilotronica"),
    ("discord", "Discord", "say hi", "https://discord.com/users/571315867426488330"),
]
ICONS = json.load(open(HERE / "icons.json"))
SEG = W // len(LINKS)     # 176 px per button slice
BTN_W, BTN_GAP = 124, 39  # buttons line up with the text column (x = 52 … 828)


def icon_markup(key, x, y, size=18):
    if key == "linkedin":   # simple generic "in" glyph (LinkedIn isn't in Simple Icons)
        return (f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="3" fill="{CYAN}"/>'
                f'<text x="{x + size/2}" y="{y + size - 4.5}" text-anchor="middle" font-weight="700" fill="#03040a" style="font-size:12px">in</text>')
    d = ICONS[key]
    return f'<path transform="translate({x} {y}) scale({size/24})" d="{d}" fill="{CYAN}"/>'


def build_links_head():
    body = heading(44, "links", "// 01") + f'''
<g class="ln" style="animation-delay:.15s"><text x="{X}" y="96" class="dim"><tspan class="gr">$</tspan> ping georgekobaidze --all-channels</text></g>'''
    return slice_svg(120, body, title="Links", desc="Where to find me", text="~/links// 01$ ping georgekobaidze --all-channels")


def build_link_button(k):
    key, label, handle, url = LINKS[k]
    h = 80
    x0 = SEG * k                       # this slice's position inside the full-width row
    lx = X + k * (BTN_W + BTN_GAP) - x0
    first, last = k == 0, k == len(LINKS) - 1
    bg0 = FL - x0 if first else 0
    bg1 = FR - x0 if last else SEG
    rails = (f"M{FL - x0} 0V{h}" if first else "") + (f"M{FR - x0} 0V{h}" if last else "")
    glow = (f"M{FL - x0} -40V{h+40}" if first else "") + (f"M{FR - x0} -40V{h+40}" if last else "")
    by, bh, cut = 12, 56, 12
    box = f"M{lx} {by}H{lx+BTN_W-cut}L{lx+BTN_W} {by+cut}V{by+bh}H{lx}Z"
    text = label + handle + "in"
    body = f'''<g class="ln" style="animation-delay:{.25 + k*.08:.2f}s">
<path d="{box}" fill="{CYAN}" fill-opacity=".05"/>
<path d="{box}" fill="none" stroke="{CYAN}" stroke-opacity=".55"/>
<path d="M{lx+BTN_W-cut} {by}L{lx+BTN_W} {by+cut}" stroke="{CYAN}" stroke-width="2"/>
<g filter="url(#g)" opacity=".5">{icon_markup(key, lx+12, by+11)}</g>
{icon_markup(key, lx+12, by+11)}
<text x="{lx+38}" y="{by+25}" font-weight="700" class="cy" style="font-size:13px">{e(label)}</text>
<text x="{lx+12}" y="{by+46}" class="dim" style="font-size:10px">{e(handle)}</text>
</g>'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{SEG}" height="{h}" viewBox="0 0 {SEG} {h}" role="img" aria-labelledby="t d">
<title id="t">{e(label)}</title>
<desc id="d">{e(label)}: {e(url)}</desc>
<style>
{faces(text)}
{BASE_CSS}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<defs>
<pattern id="grid" x="{(-x0) % 40}" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{CYAN}" stroke-opacity=".06"/></pattern>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
<filter id="g" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="4"/></filter>
</defs>
{f'<path d="{glow}" fill="none" stroke="{CYAN}" stroke-width="3" opacity=".55" filter="url(#glow)"/>' if glow else ""}
<rect x="{bg0}" y="0" width="{bg1-bg0}" height="{h}" fill="#03040a"/>
<rect x="{bg0}" y="0" width="{bg1-bg0}" height="{h}" fill="url(#grid)"/>
{body}
{f'<path d="{rails}" fill="none" stroke="{CYAN}" stroke-width="1.2"/>' if rails else ""}
</svg>
'''

def write(rel, svg):
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg)


def main():
    global OUT
    import argparse
    ap = argparse.ArgumentParser(description="Render the profile SVGs from data/*.json.")
    ap.add_argument("--data", type=pathlib.Path, default=DATA, help="folder with stats.json and articles.json")
    ap.add_argument("--out", type=pathlib.Path, default=OUT, help="folder to write the SVGs into")
    args = ap.parse_args()
    OUT = args.out
    stats = json.load(open(args.data / "stats.json"))
    articles = json.load(open(args.data / "articles.json"))
    stars = stats.get("repo_stars", {})
    write("header.svg", build_header())
    write("links.svg", build_links_head())
    for k, (key, *_) in enumerate(LINKS):
        write(f"links/{'dev' if key == 'devdotto' else key}.svg", build_link_button(k))
    write("stats.svg", build_stats(stats))
    write("projects.svg", build_projects_head())
    for i, p in enumerate(PROJECTS):
        write(f"card-{p['slug']}.svg", build_card(p, "L" if i % 2 == 0 else "R", 0.3 + i * 0.12, stars))
    write("stack.svg", build_stack())
    write("writing.svg", build_writing_head())
    for i, a in enumerate(articles[:5]):
        write(f"writing/post-{i+1}.svg", build_article_row(a, i))
    write("writing/all-articles.svg", build_writing_more())
    write("footer.svg", build_footer())
    print("rendered", len(list(OUT.rglob("*.svg"))), "SVGs into", OUT)


if __name__ == "__main__":
    main()
