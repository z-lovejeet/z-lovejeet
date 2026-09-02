import json
import os
import urllib.request
import math
from datetime import datetime

def run_query(query, headers):
    url = "https://api.github.com/graphql"
    req = urllib.request.Request(url, data=json.dumps({"query": query}).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))

def get_contributions(token, username):
    query = """
    query {
      user(login: "%s") {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """ % username
    headers = {"Authorization": f"Bearer {token}"}
    result = run_query(query, headers)
    weeks = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    
    days = []
    for week in weeks:
        for day in week["contributionDays"]:
            days.append(day)
            
    # Keep only the last 31 days
    return days[-31:]

def generate_svg(data, output_path):
    width, height = 850, 180
    margin = {"top": 25, "right": 25, "bottom": 35, "left": 45}
    chart_w = width - margin["left"] - margin["right"]
    chart_h = height - margin["top"] - margin["bottom"]
    
    if not data:
        print("No data available")
        return
        
    counts = [d["contributionCount"] for d in data]
    max_count = max(counts) if max(counts) > 0 else 1
    
    points = []
    for i, d in enumerate(data):
        x = margin["left"] + (i / (len(data) - 1)) * chart_w
        y = margin["top"] + chart_h - (d["contributionCount"] / max_count) * chart_h
        points.append((x, y))
        
    path_d = "M " + " L ".join(f"{x},{y}" for x, y in points)
    area_d = f"{path_d} L {points[-1][0]},{margin['top'] + chart_h} L {points[0][0]},{margin['top'] + chart_h} Z"
    
    # Calculate path length for animation
    path_len = 0
    for i in range(1, len(points)):
        path_len += math.sqrt((points[i][0] - points[i-1][0])**2 + (points[i][1] - points[i-1][1])**2)
    path_len = int(path_len) + 10
    
    svg = []
    svg.append(f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">')
    svg.append('  <style>')
    svg.append('    text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }')
    svg.append('    .axis-label { fill: #484f58; font-size: 10px; }')
    svg.append('  </style>')
    svg.append('  <defs>')
    svg.append('    <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">')
    svg.append('      <stop offset="0%" stop-color="#58a6ff" stop-opacity="0.25" />')
    svg.append('      <stop offset="100%" stop-color="#58a6ff" stop-opacity="0.02" />')
    svg.append('    </linearGradient>')
    svg.append('  </defs>')
    
    svg.append(f'  <rect width="{width}" height="{height}" rx="10" fill="#0d1117" stroke="#21262d" stroke-width="1" />')
    
    # Grid lines and Y axis
    for i in range(4):
        val = int(max_count * (3 - i) / 3)
        y = margin["top"] + (i / 3) * chart_h
        svg.append(f'  <line x1="{margin["left"]}" y1="{y}" x2="{width - margin["right"]}" y2="{y}" stroke="#21262d" stroke-width="0.5" stroke-dasharray="4,4" />')
        svg.append(f'  <text x="{margin["left"] - 10}" y="{y + 4}" class="axis-label" text-anchor="end">{val}</text>')
        
    # X axis
    for i, d in enumerate(data):
        if i % 5 == 0 or i == len(data) - 1:
            x = margin["left"] + (i / (len(data) - 1)) * chart_w
            y = margin["top"] + chart_h + 15
            date_str = datetime.strptime(d["date"], "%Y-%m-%d").strftime("%b %d")
            svg.append(f'  <text x="{x}" y="{y}" class="axis-label" text-anchor="middle">{date_str}</text>')
            
    # Area
    svg.append(f'  <path d="{area_d}" fill="url(#areaFill)" />')
    
    # Glow path
    svg.append(f'  <path d="{path_d}" fill="none" stroke="#58a6ff" stroke-width="6" opacity="0.15" />')
    
    # Main line with SMIL
    svg.append(f'  <path d="{path_d}" fill="none" stroke="#58a6ff" stroke-width="2" stroke-dasharray="{path_len}" stroke-dashoffset="{path_len}">')
    svg.append(f'    <animate attributeName="stroke-dashoffset" from="{path_len}" to="0" dur="2s" fill="freeze" />')
    svg.append('  </path>')
    
    # Points
    for x, y in points:
        svg.append(f'  <circle cx="{x}" cy="{y}" r="2" fill="#3ddbd9" opacity="0.6" />')
        
    svg.append('</svg>')
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write("\n".join(svg))
    print(f"Graph generated at {output_path}")

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN environment variable not set.")
        return
        
    username = "z-lovejeet"
    print(f"Fetching data for {username}...")
    try:
        data = get_contributions(token, username)
        output_path = os.path.join(os.path.dirname(__file__), "../assets/contribution-graph.svg")
        output_path = os.path.abspath(output_path)
        generate_svg(data, output_path)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
