# Homelab Atlas specification

## Problem

Hand-authored architecture diagrams explain intent but cannot detect their own drift. Generated topology maps detect facts but often communicate poorly. Homelab Atlas keeps authored Mermaid views and stores verifiable identifiers in adjacent YAML sidecars.

## Users

- Homelab operators who need diagrams that fail when system facts change.
- Contributors evaluating command safety and documentation-as-code patterns.
- Portfolio reviewers who need a runnable demonstration without private infrastructure.

## Required behavior

- Keep Mermaid source as the only hand-edited diagram representation.
- Map real object types to identifiers in YAML sidecars.
- Compare sidecars with an inventory and fail for undocumented objects, stale nodes, port changes, and subnet changes.
- Use synthetic fixtures for every public test and example.
- Validate live-read commands against fixed prefixes and reject destructive words and shell syntax.
- Invoke commands without a shell.
- Write rendered output only under the repository-owned `out/` directory.
- Produce the same artifact bytes when rendered twice from unchanged inputs.

## Security and privacy

The repository must contain no production inventory, private addresses, personal paths, account identifiers, secrets, logs, vault content, or incident records. The public CLI must not inspect the reader's host by default. Tests must prove refusal of destructive Docker and systemd commands, shell injection, writes outside `out/`, and path traversal.

## Pinned versions

| Tool | Version |
|---|---|
| Python | 3.12 |
| PyYAML | 6.0.2 |
| pytest | 9.0.3 |
| Ruff | 0.11.2 |
| Mermaid runtime | 11.16.1, vendored for offline rendering |
| Mermaid syntax | `flowchart`, `sequenceDiagram`, `subgraph`, `classDef`, `class` |

## Cost and limits

Local and CI validation use no cloud resources and create no services. The demo reads repository files and writes only generated HTML below `out/`.

## Non-goals

- Shipping an inventory collector tailored to every Linux distribution or container runtime.
- Automatically laying out diagrams.
- Monitoring, alerting, remediation, deployment, or service control.
- Publishing a sanitized copy of any private topology.

## Acceptance criteria

- `bin/verify` passes against `fixtures/demo/inventory.json`.
- Mutating the fixture to add or remove an object makes verification fail.
- Tests cover destructive commands and shell injection.
- Tests cover output path traversal and protected names.
- `bin/render` writes `out/atlas.html` and a second run has the same SHA-256 digest.
- `bin/validate` runs the complete local gate with one command.
- CI runs the local gate and Gitleaks. CodeQL analyzes Python.
- All diagrams and screenshots contain synthetic data only.
- Independent reviewers find no actionable security, privacy, shell safety, CI, or documentation issues.
- Publication remains blocked until the owner explicitly approves it.
