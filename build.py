#!/usr/bin/env python3
"""Build the static pages for therowancollection.com from catalog.json.

Run after every catalog change:  python3 build.py
- gives every visible piece a slug and its own page at /art/<slug>/
- writes each page's title, description, share tags, Google product data
  and the piece's text straight into the HTML, so search engines can read it
- rewrites the home page's built-in list of pieces
- writes sitemap.xml and robots.txt, and removes pages of pieces no longer shown
index.html is the template: only the regions between the build markers change.
"""
import html, json, re, shutil, unicodedata
from datetime import date
from pathlib import Path

SITE = "https://therowancollection.com"
ROOT = Path(__file__).resolve().parent
ART = ROOT / "art"
esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)
usd = lambda n: "" if n is None else "${:,.0f}".format(n)

GENERIC = {"signed", "unsigned", "after", "design", "artist", "unidentified", "unverified",
           "not", "authenticated", "attributed", "to", "school", "tradition", "company"}


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def maker_name(maker):
    """Short artist name for the address, e.g. 'Carl Hasch (Austrian, 1834-1897)' -> 'carl-hasch'."""
    m = re.sub(r"\(.*?\)", "", maker or "")
    m = re.split(r"[,;]", m)[0]
    m = re.sub(r"^(after|signed|attributed to)\s+", "", m.strip(), flags=re.I)
    words = [w for w in slugify(m).split("-") if w]
    if not words or all(w in GENERIC for w in words):
        return ""
    return "-".join(words[:4])


def make_slug(it, used):
    base = slugify(it["title"])[:60].strip("-")
    mk = maker_name(it.get("maker"))
    if mk and mk not in base:
        base = f"{base}-{mk}"
    s, n = base, 2
    while s in used:
        s, n = f"{base}-{n}", n + 1
    used.add(s)
    return s


def kind(it):
    m = (it.get("medium") or "").lower()
    for word, label in [("oil", "oil painting"), ("watercolor", "watercolor"), ("gouache", "gouache"),
                        ("woodblock", "woodblock print"), ("engraving", "engraving"), ("lithograph", "lithograph"),
                        ("serigraph", "serigraph"), ("photogravure", "photogravure"), ("frame", "antique frame")]:
        if re.search(rf"\b{word}\b", m):
            return label
    return {"Paintings": "painting", "Works on paper": "work on paper", "Frames": "antique frame",
            "Sculpture & objects": "sculpture"}.get(it.get("category"), "artwork")


def seo_title(it):
    if it.get("seoTitle"):
        return f"{it['seoTitle']} | The Rowan Collection"
    mk = re.sub(r"\s*\(.*?\)", "", it.get("maker") or "").strip()
    t = it["title"]
    if mk and not re.match(r"^(signed|unsigned|american school|european school)", mk, re.I):
        t = f"{t} by {mk}" if not re.match(r"^after\b", mk, re.I) else f"{t}, {mk}"
    return f"{t} | {kind(it).capitalize()} | The Rowan Collection"


def seo_desc(it):
    bits = [it["title"]]
    for k in ("maker", "medium", "date", "size"):
        if it.get(k):
            bits.append(it[k])
    d = ". ".join(bits) + f". {usd(it['price'])}, or 13% less bought direct. The Rowan Collection, Lynchburg, Virginia."
    return d if len(d) <= 300 else d[:297].rsplit(" ", 1)[0] + "..."


def is_head(p):
    return (p.endswith(":") or re.match(r"^(Details|Item Details|Condition|Provenance|Design|Dimensions|Shipping|Overview|"
            r"Item Specifics|Why This|Signature|Artistic Details|Authenticity Guaranteed)", p)) and len(p) < 45


def label(it):
    who = ", ".join(x for x in (it.get("maker"), it.get("date")) if x)
    return (f'<div class="label"><b>{esc(it["title"])}</b><span class="m">{esc(who)}</span>'
            f'<div class="p"><span>{esc(it.get("category"))}</span><span>{usd(it["price"])}</span></div></div>')


def card(it):
    return (f'<a class="card" href="/art/{it["slug"]}/"><div class="frame"><img src="/{esc(it["image"])}" '
            f'alt="{esc(it["title"])}" loading="lazy"></div>{label(it)}</a>')


def piece_body(it):
    rows = "".join(f"<dt>{k}</dt><dd>{esc(it.get(f))}</dd>" for k, f in
                   [("Date", "date"), ("Medium", "medium"), ("Size", "size"), ("Category", "category")] if it.get(f))
    desc = "".join(f'<p class="{"h" if is_head(p) else ""}">{esc(re.sub(r"^\*\s+", "— ", p))}</p>' for p in it.get("description") or [])
    return f'''<div class="wrap"><a class="back" href="/#collection">← The collection</a>
  <article class="piece">
    <div class="viewer"><div class="mount"><img id="big" src="/{esc(it["image"])}" alt="{esc(it["title"])}"></div></div>
    <div class="info">
      <p class="maker">{esc(it.get("maker"))}</p><h1>{esc(it["title"])}</h1>
      <dl>{rows}</dl>
      <p class="price">{usd(it["price"])}</p>
      <div class="direct"><b>Buy direct and save 13%: <span class="dp">{usd(round(it["price"] * 0.87))}</span></b><p>Skip eBay and buy this piece straight from us for 13% less. Email therowancollection@gmail.com and mention “{esc(it["title"])}”.</p></div>
      <div class="actions"><a class="btn" href="{esc(it["ebayUrl"])}" rel="noopener">View on eBay ↗</a></div>
      <div class="story"><h3>From the listing</h3>{desc}</div>
    </div>
  </article></div>'''


def head_tags(title, desc, url, image, extra=""):
    return f'''<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="The Rowan Collection">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{image}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">{extra}'''


def ld(obj):
    return '\n<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def product_ld(it, url):
    imgs = [f"{SITE}/{it['image']}"] + (it.get("photos") or [])[:6]
    return ld({
        "@context": "https://schema.org", "@type": "Product",
        "name": it["title"], "description": seo_desc(it), "image": imgs, "url": url,
        "sku": str(it["id"]), "category": it.get("category"),
        "brand": {"@type": "Brand", "name": "The Rowan Collection"},
        "offers": {"@type": "Offer", "price": round(it["price"] * 0.87), "priceCurrency": "USD",
                   "availability": "https://schema.org/InStock", "itemCondition": "https://schema.org/UsedCondition",
                   "url": url, "seller": {"@type": "Organization", "name": "The Rowan Collection"}},
    })


def fill(tpl, region, content):
    pat = re.compile(rf"(<!--{region}:start-->).*?(<!--{region}:end-->)", re.S)
    if not pat.search(tpl):
        raise SystemExit(f"index.html is missing the {region} build markers")
    return pat.sub(lambda m: m.group(1) + "\n" + content + "\n" + m.group(2), tpl, count=1)


def main():
    cat = json.loads((ROOT / "catalog.json").read_text())
    used = set()
    for it in cat["items"]:          # keep existing slugs so addresses never change
        if it.get("slug"):
            used.add(it["slug"])
    for it in cat["items"]:
        if not it.get("slug"):
            it["slug"] = make_slug(it, used)
    (ROOT / "catalog.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n")

    live = [i for i in cat["items"] if i.get("visible") is not False]
    tpl = (ROOT / "index.html").read_text()
    org = ld({"@context": "https://schema.org", "@type": "Store", "name": "The Rowan Collection", "url": SITE + "/",
              "logo": f"{SITE}/img/logo-ink.png", "image": f"{SITE}/img/og.jpg", "email": "therowancollection@gmail.com",
              "address": {"@type": "PostalAddress", "addressLocality": "Lynchburg", "addressRegion": "VA", "addressCountry": "US"},
              "description": "Fine and antique paintings, works on paper, sculpture and period frames, found in estates."})

    home = fill(tpl, "meta", head_tags(
        "The Rowan Collection | Fine and Antique Art, Lynchburg, Virginia",
        "Antique and vintage paintings, prints, works on paper and period frames, found in estates and offered from Lynchburg, Virginia. Buy direct and save 13%.",
        SITE + "/", f"{SITE}/img/og.jpg", org))
    home = home.replace('<body data-piece="', '<body data-x="')  # safety: home never carries a piece
    home = fill(home, "pre", '<div class="wrap band"><h1>The Rowan Collection</h1><p>Fine and antique art, chosen one piece at a time.</p>'
                f'<div class="grid">{"".join(card(i) for i in live)}</div></div>')
    (ROOT / "index.html").write_text(home)
    (ROOT / "404.html").write_text(home.replace('<link rel="canonical"', '<meta name="robots" content="noindex">\n<link rel="canonical"', 1))

    if ART.exists():
        shutil.rmtree(ART)
    for it in live:
        url = f"{SITE}/art/{it['slug']}/"
        page = fill(tpl, "meta", head_tags(seo_title(it), seo_desc(it), url, f"{SITE}/{it['image']}", product_ld(it, url)))
        page = fill(page, "pre", piece_body(it))
        page = re.sub(r"<body[^>]*>", f'<body data-piece="{esc(it["slug"])}">', page, count=1)
        d = ART / it["slug"]
        d.mkdir(parents=True)
        (d / "index.html").write_text(page)

    today = cat.get("updated") or date.today().isoformat()
    urls = [(SITE + "/", "1.0")] + [(f"{SITE}/art/{i['slug']}/", "0.8") for i in live]
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod><priority>{p}</priority></url>\n" for u, p in urls) + "</urlset>\n")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    print(f"built {len(live)} piece pages")
    for i in live:
        print(f"  /art/{i['slug']}/")


if __name__ == "__main__":
    main()
