# dropnook.app

The small overview page at **https://dropnook.app/**: it presents dropnook's two open-source tools for the home
server and sends you on to their own sites.

| | Site | Code | Licence |
|---|---|---|---|
| **Dropnook** — instant sharing for your home network | https://dropnook.dropnook.app/ | [dropnook/dropnook.app](https://github.com/dropnook/dropnook.app) | AGPL-3.0 |
| **Unraid Secretary Office** — a small office for your Unraid server | https://uso.dropnook.app/ | [dropnook/UnraidSecretaryOffice](https://github.com/dropnook/UnraidSecretaryOffice) | GPL-3.0-or-later |

Below the two products, a quieter section «From the neighbourhood» / «Aus der Nachbarschaft» lists the nine projects
from [helminet.ch](https://helminet.ch/), helmi1987's collection of their own open-source projects (which in turn
lists Dropnook and the office), with Benj's own line of introduction. Helminet is an independent
project; the descriptions are shortened from helminet.ch, the logo is a copy in `logos/`.

## What is here

Plain static files, no build step, nothing loaded from third parties, no cookies.

| File | What it is |
|---|---|
| `index.html`, `de/index.html` | The page in English and German (Swiss spelling: «ss», never «ß»). Edit both together. |
| `site.css` | One stylesheet in the family of the two product sites. Each card wears its product's accent (`--dn`, `--uso`); the neighbourhood cards wear none. The pages load it as `site.css?v=N`: raise `N` in both pages when it changes. |
| `lang.js` | The start page is English; a browser that prefers German goes to `/de/` — unless EN or DE was clicked before, which is kept (`localStorage` `dropnook.lang`). As on both product sites. |
| `theme.js` | The ☀/☾ switch: light, dark, or automatic as the system; a second click on the chosen side goes back to automatic (`dropnook.theme`). Pictures with a `prefers-color-scheme` `<source>` follow the choice. |
| `logos/` | The products' title graphics and icons, copied unchanged: `dropnook-title-*.svg` from `dropnook.app/docs`, `dropnook-icon.svg` from `dropnook.app/static/icon.svg` (the same drop as `docs/icon.png`), `uso-title-*.svg` and `uso-icon.svg` from the office's site. `helminet-wide-*.svg` and `helminet-icon-*.svg` are copies of `https://helminet.ch/logo/wide-*.svg` and `icon-*.svg` (light: blue, dark: white), checked: plain paths, no scripts, no links. |
| `icon.svg`, `icon.png`, `apple-touch-icon.png`, `favicon.ico` | The dropnook avatar (from the GitHub profile), rounded for the tab; the PNGs and the ICO are renders of it. |
| `social-preview.png` | 1200×630 card with both names, rendered from a small HTML card in headless Chrome. |
| `robots.txt`, `sitemap.xml` | For search engines; the sitemap lists `/` and `/de/` with hreflang. |

The pages carry canonical and hreflang links (en, de, x-default), Open Graph tags and schema.org JSON-LD: the
`Organization` dropnook, the `WebSite`, the `WebPage`, and one `SoftwareApplication` per product. The two
applications use the same `@id` as on their own sites (`https://dropnook.dropnook.app/#software`,
`https://uso.dropnook.app/#software`), so search engines can join them.

## Checking it

Open `index.html` in a browser for a quick look. For the real paths (the language links and the redirect use
`https://dropnook.app/`), serve the folder at the root of a host — any static host will do. Check both
languages, both themes, and a phone width (375 px): no horizontal scroll, no console errors.

## When something changes

- A product's tagline, licence or URL changes → both `index.html` files (card text, links, JSON-LD) and, if the
  names change, `social-preview.png`.
- A product's logo changes → copy the new file into `logos/` under the same name.
- New page → add it to `sitemap.xml`.
- A Helminet project changes or goes → the neighbourhood section in both `index.html` files; a new Helminet logo
  → copy it into `logos/` under the same name.
