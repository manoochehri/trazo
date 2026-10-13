import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)", re.MULTILINE)
COMMIT_PIN = re.compile(r"^[\w.-]+/[\w.-]+(?:/[\w.-]+)*@[0-9a-f]{40}$")


def test_every_third_party_action_is_pinned_to_a_commit():
    # A tag can be moved to another commit; a SHA cannot (issue #225).
    offenders = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for ref in USES.findall(path.read_text()):
            if ref.startswith("./"):
                continue
            if not COMMIT_PIN.match(ref):
                offenders.append(f"{path.name}: {ref}")
    assert offenders == []
