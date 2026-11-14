import importlib.util
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
SVG = "{http://www.w3.org/2000/svg}"

spec = importlib.util.spec_from_file_location("atlas_draft", ROOT / "bin" / "atlas_draft.py")
draft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draft)


def laid_out():
    """Every sidecar with a layout block, with its source text and volume ids."""
    found = []
    for path in sorted((ROOT / "src" / "meta").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        if doc.get("layout"):
            source = (ROOT / "src" / f"{doc['id']}.mmd").read_text()
            stores = {n["id"] for n in doc["nodes"] if n.get("kind") == "volume"}
            found.append(pytest.param(doc, source, stores, id=doc["id"]))
    return found


def words(text):
    return " ".join(text.split())


def test_proof_diagram_is_drafted():
    assert {"00-context", "02-ingress", "03-containers", "08-ai-plane"} <= {
        p.id for p in laid_out()
    }


@pytest.mark.parametrize(("doc", "source", "stores"), laid_out())
def test_every_node_edge_kind_label_and_group_survives(doc, source, stores):
    flow = draft.parse_flowchart(source)
    root = ET.fromstring(draft.draft(source, doc["layout"], doc["id"], "t", stores))
    nodes = {g.get("data-node"): g for g in root.iter(f"{SVG}g") if g.get("data-node")}
    assert set(nodes) == set(flow["nodes"])
    for node_id, node in flow["nodes"].items():
        shown = words(" ".join(t.text or "" for t in nodes[node_id].iter(f"{SVG}text")))
        assert shown == words(" ".join(node["lines"])), node_id
    drawn = Counter(
        (p.get("data-edge"), p.get("data-kind"))
        for p in root.iter(f"{SVG}path")
        if p.get("data-edge")
    )
    declared = Counter((f"{e['a']}>{e['b']}", e["kind"]) for e in flow["edges"])
    assert drawn == declared
    labels = Counter(
        (g.get("data-edge-label"), words(" ".join(t.text or "" for t in g.iter(f"{SVG}tspan"))))
        for g in root.iter(f"{SVG}g")
        if g.get("data-edge-label")
    )
    expected = Counter(
        (f"{e['a']}>{e['b']}", words(" ".join(e["label"]))) for e in flow["edges"] if e["label"]
    )
    assert labels == expected
    zones = {r.get("data-zone") for r in root.iter(f"{SVG}rect") if r.get("data-zone")}
    assert zones == {g["id"] for g in flow["groups"] if g["members"]}
    titles = Counter(t.get("data-zone-title") for t in root.iter(f"{SVG}text"))
    for group in flow["groups"]:
        shown = " ".join(
            t.text for t in root.iter(f"{SVG}text") if t.get("data-zone-title") == group["id"]
        )
        assert words(shown) == words(group["title"])
    # Nothing else: every text element belongs to a node, an edge label, or a zone title.
    loose = [
        t
        for t in root.iter(f"{SVG}text")
        if not t.get("data-zone-title") and t.get("class") not in {"ad-name", "ad-sub", None}
    ]
    assert loose == [] and titles


@pytest.mark.parametrize(("doc", "source", "stores"), laid_out())
def test_geometry_is_clean(doc, source, stores):
    assert draft.geometry_findings(draft.plan(source, doc["layout"], stores)) == []


@pytest.mark.parametrize(("doc", "source", "stores"), laid_out())
def test_output_is_byte_identical_and_inert(doc, source, stores):
    first = draft.draft(source, doc["layout"], doc["id"], "t", stores)
    assert first == draft.draft(source, doc["layout"], doc["id"], "t", stores)
    assert "<script" not in first and "foreignObject" not in first
    assert not re.search(r"<[^>]*\son\w+\s*=", first)
    assert "http://" not in first.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "https://" not in first


SOURCE = 'flowchart LR\n    a["A"]\n    b["B"]\n    c["C"]\n    a ==>|"go"| c\n'


def test_layout_must_place_every_node_and_only_real_nodes():
    with pytest.raises(draft.DraftError, match=r"missing \['c'\]"):
        draft.plan(SOURCE, {"nodes": {"a": [0, 0], "b": [1, 0]}})
    with pytest.raises(draft.DraftError, match=r"unknown \['z'\]"):
        draft.plan(SOURCE, {"nodes": {"a": [0, 0], "b": [1, 0], "c": [2, 0], "z": [3, 0]}})


def test_unsupported_syntax_fails_instead_of_dropping_edges():
    with pytest.raises(draft.DraftError, match="unsupported edge syntax"):
        draft.parse_flowchart('flowchart LR\n    a["A"]\n    b["B"]\n    a & b --> a\n')
    with pytest.raises(draft.DraftError, match="never closed"):
        draft.parse_flowchart('flowchart TB\n    subgraph g["G"]\n    a["A"]\n')


def test_invisible_layout_links_are_not_drawn():
    flow = draft.parse_flowchart('flowchart TB\n    a["A"]\n    b["B"]\n    a ~~~ b\n')
    assert flow["edges"] == []


def test_icons_must_be_verified_assets():
    source = "flowchart LR\n    a[\"<img src='./assets/x/evil.svg'/><br/>A\"]\n"
    with pytest.raises(draft.DraftError, match="not a verified asset"):
        draft.plan(source, {"nodes": {"a": [0, 0]}}, icons={"./assets/x/ok.svg"})


def test_geometry_check_catches_a_line_through_a_box():
    layout = {
        "nodes": {"a": [0, 0], "b": [1, 0], "c": [2, 0]},
        "edges": [{"from": "a", "to": "c", "via": [[None, None]]}],
    }
    findings = draft.geometry_findings(draft.plan(SOURCE, layout))
    assert any(f.startswith("EDGE THROUGH NODE: a>c crosses b") for f in findings)


def test_geometry_check_catches_crowded_nodes_and_overflowing_text():
    source = 'flowchart LR\n    a["A very long node name that cannot fit"]\n    b["B"]\n'
    findings = draft.geometry_findings(draft.plan(source, {"nodes": {"a": [0, 0], "b": [0, 0.2]}}))
    assert "NODES TOO CLOSE: a and b" in findings


def test_router_goes_around_a_box_in_the_way():
    sheet = draft.plan(SOURCE, {"nodes": {"a": [0, 0], "b": [1, 0], "c": [2, 0]}})
    assert draft.geometry_findings(sheet) == []
