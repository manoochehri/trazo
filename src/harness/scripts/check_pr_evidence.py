"""Require review and fail-first evidence in pull request descriptions."""

import json
import os
import re
import sys
from pathlib import Path


def validate(body: str) -> list[str]:
    errors: list[str] = []
    rounds = re.search(r"(?im)^Review rounds:\s*(\d+)\s*$", body)
    if rounds is None:
        errors.append("Add 'Review rounds: <number>'.")

    defects = re.search(r"(?im)^Defects found and fixed:\s*(.+?)\s*$", body)
    if defects is None or re.search(r"<[^>]+>", defects.group(1)):
        errors.append("Add 'Defects found and fixed: <summary or none>'.")

    exemption = re.search(r"(?im)^Fail-first exemption:\s*(.+?)\s*$", body)
    if (
        exemption
        and len(exemption.group(1).strip()) >= 20
        and not re.search(r"<[^>]+>", exemption.group(1))
    ):
        return errors

    output = re.search(r"(?im)^Fail-first output:\s*\n(.*)", body, re.DOTALL)
    if output is None or re.search(r"<[^>]+>", output.group(1)):
        errors.append("Add failing test output or a specific Fail-first exemption.")
    elif not re.search(r"(?im)^.*\b(FAILED|ERROR)\b|AssertionError|Traceback", output.group(1)):
        errors.append(
            "Fail-first output must show failing test output "
            "(for example, FAILED or AssertionError)."
        )
    return errors


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("GITHUB_EVENT_PATH is not set.", file=sys.stderr)
        return 2
    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read GitHub event payload: {exc}", file=sys.stderr)
        return 2
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        print("GitHub event does not contain a pull request.", file=sys.stderr)
        return 2
    errors = validate(pull_request.get("body") or "")
    if errors:
        print("Pull request evidence is incomplete:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Pull request evidence fields are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
