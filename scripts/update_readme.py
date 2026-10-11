import json
import os
import urllib.request

USER = "ProAdmin007"
MAX_REPOS = 8
START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"

req = urllib.request.Request(
    f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=created",
    headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
             "Accept": "application/vnd.github+json"},
)
repos = json.load(urllib.request.urlopen(req))
repos = [r for r in repos
         if not r["fork"] and not r["private"] and not r["archived"] and r["name"] != USER]
repos.sort(key=lambda r: r["created_at"], reverse=True)

rows = ["| Project | Wat is het |", "|---|---|"]
for r in repos[:MAX_REPOS]:
    desc = (r["description"] or "-").replace("|", "&#124;").strip()
    rows.append(f"| [{r['name']}]({r['html_url']}) | {desc} |")

text = open("README.md", encoding="utf-8").read()
head, rest = text.split(START, 1)
_, tail = rest.split(END, 1)
new = f"{head}{START}\n" + "\n".join(rows) + f"\n{END}{tail}"
if new != text:
    open("README.md", "w", encoding="utf-8").write(new)
