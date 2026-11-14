# Homelab Atlas contributor instructions

## Architecture

- `src/*.mmd` contains hand-authored Mermaid diagrams.
- `src/meta/*.yaml` contains machine-checkable node sidecars.
- `src/assets/*/manifest.yaml` records local, checksum-verified SVG assets.
- `fixtures/demo/evidence.json` is the deterministic dashboard evidence fixture.
- A sidecar `layout:` block places a flowchart's nodes on `[column, row]` cells; `bin/atlas_draft.py` then draws it as static, gutter-routed SVG. The `.mmd` file stays the source of nodes, edges, and labels. Flowcharts without `layout:` and sequence diagrams still use the vendored Mermaid runtime.
- `bin/render-artifact` generates the static dashboard below `out/`. A drafted diagram with geometry findings refuses to render.
- `bin/redaction.py` scans generated output for private markers. `bin/derive-private-vocab PRIVATE_ATLAS_DIR --dictionary /usr/share/dict/words` writes salted hashes of private-only terms outside the repository (default `~/.config/homelab-atlas/private-vocab.sha256`, or `ATLAS_PRIVATE_VOCAB`); the tests check output against it when present and report a skip when not.
- `vendor/fonts/` holds Roboto and Roboto Mono with their licenses and checksums.
- `out/` is generated. Never hand-edit it.

## Commands

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
PATH="$PWD/.venv/bin:$PATH bin/validate
```

## Boundaries

- Keep publication content free of personal identifiers, non-public addresses, account data, credentials, local machine paths, logs, and live host observations.
- The public renderer must use committed fixtures. It must not inspect the local machine, Docker, systemd, listeners, or network state.
- Never use `shell=True` or pass commands through a shell.
- Render only below this repository's `out/` directory.
- Never commit the private vocabulary, in clear text or hashed.
- Treat SVG assets as inert local files: verify checksums and reject scripts, event handlers, external URLs, and oversized files.
- Do not create a repository, push, tag, publish, or release without the owner's explicit approval.

## Validation

The full gate is `PATH="$PWD/.venv/bin:$PATH" bin/validate`. Diagram changes also require browser checks of `out/site/index.html` at 1440 px and 390 px in light and dark. Run the gate with the private vocabulary present before any publication.
