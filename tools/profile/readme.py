"""Updates the dynamic parts of README.md from data/*.json.

- the latest-articles block between <!-- writing:start --> and <!-- writing:end -->
  (links + alt text; the images themselves come from render.py)
- the alt text of the stats image, so screen readers get today's numbers

Everything else in the README is left exactly as it is.
"""
import datetime
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
README = HERE.parent.parent / "README.md"
DATA = HERE / "data"


def writing_block(articles):
    lines = []
    for i, a in enumerate(articles[:5], 1):
        alt = html.escape(f'{a["title"]} — published {a["published_at"][:10]}, '
                          f'{a["reactions"]} reactions, {a["comments"]} comments', quote=True)
        lines.append(f'<a href="{html.escape(a["url"], quote=True)}"><img src="./assets/writing/post-{i}.svg" '
                     f'width="100%" align="top" alt="{alt}"></a>')
    return "<!-- writing:start -->\n" + "\n".join(lines) + "\n<!-- writing:end -->"


def days(n):
    return f"{n} day" if n == 1 else f"{n} days"


def stats_alt(d):
    since = datetime.date.fromisoformat(d["created_at"][:10])
    langs = sorted(d["languages"].items(), key=lambda kv: -kv[1])[:5]
    parts = [f'{d["stars"]} total stars',
             f'{d["commits_year"]} commits in {d["year"]}, {d["commits_all"]} all time',
             f'{d["prs"]} pull requests ({d["prs_merged"]} merged)',
             f'current streak {days(d["streak_current"])}, longest {days(d["streak_longest"])}',
             f'{d["followers"]} followers', f'{d["forks"]} forks',
             f'member since {since:%B %Y}', f'{d["hackathon_wins"]} hackathon wins']
    text = "Stats: " + "; ".join(parts) + ". Top languages: " + ", ".join(k for k, _ in langs) + "."
    dev = {k: v for k, v in (d.get("dev") or {}).items() if v is not None}
    if dev:
        text += " DEV Community: " + ", ".join(f"{v:,} {k}" for k, v in dev.items()) + "."
    return html.escape(text, quote=True)


def main():
    stats = json.loads((DATA / "stats.json").read_text())
    articles = json.loads((DATA / "articles.json").read_text())
    s = README.read_text()

    s, n = re.subn(r"<!-- writing:start -->.*?<!-- writing:end -->", lambda _: writing_block(articles), s, flags=re.S)
    if n != 1:
        sys.exit("error: README needs exactly one <!-- writing:start --> … <!-- writing:end --> block")

    s, n = re.subn(r'(<img src="\./assets/stats\.svg"[^>]*?alt=")[^"]*(")',
                   lambda m: m.group(1) + stats_alt(stats) + m.group(2), s)
    if n != 1:
        sys.exit("error: README needs exactly one stats.svg image with an alt attribute")

    README.write_text(s)
    print("README updated")


if __name__ == "__main__":
    main()
