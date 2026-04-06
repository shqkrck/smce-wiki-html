#!/usr/bin/env python3
import html
import re
from collections import defaultdict
from pathlib import Path

import markdown

VAULT_ROOT = Path('/home/jhr/Documents/Obsidian Vault/SMCE Wiki')
REPO_ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = REPO_ROOT / 'pages'
INDEX_HTML = REPO_ROOT / 'index.html'

EXCLUDE_NAMES = {'AGENTS.md'}
EXCLUDE_PARTS = {'raw', 'outputs'}
WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]')
HEADING_RE = re.compile(r'^#\s+(.+)$', re.MULTILINE)

TOP_LINKS = [
    ('Landing', '../index.html'),
    ('SMCE Wiki Home', '../pages/smce-wiki-home.html'),
    ('How to use this wiki', '../pages/how-to-use-this-wiki.html'),
    ('SMCE', '../pages/smce.html'),
    ('Better Regulation Guidelines and Toolbox', '../pages/better-regulation-guidelines-and-toolbox.html'),
    ('Source ingestion index', '../pages/source-ingestion-index.html'),
]
LANDING_LINKS = [
    ('SMCE Wiki Home', 'pages/smce-wiki-home.html'),
    ('How to use this wiki', 'pages/how-to-use-this-wiki.html'),
    ('SMCE', 'pages/smce.html'),
    ('Better Regulation Guidelines and Toolbox', 'pages/better-regulation-guidelines-and-toolbox.html'),
    ('Source ingestion index', 'pages/source-ingestion-index.html'),
    ('Knowledge graph', 'graph.html'),
]


def slugify(text: str) -> str:
    value = text.lower().replace('&', ' and ')
    value = re.sub(r'[^a-z0-9]+', '-', value)
    return re.sub(r'-+', '-', value).strip('-')


def iter_notes():
    for path in sorted(VAULT_ROOT.rglob('*.md')):
        rel = path.relative_to(VAULT_ROOT)
        if path.name in EXCLUDE_NAMES:
            continue
        if any(part in EXCLUDE_PARTS for part in rel.parts):
            continue
        yield path, rel


def title_from_text(text: str, path: Path) -> str:
    m = HEADING_RE.search(text)
    return m.group(1).strip() if m else path.stem


def convert_wikilinks(text: str, title_to_slug: dict[str, str], prefix: str = '../pages/'):
    def repl(match):
        target = match.group(1).strip()
        label = (match.group(2) or target).strip()
        slug = title_to_slug.get(target)
        if not slug:
            return label
        return f'[{label}]({prefix}{slug}.html)'
    return WIKILINK_RE.sub(repl, text)


def page_template(title, sidebar_html, content_html, outgoing_html, backlinks_html, source_name, out_count, back_count):
    top = ''.join(f'<a href="{href}">{html.escape(label)}</a>' for label, href in TOP_LINKS)
    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · SMCE Wiki</title>
<link rel="stylesheet" href="../styles.css"><script defer src="../app.js"></script>
</head><body>
<div class="topbar"><div class="inner"><div class="brand"><a href="../index.html" style="color:inherit;text-decoration:none">SMCE Wiki</a></div><div class="toplinks">{top}</div></div></div>
<section class="hero compact-hero"><details class="hero-dropdown hero-card"><summary><span class="dropdown-title">Page info</span><span class="dropdown-subtitle">Source and note connections</span></summary><div class="dropdown-content"><div class="hero-menu-meta"><span class="pill">{out_count} outgoing wikilinks</span><span class="pill">{back_count} backlinks</span><span class="pill">Source: {html.escape(source_name)}</span></div><div class="page-dropdown-grid"><div class="meta-card"><h4>Links out</h4>{outgoing_html}</div><div class="meta-card"><h4>Backlinks</h4>{backlinks_html}</div></div></div></details></section>
<div class="layout"><aside class="panel sidebar"><input id="navSearch" class="search-box" type="text" placeholder="Filter pages..." oninput="filterNav()"><div class="sidebar-section"><h3>Wiki pages</h3>{sidebar_html}</div></aside><main class="panel content">{content_html}</main></div>
<div class="footer">Page exported from the SMCE Wiki Obsidian vault.</div>
</body></html>'''


def landing_template(sidebar_html, home_slug, count):
    top = ''.join(f'<a href="{href}">{html.escape(label)}</a>' for label, href in LANDING_LINKS)
    buttons = ''.join(f'<a class="button{" primary" if i==0 else ""}" href="{href}">{html.escape(label)}</a>' for i,(label,href) in enumerate(LANDING_LINKS))
    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SMCE Wiki</title>
<link rel="stylesheet" href="styles.css"><script defer src="app.js"></script>
</head><body>
<div class="topbar"><div class="inner"><div class="brand">SMCE Wiki</div><div class="toplinks">{top}</div></div></div>
<section class="hero compact-hero"><details class="hero-dropdown hero-card" open><summary><span class="dropdown-title">SMCE Wiki menu</span><span class="dropdown-subtitle">Open quick links</span></summary><div class="dropdown-content"><div class="actions dropdown-actions">{buttons}</div><div class="hero-menu-meta"><span class="pill">{count} source notes</span><span class="pill">Wikilinks converted to HTML pages</span><span class="pill">Offline local reference</span></div></div></details></section>
<div class="layout"><aside class="panel sidebar"><input id="navSearch" class="search-box" type="text" placeholder="Filter pages..." oninput="filterNav()"><div class="sidebar-section"><h3>Wiki pages</h3>{sidebar_html}</div></aside><main class="panel content"><h1>SMCE Wiki</h1><p>This published site is generated from the SMCE Obsidian vault and mirrors the current wiki structure, including the downloaded source library, source-derived notes, and the knowledge graph.</p><p>Start with <a href="pages/{home_slug}.html">SMCE Wiki Home</a>, then use the sidebar, catalogues, and graph to navigate.</p><ul><li><a href="pages/{home_slug}.html">Wiki home</a></li><li><a href="pages/source-ingestion-index.html">Source ingestion index</a></li><li><a href="pages/catalogue-downloaded-smce-and-better-regulation-library.html">Downloaded source library</a></li><li><a href="graph.html">Knowledge graph</a></li></ul></main></div>
<div class="footer">Generated from the SMCE Wiki vault in Documents/Obsidian Vault.</div>
</body></html>'''


def make_list(items, prefix='../pages/'):
    if not items:
        return '<p class="small">None</p>'
    lis = ''.join(f'<li><a href="{prefix}{slugify(title)}.html">{html.escape(title)}</a></li>' for title in items)
    return f'<ul>{lis}</ul>'


def main():
    md = markdown.Markdown(extensions=['tables', 'sane_lists', 'fenced_code'])
    notes = []
    for path, rel in iter_notes():
        text = path.read_text(encoding='utf-8')
        title = title_from_text(text, path)
        notes.append({'path': path, 'rel': rel, 'title': title, 'slug': slugify(title), 'text': text})
    title_to_slug = {n['title']: n['slug'] for n in notes}
    outgoing = {}
    backlinks = defaultdict(list)
    for n in notes:
        links = []
        seen = set()
        for m in WIKILINK_RE.finditer(n['text']):
            target = m.group(1).strip()
            if target in title_to_slug and target != n['title'] and target not in seen:
                links.append(target)
                backlinks[target].append(n['title'])
                seen.add(target)
        outgoing[n['title']] = links
    sorted_notes = sorted(notes, key=lambda n: (str(n['rel']).lower(), n['title'].lower()))
    sidebar_html = '<ul>' + ''.join(f'<li data-nav-item="{html.escape(n["title"])}"><a href="../pages/{n["slug"]}.html">{html.escape(n["title"])}' + '</a></li>' for n in sorted_notes) + '</ul>'
    landing_sidebar_html = '<ul>' + ''.join(f'<li data-nav-item="{html.escape(n["title"])}"><a href="pages/{n["slug"]}.html">{html.escape(n["title"])}' + '</a></li>' for n in sorted_notes) + '</ul>'
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    for old in PAGES_DIR.glob('*.html'):
        old.unlink()
    for n in notes:
        body_md = convert_wikilinks(n['text'], title_to_slug)
        content_html = md.reset().convert(body_md)
        page_html = page_template(
            n['title'], sidebar_html, content_html,
            make_list(outgoing[n['title']]), make_list(sorted(backlinks[n['title']])),
            n['rel'].name, len(outgoing[n['title']]), len(backlinks[n['title']])
        )
        (PAGES_DIR / f'{n["slug"]}.html').write_text(page_html, encoding='utf-8')
    home_slug = title_to_slug.get('SMCE Wiki Home', 'smce-wiki-home')
    INDEX_HTML.write_text(landing_template(landing_sidebar_html, home_slug, len(notes)), encoding='utf-8')
    print(f'Exported {len(notes)} pages to {PAGES_DIR}')

if __name__ == '__main__':
    main()
