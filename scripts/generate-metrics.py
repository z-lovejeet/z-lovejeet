#!/usr/bin/env python3
"""Fetches real GitHub stats and generates assets/metrics.svg with accurate data."""

import json
import os
import urllib.request
from datetime import datetime

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = "z-lovejeet"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(SCRIPT_DIR, "..", "assets", "metrics.svg")


def api(path, accept="application/vnd.github+json"):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": accept},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def graphql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def fetch_stats():
    # Total commits (all time)
    c = api(
        f"/search/commits?q=author:{USERNAME}&per_page=1",
        accept="application/vnd.github.cloak-preview+json",
    )
    total_commits = c.get("total_count", 0)

    # Total PRs (all time)
    p = api(f"/search/issues?q=author:{USERNAME}+type:pr&per_page=1")
    total_prs = p.get("total_count", 0)

    # User info
    u = api(f"/users/{USERNAME}")
    total_repos = u["public_repos"]
    created_year = int(u["created_at"][:4])
    years_active = datetime.now().year - created_year

    # Contribution calendar (last year) via GraphQL
    gql = graphql(
        """
        query {
          user(login: "%s") {
            contributionsCollection {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    contributionLevel
                  }
                }
              }
            }
          }
        }
        """
        % USERNAME
    )
    cal = gql["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    total_contributions = cal["totalContributions"]

    # Flatten contribution days
    days = []
    for week in cal["weeks"]:
        for day in week["contributionDays"]:
            days.append(day["contributionLevel"])

    return {
        "commits": total_commits,
        "prs": total_prs,
        "repos": total_repos,
        "years": years_active,
        "contributions": total_contributions,
        "days": days,
    }


LEVEL_COLORS = {
    "NONE": "#161b22",
    "FIRST_QUARTILE": "#0e4429",
    "SECOND_QUARTILE": "#006d32",
    "THIRD_QUARTILE": "#26a641",
    "FOURTH_QUARTILE": "#39d353",
}


def generate_svg(stats):
    commits = stats["commits"]
    prs = stats["prs"]
    repos = stats["repos"]
    years = stats["years"]
    contributions = stats["contributions"]
    days = stats["days"]

    # Bar widths (proportional, max 100)
    commit_bar = min(int(commits / max(commits, 800) * 100), 98)
    pr_bar = max(min(int(prs / 50 * 100), 98), 8)
    repo_bar = max(min(int(repos / 30 * 100), 98), 8)
    year_bar = max(min(int(years / 10 * 100), 98), 8)

    # Contribution dots — last 30 days
    last_30 = days[-30:]
    dots = ""
    for i, level in enumerate(last_30):
        x = 215 + i * 14
        color = LEVEL_COLORS.get(level, "#161b22")
        dots += f'  <rect x="{x}" y="148" width="10" height="10" fill="{color}" rx="2"/>\n'

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="850" height="200" viewBox="0 0 850 200">
  <!-- Background -->
  <rect width="850" height="200" fill="#0d1117" rx="10"/>
  <rect width="850" height="200" fill="none" stroke="#21262d" stroke-width="1" rx="10"/>

  <!-- COMMITS -->
  <text x="130" y="72" text-anchor="middle" fill="#58a6ff" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif" font-size="38" font-weight="700" opacity="0">
    {commits}
    <animate attributeName="opacity" from="0" to="1" dur="0.6s" fill="freeze" begin="0.2s"/>
  </text>
  <text x="130" y="95" text-anchor="middle" fill="#7d8590" font-family="'Consolas','Courier New',monospace" font-size="10" letter-spacing="2.5">COMMITS</text>
  <rect x="80" y="110" width="100" height="2" fill="#21262d" rx="1"/>
  <rect x="80" y="110" width="0" height="2" fill="#58a6ff" rx="1">
    <animate attributeName="width" from="0" to="{commit_bar}" dur="1.2s" fill="freeze" begin="0.3s" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>
  </rect>

  <!-- PULL REQUESTS -->
  <text x="325" y="72" text-anchor="middle" fill="#3ddbd9" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif" font-size="38" font-weight="700" opacity="0">
    {prs}
    <animate attributeName="opacity" from="0" to="1" dur="0.6s" fill="freeze" begin="0.4s"/>
  </text>
  <text x="325" y="95" text-anchor="middle" fill="#7d8590" font-family="'Consolas','Courier New',monospace" font-size="10" letter-spacing="2.5">PULL REQUESTS</text>
  <rect x="275" y="110" width="100" height="2" fill="#21262d" rx="1"/>
  <rect x="275" y="110" width="0" height="2" fill="#3ddbd9" rx="1">
    <animate attributeName="width" from="0" to="{pr_bar}" dur="1.2s" fill="freeze" begin="0.5s" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>
  </rect>

  <!-- REPOSITORIES -->
  <text x="525" y="72" text-anchor="middle" fill="#a371f7" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif" font-size="38" font-weight="700" opacity="0">
    {repos}
    <animate attributeName="opacity" from="0" to="1" dur="0.6s" fill="freeze" begin="0.6s"/>
  </text>
  <text x="525" y="95" text-anchor="middle" fill="#7d8590" font-family="'Consolas','Courier New',monospace" font-size="10" letter-spacing="2.5">REPOSITORIES</text>
  <rect x="475" y="110" width="100" height="2" fill="#21262d" rx="1"/>
  <rect x="475" y="110" width="0" height="2" fill="#a371f7" rx="1">
    <animate attributeName="width" from="0" to="{repo_bar}" dur="1.2s" fill="freeze" begin="0.7s" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>
  </rect>

  <!-- YEARS ACTIVE -->
  <text x="720" y="72" text-anchor="middle" fill="#3fb950" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif" font-size="38" font-weight="700" opacity="0">
    {years}
    <animate attributeName="opacity" from="0" to="1" dur="0.6s" fill="freeze" begin="0.8s"/>
  </text>
  <text x="720" y="95" text-anchor="middle" fill="#7d8590" font-family="'Consolas','Courier New',monospace" font-size="10" letter-spacing="2.5">YEARS ACTIVE</text>
  <rect x="670" y="110" width="100" height="2" fill="#21262d" rx="1"/>
  <rect x="670" y="110" width="0" height="2" fill="#3fb950" rx="1">
    <animate attributeName="width" from="0" to="{year_bar}" dur="1.2s" fill="freeze" begin="0.9s" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>
  </rect>

  <!-- SEPARATOR -->
  <line x1="50" y1="132" x2="800" y2="132" stroke="#21262d" stroke-width="0.5"/>

  <!-- CONTRIBUTION DOTS (last 30 days, real data) -->
{dots}
  <!-- FOOTER -->
  <text x="425" y="186" text-anchor="middle" fill="#484f58" font-family="'Segoe UI','Helvetica Neue',Arial,sans-serif" font-size="11" letter-spacing="3">{contributions} CONTRIBUTIONS IN THE LAST YEAR</text>
</svg>"""

    return svg


if __name__ == "__main__":
    print("Fetching GitHub stats...")
    stats = fetch_stats()
    print(
        f"  Commits: {stats['commits']}  PRs: {stats['prs']}  "
        f"Repos: {stats['repos']}  Years: {stats['years']}  "
        f"Contributions: {stats['contributions']}"
    )

    svg = generate_svg(stats)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        f.write(svg)
    print(f"Written to {OUTPUT}")
