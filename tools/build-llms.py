#!/usr/bin/env python3
"""Writes llms.txt and llms-full.txt for dropnook.app from the two product cards of the pages.

The cards (li.product in index.html and de/index.html) are the one source of the words: what each product is, what
it does, its site, its code and its licence. GitHub adds the language, the topics and the time of the last commit on the default branch (never pushed_at). llms-full.txt
uses the same layout as helminet.ch's (### name, a description, then «- Key: value» lines), so a reader of one reads
the other; our extra keys (German description, logos) come after the shared ones.

    python3 tools/build-llms.py            # write both files
    python3 tools/build-llms.py --check    # exit 1 if they would change (nothing written)

Standard library only. When GitHub can't be asked, nothing is written (exit 2).
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.request

SITE = "https://dropnook.app"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = {"en": os.path.join(ROOT, "index.html"), "de": os.path.join(ROOT, "de", "index.html")}


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def cards(path):
    page = open(path, encoding="utf-8").read()
    head = {"h1": text(re.search(r"<h1>(.*?)</h1>", page, re.S).group(1)),
            "lead": text(re.search(r'<p class="lead">(.*?)</p>', page, re.S).group(1))}
    out = []
    for li in re.findall(r'<li class="product (\w+)">(.*?)\n      </li>', page, re.S):
        body = li[1]
        site = re.search(r'<a class="btn two" href="([^"]+)"', body).group(1)
        code = re.search(r'<a class="btn ghost" href="(https://github\.com/[^"]+)"', body).group(1)
        out.append({
            "key": li[0],
            "name": re.search(r'<img src="[^"]*title-light\.svg"[^>]*alt="([^"]+)"', body).group(1),
            "what": text(re.search(r'<p class="what">(.*?)</p>', body, re.S).group(1)),
            "does": [text(x) for x in re.findall(r"<li>(.*?)</li>", re.search(r'<ul class="does">(.*?)</ul>', body, re.S).group(1), re.S)],
            "site": site, "code": code,
            "licence": text(re.search(r'<p class="meta"><a[^>]*>(.*?)</a>', body, re.S).group(1)),
            "icon": SITE + "/" + re.search(r'<img class="icon" src="(?:\.\./)?([^"]+)"', body).group(1),
            "title_light": SITE + "/" + re.search(r'<img src="(?:\.\./)?([^"]+title-light\.svg)"', body).group(1),
            "title_dark": SITE + "/" + re.search(r'srcset="(?:\.\./)?([^"]+title-dark\.svg)"', body).group(1),
        })
    return head, out


def github(repo_url):
    repo = repo_url.removeprefix("https://github.com/").strip("/")
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}",
                                 headers={"User-Agent": "dropnook.app llms.txt", "Accept": "application/vnd.github+json"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def last_commit(repo_url, branch):
    repo = repo_url.removeprefix("https://github.com/").strip("/")
    return github(f"https://github.com/{repo}/commits/{branch}")["commit"]["committer"]["date"]


def build():
    head_en, en = cards(PAGES["en"])
    head_de, de = cards(PAGES["de"])
    assert [c["key"] for c in en] == [c["key"] for c in de], "the two pages list different products"
    gh = {c["key"]: github(c["code"]) for c in en}
    for c in en:                        # the last commit, not pushed_at (any push to any branch moves that)
        gh[c["key"]]["committed"] = last_commit(c["code"], gh[c["key"]]["default_branch"])

    short = [f"# dropnook.app", "", f"> {head_en['h1']}. {head_en['lead']}", "",
             f"dropnook makes tools for the home server, made for Unraid. "
             f"German: {SITE}/de/ · the full list: {SITE}/llms-full.txt", "", "## Products", ""]
    for c in en:
        short.append(f"- [{c['name']}]({c['site']}): {c['what']} Code: {c['code']} ({c['licence']})")
    short += ["", "## From the neighbourhood", "",
              "- [helminet.ch](https://helminet.ch/): helmi1987's projects (https://helminet.ch/llms-full.txt)", ""]

    full = [f"# dropnook.app", "", f"> {head_en['h1']}. {head_en['lead']}", "",
            f"> {head_de['h1']}. {head_de['lead']}", "", "## Eigene Projekte", ""]
    for c, d in zip(en, de):
        g = gh[c["key"]]
        full += [f"### {c['name']}", "", c["what"] + " " + " ".join(c["does"]), "",
                 f"- Projektseite: {c['site']}",
                 f"- Quellcode: {c['code']}",
                 f"- Webseite: {c['site']}",
                 f"- Sprache: {g.get('language') or '-'}",
                 f"- Lizenz: {c['licence']}",
                 f"- Letzte Änderung: {g['committed'][:10]}",
                 f"- Letzter Commit: {g['committed']}",
                 f"- Tags: {', '.join(g.get('topics') or [])}",
                 f"- Beschreibung (de): {d['what']} {' '.join(d['does'])}",
                 f"- Kurz (en): {c['what']}",
                 f"- Kurz (de): {d['what']}",
                 f"- Webseite (de): {d['site']}",
                 f"- Logo: {c['icon']}",
                 f"- Logo (Titel, hell): {c['title_light']}",
                 f"- Logo (Titel, dunkel): {c['title_dark']}",
                 ""]
    return "\n".join(short), "\n".join(full)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    try:
        short, full = build()
    except Exception as err:            # noqa: BLE001 — GitHub or a page we can't read: keep the files
        print(f"llms: can't build ({err}) — nothing changed", file=sys.stderr)
        return 2
    changed = False
    for name, body in (("llms.txt", short), ("llms-full.txt", full)):
        path = os.path.join(ROOT, name)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != body:
            changed = True
            if not a.check:
                open(path, "w", encoding="utf-8").write(body)
    print(f"llms: {'changed' if changed else 'no change'}")
    return 1 if (a.check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
