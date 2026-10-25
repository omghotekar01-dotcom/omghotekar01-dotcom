#!/usr/bin/env python3
"""Refresh a public GitHub profile activity SVG using GitHub's APIs (stdlib only)."""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

USER = "omghotekar01-dotcom"
OUT = pathlib.Path("assets/activity.svg")
TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "om-ghotekar-profile-readme"}
if TOKEN:
    HEADERS["Authorization"] = "Bearer " + TOKEN

def request(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = dict(HEADERS)
    if data is not None:
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=25) as result:
        return json.load(result)

def main():
    try:
        user = request("https://api.github.com/users/" + USER)
        repos = request("https://api.github.com/users/" + USER + "/repos?per_page=100&type=owner")
    except (OSError, ValueError) as err:
        print("Skipping refresh; public GitHub API unavailable: " + str(err), file=sys.stderr)
        return
    public = [repo for repo in repos if not repo.get("private") and not repo.get("fork")]
    stars = sum(int(repo.get("stargazers_count", 0)) for repo in public)
    repo_count = int(user.get("public_repos", len(public)))
    followers = int(user.get("followers", 0))
    days, total = [], None
    if TOKEN:
        query = """query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } } } }"""
        try:
            response = request("https://api.github.com/graphql", {"query": query, "variables": {"login": USER}})
            calendar = response["data"]["user"]["contributionsCollection"]["contributionCalendar"]
            total = calendar["totalContributions"]
            days = [d for week in calendar["weeks"] for d in week["contributionDays"]]
        except (KeyError, TypeError, OSError, ValueError) as err:
            print("Contribution calendar unavailable; keeping exact counts omitted: " + str(err), file=sys.stderr)
    width, height = 1160, 265
    rect = []
    colors = ["#1B2732", "#155F4B", "#1D9B72", "#34D399", "#A7F3D0"]
    max_count = max([d["contributionCount"] for d in days], default=0)
    # Show at most the most recent 53 GitHub weeks. 0=Sunday ... 6=Saturday.
    recent = days[-371:]
    by_date = {x["date"]: x["contributionCount"] for x in recent}
    today = dt.datetime.now(dt.timezone.utc).date()
    end_saturday = today + dt.timedelta(days=(5 - today.weekday()) % 7)
    start_sunday = end_saturday - dt.timedelta(days=370)
    for col in range(53):
        for row in range(7):
            day = start_sunday + dt.timedelta(days=col * 7 + row)
            count = by_date.get(day.isoformat())
            level = 0 if count is None or count == 0 else min(4, 1 + int(3 * count / max(max_count, 1)))
            color = colors[level]
            x, y = 29 + col * 21, 91 + row * 20
            rect.append(f'<rect x="{x}" y="{y}" width="15" height="15" rx="3" fill="{color}"/>')
    updated = today.strftime("%d %b %Y")
    contribution_text = str(total) + " contributions" if total is not None else "See GitHub calendar for totals"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="t">
<title id="t">Om Ghotekar: GitHub profile activity summary updated {escape(updated)}</title>
<rect x="1" y="1" width="1158" height="263" rx="17" fill="#0D1420" stroke="#334155" stroke-width="2"/>
<text x="28" y="38" font-family="monospace" letter-spacing="2" font-size="14" fill="#5EEAD4">GITHUB / CONTRIBUTION ACTIVITY</text>
<text x="28" y="69" font-family="Arial,sans-serif" font-size="19" font-weight="bold" fill="#F1F5F9">{escape(contribution_text)}</text>
{''.join(rect)}
<text x="28" y="247" font-family="monospace" font-size="12" fill="#879BB4">Updated {escape(updated)} UTC</text>
<text x="804" y="247" font-family="monospace" font-size="12" fill="#B5C8D8">{repo_count} PUBLIC REPOS   /   {stars} STARS   /   {followers} FOLLOWERS</text>
</svg>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"Updated {OUT} — {repo_count} public repos; {stars} stars; {followers} followers.")

if __name__ == "__main__":
    main()
