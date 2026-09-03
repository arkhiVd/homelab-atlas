# Contributing

Changes are welcome when they preserve the separation between authored diagrams, machine-checkable facts, and discovered inventory.

## Before opening a pull request

1. Create a focused branch.
2. Add or update a negative test before changing command validation or path guards.
3. Use synthetic fixtures. Never capture a real host into the repository.
4. Run `PATH="$PWD/.venv/bin:$PATH" bin/validate`.
5. Review generated `out/atlas.html` in a browser when diagram or renderer output changes.
6. Update `SPEC.md` when behavior or security assumptions change.

Pin GitHub Actions by full commit SHA. Do not submit credentials, `.env` files, real inventory, logs, private diagrams, vault content, or screenshots from a production system.

Changes that add live discovery must document every command, prove it is read-only, keep `shell=False`, and add refusal tests for destructive subcommands and shell injection. Changes that add an output destination must enforce its resolved path in code and test path traversal.
