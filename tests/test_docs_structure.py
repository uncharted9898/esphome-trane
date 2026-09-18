import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _markdown_files():
    yield ROOT / "README.md"
    yield from sorted(DOCS.rglob("*.md"))


def test_relative_markdown_links_resolve():
    missing = []
    for source in _markdown_files():
        text = source.read_text()
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip()
            if (
                not target
                or target.startswith("#")
                or target.startswith("http://")
                or target.startswith("https://")
                or target.startswith("mailto:")
            ):
                continue

            # Markdown destinations may contain an anchor. The path portion is
            # what needs to exist on disk.
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue

            resolved = (source.parent / target_path).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                missing.append((source.relative_to(ROOT), target, "outside repository"))
                continue

            if not resolved.exists():
                missing.append((source.relative_to(ROOT), target, "missing"))

    assert not missing, "Broken relative Markdown links: " + "; ".join(
        f"{src}: {target} ({reason})" for src, target, reason in missing
    )


def test_dated_target_notes_live_under_evidence():
    stale_top_level = [
        path.name
        for path in DOCS.glob("TARGET-*.md")
        if path.is_file()
    ]
    assert not stale_top_level, (
        "Dated target evidence belongs under docs/evidence/YYYY-MM-DD/: "
        + ", ".join(stale_top_level)
    )


def test_docs_index_exists():
    assert (DOCS / "README.md").is_file()
    assert (DOCS / "evidence" / "README.md").is_file()
