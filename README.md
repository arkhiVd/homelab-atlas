# Homelab Atlas

A static architecture atlas built from hand-authored Mermaid diagrams and machine-readable sidecars. The dashboard uses the Board layout shared with the private atlas: a sticky bar with breadcrumb, find box, and row jumps; an overview row; and one row of panels per diagram, in light and dark themes. Flowcharts are hand-placed, gutter-routed SVG drawn by `bin/atlas_draft.py`; sequence diagrams use the vendored Mermaid runtime.

The bundled evidence is deterministic. Rendering does not inspect the host.

## Render

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
PATH="$PWD/.venv/bin:$PATH bin/validate
bin/render-artifact
```

Open `out/site/index.html` through a static web server so local fonts, icons, and Mermaid load correctly.
