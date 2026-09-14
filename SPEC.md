# Specification

## Requirements

- Preserve hand-authored Mermaid topology and sidecar metadata as the dashboard source.
- Generate a standalone static site under `out/site/`.
- Provide the architecture dashboard layout, navigation, catalog, filters, inspector, zoom controls, responsive behavior, and theme handling.
- Use only committed fixture evidence. Rendering must not inspect the host.
- Load fonts, Mermaid, icons, and screenshots from local checked inputs.
- Validate SVG checksums and reject active or externally loaded SVG content.
- Keep output deterministic and contained beneath `out/`.
