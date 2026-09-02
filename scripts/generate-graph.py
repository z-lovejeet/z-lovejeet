#!/usr/bin/env python3
"""Generates contribution-graph.svg with real GitHub data.
Works with or without GITHUB_TOKEN — uses public API as fallback."""

import json, os, math, urllib.request
from datetime import datetime, timedelta

USERNAME = "z-lovejeet"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(SCRIPT_DIR, "..", "assets", "contribution-graph.svg")

# ── Data fetching ──────────────────────────────────────────────

def fetch_public_api():
    """Fetch from public contributions API (no auth needed)."""
    url = f"https://github-contributions-api.jogruber.de/v4/{USERNAME}?y=last"
    req = urllib.request.Request(url, headers={"User-Agent": "contribution-graph-gen"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
    return [(d["date"], d["count"]) for d in data.get("contributions", [])]

def fetch_graphql():
    """Fetch from GitHub GraphQL API (needs GITHUB_TOKEN)."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        return None
    query = '{"query":"{ user(login: \\"%s\\") { contributionsCollection { contributionCalendar { weeks { contributionDays { date contributionCount } } } } } }"}' % USERNAME
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=query.encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
    days = []
    for week in data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            days.append((day["date"], day["contributionCount"]))
    return days

def get_contributions(num_days=31):
    """Get last N days of contributions, trying GraphQL first then public API."""
    all_days = None
    try:
        print("Trying GraphQL API...")
        all_days = fetch_graphql()
        if all_days:
            print(f"  ✓ Got {len(all_days)} days from GraphQL")
    except Exception as e:
        print(f"  ✗ GraphQL failed: {e}")

    if not all_days:
        try:
            print("Trying public API...")
            all_days = fetch_public_api()
            print(f"  ✓ Got {len(all_days)} days from public API")
        except Exception as e:
            print(f"  ✗ Public API failed: {e}")
            return []

    return all_days[-num_days:] if len(all_days) >= num_days else all_days

# ── SVG generation ─────────────────────────────────────────────

def generate_svg(days):
    W, H = 850, 180
    ML, MR, MT, MB = 50, 25, 28, 35   # margins
    CW = W - ML - MR                   # chart width  = 775
    CH = H - MT - MB                   # chart height = 117

    counts = [c for _, c in days]
    max_val = max(counts) if counts else 1
    # Round up to nearest nice number
    nice = max_val
    for step in [5, 10, 15, 20, 30, 50, 100]:
        if max_val <= step:
            nice = step
            break
    else:
        nice = ((max_val // 10) + 1) * 10

    n = len(days)
    dx = CW / max(n - 1, 1)

    # Calculate points
    pts = []
    for i, (date, count) in enumerate(days):
        x = round(ML + i * dx, 1)
        y = round(MT + CH - (count / nice) * CH, 1)
        pts.append((x, y, date, count))

    bottom_y = MT + CH  # 145

    # Build path strings
    line_d = " ".join(f"{'M' if i==0 else 'L'} {x},{y}" for i, (x, y, _, _) in enumerate(pts))
    area_d = line_d + f" L {pts[-1][0]},{bottom_y} L {pts[0][0]},{bottom_y} Z"

    # Path length for animation
    total_len = sum(
        math.sqrt((pts[i][0]-pts[i-1][0])**2 + (pts[i][1]-pts[i-1][1])**2)
        for i in range(1, len(pts))
    )
    dash = int(total_len + 50)

    # Grid lines (4 horizontal)
    grid_vals = []
    grid_step = nice / 4
    for i in range(5):
        v = int(i * grid_step)
        gy = round(MT + CH - (v / nice) * CH, 1)
        grid_vals.append((v, gy))

    # X-axis labels (every ~5 days)
    xlabels = []
    step = max(1, n // 6)
    for i in range(0, n, step):
        d = datetime.strptime(days[i][0], "%Y-%m-%d")
        label = d.strftime("%b %-d")
        xlabels.append((pts[i][0], label))
    # Always include last day
    d = datetime.strptime(days[-1][0], "%Y-%m-%d")
    xlabels.append((pts[-1][0], d.strftime("%b %-d")))

    # Data point circles (highlight peaks)
    avg = sum(counts) / len(counts) if counts else 0
    circles = []
    for x, y, date, count in pts:
        if count >= avg * 2 and count > 0:  # highlight above-average days
            r = min(3.5, 2 + (count / nice) * 2)
            op = min(0.9, 0.4 + (count / nice) * 0.5)
            circles.append(f'    <circle cx="{x}" cy="{y}" r="{round(r,1)}" fill="#3ddbd9" opacity="{round(op,2)}"/>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="af" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#58a6ff" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#58a6ff" stop-opacity="0.01"/>
    </linearGradient>
    <linearGradient id="lg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#58a6ff"/>
      <stop offset="100%" stop-color="#3ddbd9"/>
    </linearGradient>
  </defs>

  <rect width="{W}" height="{H}" fill="#0d1117" rx="10"/>
  <rect width="{W}" height="{H}" fill="none" stroke="#21262d" stroke-width="1" rx="10"/>

  <!-- Grid -->
'''
    for v, gy in grid_vals:
        dash_style = ' stroke-dasharray="4,4"' if v > 0 else ''
        svg += f'  <line x1="{ML}" y1="{gy}" x2="{W-MR}" y2="{gy}" stroke="#21262d" stroke-width="0.5"{dash_style}/>\n'
        svg += f'  <text x="{ML-8}" y="{gy+3}" fill="#484f58" font-family="\'Consolas\',monospace" font-size="9" text-anchor="end">{v}</text>\n'

    svg += f'''
  <!-- Area fill -->
  <path d="{area_d}" fill="url(#af)" opacity="0">
    <animate attributeName="opacity" from="0" to="1" dur="0.8s" fill="freeze" begin="0.5s"/>
  </path>

  <!-- Glow line -->
  <path d="{line_d}" fill="none" stroke="#58a6ff" stroke-width="6" opacity="0.1"
    stroke-linecap="round" stroke-linejoin="round"
    stroke-dasharray="{dash}" stroke-dashoffset="{dash}">
    <animate attributeName="stroke-dashoffset" from="{dash}" to="0" dur="2s" fill="freeze" begin="0.2s"/>
  </path>

  <!-- Main line -->
  <path d="{line_d}" fill="none" stroke="url(#lg)" stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round"
    stroke-dasharray="{dash}" stroke-dashoffset="{dash}">
    <animate attributeName="stroke-dashoffset" from="{dash}" to="0" dur="2s" fill="freeze" begin="0.2s"/>
  </path>

  <!-- Peak dots -->
  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" dur="0.4s" fill="freeze" begin="2s"/>
{chr(10).join(circles)}
  </g>

  <!-- X-axis labels -->
'''
    for lx, label in xlabels:
        svg += f'  <text x="{lx}" y="{H-10}" fill="#484f58" font-family="\'Consolas\',monospace" font-size="8" text-anchor="middle">{label}</text>\n'

    svg += '</svg>\n'
    return svg

# ── Main ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Fetching contributions for {USERNAME}...")
    days = get_contributions(31)
    if not days:
        print("ERROR: Could not fetch contribution data")
        exit(1)

    print(f"Generating SVG with {len(days)} days of data...")
    svg = generate_svg(days)

    out = os.path.abspath(OUTPUT)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(svg)
    print(f"✓ Written to {out}")
    print(f"  Date range: {days[0][0]} → {days[-1][0]}")
    print(f"  Max contributions: {max(c for _, c in days)}")
