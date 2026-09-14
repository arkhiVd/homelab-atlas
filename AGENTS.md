# Homelab Atlas contributor instructions

## Architecture

- `src/*.mmd` contains hand-authored Mermaid diagrams.
- `src/meta/*.yaml` contains machine-checkable node sidecars.
- `src/assets/*/manifest.yaml` records local, checksum-verified SVG assets.
- `fixtures/demo/evidence.json` is the deterministic dashboard evidence fixture.
- `bin/render-artifact` generates the static dashboard below `out/`.
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
- Treat SVG assets as inert local files: verify checksums and reject scripts, event handlers, external URLs, and oversized files.
- Do not create a repository, push, tag, publish, or release without the owner's explicit approval.

## Validation

The full gate is `PATH="$PWD/.venv/bin:$PATH" bin/validate`. Diagram changes also require browser checks of `out/site/index.html` at desktop and mobile widths.
