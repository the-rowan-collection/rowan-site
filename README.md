# therowancollection.com

Static site for The Rowan Collection. Netlify publishes the `main` branch automatically.

- `index.html` — the whole site (home, collection, piece pages)
- `catalog.json` — the pieces shown; rebuilt each Monday from the eBay store
- `build.py` — run `python3 build.py` after any catalog change: builds `/art/<slug>/` pages, sitemap.xml, robots.txt and 404.html
- `art/` — generated piece pages (don't edit by hand)
- `img/` — logo, icons and each piece's main photo

Live at https://therowancollection.com
