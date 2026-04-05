# SMCE wiki publishing tools

This repository includes a graph-generation step adapted from rahulnyk/knowledge_graph.

## Graph refresh workflow

After updating the SMCE wiki content and regenerating the published HTML pages, run:

```bash
/tmp/kg-venv/bin/python tools/generate_smce_graph.py
```

This rebuilds:
- `graph.html` — human-facing graph page
- `graph-vis.html` — interactive pyvis network
- `graph-data.json` — node/edge export

## Graph model used here

- each published wiki note is a node
- Obsidian wikilinks become weighted edges
- top-level wiki folders become graph communities/colors
- double-clicking a node opens the corresponding published wiki page
