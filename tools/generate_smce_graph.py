#!/usr/bin/env python3
import json
import re
from collections import Counter
from pathlib import Path

import networkx as nx
from pyvis.network import Network

VAULT_ROOT = Path('/home/jhr/Documents/Obsidian Vault/SMCE Wiki')
REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_HTML = REPO_ROOT / 'graph.html'
OUT_JSON = REPO_ROOT / 'graph-data.json'
OUT_VIS = REPO_ROOT / 'graph-vis.html'

EXCLUDE_NAMES = {'AGENTS.md'}
EXCLUDE_PARTS = {'raw', 'outputs'}
WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]')
HEADING_RE = re.compile(r'^#\s+(.+)$', re.MULTILINE)
WORD_RE = re.compile(r"\b[\w'-]{4,}\b")

CATEGORY_COLORS = {
    '00 System': '#94a3b8',
    '10 Catalogues': '#f59e0b',
    '20 Core Concepts': '#8b5cf6',
    '30 Methods': '#10b981',
    '40 Policy Process': '#3b82f6',
    '50 Stakeholders, Equity and Distribution': '#ef4444',
    '60 AI, Governance and Technical Delivery': '#06b6d4',
    '70 Contract Execution': '#f97316',
    '80 Drafts and Review': '#e11d48',
    '90 Aliases': '#64748b',
    'root': '#a78bfa',
}


def iter_notes():
    for path in sorted(VAULT_ROOT.rglob('*.md')):
        rel = path.relative_to(VAULT_ROOT)
        if path.name in EXCLUDE_NAMES:
            continue
        if any(part in EXCLUDE_PARTS for part in rel.parts):
            continue
        yield path, rel


def note_title(text: str, path: Path) -> str:
    match = HEADING_RE.search(text)
    return match.group(1).strip() if match else path.stem


def slugify(text: str) -> str:
    value = text.lower().replace('&', ' and ')
    value = re.sub(r'[^a-z0-9]+', '-', value)
    return re.sub(r'-+', '-', value).strip('-')


def folder_category(rel: Path) -> str:
    return rel.parts[0] if len(rel.parts) > 1 else 'root'


def extract_keywords(text: str, limit: int = 8):
    stop = {
        'this','that','with','from','into','where','when','which','their','there','these','those','about','because','while','within',
        'also','than','then','them','they','have','will','would','could','should','being','used','using','such','page','wiki','note',
        'what','why','how','does','each','more','most','very','much','between','across','under','after','before','through',
        'work','part','main','overview','related','pages','draft','version','preferred','canonical'
    }
    counts = Counter(w.lower() for w in WORD_RE.findall(text) if w.lower() not in stop)
    return [w for w, _ in counts.most_common(limit)]


def build_graph():
    notes = []
    title_to_meta = {}
    for path, rel in iter_notes():
        text = path.read_text(encoding='utf-8')
        title = note_title(text, path)
        category = folder_category(rel)
        meta = {
            'title': title,
            'category': category,
            'path': str(rel),
            'text': text,
            'slug': slugify(title),
            'keywords': extract_keywords(text),
        }
        notes.append(meta)
        title_to_meta[title] = meta

    graph = nx.Graph()
    for meta in notes:
        color = CATEGORY_COLORS.get(meta['category'], '#6366f1')
        graph.add_node(
            meta['title'],
            label=meta['title'],
            title=(
                f"<b>{meta['title']}</b><br>"
                f"Category: {meta['category']}<br>"
                f"Source: {meta['path']}<br>"
                f"Keywords: {', '.join(meta['keywords'])}<br>"
                f"Open page: pages/{meta['slug']}.html"
            ),
            group=meta['category'],
            color=color,
            source=meta['path'],
            url=f"pages/{meta['slug']}.html",
        )

    edge_weights = Counter()
    edge_context = {}
    for meta in notes:
        src = meta['title']
        links = []
        for m in WIKILINK_RE.finditer(meta['text']):
            target = m.group(1).strip()
            if target in title_to_meta and target != src:
                links.append(target)
        for target, count in Counter(links).items():
            key = tuple(sorted((src, target)))
            edge_weights[key] += count
            edge_context.setdefault(key, []).append(src)

    for (a, b), weight in edge_weights.items():
        graph.add_edge(
            a,
            b,
            value=min(12, 1 + weight),
            weight=weight,
            title=f"Shared wikilink connection weight: {weight}<br>Seen from: {', '.join(sorted(set(edge_context[(a, b)]))[:6])}",
        )

    degrees = dict(graph.degree())
    for node, degree in degrees.items():
        graph.nodes[node]['value'] = 12 + degree * 2
        graph.nodes[node]['degree'] = degree

    data = {
        'node_count': graph.number_of_nodes(),
        'edge_count': graph.number_of_edges(),
        'categories': Counter(nx.get_node_attributes(graph, 'group').values()),
        'nodes': [dict(id=n, **graph.nodes[n]) for n in graph.nodes],
        'edges': [dict(source=u, target=v, **graph.edges[u, v]) for u, v in graph.edges],
    }
    OUT_JSON.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return graph, data


def render_graph(graph, data):
    net = Network(height='100vh', width='100%', bgcolor='#0f172a', font_color='#e5e7eb', directed=False)
    net.barnes_hut(gravity=-2500, central_gravity=0.18, spring_length=160, spring_strength=0.02, damping=0.9)
    net.from_nx(graph)
    for node in net.nodes:
        node['shape'] = 'dot'
        node['font'] = {'size': 18, 'face': 'Inter, sans-serif'}
    for edge in net.edges:
        edge['color'] = '#475569'
        edge['opacity'] = 0.45
    net.save_graph(str(OUT_VIS))

    vis_html = OUT_VIS.read_text(encoding='utf-8')
    click_js = """
network.on('doubleClick', function(params) {
  if (params.nodes.length > 0) {
    var node = nodes.get(params.nodes[0]);
    if (node && node.url) {
      window.open(node.url, '_blank');
    }
  }
});
"""
    vis_html = vis_html.replace('drawGraph();', 'drawGraph();\n' + click_js)
    OUT_VIS.write_text(vis_html, encoding='utf-8')

    legend = ''.join(
        f'<span class="legend-item"><span class="legend-swatch" style="background:{color}"></span>{category}</span>'
        for category, color in CATEGORY_COLORS.items() if category in data['categories']
    )
    summary = ''.join(
        f'<li><strong>{category}</strong>: {count}</li>'
        for category, count in sorted(data['categories'].items())
    )

    wrapper = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>SMCE Knowledge Graph</title>
<style>
body {{ margin:0; font-family: Inter, Arial, sans-serif; background:#020617; color:#e5e7eb; }}
.topbar {{ padding:14px 18px; border-bottom:1px solid #1e293b; background:#0f172a; display:flex; justify-content:space-between; gap:12px; align-items:center; position:sticky; top:0; z-index:10; }}
.topbar a {{ color:#93c5fd; text-decoration:none; margin-right:14px; }}
.wrap {{ padding:18px; }}
.panel {{ background:#0f172a; border:1px solid #1e293b; border-radius:14px; padding:16px; margin-bottom:16px; }}
.small {{ color:#94a3b8; font-size:14px; }}
.legend-item {{ display:inline-flex; align-items:center; gap:8px; margin-right:14px; margin-bottom:8px; }}
.legend-swatch {{ width:12px; height:12px; border-radius:999px; display:inline-block; }}
iframe {{ width:100%; height:88vh; border:1px solid #1e293b; border-radius:14px; background:#0f172a; }}
ul {{ margin:8px 0 0 18px; }}
</style>
</head>
<body>
<div class="topbar">
  <div><strong>SMCE Knowledge Graph</strong></div>
  <div>
    <a href="index.html">Published wiki</a>
    <a href="pages/smce-wiki-home.html">Wiki home</a>
  </div>
</div>
<div class="wrap">
  <div class="panel">
    <h1 style="margin-top:0">SMCE knowledge graph</h1>
    <p class="small">Generated from the SMCE Obsidian wiki using the graph-building approach adapted from rahulnyk/knowledge_graph. Notes become nodes, wikilinks become weighted edges, and folder groupings become communities/colors.</p>
    <p><strong>{data['node_count']}</strong> notes and <strong>{data['edge_count']}</strong> weighted note-to-note connections. Double-click a node to open its published page.</p>
    <div>{legend}</div>
    <details>
      <summary>Node counts by folder</summary>
      <ul>{summary}</ul>
    </details>
  </div>
  <iframe src="graph-vis.html" title="SMCE graph"></iframe>
</div>
</body>
</html>'''
    OUT_HTML.write_text(wrapper, encoding='utf-8')


if __name__ == '__main__':
    graph, data = build_graph()
    render_graph(graph, data)
    print(json.dumps({
        'graph_html': str(OUT_HTML),
        'graph_json': str(OUT_JSON),
        'graph_vis': str(OUT_VIS),
        'nodes': data['node_count'],
        'edges': data['edge_count']
    }, indent=2))
