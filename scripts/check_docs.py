"""Validate documentation states, the index, and local links."""

import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
index = (root / "Docs/README.md").read_text()
documents = sorted((root / "Docs").glob("*.md"))
for path in [root / "README.md", root / "AGENTS.md", *documents]:
    text = path.read_text()
    states = re.findall(r"^State: (.+)$", text, re.MULTILINE)
    assert len(states) == 1 and states[0] in {"implemented", "partially implemented", "not implemented"}, path
    assert text.endswith("\n"), path
    assert all(line == line.rstrip() for line in text.splitlines()), path
    assert sum(line.startswith("```") for line in text.splitlines()) % 2 == 0, path
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if "://" not in target:
            assert (path.parent / target.split("#", 1)[0]).exists(), (path, target)
    if path.parent.name == "Docs" and path.name != "README.md":
        rows = [line for line in index.splitlines() if f"]({path.name})" in line]
        assert len(rows) == 1 and rows[0].endswith(f"| {states[0]} |"), path
print(f"Validated {len(documents)} documents, root Markdown files, states, links, and index entries.")
