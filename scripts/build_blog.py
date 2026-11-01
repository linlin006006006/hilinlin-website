#!/usr/bin/env python3
"""Regenerate the blog from _posts_src/. Run from anywhere: python3 scripts/build_blog.py

Each post = an entry in _posts_src/posts.json + an HTML body fragment at _posts_src/<slug>.html.
Outputs: blog/index.html, blog/<slug>/index.html, feed.xml, sitemap.xml, and the
"Writing" teaser on the home page (between the BLOG:START / BLOG:END markers).
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
        og_image = (f'<meta property="og:image" content="{SITE}{escape(c["src"], quote=True)}">\n'
                    '<meta name="twitter:card" content="summary_large_image">')
        jsonld["image"] = SITE + c["src"]
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
            '<section id="writing" class="section">\n'
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


def build_sitemap(posts):
    urls = [f"{SITE}/", f"{SITE}/blog/"] + [f"{SITE}/blog/{p['slug']}/" for p in posts]
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
    build_feed(posts)
    build_sitemap(posts)
    print(f"Built {len(posts)} post(s).")


if __name__ == "__main__":
    main()
