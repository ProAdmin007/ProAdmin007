"""Genereert de SVG's voor het profiel (stats, talen, projectkaarten, activiteit, views-trend)."""
import csv
import datetime as dt
import json
import os
import re
import textwrap
import urllib.request
from xml.sax.saxutils import escape

USER = "ProAdmin007"
FEATURED = ["Poland-Energy-Attack-Visualizer-2025-2026", "Onderstation-SIM-Pro",
            "Groningen050Parkeren-Live", "nederlandse-geldstromen"]
BG, BORDER, FG, MUTED, ACCENT = "#0d1117", "#30363d", "#e6edf3", "#8b949e", "#00e676"
FONT = 'font-family="Segoe UI,Ubuntu,Arial,sans-serif"'
LANG_COLORS = {"Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "HTML": "#e34c26",
               "PowerShell": "#012456", "Shell": "#89e051", "CSS": "#563d7c", "PHP": "#4F5D95",
               "Dockerfile": "#384d54", "C": "#555555", "Jinja": "#a52a2a"}
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def api(url, data=None):
    h = {"Accept": "application/vnd.github+json", "User-Agent": "profile-assets"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, data=data, headers=h)
    return json.load(urllib.request.urlopen(req, timeout=30))


def gql(query):
    return api("https://api.github.com/graphql", json.dumps({"query": query}).encode())["data"]


def write(path, body):
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


def svg(w, h, inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" {FONT}>'
            f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="12" fill="{BG}" stroke="{BORDER}"/>{inner}</svg>')


def t(x, y, s, size=14, fill=FG, weight="400", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{escape(str(s))}</text>')


os.makedirs("assets", exist_ok=True)
os.makedirs("data", exist_ok=True)

repos = [r for r in api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
         if not r["private"] and not r["archived"]]
own = [r for r in repos if not r["fork"] and r["name"] != USER]

# ---- stats ----
since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
g = gql('{user(login:"%s"){followers{totalCount} contributionsCollection(from:"%s"){totalCommitContributions '
        'totalPullRequestContributions totalIssueContributions restrictedContributionsCount '
        'contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}'
        % (USER, since))["user"]
cc = g["contributionsCollection"]
stars = sum(r["stargazers_count"] for r in own)
rows = [("Repositories (publiek)", len(own)), ("Sterren", stars), ("Volgers", g["followers"]["totalCount"]),
        ("Commits (laatste jaar)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("Pull requests", cc["totalPullRequestContributions"]),
        ("Contributies (jaar)", cc["contributionCalendar"]["totalContributions"])]
inner = t(24, 36, "GitHub stats", 18, ACCENT, "600")
for i, (k, v) in enumerate(rows):
    y = 68 + i * 26
    inner += t(24, y, k, 14, MUTED) + t(266, y, v, 14, FG, "600", "end")
write("assets/stats.svg", svg(290, 232, inner))

# ---- talen ----
bytes_by = {}
for r in own:
    try:
        for lang, n in api(r["languages_url"]).items():
            bytes_by[lang] = bytes_by.get(lang, 0) + n
    except Exception:
        pass
tot = sum(bytes_by.values()) or 1
top = sorted(bytes_by.items(), key=lambda kv: -kv[1])[:6]
inner = t(24, 36, "Meest gebruikte talen", 18, ACCENT, "600")
x = 24.0
for lang, n in top:
    w = 342 * n / tot
    inner += f'<rect x="{x:.1f}" y="52" width="{w:.1f}" height="10" fill="{LANG_COLORS.get(lang, "#8b949e")}"/>'
    x += w
for i, (lang, n) in enumerate(top):
    cx, y = 24 + (i % 2) * 180, 92 + (i // 2) * 26
    inner += (f'<circle cx="{cx+5}" cy="{y-5}" r="5" fill="{LANG_COLORS.get(lang, "#8b949e")}"/>'
              + t(cx + 18, y, f"{lang} {100*n/tot:.1f}%", 13))
write("assets/langs.svg", svg(390, 190, inner))

# ---- projectkaarten ----
by_name = {r["name"]: r for r in repos}
for name in FEATURED:
    r = by_name.get(name)
    if not r:
        continue
    desc = " ".join((r["description"] or "").split())
    wrapped = textwrap.wrap(desc, 58)
    lines = wrapped[:3]
    if len(wrapped) > 3:
        lines[-1] = lines[-1][:55].rstrip() + "…"
    inner = t(24, 36, r["name"][:40] + ("…" if len(r["name"]) > 40 else ""), 17, ACCENT, "600")
    for i, ln in enumerate(lines):
        inner += t(24, 64 + i * 20, ln, 13, MUTED)
    lang = r["language"] or ""
    if lang:
        inner += (f'<circle cx="29" cy="136" r="5" fill="{LANG_COLORS.get(lang, "#8b949e")}"/>'
                  + t(42, 141, lang, 13))
    inner += t(396, 141, f"★ {r['stargazers_count']}", 13, MUTED, anchor="end")
    write(f"assets/card-{name}.svg", svg(420, 160, inner))

# ---- activiteit (laatste 90 dagen) ----
days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]][-90:]
vals = [d["contributionCount"] for d in days]
W, H, L, B = 800, 200, 40, 30
mx = max(vals + [1])
pts = [(L + (W - L - 20) * i / (len(vals) - 1), H - B - (H - B - 40) * v / mx) for i, v in enumerate(vals)]
line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
area = f"{L},{H-B} {line} {pts[-1][0]:.1f},{H-B}"
inner = (t(24, 30, "Activiteit · laatste 90 dagen", 16, ACCENT, "600")
         + f'<polygon points="{area}" fill="{ACCENT}" fill-opacity="0.15"/>'
         + f'<polyline points="{line}" fill="none" stroke="{ACCENT}" stroke-width="2"/>'
         + t(L, H - 8, days[0]["date"], 11, MUTED) + t(W - 20, H - 8, days[-1]["date"], 11, MUTED, anchor="end")
         + t(L - 6, 52, mx, 11, MUTED, anchor="end") + t(L - 6, H - B, 0, 11, MUTED, anchor="end"))
write("assets/activity.svg", svg(W, H, inner))

# ---- profielweergaven (trend) ----
csv_path = "data/views.csv"
hist = {}
if os.path.exists(csv_path):
    with open(csv_path, encoding="utf-8") as f:
        hist = {r["date"]: int(r["views"]) for r in csv.DictReader(f)}
try:
    body = urllib.request.urlopen(urllib.request.Request(
        f"https://komarev.com/ghpvc/?username={USER}&label=x",
        headers={"User-Agent": "profile-assets"}), timeout=30).read().decode()
    m = re.findall(r">([\d,]+)<", body)
    if m:
        hist[dt.date.today().isoformat()] = int(m[0].replace(",", ""))
except Exception as e:
    print("views ophalen mislukt:", e)
if hist:
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(["date", "views"])
        for d in sorted(hist):
            cw.writerow([d, hist[d]])
    series = [(dt.date.fromisoformat(d), hist[d]) for d in sorted(hist)][-120:]
    d0, d1 = series[0][0], series[-1][0]
    span = max((d1 - d0).days, 1)
    lo, hi = min(v for _, v in series), max(v for _, v in series)
    rng = max(hi - lo, 1)
    W, H, L, B = 800, 220, 50, 32
    multi = len(series) > 1
    xy = [(L + (W - L - 30) * (((d - d0).days / span) if multi else 0.5),
           H - B - (H - B - 56) * (((v - lo) / rng) if multi else 0.5)) for d, v in series]
    week = [v for d, v in series if (d1 - d).days <= 7]
    gained = series[-1][1] - (week[0] if week else series[-1][1])
    inner = (t(24, 30, "Profielweergaven · trend", 16, ACCENT, "600")
             + t(W - 24, 30, f"Totaal {series[-1][1]} · +{gained} afgelopen 7 dagen", 13, MUTED, anchor="end"))
    if multi:
        pl = " ".join(f"{px:.1f},{py:.1f}" for px, py in xy)
        inner += (f'<polygon points="{L},{H-B} {pl} {xy[-1][0]:.1f},{H-B}" fill="{ACCENT}" fill-opacity="0.15"/>'
                  f'<polyline points="{pl}" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>')
    inner += "".join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{ACCENT}"/>' for px, py in xy[-1:])
    inner += (t(L, H - 10, d0.isoformat(), 11, MUTED) + t(W - 30, H - 10, d1.isoformat(), 11, MUTED, anchor="end")
              + t(L - 6, 64, hi, 11, MUTED, anchor="end") + t(L - 6, H - B, lo, 11, MUTED, anchor="end"))
    if not multi:
        inner += t(W / 2, H / 2 + 10, "De trendlijn vult zich vanaf nu elke dag", 13, MUTED, anchor="middle")
    write("assets/views.svg", svg(W, H, inner))
print("assets klaar")
