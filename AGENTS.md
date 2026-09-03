# Homelab Atlas contributor instructions

## Architecture

- `src/*.mmd` contains hand-authored Mermaid diagrams.
- `src/meta/*.yaml` contains machine-checkable node identifiers.
- `fixtures/demo/inventory.json` is the only bundled inventory.
- `atlas/core.py` owns command and path safety boundaries.
- `out/` is generated. Never hand-edit it.

## Commands

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
PATH="$PWD/.venv/bin:$PATH" bin/validate
```

## Boundaries

- Use synthetic infrastructure only. Never commit real hostnames, private addresses, account names, mount paths, inventories, observations, logs, vault content, or secrets.
- Never use `shell=True` or pass a command through a shell.
- Live discovery additions must pass through `validate_command` and remain read-only.
- Keep the public CLI fixture-first. It must not inspect the local machine by default.
- Render only below this repository's `out/` directory.
- Add negative tests for destructive commands, injection strings, and path traversal.
- Do not create a repository, push, tag, publish, or release without the owner's explicit approval.

## Validation

The full gate is `PATH="$PWD/.venv/bin:$PATH" bin/validate`. Diagram changes also require a browser check of `out/atlas.html` and an updated synthetic screenshot.
