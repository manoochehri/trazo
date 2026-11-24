#!/usr/bin/env python3
"""PreToolUse hook for the `Agent` tool: only the pinned Trazo roles may be started (issue #326).

The front door once started generic subagents and gave them a role in the prompt, instead of the
pinned agents or the role commands. A prompt did not stop that, so this hook does: it is an
allowlist of subagent types, and anything it does not recognise is blocked.

Contract (Claude Code hooks): the call arrives as JSON on stdin with `tool_name` and
`tool_input.subagent_type`. Exit 0 allows (permission deny rules still win), exit 2 blocks and
stderr is the reason. Any error blocks: the hook fails closed, and so does a missing or empty
`subagent_type` (UNVERIFIED: whether the harness fills in a default type when it is omitted; the
guard does not rely on one).

UNVERIFIED live: the input shape above comes from the Claude Code hooks documentation, not from a
recorded payload. The tests pin the contract this hook assumes; a payload of another shape is
denied, not allowed.

Allowed: `pm`, `reviewer`, `security`, `skeptic`, and the installer's prefixed copies
(`trazo-pm` and so on). Engineering is `/eng`, `/senior-eng` or `/work`; architecture is
`/architect`. Every other tool is not this hook's business and is allowed through.
"""

import json
import sys

PINNED = {"pm", "engineer", "senior-engineer", "reviewer", "security", "skeptic"}
ALLOWED = PINNED | {f"trazo-{name}" for name in PINNED}
AGENT_TOOLS = {"Agent", "Task"}  # the tool was named Task in earlier Claude Code releases

REASON = (
    "agent role guard: {why}. Only the pinned roles may be started as subagents: "
    "pm, reviewer, security, skeptic. Engineering is /eng, /senior-eng or /work; architecture "
    "is /architect (issue #326)."
)


class Deny(Exception):
    pass


def check(payload: object) -> None:
    if not isinstance(payload, dict):
        raise Deny("the hook input is not a JSON object")
    if payload.get("tool_name") not in AGENT_TOOLS:
        return
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        raise Deny("the Agent call carries no tool_input")
    kind = tool_input.get("subagent_type")
    if not isinstance(kind, str) or not kind.strip():
        raise Deny("the Agent call names no subagent_type")
    if kind not in ALLOWED:
        raise Deny(f"subagent_type {kind!r} is not a Trazo role")


def main() -> int:
    try:
        check(json.load(sys.stdin))
    except Deny as why:
        print(REASON.format(why=why), file=sys.stderr)
        return 2
    except Exception as err:  # noqa: BLE001 - fail closed on anything unexpected
        why = f"hook could not parse the call ({type(err).__name__})"
        print(REASON.format(why=why), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
