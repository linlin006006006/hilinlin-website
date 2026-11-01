#!/usr/bin/env python3
"""Regenerate the blog and case studies. Run from anywhere: python3 scripts/build_blog.py

Each post = an entry in _posts_src/posts.json + an HTML body fragment at _posts_src/<slug>.html.
Each case study = an entry in _cases_src/cases.json + a body fragment at _cases_src/<slug>.html.
Outputs: blog/, work/, feed.xml, sitemap.xml, and the home page "Writing" and "Case studies"
sections (between the BLOG / CASES START and END markers).
"""
import json
import re
import shutil
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_posts_src"
TPL = ROOT / "_templates"
SITE = "https://hilinlin.com"
HOME_TEASER_COUNT = 3
FIGMA_FILE = "https://www.figma.com/proto/HPcXXnqr8t4jGB4Sx4AUlT/Case-Studies"
FIGMA_EMBED = "https://embed.figma.com/proto/HPcXXnqr8t4jGB4Sx4AUlT/Case-Studies"
FIGMA_QS = "scaling=scale-down&content-scaling=fixed&page-id=0%3A1"


def fill(template, values):
    for key, val in values.items():
        template = template.replace(f"%%{key}%%", val)
    return template


def human_date(iso):
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def tags_html(tags):
    return "".join(f' · <span class="post__tag">{escape(t)}</span>' for t in tags)


def load_posts():
    posts = json.loads((SRC / "posts.json").read_text(encoding="utf-8"))
    for p in posts:
        for field in ("slug", "title", "date", "summary"):
            if not p.get(field):
                raise SystemExit(f"post missing '{field}': {p}")
        if not (SRC / f"{p['slug']}.html").exists():
            raise SystemExit(f"missing body file _posts_src/{p['slug']}.html")
    return sorted(posts, key=lambda p: p["date"], reverse=True)


def build_post(p):
    url = f"{SITE}/blog/{p['slug']}/"
    jsonld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": p["title"],
        "description": p["summary"],
        "datePublished": p["date"],
        "mainEntityOfPage": url,
        "author": {"@type": "Person", "name": "Linlin Liu", "url": SITE},
    }
    if p.get("linkedin_url"):
        jsonld["sameAs"] = p["linkedin_url"]
    source = ""
    if p.get("linkedin_url"):
        source = (f'Originally published on <a href="{escape(p["linkedin_url"], quote=True)}" '
                  'target="_blank" rel="noopener">LinkedIn</a>.')
    cover_html, og_image = "", ""
    if p.get("cover"):
        c = p["cover"]
        caption = f'\n      <figcaption>{escape(c["caption"])}</figcaption>' if c.get("caption") else ""
        cover_html = (f'<figure class="post__cover">\n      <img src="{escape(c["src"], quote=True)}" '
                      f'alt="{escape(c.get("alt", ""), quote=True)}">{caption}\n    </figure>')
        og_src = c.get("og", c["src"])
        og_image = (f'<meta property="og:image" content="{SITE}{escape(og_src, quote=True)}">\n'
                    '<meta name="twitter:card" content="summary_large_image">')
        jsonld["image"] = SITE + og_src
    else:
        og_image = '<meta name="twitter:card" content="summary">'
    html = fill((TPL / "post.html").read_text(encoding="utf-8"), {
        "COVER": cover_html,
        "OGIMAGE": og_image,
        "TITLE": escape(p["title"]),
        "DESC": escape(p["summary"], quote=True),
        "URL": url,
        "DATE_ISO": p["date"],
        "DATE_HUMAN": human_date(p["date"]),
        "TAGS": tags_html(p.get("tags", [])),
        "BODY": (SRC / f"{p['slug']}.html").read_text(encoding="utf-8").strip(),
        "SOURCE_NOTE": source,
        "JSONLD": json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/"),
    })
    out = ROOT / "blog" / p["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")


def list_item(p):
    return (f'    <li class="post-list__item">\n'
            f'      <a href="/blog/{p["slug"]}/">\n'
            f'        <span class="post-list__date">{human_date(p["date"])}</span>\n'
            f'        <span class="post-list__title">{escape(p["title"])}</span>\n'
            f'        <span class="post-list__summary">{escape(p["summary"])}</span>\n'
            f'      </a>\n'
            f'    </li>')


def build_index(posts):
    blog = ROOT / "blog"
    blog.mkdir(exist_ok=True)
    items = "\n".join(list_item(p) for p in posts)
    html = fill((TPL / "blog_index.html").read_text(encoding="utf-8"), {"ITEMS": items})
    (blog / "index.html").write_text(html, encoding="utf-8")


def build_home_teaser(posts):
    path = ROOT / "index.html"
    html = path.read_text(encoding="utf-8")
    if posts:
        items = "\n".join(list_item(p) for p in posts[:HOME_TEASER_COUNT])
        block = (
            '<section id="writing" class="section section--tint">\n'
            '    <div class="wrap">\n'
            '      <p class="eyebrow">Writing</p>\n'
            '      <h2 class="section__title">Thinking out loud.</h2>\n'
            '      <ul class="post-list">\n' + items + '\n      </ul>\n'
            '      <p class="writing__all"><a class="btn btn--ghost" href="/blog/">All writing</a></p>\n'
            '    </div>\n'
            '  </section>'
        )
    else:
        block = ""
    new, n = re.subn(r"(<!-- BLOG:START -->).*?(<!-- BLOG:END -->)",
                     lambda m: f"{m.group(1)}\n  {block}\n  {m.group(2)}", html, flags=re.S)
    if n != 1:
        raise SystemExit("index.html is missing the BLOG:START / BLOG:END markers")
    path.write_text(new, encoding="utf-8")


def load_cases():
    cases = json.loads((ROOT / "_cases_src" / "cases.json").read_text(encoding="utf-8"))
    for c in cases:
        if not (ROOT / "_cases_src" / f"{c['slug']}.html").exists():
            raise SystemExit(f"missing body file _cases_src/{c['slug']}.html")
    return cases


def build_case(c):
    meta = "\n".join(f"    <div><dt>{escape(k)}</dt><dd>{escape(v)}</dd></div>" for k, v in c["meta"])
    stats = "\n".join(
        f'    <div class="stat"><span class="stat__num">{escape(n)}</span><span class="stat__label">{escape(l)}</span></div>'
        for n, l in c["stats"])
    node = c["figma_node"]
    html = fill((TPL / "case.html").read_text(encoding="utf-8"), {
        "COMPANY": escape(c["company"]),
        "TITLE": escape(c["title"]),
        "DESC": escape(c["summary"], quote=True),
        "URL": f"{SITE}/work/{c['slug']}/",
        "META": meta,
        "STATS": stats,
        "BODY": (ROOT / "_cases_src" / f"{c['slug']}.html").read_text(encoding="utf-8").strip(),
        "FIGMA_URL": escape(f"{FIGMA_FILE}?node-id={node}&{FIGMA_QS}", quote=True),
        "EMBED_URL": escape(f"{FIGMA_EMBED}?node-id={node}&embed-host=share&{FIGMA_QS}", quote=True),
    })
    out = ROOT / "work" / c["slug"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")


def case_card(c):
    stats = "".join(f"<li><strong>{escape(n)}</strong> {escape(l)}</li>" for n, l in c["stats"][:2])
    return (f'        <a class="case-card" href="/work/{c["slug"]}/">\n'
            f'          <span class="case-card__company">{escape(c["company"])}</span>\n'
            f'          <h3 class="case-card__title">{escape(c["title"])}</h3>\n'
            f'          <p class="case-card__blurb">{escape(c["blurb"])}</p>\n'
            f'          <ul class="case-card__stats">{stats}</ul>\n'
            f'          <span class="case-card__cta">Read the case study &rarr;</span>\n'
            f'        </a>')


def build_home_cases(cases):
    path = ROOT / "index.html"
    html = path.read_text(encoding="utf-8")
    block = (
        '<section id="case-studies" class="section">\n'
        '    <div class="wrap">\n'
        '      <p class="eyebrow">Case studies</p>\n'
        '      <h2 class="section__title">Two products, from problem to launch.</h2>\n'
        '      <div class="case-grid">\n' + "\n".join(case_card(c) for c in cases) + '\n      </div>\n'
        '    </div>\n'
        '  </section>')
    new, n = re.subn(r"(<!-- CASES:START -->).*?(<!-- CASES:END -->)",
                     lambda m: f"{m.group(1)}\n  {block}\n  {m.group(2)}", html, flags=re.S)
    if n != 1:
        raise SystemExit("index.html is missing the CASES:START / CASES:END markers")
    path.write_text(new, encoding="utf-8")


def build_feed(posts):
    items = []
    for p in posts:
        url = f"{SITE}/blog/{p['slug']}/"
        pub = datetime.strptime(p["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        items.append(
            "    <item>\n"
            f"      <title>{escape(p['title'])}</title>\n"
            f"      <link>{url}</link>\n"
            f"      <guid isPermaLink=\"true\">{url}</guid>\n"
            f"      <pubDate>{format_datetime(pub)}</pubDate>\n"
            f"      <description>{escape(p['summary'])}</description>\n"
            "    </item>")
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n  <channel>\n'
        '    <title>Linlin Liu — Writing</title>\n'
        f'    <link>{SITE}/blog/</link>\n'
        "    <description>Essays on femtech, women's health, and how products get built.</description>\n"
        + "\n".join(items) + "\n  </channel>\n</rss>\n")
    (ROOT / "feed.xml").write_text(feed, encoding="utf-8")


def build_sitemap(posts, cases):
    urls = ([f"{SITE}/", f"{SITE}/blog/"] + [f"{SITE}/work/{c['slug']}/" for c in cases]
            + [f"{SITE}/blog/{p['slug']}/" for p in posts])
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n",
        encoding="utf-8")


def remove_stale_post_dirs(posts):
    keep = {p["slug"] for p in posts}
    for d in (ROOT / "blog").iterdir():
        if d.is_dir() and d.name not in keep:
            shutil.rmtree(d)


def main():
    posts = load_posts()
    for p in posts:
        build_post(p)
    build_index(posts)
    remove_stale_post_dirs(posts)
    build_home_teaser(posts)
    cases = load_cases()
    for c in cases:
        build_case(c)
    build_home_cases(cases)
    build_feed(posts)
    build_sitemap(posts, cases)
    print(f"Built {len(posts)} post(s) and {len(cases)} case stud{'y' if len(cases) == 1 else 'ies'}.")


if __name__ == "__main__":
    main()
