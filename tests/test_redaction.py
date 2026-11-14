import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


redaction = load("redaction_under_test", ROOT / "bin" / "redaction.py")
renderer = load("renderer_for_redaction", ROOT / "bin" / "render-artifact")


@pytest.fixture(scope="module")
def pages():
    inner = renderer.build(renderer.load(), renderer.load_fixture_evidence())
    return {"fragment": inner, "standalone": renderer.standalone(inner)}


def test_generic_markers_are_detected():
    sample = "10.1.2.3 192.168.4.5 100.64.0.9 host.tailabc123.ts.net /home/someone a@b.example"
    found = redaction.generic_findings(sample)
    assert len(found) == 6
    assert redaction.generic_findings("127.0.0.1 192.0.2.10 198.51.100.7 203.0.113.9 :8080") == []


def test_output_has_no_generic_private_markers(pages):
    for name, page in pages.items():
        assert redaction.generic_findings(redaction.visible_text(page)) == [], name


def test_vocabulary_hashes_match_terms_and_their_parts():
    salt = "test-salt"
    hashes = {redaction.digest(salt, "secretbox"), redaction.digest(salt, "lab-node-7")}
    page = '<p data-node="x_secretbox">see lab-node-7.internal</p>'
    assert redaction.private_hits(page, salt, hashes) == ["lab-node-7", "secretbox"]


def test_output_has_no_private_only_vocabulary(pages):
    path = redaction.vocab_path()
    if not path.is_file():
        pytest.skip(
            "private vocabulary not available; run bin/derive-private-vocab or set "
            "ATLAS_PRIVATE_VOCAB to check generated output against it"
        )
    salt, hashes = redaction.load_vocab(path)
    assert hashes, "private vocabulary file is empty"
    for name, page in pages.items():
        assert redaction.private_hits(page, salt, hashes) == [], name
