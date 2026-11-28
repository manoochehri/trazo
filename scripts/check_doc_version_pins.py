"""Fail when public docs pin a Trazo version other than `.template/VERSION` (#403).

A pin is a `vX.Y.Z` token (install.sh URLs, `install.sh install|upgrade vX.Y.Z`,
`git checkout vX.Y.Z`) or a bare version after "current ... is". The changelog page
is exempt, and so are ADRs, which are never scanned.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

V_PIN = re.compile(r"(?<![\w.])v(\d+\.\d+\.\d+)\b")
CURRENT_PIN = re.compile(r"\bcurrent\b[^\n.]{0,40}?\bis\s+\**v?(\d+\.\d+\.\d+)\b", re.IGNORECASE)
EXEMPT = {"changelog.md"}


def find_stale_pins(root: Path, files: list[str] | None = None) -> list[str]:
    """Return one message per stale pin in README.md and handbook/ under `root`.

    `files` limits the scan to those paths relative to `root`; None scans README.md
    and every page under handbook/.
    """
    current = (root / ".template" / "VERSION").read_text(encoding="utf-8").strip()
    if files is None:
        paths = [root / "README.md", *sorted((root / "handbook").rglob("*.md"))]
    else:
        paths = [root / name for name in files]
    problems: list[str] = []
    for path in paths:
        if path.name in EXEMPT or not path.is_file():
            continue
        rel = path.relative_to(root)
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            found = V_PIN.findall(line) + CURRENT_PIN.findall(line)
            for version in dict.fromkeys(found):
                if version != current:
                    problems.append(f"{rel}:{number}: pins v{version}, current is v{current}")
    return problems


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    problems = find_stale_pins(root, argv or None)
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
