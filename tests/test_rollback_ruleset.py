"""scripts/rollback_ruleset.sh restores a ruleset and proves it (#320). A stub `gh` is GitHub."""

import json
import os
import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "rollback_ruleset.sh"
SAVED = Path(__file__).resolve().parent.parent / "scripts" / "rulesets" / "main-ruleset.saved.json"

# PUT stores stdin (and logs it); GET returns the stored body plus GitHub's read-only fields.
# STUB_DRIFT makes the stored copy differ after a PUT, as if GitHub had not applied it.
STUB = """#!/usr/bin/env bash
d=$(dirname "$0")
if [[ "$*" == *"-X PUT"* ]]; then
  cat > "$d/live.json"; touch "$d/put.called"
  if [[ -n "${STUB_DRIFT:-}" ]]; then
    jq '.enforcement="disabled"' "$d/live.json" > "$d/t" && mv "$d/t" "$d/live.json"
  fi
  exit 0
fi
if [[ "$1" == repo ]]; then echo o/r; exit 0; fi
body=$(jq '. + {id:1,node_id:"x",_links:{},current_user_can_bypass:"never"}' "$d/live.json")
while [[ $# -gt 0 ]]; do
  if [[ "$1" == -q ]]; then jq -r "$2" <<< "$body"; exit 0; fi
  shift
done
printf '%s\\n' "$body"
"""


def run(tmp_path, args, live=None, drift=False):
    stub = tmp_path / "gh"
    stub.write_text(STUB)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "live.json").write_text(
        json.dumps(live if live is not None else json.loads(SAVED.read_text()))
    )
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    if drift:
        env["STUB_DRIFT"] = "1"
    cmd = ["bash", str(SCRIPT), *args]
    return subprocess.run(cmd, env=env, capture_output=True, text=True)  # noqa: S603, S607


def test_match_exits_zero(tmp_path):
    r = run(tmp_path, [])
    assert r.returncode == 0, r.stderr
    assert "equals" in r.stdout


def test_drift_exits_nonzero(tmp_path):
    r = run(tmp_path, [], drift=True)
    assert r.returncode == 1
    assert "MISMATCH" in r.stderr


def test_non_numeric_id_refused(tmp_path):
    r = run(tmp_path, ["not-a-number"])
    assert r.returncode == 2
    assert not (tmp_path / "put.called").exists()


def test_missing_file_refused(tmp_path):
    r = run(tmp_path, ["24085136", str(tmp_path / "nope.json")])
    assert r.returncode == 2
    assert not (tmp_path / "put.called").exists()


def test_name_mismatch_refused_before_any_write(tmp_path):
    live = json.loads(SAVED.read_text())
    live["name"] = "some other ruleset"
    r = run(tmp_path, [], live=live)
    assert r.returncode == 2
    assert not (tmp_path / "put.called").exists()
    assert json.loads((tmp_path / "live.json").read_text())["name"] == "some other ruleset"
