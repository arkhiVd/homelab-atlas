"""Safe verification and rendering primitives for Homelab Atlas."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import yaml

ALLOWED_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("docker", "ps"),
    ("docker", "network", "ls"),
    ("docker", "network", "inspect"),
    ("systemctl", "list-units"),
    ("systemctl", "list-timers"),
    ("ss",),
)
FORBIDDEN_WORDS = frozenset(
    {
        "apply",
        "compose",
        "create",
        "destroy",
        "disable",
        "down",
        "enable",
        "exec",
        "kill",
        "prune",
        "reload",
        "restart",
        "rm",
        "run",
        "start",
        "stop",
        "up",
    }
)
SHELL_METACHARS = re.compile(r"[;&|`$><\n\\]")
VALID_KINDS = frozenset(
    {"container", "network", "unit", "timer", "host", "external", "volume", "concept"}
)
CHECKED_KINDS = frozenset({"container", "network", "unit", "timer"})


class SafetyError(RuntimeError):
    """Raised when a command or output path crosses a safety boundary."""


def validate_command(argv: Sequence[str]) -> None:
    """Refuse every command outside the exact read-only prefix allowlist."""
    if not argv or not any(tuple(argv[: len(prefix)]) == prefix for prefix in ALLOWED_COMMANDS):
        raise SafetyError(f"command is not allowlisted: {list(argv)!r}")
    if argv[0] == "ss" and tuple(argv) not in {("ss",), ("ss", "-tln")}:
        raise SafetyError(f"ss arguments are not allowlisted: {list(argv)!r}")
    for token in argv:
        if SHELL_METACHARS.search(token):
            raise SafetyError(f"shell metacharacter refused in argument: {token!r}")
        words = set(re.split(r"[^a-z-]+", token.lower()))
        if words & FORBIDDEN_WORDS:
            raise SafetyError(f"destructive command word refused: {token!r}")


def run_read_only(argv: Sequence[str]) -> str:
    validate_command(argv)
    result = subprocess.run(
        list(argv), shell=False, text=True, capture_output=True, timeout=20, check=False
    )
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(argv)}\n{result.stderr.strip()}"
        )
    return result.stdout


@dataclass(frozen=True)
class Inventory:
    containers: dict[str, dict]
    networks: dict[str, dict]
    units: set[str]
    timers: set[str]

    @classmethod
    def from_fixture(cls, path: Path) -> "Inventory":
        data = json.loads(path.read_text())
        required = {"containers", "networks", "units", "timers"}
        if set(data) != required:
            raise ValueError(f"fixture keys must be exactly {sorted(required)}")
        return cls(data["containers"], data["networks"], set(data["units"]), set(data["timers"]))


def discover_live(runner=run_read_only) -> Inventory:
    """Read a Linux host through the guarded command boundary.

    This function never writes and the CLI calls it only after an explicit
    ``--live`` flag. Operators should narrow unit scope for their own host.
    """
    containers: dict[str, dict] = {}
    output = runner(["docker", "ps", "--format", "{{json .}}"])
    for line in output.splitlines():
        row = json.loads(line)
        ports = [part.strip() for part in row.get("Ports", "").split(",") if "->" in part]
        containers[row["Names"]] = {"image": row.get("Image", ""), "ports": ports}

    networks: dict[str, dict] = {}
    names = runner(["docker", "network", "ls", "--format", "{{.Name}}"]).splitlines()
    for name in filter(None, map(str.strip, names)):
        raw = runner(["docker", "network", "inspect", name, "--format", "{{json .IPAM.Config}}"])
        configs = json.loads(raw or "[]")
        subnet = configs[0].get("Subnet") if configs else None
        networks[name] = {"subnet": subnet}

    units = _names_ending(
        runner(["systemctl", "list-units", "--type=service", "--all", "--no-legend"]), ".service"
    )
    timers = _names_ending(runner(["systemctl", "list-timers", "--all", "--no-legend"]), ".timer")
    return Inventory(containers, networks, units, timers)


def _names_ending(output: str, suffix: str) -> set[str]:
    return {
        token for line in output.splitlines() for token in line.split() if token.endswith(suffix)
    }


def load_sidecars(meta_dir: Path) -> tuple[list[dict], list[str]]:
    nodes: list[dict] = []
    findings: list[str] = []
    for path in sorted(meta_dir.glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as exc:
            findings.append(f"{path.name}: invalid YAML: {exc}")
            continue
        if not isinstance(doc, dict) or not doc.get("id") or not doc.get("title"):
            findings.append(f"{path.name}: requires id and title")
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(doc["id"])):
            findings.append(
                f"{path.name}: id must contain only lowercase letters, digits, and hyphens"
            )
            continue
        raw_nodes = doc.get("nodes", [])
        if not isinstance(raw_nodes, list):
            findings.append(f"{path.name}: nodes must be a list")
            continue
        for raw in raw_nodes:
            if not isinstance(raw, dict):
                findings.append(f"{path.name}: node must be a mapping")
                continue
            node = dict(raw, _file=path.name)
            if node.get("kind") not in VALID_KINDS:
                findings.append(f"{path.name}: invalid kind for {node.get('id')!r}")
            if not node.get("id"):
                findings.append(f"{path.name}: node missing id")
            if node.get("kind") in CHECKED_KINDS and not node.get("name"):
                findings.append(f"{path.name}: checked node {node.get('id')!r} missing name")
            nodes.append(node)
    return nodes, findings


def compare(nodes: list[dict], inventory: Inventory) -> list[str]:
    live = {
        "container": set(inventory.containers),
        "network": set(inventory.networks),
        "unit": inventory.units,
        "timer": inventory.timers,
    }
    documented = {kind: set() for kind in CHECKED_KINDS}
    findings: list[str] = []
    for node in nodes:
        kind, name = node.get("kind"), node.get("name")
        if kind not in CHECKED_KINDS or not name:
            continue
        documented[kind].add(name)
        if name not in live[kind]:
            findings.append(f"STALE {kind.upper()}: {name} ({node['_file']})")
        if kind == "container" and name in inventory.containers and "ports" in node:
            actual = set(inventory.containers[name].get("ports", []))
            declared = set(node.get("ports", []))
            if actual != declared:
                findings.append(
                    f"PORT MISMATCH: {name}: declared {sorted(declared)}, actual {sorted(actual)}"
                )
        if kind == "network" and name in inventory.networks and "subnet" in node:
            actual_subnet = inventory.networks[name].get("subnet")
            if node["subnet"] != actual_subnet:
                findings.append(
                    f"SUBNET MISMATCH: {name}: declared {node['subnet']}, actual {actual_subnet}"
                )
    for kind in sorted(CHECKED_KINDS):
        for name in sorted(live[kind] - documented[kind]):
            findings.append(f"UNDOCUMENTED {kind.upper()}: {name}")
    return findings


def check_diagram_nodes(src_dir: Path, meta_dir: Path) -> list[str]:
    """Require every sidecar node ID to appear in its Mermaid source."""
    findings: list[str] = []
    for path in sorted(meta_dir.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text()) or {}
        diagram_id = str(doc.get("id", ""))
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", diagram_id):
            continue
        source = src_dir / f"{diagram_id}.mmd"
        if not source.exists():
            findings.append(f"{path.name}: missing diagram {source.name}")
            continue
        text = source.read_text()
        declared = set(re.findall(r"\b([A-Za-z][A-Za-z0-9_]*)\s*[\[({]", text))
        declared.update(re.findall(r"^\s*subgraph\s+([A-Za-z][A-Za-z0-9_]*)\b", text, re.M))
        for node in doc.get("nodes", []):
            node_id = node.get("id") if isinstance(node, dict) else None
            if node_id and node_id not in declared:
                findings.append(f"{path.name}: node {node_id!r} is absent from {source.name}")
    return findings


def lint_mermaid(src_dir: Path) -> list[str]:
    palette = set(re.findall(r"^classDef\s+(\w+)\s", (src_dir / "style.md").read_text(), re.M))
    findings: list[str] = []
    for path in sorted(src_dir.glob("*.mmd")):
        text = path.read_text()
        header = next(
            (
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.lstrip().startswith("%%")
            ),
            "",
        )
        if not re.fullmatch(r"flowchart\s+(LR|RL|TD|TB|BT)|sequenceDiagram", header):
            findings.append(f"{path.name}: unsupported diagram header {header!r}")
        depth = 0
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("subgraph ") or re.match(
                r"(alt|opt|loop|par|critical|break|rect)\b", stripped
            ):
                depth += 1
            elif stripped == "end":
                depth -= 1
            match = re.match(r"class\s+[\w,\s]+\s+(\w+)\s*$", stripped)
            if match and match.group(1) not in palette:
                findings.append(f"{path.name}: unknown class {match.group(1)!r}")
        if depth:
            findings.append(f"{path.name}: unbalanced block depth {depth}")
    return findings


def safe_output_path(repo: Path, path: Path) -> Path:
    """Allow writes only below this repository's generated out directory."""
    root_path = repo.resolve() / "out"
    if root_path.is_symlink():
        raise SafetyError(f"output root may not be a symlink: {root_path}")
    root = root_path.resolve()
    resolved = path.resolve()
    if resolved == root or root not in resolved.parents:
        raise SafetyError(f"output path is outside {root}: {resolved}")
    if "sync-conflict" in resolved.name or ".bak" in resolved.name:
        raise SafetyError(f"protected output name: {resolved.name}")
    return resolved
