"""Command-line interface for fixture verification and safe rendering."""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

import yaml

from atlas.core import (
    Inventory,
    check_diagram_nodes,
    compare,
    discover_live,
    lint_mermaid,
    load_sidecars,
    safe_output_path,
)

REPO = Path(__file__).resolve().parent.parent


def verify(fixture: Path, live: bool = False) -> int:
    nodes, findings = load_sidecars(REPO / "src" / "meta")
    findings += lint_mermaid(REPO / "src")
    findings += check_diagram_nodes(REPO / "src", REPO / "src" / "meta")
    if live:
        print(
            "WARNING: live findings may expose private host identifiers; do not publish the output.",
            file=sys.stderr,
        )
    inventory = discover_live() if live else Inventory.from_fixture(fixture)
    findings += compare(nodes, inventory)
    if findings:
        print(f"FAIL: {len(findings)} finding(s)")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    if live:
        source = "explicit live discovery"
    else:
        try:
            source = str(fixture.relative_to(REPO))
        except ValueError:
            source = str(fixture)
    print(f"PASS: {len(nodes)} sidecar nodes match {source}")
    return 0


def render_page(docs: list[tuple[dict, str]]) -> str:
    sections = []
    for meta, source in docs:
        sections.append(
            f'<section id="{html.escape(meta["id"], quote=True)}">'
            f"<h2>{html.escape(meta['title'])}</h2>"
            f'<pre class="mermaid">{html.escape(source)}</pre></section>'
        )
    body = "\n".join(sections)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Homelab Atlas demo</title><style>body{{font:16px system-ui;max-width:80rem;margin:auto;padding:2rem;background:#f8fafc;color:#172033}}section{{background:white;border:1px solid #cbd5e1;margin:2rem 0;padding:1.5rem;overflow:auto}}code{{font-family:monospace}}</style></head>
<body><h1>Homelab Atlas demo</h1><p>This artifact contains synthetic infrastructure only. Mermaid source remains visible when JavaScript is unavailable.</p>{body}
<script src="mermaid.min.js"></script><script>mermaid.initialize({{startOnLoad:true,securityLevel:"strict"}});</script></body></html>\n"""


def render(output: Path) -> int:
    target = safe_output_path(REPO, output)
    docs = []
    src_root = (REPO / "src").resolve()
    for sidecar in sorted((src_root / "meta").glob("*.yaml")):
        meta = yaml.safe_load(sidecar.read_text())
        diagram_id = str(meta["id"])
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", diagram_id):
            raise ValueError(f"unsafe diagram id in {sidecar.name}: {diagram_id!r}")
        source = (src_root / f"{diagram_id}.mmd").resolve()
        if src_root not in source.parents:
            raise ValueError(f"diagram source escaped src: {source}")
        docs.append((meta, source.read_text()))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_page(docs))
    runtime = safe_output_path(REPO, target.parent / "mermaid.min.js")
    runtime.write_bytes((REPO / "vendor" / "mermaid.min.js").read_bytes())
    print(f"wrote {target.relative_to(REPO)} ({len(docs)} diagrams)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("verify")
    check.add_argument(
        "--fixture", type=Path, default=REPO / "fixtures" / "demo" / "inventory.json"
    )
    check.add_argument(
        "--live", action="store_true", help="explicitly inspect local Docker and systemd state"
    )
    build = sub.add_parser("render")
    build.add_argument("--output", type=Path, default=REPO / "out" / "atlas.html")
    args = parser.parse_args()
    if args.command == "verify":
        return verify(args.fixture.resolve(), args.live)
    return render(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
