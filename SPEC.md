# Specification

## Requirements

- Preserve hand-authored Mermaid topology and sidecar metadata as the dashboard source.
- Generate a standalone static site under `out/site/`.
- Provide the architecture dashboard layout, navigation, zoom controls, and responsive behavior in the Board visual system shared with the private atlas (phase 2 below).
- Provide light and dark themes that follow the system preference, with a toggle whose choice persists in the browser. This replaces the phase A deep-ocean, single-theme, loading-veil design.
- Use only committed fixture evidence. Rendering must not inspect the host.
- Load fonts, Mermaid, icons, and screenshots from local checked inputs.
- Validate SVG checksums and reject active or externally loaded SVG content.
- Keep output deterministic and contained beneath `out/`.

## Phase 2: Board dashboard and drafted diagrams

### Behavior

- The page uses the "Board" ops-dashboard layout: a sticky top bar with a breadcrumb, a find box (`/` focuses it), and a fixture snapshot chip; a second bar with one jump button per diagram row, the visible row highlighted; an Overview row of stat panels with threshold colors; then one dashboard row per diagram on a 24-column panel grid.
- Each diagram row holds a full-width drawing panel (source file in its header, an "Actual size" toggle, and the existing zoom dialog), a Notes panel (span 16), and a Source panel (span 8: file, state badge, check, revision, snapshot). Findings show in an alert-style list panel.
- Panels are flat, with a 2px radius and 1px borders. Light (`#f4f5f5` page, `#fff` panels) and dark (`#111217` page, `#181b1f` panels) themes both work, follow the system preference, and keep the manual toggle.
- The theme, tokens, and panel styling match the private atlas Board design: Space Grotesk and JetBrains Mono (vendored under `vendor/fonts/`, listed in `vendor/fonts/manifest.yaml`), an indigo accent, `#f4f5f5`/`#fff` light and `#080c0b`/`#0f1614` dark surfaces, dashed zone frames, and node planes from `src/style.md` with matching dark class colors. No runtime remote assets.
- At 390 px the body never scrolls horizontally; the panel grid collapses to one column.

### Drafted diagrams

- A sidecar with a `layout:` block draws its flowchart as static SVG with the grid drafter (`bin/atlas_draft.py`) instead of Mermaid. The `.mmd` file stays the only source of nodes, edges, kinds, labels, and groups; `layout:` only places nodes on `[column, row]` cells and may add routing hints.
- Edges route orthogonally through the gutters between columns. Edges that share an endpoint share a trunk. Crossings over intermediate columns take the nearest clear height. Labels are knocked out on the line. Zone titles may sit below the frame. Key nodes get a double border.
- Diagrams without `layout:` and sequence diagrams keep rendering with the vendored Mermaid runtime.

### Acceptance criteria

| Criterion | Check |
|---|---|
| Every `.mmd` node, edge (with kind), edge label, and group appears in the drafted SVG, and nothing else does | `tests/test_atlas_draft.py` preservation test |
| No edge passes through a foreign box; no label or zone title sits on a box; no unrelated edges share a run; no duplicate edges coincide | `geometry_findings()` is empty for every laid-out diagram |
| Drafted SVG has no script, event handler, or remote URL, and is byte-identical across renders | drafter test plus `bin/validate` render-twice check |
| Generated output contains no generic private markers (non-documentation IP ranges, overlay network domains, home paths, email addresses) | `tests/test_redaction.py`, always on |
| Generated output contains no term from the private-only vocabulary | `tests/test_redaction.py` against a hashed vocabulary file kept outside the repository (`ATLAS_PRIVATE_VOCAB`); reports a skip when the file is absent |
| Page is usable at 1440 px and 390 px in light and dark, with no horizontal body scroll at 390 px | Chromium screenshots of `out/site/index.html` |

### Non-goals

- No change to diagram content, sidecar facts, or the evidence fixture's meaning.
- No live discovery, no new runtime dependency, no Mermaid upgrade.
- Converting every flowchart lands only after the owner approves the proof diagram.

### Pinned inputs

- Space Grotesk and JetBrains Mono latin subsets, the existing local artifacts, SIL OFL 1.1 (`vendor/fonts/manifest.yaml`).
