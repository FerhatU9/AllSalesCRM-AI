"""Check that internal Markdown file links resolve inside this repository.

External URLs and fragment-only references are intentionally out of scope.
"""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def test_relative_markdown_file_links():
    broken = []
    for markdown in sorted(ROOT.rglob("*.md")):
        if any(part in {".venv", "node_modules", ".next"} for part in markdown.parts):
            continue
        for raw in LINK.findall(markdown.read_text(encoding="utf-8")):
            target = raw.strip().split("#", 1)[0].split("?", 1)[0]
            if not target or urlsplit(target).scheme or target.startswith("//"):
                continue
            # Text-only links can use Markdown titles; repository links currently do not.
            path = (markdown.parent / unquote(target)).resolve()
            if not path.is_relative_to(ROOT) or not path.exists():
                broken.append(f"{markdown.relative_to(ROOT)} -> {raw}")
    assert not broken, "Broken local documentation links:\n" + "\n".join(broken)
