#!/usr/bin/env python3
"""Fills «From the neighbourhood» / «Aus der Nachbarschaft» from helminet.ch.

Reads helmi1987's own projects from https://helminet.ch/llms-full.txt (the section «Eigene Projekte»; the supported
ones are dropnook's two products, already on this page) and writes the cards between the markers
<!-- helminet:start --> and <!-- helminet:end --> in index.html and de/index.html.

neighbours/helminet.json holds what helminet.ch can't say: our own German and English sentence and meta line per
project, and the order. A project helminet.ch lists that we have no sentence for yet appears first, with helminet's
own description in both languages; a project helminet.ch no longer lists leaves the page. Links (project page, site,
code), the licence and the language always come from helminet.ch.

    python3 tools/import-helminet.py            # fetch, write the pages
    python3 tools/import-helminet.py --check    # fetch, exit 1 if the pages would change (nothing written)
    python3 tools/import-helminet.py --file F   # read a saved llms-full.txt instead of fetching

Standard library only. Everything from helminet.ch is escaped; only http(s) links are used. When the fetch fails or
the feed lists no project, nothing is written (exit 2) — the page keeps its cards.
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.request

FEED = "https://helminet.ch/llms-full.txt"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "neighbours", "helminet.json")
PAGES = {"en": os.path.join(ROOT, "index.html"), "de": os.path.join(ROOT, "de", "index.html")}
START, END = "<!-- helminet:start -->", "<!-- helminet:end -->"
PROJECT_URL = re.compile(r"^https://helminet\.ch/projekte/([a-z0-9-]+)$")
WORDS = {
    "en": {"site": "Visit the site", "code": "Code", "here": "On helminet.ch", "more": "More on helminet.ch."},
    "de": {"site": "Zur Webseite", "code": "Code", "here": "Auf helminet.ch", "more": "Mehr dazu auf helminet.ch."},
}
FIELDS = {"Projektseite": "page", "Quellcode": "code", "Webseite": "site", "Sprache": "language",
          "Lizenz": "licence", "Letzte Änderung": "changed"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "dropnook.app neighbourhood importer"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(1_000_000).decode("utf-8")


def parse(text):
    """The projects of «## Eigene Projekte», in the feed's order."""
    own = re.search(r"^## Eigene Projekte\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not own:
        return []
    projects = []
    for block in re.split(r"^### ", own.group(1), flags=re.M)[1:]:
        lines = block.strip().splitlines()
        p = {"name": lines[0].strip(), "description": ""}
        desc = []
        for line in lines[1:]:
            m = re.match(r"^- ([^:]+):\s*(.*)$", line.strip())
            if m:
                if m.group(1) in FIELDS:
                    p[FIELDS[m.group(1)]] = m.group(2).strip()
            elif line.strip():
                desc.append(line.strip())
        p["description"] = " ".join(desc)
        m = PROJECT_URL.match(p.get("page", ""))
        if not m:
            continue                    # no project page on helminet.ch: not a card of ours
        p["slug"] = m.group(1)
        for k in ("code", "site"):
            if not re.match(r"^https?://[^\s\"'<>]+$", p.get(k, "")):
                p.pop(k, None)
        projects.append(p)
    return projects


def card(p, cur, lang):
    w, e = WORDS[lang], html.escape
    t = lambda x: html.escape(x, quote=False)    # text: quotes stay as they are
    text = cur.get(lang) or p["description"] or w["more"]
    meta = cur.get("meta_" + lang) or " · ".join(x for x in (p.get("licence"), p.get("language")) if x)
    ctas = []
    if p.get("site"):
        ctas.append((p["site"], w["site"]))
    if p.get("code"):
        ctas.append((p["code"], "GitHub" if p["code"].startswith("https://github.com/") else w["code"]))
    if not ctas:
        ctas.append((p["page"], w["here"]))
    out = ['      <li class="mini">',
           f'        <h3><a href="{e(p["page"])}">{t(p["name"])}</a></h3>',
           f'        <p>{t(text)}</p>',
           '        <p class="ctas">']
    out += [f'          <a class="btn small ghost" href="{e(u)}">{t(label)}</a>' for u, label in ctas]
    out.append('        </p>')
    if meta:
        out.append(f'        <p class="meta">{t(meta)}</p>')
    out.append('      </li>')
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if the pages would change; write nothing")
    ap.add_argument("--file", help="a saved llms-full.txt instead of fetching " + FEED)
    a = ap.parse_args()
    try:
        text = open(a.file, encoding="utf-8").read() if a.file else fetch(FEED)
    except Exception as err:            # noqa: BLE001 — any failure leaves the page as it is
        print(f"helminet: can't read the feed ({err}) — nothing changed", file=sys.stderr)
        return 2
    projects = parse(text)
    if not projects:
        print("helminet: the feed lists no project of its own — nothing changed", file=sys.stderr)
        return 2
    data = json.load(open(DATA, encoding="utf-8"))
    curated = data.get("projects", {})
    known = [s for s in data.get("order", []) if s in curated]
    by_slug = {p["slug"]: p for p in projects}
    new = sorted((p for p in projects if p["slug"] not in curated), key=lambda p: p.get("changed", ""), reverse=True)
    order = [p["slug"] for p in new] + [s for s in known if s in by_slug]

    for p in new:
        print(f"helminet: new project «{p['name']}» — shown with helminet's description; add our sentences to "
              f"neighbours/helminet.json")
    for s in known:
        if s not in by_slug:
            print(f"helminet: «{s}» is no longer on helminet.ch — left off the page")
    for s in order:
        up = curated.get(s, {}).get("upstream")
        if up is not None and up != by_slug[s]["description"]:
            print(f"helminet: helminet's description of «{by_slug[s]['name']}» changed — check our sentences")

    changed = False
    for lang, path in PAGES.items():
        page = open(path, encoding="utf-8").read()
        if page.count(START) != 1 or page.count(END) != 1:
            print(f"helminet: {path} lacks the markers — nothing changed", file=sys.stderr)
            return 2
        body = "\n".join(card(by_slug[s], curated.get(s, {}), lang) for s in order)
        new_page = re.sub(re.escape(START) + r".*?" + re.escape(END),
                          lambda _: f"{START}\n{body}\n      {END}", page, flags=re.S)
        if new_page != page:
            changed = True
            if not a.check:
                open(path, "w", encoding="utf-8").write(new_page)
    print(f"helminet: {len(order)} projects — {'changed' if changed else 'no change'}")
    return 1 if (a.check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
