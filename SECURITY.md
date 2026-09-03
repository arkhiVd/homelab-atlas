# Security policy

## Supported versions

Security fixes target the latest commit on the default branch.

## Reporting a vulnerability

Use GitHub private vulnerability reporting. Do not open a public issue if a finding could permit command execution, shell injection, writes outside an owned output directory, or disclosure of host inventory.

Include a minimal reproduction built from synthetic fixtures. Do not include credentials, private addresses, hostnames, command output, logs, or screenshots from a real system.

## Trust boundaries

Inventory data is untrusted input. A sidecar or fixture may contain strings intended to escape HTML, alter a command, or traverse a path.

- Commands pass through an exact read-only prefix allowlist.
- `subprocess.run` always receives an argument list and `shell=False`.
- Shell metacharacters and destructive words are refused before execution.
- The renderer resolves its target and permits writes only below this repository's `out/` directory.
- The public CLI uses synthetic fixtures and runs no discovery commands.
- HTML rendering escapes titles, identifiers, and Mermaid source.

Do not add `.env` readers, unrestricted command templates, `shell=True`, broad output roots, or automatic vault writes. A real deployment should use a dedicated low-privilege account and grant only the read access its discovery commands need.

## Privacy

Never commit real inventory snapshots. Container names, internal DNS names, private IP addresses, private account identifiers, mount paths, unit names, labels, image references, and timestamps can identify a private environment even when they contain no secret. Replace them with coherent synthetic data before opening a pull request.
