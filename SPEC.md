# Specification

## Requirements

- Preserve hand-authored Mermaid topology and sidecar metadata as the dashboard source.
- Generate a standalone static site under `out/site/`.
- Provide the architecture dashboard layout, navigation, catalog, filters, inspector, zoom controls, and responsive behavior in the portfolio deep-ocean visual system.
- Keep diagram cards opaque. Restrict glass effects to navigation and controls.
- Show an initial loading veil until local Mermaid rendering and icon loads settle. After rejection or 45 seconds, offer Retry and Show text; without JavaScript, reveal the text content.
- Do not provide theme controls or browser theme persistence.
- Use only committed fixture evidence. Rendering must not inspect the host.
- Load fonts, Mermaid, icons, and screenshots from local checked inputs.
- Validate SVG checksums and reject active or externally loaded SVG content.
- Keep output deterministic and contained beneath `out/`.
