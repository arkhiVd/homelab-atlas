# Homelab Atlas

A static architecture atlas built from hand-authored Mermaid diagrams and machine-readable sidecars. The dashboard preserves the full diagram and catalog content in a deep-ocean interface, with opaque diagram cards, local assets, and a loading veil that waits for Mermaid and icons.

The bundled evidence is deterministic. Rendering does not inspect the host.

## Render

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
PATH="$PWD/.venv/bin:$PATH bin/validate
bin/render-artifact
```

Open `out/site/index.html` through a static web server so local fonts, icons, and Mermaid load correctly.
