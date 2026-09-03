from pathlib import Path

from atlas.cli import render_page, verify
from atlas.core import Inventory, check_diagram_nodes, compare, lint_mermaid, load_sidecars

REPO = Path(__file__).resolve().parents[1]


def demo():
    return Inventory.from_fixture(REPO / "fixtures/demo/inventory.json")


def test_demo_sidecars_match_fixture():
    nodes, errors = load_sidecars(REPO / "src/meta")
    assert errors == []
    assert compare(nodes, demo()) == []


def test_undocumented_live_object_fails():
    inventory = demo()
    inventory.containers["surprise-admin"] = {"ports": []}
    nodes, _ = load_sidecars(REPO / "src/meta")
    assert "UNDOCUMENTED CONTAINER: surprise-admin" in compare(nodes, inventory)


def test_stale_node_and_changed_port_fail():
    inventory = demo()
    del inventory.containers["demo-api"]
    inventory.containers["demo-dashboard"]["ports"] = ["127.0.0.1:9999->3000/tcp"]
    nodes, _ = load_sidecars(REPO / "src/meta")
    findings = compare(nodes, inventory)
    assert any(item.startswith("STALE CONTAINER: demo-api") for item in findings)
    assert any(item.startswith("PORT MISMATCH: demo-dashboard") for item in findings)


def test_changed_subnet_fails():
    inventory = demo()
    inventory.networks["demo_backend"]["subnet"] = "172.30.99.0/24"
    nodes, _ = load_sidecars(REPO / "src/meta")
    assert any(
        item.startswith("SUBNET MISMATCH: demo_backend") for item in compare(nodes, inventory)
    )


def test_renderer_escapes_untrusted_metadata_and_source():
    page = render_page(
        [({"id": '" onmouseover="alert(1)', "title": "<script>x</script>"}, "A-->B<script>")]
    )
    assert "<script>x</script>" not in page
    assert "&lt;script&gt;x&lt;/script&gt;" in page
    assert "&quot; onmouseover=&quot;alert(1)" in page


def test_sidecar_nodes_must_appear_in_diagram(tmp_path: Path):
    src = tmp_path / "src"
    meta = src / "meta"
    meta.mkdir(parents=True)
    (src / "demo.mmd").write_text("flowchart LR\n  present[Present]\n")
    (meta / "demo.yaml").write_text(
        "id: demo\ntitle: Demo\nnodes:\n  - {id: missing, kind: concept}\n"
    )
    assert check_diagram_nodes(src, meta) == ["demo.yaml: node 'missing' is absent from demo.mmd"]


def test_external_matching_fixture_prints_pass(tmp_path: Path, capsys):
    fixture = tmp_path / "inventory.json"
    fixture.write_text((REPO / "fixtures/demo/inventory.json").read_text())
    assert verify(fixture) == 0
    assert str(fixture) in capsys.readouterr().out


def test_mermaid_portable_subset_lints():
    assert lint_mermaid(REPO / "src") == []
    assert check_diagram_nodes(REPO / "src", REPO / "src/meta") == []
