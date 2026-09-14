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
        font = out / "site" / "fonts" / "instrument-sans-var.woff2"
        assert font.is_file()
        assert hashlib.sha256(font.read_bytes()).hexdigest() == (
            "2ee17598a98d8a59e4df8152d015bec9ab8e4d5672cc0ab42bef806b568e3971"
        )
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


def test_page_is_an_architecture_guide_with_fixture_backed_catalog_content():
    html = renderer.build(renderer.load(), renderer.load_fixture_evidence())
    assert "A self-hosted environment organized around" in html
    assert "Evidence snapshot" in html
    assert "Service catalog" in html
    assert "fixture evidence" in html
    assert "https://github.com/arkhiVd/agent-workbench" in html
    assert "https://github.com/arkhiVd/invest-pipeline" in html
    assert "https://github.com/arkhiVd/librarian" in html
    assert '<section class="atlas-notes" aria-label="Notes">' in html
    assert "<summary>Notes</summary>" not in html


def test_standalone_uses_local_assets_and_recovers_from_loading_failures():
    page = renderer.standalone(renderer.build(renderer.load(), renderer.load_fixture_evidence()))
    assert 'src="./mermaid.min.js"' in page
    assert "loading homelab atlas…" in page
    assert "Retry" in page
    assert "Show text" in page
    assert "45000" in page
    assert "<noscript>" in page
    assert "localStorage" not in page
    assert "atlas-theme" not in page
    assert "linux-mint" not in page
    assert "atlas-participant M debian" in page
    assert "image.setAttribute('href',assets[id])" in page
    assert "Instrument Sans" in page
    assert "Space Grotesk" not in page
    assert "space-grotesk" not in page


def test_participant_decorations_only_reference_manifest_backed_assets():
    page = renderer.standalone(renderer.build(renderer.load(), renderer.load_fixture_evidence()))
    assert '"T":"overlay"' not in page
    assert "14-runbooks-overlay.svg" not in page
    assert "&quot;M&quot;:&quot;./assets/14-runbooks/14-runbooks-debian.svg&quot;" in page
    assert "image.onerror=resolve" in page


def test_dashboard_catalog_stats_filters_and_service_interactions_are_preserved():
    html = renderer.build(renderer.load(), renderer.load_fixture_evidence())
    for marker in (
        'aria-label="Evidence snapshot"',
        'aria-label="Evidence statistics"',
        'id="atlas-catalog"',
        'data-filter="lifecycle"',
        'data-filter="capability"',
        'class="atlas-service"',
        "data-inspect=",
        'id="atlas-inspector"',
        "function apply()",
        "data-layer",
        "data-zoom-action",
    ):
        assert marker in html


def test_loading_retry_rearms_timeout_and_show_text_replaces_diagrams():
    page = renderer.standalone(renderer.build(renderer.load(), renderer.load_fixture_evidence()))
    assert (
        "function arm(generation){clearTimeout(timer);timer=setTimeout(function(){fail(generation)},45000)}"
        in page
    )
    assert "var generation=++attempt;settled=false;arm(generation)" in page
    assert "function showText()" in page
    assert "sheet.replaceChildren(pre)" in page
    assert "data-atlas-source=" in page


def test_loading_attempt_token_ignores_stale_retry_callbacks_and_timeouts():
    page = renderer.standalone(renderer.build(renderer.load(), renderer.load_fixture_evidence()))
    assert "timer,settled=false,attempt=0" in page
    assert "function current(generation){return generation===attempt}" in page
    assert "if(!current(generation))return" in page
    assert "if(!current(generation)||settled)return" in page
    assert "reveal(generation)" in page
    assert "fail(generation)" in page


def test_loading_waits_for_mermaid_decoration_assets_not_lazy_screenshots():
    page = renderer.standalone(renderer.build(renderer.load(), renderer.load_fixture_evidence()))
    assert "function decorationAssets()" in page
    assert "querySelectorAll('.atlas-sheet svg image[href]')" in page
    assert "document.images" not in page
    assert "var image=new Image()" in page
    assert 'loading="lazy"' in renderer.build(
        [
            {
                "id": "demo",
                "screenshots": [
                    {"src": "./screenshots/demo.svg", "alt": "demo", "caption": "demo"}
                ],
                "bodies": [],
                "notes": [],
                "anchor": "atlas-diagram-demo",
                "layer": "A",
                "stack_key": "foundations",
                "stack": "Foundations",
                "title": "demo",
                "summary": "demo",
                "services": [],
            }
        ],
        renderer.load_fixture_evidence(),
    )


def test_generated_css_has_valid_hyphenated_properties_and_balanced_media_rule():
    html = renderer.build(renderer.load(), renderer.load_fixture_evidence())
    for malformed in ("grid -", "margin -", "font -", "border -", "template -", "{{{{"):
        assert malformed not in html
    assert "grid-column:1/-1" in html
    assert "@media(max-width:680px){#atlas-root .atlas-service" in html


def test_automation_user_manager_uses_debian_artwork_with_accurate_manifest():
    asset = ROOT / "src" / "assets" / "11-automation" / "11-automation-x-user-manager.svg"
    manifest = renderer.yaml.safe_load(
        (ROOT / "src" / "assets" / "11-automation" / "manifest.yaml").read_text()
    )
    entry = next(
        item for item in manifest["assets"] if item["id"] == "11-automation-x_user_manager"
    )
    assert entry["sha256"] == hashlib.sha256(asset.read_bytes()).hexdigest()
    assert entry["fallback"] == "Debian user manager"
    assert "#a80030" in asset.read_text()
    assert "#69b53f" not in asset.read_text()
