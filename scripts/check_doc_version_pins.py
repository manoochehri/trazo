"""Fail when public docs hard-code a Trazo release number (#403).

Docs must not show a version, because it changes. Install commands use `latest`
(scripts/install.sh resolves the highest release tag). A hard-coded number is a
`vX.Y.Z` token anywhere, or a bare `X.Y.Z` on a line about install, upgrade, a
release, the current version or a tag. URLs to the changelog, tags or releases
pages are allowed, `handbook/changelog.md` is exempt, and ADRs are never scanned.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

V_PIN = re.compile(r"(?<![\w.])v(\d+\.\d+\.\d+)\b")
BARE_PIN = re.compile(r"(?<![\w.\-])(\d+\.\d+\.\d+)\b(?![.\-]\w)")
CONTEXT = re.compile(r"install|upgrade|release|current|version|\btag\b|checkout", re.IGNORECASE)
ALLOWED_URL = re.compile(r"https?://\S*/(?:changelog|tags|releases)\S*", re.IGNORECASE)
EXEMPT = {"changelog.md"}


def find_stale_pins(root: Path, files: list[str] | None = None) -> list[str]:
    """Return one message per hard-coded release number in README.md and handbook/.

    `files` limits the scan to those paths relative to `root`; None scans README.md
    and every page under handbook/.
    """
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
            text = ALLOWED_URL.sub("", line)
            found = V_PIN.findall(text)
            if CONTEXT.search(text):
                found += BARE_PIN.findall(text)
            for version in dict.fromkeys(found):
                problems.append(f"{rel}:{number}: hard-codes release {version}; use `latest`")
    return problems


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    problems = find_stale_pins(root, argv or None)
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
