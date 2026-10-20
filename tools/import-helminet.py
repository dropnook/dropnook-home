#!/usr/bin/env python3
"""Fills «From the neighbourhood» / «Aus der Nachbarschaft» from helminet.ch.

Reads helmi1987's own projects from https://helminet.ch/llms-full.txt (the section «Eigene Projekte»; the supported
ones are dropnook's two products, already on this page) and writes the cards between the markers
<!-- helminet:start --> and <!-- helminet:end --> in index.html and de/index.html.

neighbours/helminet.json holds what helminet.ch can't say: our own German and English sentence and meta line per
project. A project helminet.ch lists that we have no sentence for yet shows helminet's own description in both
languages; a project helminet.ch no longer lists leaves the page. Links (project page, site, code), the licence and
the language always come from helminet.ch.

The newest first, by the last commit (date and time, as helminet.ch sorts — never GitHub's pushed_at, which moves
with any push to any branch): helminet's «Letzte Änderung» gives the day; for a project with its code on GitHub the
time of the last commit on its default branch decides within the day (GitHub's public API, two calls per project; a
project without public code, or when GitHub doesn't answer, counts as the start of its day).

    python3 tools/import-helminet.py            # fetch, write the pages
    python3 tools/import-helminet.py --check    # fetch, exit 1 if the pages would change (nothing written)
    python3 tools/import-helminet.py --file F   # read a saved llms-full.txt instead of fetching

Pictures: each project page on helminet.ch names its logo and its preview picture (the repository's social preview,
og:image) under /projekt-medien/. They are copied into neighbours/img/ (the page loads nothing from other hosts),
checked first: a PNG, JPEG or WebP by its first bytes, an SVG only without script, event handlers or external
references, at most 300 KB (logo) and 1.5 MB (preview). A picture that can't be fetched keeps the copy there; a project
without one shows none.

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


def last_commit(code_url):
    """ISO time of the last commit on the default branch of a public GitHub repository, or None."""
    m = re.match(r"^https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", code_url or "")
    if not m:
        return None
    api = f"https://api.github.com/repos/{m.group(1)}/{m.group(2)}"
    try:
        def get(url):
            req = urllib.request.Request(url, headers={"User-Agent": "dropnook.app neighbourhood importer",
                                                       "Accept": "application/vnd.github+json"})
            if os.environ.get("GITHUB_TOKEN"):
                req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        branch = get(api)["default_branch"]
        return get(f"{api}/commits/{branch}")["commit"]["committer"]["date"]
    except Exception:                   # noqa: BLE001 — no time: the start of its day
        return None


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


IMG_DIR = os.path.join(ROOT, "neighbours", "img")
MEDIA = re.compile(r"^/projekt-medien/\d+/[\w.-]+\.(svg|png|webp|jpe?g)$")
IMG_MAX = {"logo": 300_000, "banner": 1_500_000}


def picture_ok(data, ext):
    if ext == "png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in ("jpg", "jpeg"):
        return data.startswith(b"\xff\xd8\xff")
    if ext == "webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if ext == "svg":
        try:
            t = data.decode("utf-8").lower()
        except UnicodeDecodeError:
            return False
        return "<svg" in t and not re.search(r"<script|<foreignobject|\son\w+\s*=|javascript:|xlink:href\s*=\s*[\"']?(https?:|//)|href\s*=\s*[\"']?(https?:|//)|<!entity", t)
    return False


def fetch_bytes(url, limit):
    req = urllib.request.Request(url, headers={"User-Agent": "dropnook.app neighbourhood importer"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read(limit + 1)
    return data if len(data) <= limit else None


def pictures(slug):
    """{kind: file name in neighbours/img} — fetched anew when helminet.ch answers, else the copies there."""
    found = {}
    try:
        page = fetch(f"https://helminet.ch/projekte/{slug}")
    except Exception:                   # noqa: BLE001 — keep what is there
        page = ""
    want = {}
    m = re.search(r'<meta property="og:image" content="https://helminet\.ch(/projekt-medien/[^"]+)"', page)
    if m and MEDIA.match(m.group(1)) and "banner" in m.group(1).rsplit("/", 1)[-1]:
        want["banner"] = m.group(1)    # a project without a preview has its logo (or the owner's avatar) as og:image
    for src in re.findall(r'<img src="(/projekt-medien/[^"]+)"', page):
        name = src.rsplit("/", 1)[-1]
        if MEDIA.match(src) and re.match(r"^(gh-)?logo[-\w]*\.", name) and "dark" not in name:
            want["logo"] = src
            break
    os.makedirs(IMG_DIR, exist_ok=True)
    for kind in ("logo", "banner"):
        old = [f for f in os.listdir(IMG_DIR) if f.startswith(f"{slug}-{kind}.")]
        if kind in want:
            ext = want[kind].rsplit(".", 1)[-1].lower()
            name = f"{slug}-{kind}.{ext}"
            try:
                data = fetch_bytes("https://helminet.ch" + want[kind], IMG_MAX[kind])
            except Exception:           # noqa: BLE001
                data = None
            if data and picture_ok(data, ext):
                path = os.path.join(IMG_DIR, name)
                if not os.path.exists(path) or open(path, "rb").read() != data:
                    open(path, "wb").write(data)
                for f in old:
                    if f != name:
                        os.remove(os.path.join(IMG_DIR, f))
                found[kind] = name
                continue
        if old and (kind in want or not page):    # not fetched now: keep the copy
            found[kind] = old[0]
        elif old and page:                        # helminet.ch has none any more
            for f in old:
                os.remove(os.path.join(IMG_DIR, f))
    return found


def card(p, cur, lang, pics=None):
    w, e = WORDS[lang], html.escape
    pics = pics or {}
    up = "../" if lang == "de" else ""
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
    out = ['      <li class="mini">']
    if pics.get("banner"):
        out.append(f'        <img class="mini-banner" src="{up}neighbours/img/{e(pics["banner"])}" alt="" width="1600" height="600" loading="lazy" decoding="async">')
    elif pics.get("logo"):              # no preview: the same space, its logo in the middle — every card the same shape
        out.append(f'        <div class="mini-banner mini-banner-logo"><img src="{up}neighbours/img/{e(pics["logo"])}" alt="" width="72" height="72" loading="lazy" decoding="async"></div>')
    logo = f'<img class="mini-logo" src="{up}neighbours/img/{e(pics["logo"])}" alt="" width="28" height="28" loading="lazy" decoding="async">' if pics.get("logo") else ""
    out += [f'        <h3>{logo}<a href="{e(p["page"])}">{t(p["name"])}</a></h3>',
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
    new = [p for p in projects if p["slug"] not in curated]
    for p in projects:
        p["committed"] = last_commit(p.get("code", ""))
    rank = {s: i for i, s in enumerate(known)}
    order = [p["slug"] for p in sorted(projects, key=lambda p: (p.get("changed", ""), p["committed"] or "",
                                                                 -rank.get(p["slug"], -1)), reverse=True)]

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

    pics = {} if a.check or a.file else {slug: pictures(slug) for slug in order}
    if not (a.check or a.file):         # copies of projects that left the page go too
        keep = {f for v in pics.values() for f in v.values()}
        for f in os.listdir(IMG_DIR) if os.path.isdir(IMG_DIR) else []:
            if f not in keep and re.match(r"^[a-z0-9-]+-(logo|banner)\.\w+$", f):
                os.remove(os.path.join(IMG_DIR, f))
    elif os.path.isdir(IMG_DIR):        # --check / --file: the copies as they are
        for slug in order:
            pics[slug] = {k: f for f in os.listdir(IMG_DIR) for k in ("logo", "banner") if f.startswith(f"{slug}-{k}.")}

    changed = False
    for lang, path in PAGES.items():
        page = open(path, encoding="utf-8").read()
        if page.count(START) != 1 or page.count(END) != 1:
            print(f"helminet: {path} lacks the markers — nothing changed", file=sys.stderr)
            return 2
        body = "\n".join(card(by_slug[s], curated.get(s, {}), lang, pics.get(s)) for s in order)
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
