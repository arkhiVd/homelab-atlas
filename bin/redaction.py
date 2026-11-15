"""Redaction checks shared by the test suite and `bin/derive-private-vocab`.

The private-only vocabulary never enters this repository, not even as a hash list: a hash of a
short service name can be reversed by guessing. The vocabulary lives in a local file named by
`ATLAS_PRIVATE_VOCAB` (default `~/.config/homelab-atlas/private-vocab.sha256`), holding salted
SHA-256 digests of terms that appear in the private atlas sources and nowhere in this one.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
from pathlib import Path

DEFAULT_VOCAB = Path("~/.config/homelab-atlas/private-vocab.sha256")
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*[A-Za-z0-9]")
PART_RE = re.compile(r"[._:-]+")
DOT_RE = re.compile(r"[.:]+")
NUMBER_RE = re.compile(r"\d+")
ATTR_RE = re.compile(r'\s(?:data-[\w-]+|href|src|id|aria-label|alt|title)="([^"]*)"')
TAG_RE = re.compile(r"<[^>]*>")

# Markers that identify a private network or person, whatever the vocabulary says. Loopback and
# the RFC 5737 documentation ranges stay allowed.
GENERIC_MARKERS = {
    "private IPv4 address": re.compile(
        r"(?<![\d.])(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168|"
        r"100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7]))\.\d{1,3}\.\d{1,3}(?![\d.])"
    ),
    "overlay network domain": re.compile(r"\b[\w-]+\.ts\.net\b|\btail[0-9a-f]{4,}\b", re.I),
    "local home or service path": re.compile(r"(?:/home/|/Users/|/opt/|/root/)\w"),
    "email address": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]*[a-z]{2,}\b", re.I),
}


def generic_findings(text: str) -> list[str]:
    return sorted(
        f"{name}: {match}"
        for name, pattern in GENERIC_MARKERS.items()
        for match in set(pattern.findall(text))
    )


def terms(text: str) -> set[str]:
    """Lowercased tokens plus their dot, dash, colon, slash, and underscore separated parts."""
    found = set()
    for token in TOKEN_RE.findall(text):
        token = token.lower()
        found.add(token)
        found.update(part for part in PART_RE.split(token) if len(part) >= 3)
        found.update(part for part in DOT_RE.split(token) if len(part) >= 3)
    return found


def keep(term: str, dictionary: set[str]) -> bool:
    """Plain words in the system dictionary and short or numeric fragments are too common."""
    if NUMBER_RE.fullmatch(term):
        return len(term) >= 4
    if len(term) < 4:
        return False
    if term.isalpha() and term in dictionary:
        return False
    return True


def visible_text(page: str) -> str:
    """Text a reader can see or a crawler can index: element text and identifying attributes."""
    attributes = " ".join(html.unescape(value) for value in ATTR_RE.findall(page))
    return html.unescape(TAG_RE.sub(" ", page)) + " " + attributes


def digest(salt: str, term: str) -> str:
    return hashlib.sha256(f"{salt}\0{term}".encode()).hexdigest()


def vocab_path() -> Path:
    return Path(os.environ.get("ATLAS_PRIVATE_VOCAB") or DEFAULT_VOCAB).expanduser()


def load_vocab(path: Path) -> tuple[str, set[str]]:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    if not lines or not lines[0].startswith("salt "):
        raise ValueError(f"{path}: first line must be 'salt <hex>'")
    return lines[0].split(" ", 1)[1], {line for line in lines[1:] if not line.startswith("#")}


def private_hits(page: str, salt: str, hashes: set[str]) -> list[str]:
    return sorted(term for term in terms(visible_text(page)) if digest(salt, term) in hashes)
