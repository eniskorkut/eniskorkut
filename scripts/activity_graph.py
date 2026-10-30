#!/usr/bin/env python3
"""Generate a dark, cyan-accented GitHub contribution graph as SVG."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import ssl
import urllib.request
from pathlib import Path

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
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
"""

MONTHS = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
COLORS = ["#1E293B", "#164E63", "#0E7490", "#06B6D4", "#22D3EE"]


def fetch(username: str, token: str) -> dict:
    payload = json.dumps({"query": QUERY, "variables": {"login": username}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-activity-graph",
        },
    )
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=30, context=context) as response:
        data = json.load(response)
    if "errors" in data:
        raise RuntimeError(str(data["errors"][:2]))
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def color_for(count: int) -> str:
    if count <= 0:
        return COLORS[0]
    if count <= 2:
        return COLORS[1]
    if count <= 5:
        return COLORS[2]
    if count <= 9:
        return COLORS[3]
    return COLORS[4]


def render(calendar: dict, username: str) -> str:
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]

    cell, gap = 14, 3
    step = cell + gap
    left, top = 86, 102
    width = 1200
    height = 300
    grid_width = len(weeks) * step
    grid_height = 7 * step

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">Son 12 ay GitHub katkı grafiği</title>',
        f'<desc id="desc">{username} için son 12 ayda toplam {total} katkı.</desc>',
        '<rect width="1200" height="300" rx="14" fill="#0B1220"/>',
        '<rect x="1" y="1" width="1198" height="298" rx="13" fill="none" stroke="#1E293B"/>',
        f'<text x="32" y="42" font-family="Helvetica Neue, Arial, sans-serif" font-size="20" font-weight="700" fill="#E2E8F0">Son 12 ay · {total} katkı</text>',
        f'<text x="32" y="62" font-family="Helvetica Neue, Arial, sans-serif" font-size="13" fill="#64748B">github.com/{username}</text>',
    ]

    # Month labels: one label at the first week of each month.
    last_month = None
    last_label_x = -999
    for index, week in enumerate(weeks):
        days = week["contributionDays"]
        if not days:
            continue
        date = dt.date.fromisoformat(days[0]["date"])
        label_x = left + index * step
        if date.month != last_month and label_x - last_label_x >= 45:
            parts.append(
                f'<text x="{label_x}" y="{top - 14}" font-family="Helvetica Neue, Arial, sans-serif" '
                f'font-size="12" fill="#94A3B8">{MONTHS[date.month - 1]}</text>'
            )
            last_month = date.month
            last_label_x = label_x

    # Weekday labels (Monday, Wednesday, Friday).
    for row, label in ((0, "Pzt"), (2, "Çar"), (4, "Cum")):
        parts.append(
            f'<text x="32" y="{top + row * step + 11}" font-family="Helvetica Neue, Arial, sans-serif" '
            f'font-size="11" fill="#64748B">{label}</text>'
        )

    # Contribution cells.
    for index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            date = dt.date.fromisoformat(day["date"])
            row = date.weekday()
            count = day["contributionCount"]
            parts.append(
                f'<rect x="{left + index * step}" y="{top + row * step}" width="{cell}" height="{cell}" rx="3" '
                f'fill="{color_for(count)}"><title>{date.isoformat()} · {count} katkı</title></rect>'
            )

    # Legend.
    legend_x = width - 210
    legend_y = height - 28
    parts.append(
        f'<text x="{legend_x - 30}" y="{legend_y + 11}" font-family="Helvetica Neue, Arial, sans-serif" '
        f'font-size="11" fill="#64748B">Az</text>'
    )
    for index, color in enumerate(COLORS):
        parts.append(
            f'<rect x="{legend_x + index * 20}" y="{legend_y}" width="14" height="14" rx="3" fill="{color}"/>'
        )
    parts.append(
        f'<text x="{legend_x + len(COLORS) * 20 + 4}" y="{legend_y + 11}" '
        f'font-family="Helvetica Neue, Arial, sans-serif" font-size="11" fill="#64748B">Çok</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="eniskorkut")
    parser.add_argument("--output", default="profile/activity.svg")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required")
        return 2

    calendar = fetch(args.username, token)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(calendar, args.username), encoding="utf-8")
    print(f"wrote {output} total={calendar['totalContributions']} weeks={len(calendar['weeks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
