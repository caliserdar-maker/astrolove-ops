#!/usr/bin/env python3
"""MAGAZA_METINLERI.md taslaklarini cevrimdisi PASS/FAIL denetler."""

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILE = ROOT / "docs" / "MAGAZA_METINLERI.md"
SECTIONS = (
    "Shop title",
    "Announcement",
    "About story",
    "Sale message",
    "Digital order message",
    "Personalized order message",
)
FORBIDDEN = (
    ("OBA-free", re.compile(r"\bOBA[\s-]*free\b", re.I)),
    ("bright white", re.compile(r"\bbright\s+white\b", re.I)),
    ("lifespan claim", re.compile(r"\b\d+\s*(?:-|to)\s*\d+\s*years?\b", re.I)),
    ("12-colour", re.compile(r"\b12[\s-]*colou?r\b", re.I)),
)


def parse(text):
    """Return heading to fenced text mapping; reject missing or duplicate drafts."""
    found = {}
    pattern = re.compile(r"^## (.+?)\n\n```text\n(.*?)\n```$", re.M | re.S)
    for heading, value in pattern.findall(text):
        if heading in found:
            raise ValueError(f"duplicate section: {heading}")
        found[heading] = value
    missing = [heading for heading in SECTIONS if heading not in found]
    if missing:
        raise ValueError("missing section: " + ", ".join(missing))
    return {heading: found[heading] for heading in SECTIONS}


def audit(drafts):
    """Return one PASS/FAIL result for every required shop text."""
    results = []
    for heading in SECTIONS:
        text = drafts.get(heading, "")
        errors = []
        if not text.strip():
            errors.append("text is empty")
        if "—" in text or "–" in text:
            errors.append("long or medium dash")
        for label, pattern in FORBIDDEN:
            if pattern.search(text):
                errors.append(f"forbidden phrase: {label}")
        if heading == "Shop title" and len(text) > 55:
            errors.append(f"shop title exceeds 55 characters ({len(text)})")
        if heading != "Shop title":
            if not re.search(r"\bwe\b|\bour\b|\bus\b", text, re.I):
                errors.append("we voice is missing")
            if "Lena & Serdar / AstroLoveArt" not in text:
                errors.append("signature is missing")
        results.append((heading, "FAIL" if errors else "PASS", errors))

    corpus = "\n".join(drafts.values())
    shared = []
    for phrase in ("zodiac couple art", "personalized", "compatibility"):
        if phrase not in corpus.lower():
            shared.append(f"SEO phrase is missing: {phrase}")
    if not re.search(r"every (?:product|order) is personalized", corpus, re.I):
        shared.append("all products personalized statement is missing")
    if not re.search(r"manually check every file", corpus, re.I):
        shared.append("manual file review statement is missing")

    digital = drafts.get("Digital order message", "")
    if "not an instant download" not in digital.lower():
        shared.append("digital no instant download statement is missing")
    if "order specific delivery" not in digital.lower():
        shared.append("digital order specific delivery statement is missing")

    physical = "\n".join((drafts.get("About story", ""), drafts.get("Personalized order message", "")))
    if "made to order" not in physical.lower() or "produced by" not in physical.lower() or "Prodigi" not in physical:
        shared.append("POD made to order and Prodigi production statement is missing")
    results.append(("Shared requirements", "FAIL" if shared else "PASS", shared))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path, default=DEFAULT_FILE)
    args = parser.parse_args(argv)
    try:
        results = audit(parse(args.file.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 2
    for heading, status, errors in results:
        detail = "" if not errors else ": " + "; ".join(errors)
        print(f"{heading}: {status}{detail}")
    return 1 if any(status == "FAIL" for _, status, _ in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
