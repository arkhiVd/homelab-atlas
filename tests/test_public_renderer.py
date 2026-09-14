import hashlib
import importlib.machinery
import importlib.util
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_loader(
    "public_renderer",
    importlib.machinery.SourceFileLoader("public_renderer", str(ROOT / "bin" / "render-artifact")),
)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


def test_renderer_has_no_host_command_modules_or_private_paths():
    source = (ROOT / "bin" / "render-artifact").read_text()
    for forbidden in (
        "subprocess",
        "socket",
        "bin/verify",
        "/opt/",
        "/home/",
        "import docker",
        "systemctl",
        "tailscale status",
    ):
        assert forbidden not in source


def test_fixture_render_is_deterministic_and_stays_under_out():
    out = ROOT / "out" / "test-render"
    shutil.rmtree(out, ignore_errors=True)
    try:
        with patch.object(renderer, "OUT", out):
            assert renderer.main() == 0
            first = (out / "site" / "index.html").read_bytes()
            assert renderer.main() == 0
            assert (out / "site" / "index.html").read_bytes() == first
        assert (out / "atlas.html").is_file()
        assert any((out / "site" / "assets").rglob("*.svg"))
        assert (out / "site" / "fonts" / "space-grotesk-latin.woff2").is_file()
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_assets_require_hashed_inert_local_svg():
    with TemporaryDirectory() as temporary:
        asset_root = Path(temporary) / "assets" / "demo"
        asset_root.mkdir(parents=True)
        icon = asset_root / "safe.svg"
        icon.write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>')
        manifest = {
            "assets": [
                {
                    "id": "safe",
                    "file": "safe.svg",
                    "sha256": hashlib.sha256(icon.read_bytes()).hexdigest(),
                    "source_url": "local-authored: test",
                    "revision": "local fallback v1",
                    "license": "CC0-1.0",
                    "attribution": "test",
                    "trademark": "Generic",
                    "fallback": "Safe",
                }
            ]
        }
        (asset_root / "manifest.yaml").write_text(renderer.yaml.safe_dump(manifest))
        with patch.object(renderer, "ASSETS_ROOT", asset_root.parent):
            assert renderer.load_identity_assets()["safe"]["url"] == "./assets/demo/safe.svg"
        icon.write_text("<svg><script>bad()</script></svg>")
        with (
            patch.object(renderer, "ASSETS_ROOT", asset_root.parent),
            pytest.raises(ValueError, match="checksum mismatch|unsafe SVG"),
        ):
            renderer.load_identity_assets()


def test_fixture_is_committed_and_has_required_shape():
    evidence = json.loads((ROOT / "fixtures" / "demo" / "evidence.json").read_text())
    assert renderer.load_fixture_evidence() == evidence
    assert {"captured_at", "host", "source_commit", "stats"} <= evidence.keys()


def test_page_is_an_architecture_guide_without_snapshot_or_catalog_cards():
    html = renderer.build(renderer.load(), renderer.load_fixture_evidence())
    assert "A self-hosted environment organized around" in html
    assert "Evidence snapshot" not in html
    assert "Service catalog" not in html
    assert "observed live" not in html
    assert "https://github.com/arkhiVd/agent-workbench" in html
    assert "https://github.com/arkhiVd/invest-pipeline" in html
    assert "https://github.com/arkhiVd/librarian" in html
    assert '<section class="atlas-notes" aria-label="Notes">' in html
    assert "<summary>Notes</summary>" not in html
