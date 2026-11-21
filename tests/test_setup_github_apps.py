"""scripts/setup_github_apps.zsh creates the Apps, stores the secrets and checks them (#252).

It runs against a fake GitHub (a local API server), a fake `gh` that records what it is asked to
store (never the key itself) and a fake `open` that plays GitHub's side of the manifest redirect.
No real GitHub, no real key and no browser are involved.
"""

import base64
import json
import os
import shutil
import signal
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
OPENSSL = shutil.which("openssl") or "openssl"
ZSH = shutil.which("zsh") or "zsh"
SCRIPT = ROOT / "scripts" / "setup_github_apps.zsh"

pytestmark = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("zsh", "jq", "openssl", "curl", "python3")),
    reason="zsh, jq, openssl, curl and python3 are required",
)

PERMS = {
    "trazo-builder": {
        "metadata": "read",
        "contents": "write",
        "pull_requests": "write",
        "issues": "write",
    },
    "trazo-reviewer": {
        "metadata": "read",
        "contents": "read",
        "pull_requests": "write",
        "issues": "read",
        "statuses": "write",
    },
}


def _b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class FakeGitHub:
    """Answers the three API calls the script makes and verifies the JWT signature."""

    def __init__(
        self, tmp: Path, perms: dict[str, dict[str, str]], selection: str = "selected"
    ) -> None:
        self.perms = perms
        self.selection = selection
        self.key = tmp / "app.pem"
        subprocess.run(  # noqa: S603 - fixed argv, test helper
            [OPENSSL, "genrsa", "-out", str(self.key), "2048"], check=True, capture_output=True
        )
        self.pub = tmp / "app.pub"
        subprocess.run(  # noqa: S603
            [OPENSSL, "rsa", "-in", str(self.key), "-pubout", "-out", str(self.pub)],
            check=True,
            capture_output=True,
        )
        self.pem = self.key.read_text()
        self.created: list[str] = []
        self.bad_signature = False
        self.owner = "o"
        self.name_override = ""
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:
                pass

            def _json(self, status: int, body: dict) -> None:
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _signature_ok(self) -> bool:
                token = self.headers.get("Authorization", "").removeprefix("Bearer ")
                parts = token.split(".")
                if len(parts) != 3:
                    return False
                signature = tmp / "sig.bin"
                signature.write_bytes(_b64url_decode(parts[2]))
                result = subprocess.run(  # noqa: S603
                    [
                        OPENSSL,
                        "dgst",
                        "-sha256",
                        "-verify",
                        str(fake.pub),
                        "-signature",
                        str(signature),
                    ],
                    input=f"{parts[0]}.{parts[1]}".encode(),
                    capture_output=True,
                    check=False,
                )
                return result.returncode == 0

            def do_POST(self) -> None:
                if self.path.startswith("/app-manifests/testcode/conversions"):
                    name = fake.next_name()
                    self._json(
                        201,
                        {
                            "id": 4242 + len(fake.created),
                            "slug": name,
                            "name": fake.name_override or name,
                            "owner": {"login": fake.owner},
                            "events": [],
                            "pem": fake.pem,
                            "webhook_secret": None,
                        },
                    )
                else:
                    self._json(404, {"message": "not found"})

            def do_GET(self) -> None:
                if self.path == "/app":
                    if not self._signature_ok():
                        fake.bad_signature = True
                        self._json(401, {"message": "bad jwt"})
                        return
                    self._json(200, {"permissions": fake.perms[fake.created[-1]]})
                elif self.path.startswith("/repos/o/r/installation"):
                    if not self._signature_ok():
                        fake.bad_signature = True
                        self._json(401, {"message": "bad jwt"})
                        return
                    self._json(200, {"repository_selection": fake.selection})
                else:
                    self._json(404, {"message": "not found"})

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def next_name(self) -> str:
        name = ["trazo-builder", "trazo-reviewer"][len(self.created)]
        self.created.append(name)
        return name

    def close(self) -> None:
        self.server.shutdown()


FAKE_GH = """#!/usr/bin/env bash
# Fake gh: records secret names, scope and sizes, never values; keeps a fake environment.
case "$1 $2" in
  "secret list")
    if [[ " $* " == *" --env trazo-apps "* ]]; then cat "$FAKE_EXISTING" 2>/dev/null
    else cat "$FAKE_REPO_SECRETS" 2>/dev/null; fi
    exit 0 ;;
  "secret set")
    name="$3"
    if [[ " $* " == *" --body "* ]]; then value_len=body
    else value_len="stdin:$(wc -c | tr -d ' ')"; fi
    scope=repo; [[ " $* " == *" --env trazo-apps "* ]] && scope=env:trazo-apps
    app=none; [[ " $* " == *" --app actions "* ]] && app=actions
    echo "$name $value_len $scope $app" >> "$FAKE_LOG"
    [[ -n "$FAKE_SET_FAIL" && "$name" == "$FAKE_SET_FAIL" ]] && exit 1
    exit 0 ;;
  "repo view") echo "o/r"; exit 0 ;;
  "api "*)
    shift
    method=GET; [[ "$1" == -X ]] && { method="$2"; shift 2; }
    path="$1"; input=""
    [[ " $* " == *" --input - "* ]] && input="$(cat)"
    echo "$method $path $input" >> "$FAKE_API_LOG"
    case "$method $path" in
      "PUT repos/o/r/environments/trazo-apps")
        printf '%s' "$input" > "$FAKE_ENVDIR/env.json"; echo '{}' ;;
      "GET repos/o/r/environments/trazo-apps")
        jq -c '{deployment_branch_policy}' "$FAKE_ENVDIR/env.json" ;;
      "GET repos/o/r/environments/trazo-apps/deployment-branch-policies")
        [[ -f "$FAKE_ENVDIR/policies" ]] || echo '[]' > "$FAKE_ENVDIR/policies"
        jq -c '{total_count:length,branch_policies:.}' "$FAKE_ENVDIR/policies" ;;
      "POST repos/o/r/environments/trazo-apps/deployment-branch-policies")
        [[ -f "$FAKE_ENVDIR/policies" ]] || echo '[]' > "$FAKE_ENVDIR/policies"
        jq -c --argjson n "$input" '. + [$n]' "$FAKE_ENVDIR/policies" > "$FAKE_ENVDIR/p2" \\
          && mv "$FAKE_ENVDIR/p2" "$FAKE_ENVDIR/policies"; echo '{}' ;;
      *) exit 1 ;;
    esac
    exit 0 ;;
esac
exit 1
"""

# Plays GitHub: fetch the helper's /start form, read the state off its action URL, then call back.
FAKE_OPEN = """#!/usr/bin/env bash
url="$1"
case "$url" in
  */start)
    [[ -z "$FAKE_NO_CALLBACK" ]] || exit 0
    page="$(curl -fsS "$url")"
    state="$(printf '%s' "$page" | sed -n 's/.*state=\\([0-9a-f]*\\)".*/\\1/p' | head -1)"
    base="${url%/start}"
    printf '%s' "$page" > "$FAKE_PAGE"
    if [[ -n "$FAKE_START_TWICE" ]]; then
      curl -s -o /dev/null -w '%{http_code}' "$url" > "$FAKE_SECOND_START"
    fi
    if [[ -n "$FAKE_HOST" ]]; then
      curl -s -o /dev/null -H "Host: $FAKE_HOST" \\
        "$base/callback?code=${FAKE_CODE:-testcode}&state=$state"
    else
      curl -fsS "$base/callback?code=${FAKE_CODE:-testcode}&state=${FAKE_STATE:-$state}" >/dev/null
    fi
    ;;
esac
exit 0
"""


@pytest.fixture
def world(tmp_path: Path):
    fake = FakeGitHub(tmp_path, PERMS)
    envdir = tmp_path / "env"
    envdir.mkdir()
    tmpdir = tmp_path / "tmp"
    tmpdir.mkdir()
    gh = tmp_path / "gh"
    gh.write_text(FAKE_GH)
    opener = tmp_path / "opener"
    opener.write_text(FAKE_OPEN)
    gh.chmod(0o755)
    opener.chmod(0o755)
    env = {
        **os.environ,
        "GH_BIN": str(gh),
        "OPEN_CMD": str(opener),
        "GITHUB_API": fake.url,
        "GITHUB_WEB": fake.url,
        "WAIT_SECONDS": "20",
        "FAKE_LOG": str(tmp_path / "secrets.log"),
        "FAKE_PAGE": str(tmp_path / "page.html"),
        "FAKE_EXISTING": str(tmp_path / "existing.txt"),
        "FAKE_REPO_SECRETS": str(tmp_path / "repo_secrets.txt"),
        "FAKE_API_LOG": str(tmp_path / "api.log"),
        "FAKE_SECOND_START": str(tmp_path / "second_start.txt"),
        "FAKE_ENVDIR": str(envdir),
        "TRAZO_TEST": "1",
        "TMPDIR": str(tmpdir),
    }
    yield fake, env, tmp_path
    fake.close()


def _run(env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - the script under test, fixed argv
        [ZSH, str(SCRIPT), "--repo", "o/r", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_dry_run_prints_both_manifests_and_touches_nothing(world) -> None:
    fake, env, tmp = world
    env = {**env, "GITHUB_API": "http://127.0.0.1:9"}
    result = _run(env, "--dry-run")
    assert result.returncode == 0
    for name, perms in PERMS.items():
        assert f'"name": "{name}"' in result.stdout
        for permission, level in perms.items():
            assert f'"{permission}": "{level}"' in result.stdout
    assert "hook_attributes" not in result.stdout
    assert not (tmp / "secrets.log").exists()


def test_each_app_is_created_stored_verified_and_the_key_is_never_printed(world) -> None:
    fake, env, tmp = world
    result = _run(env)
    assert result.returncode == 0, result.stdout + result.stderr
    stored = (tmp / "secrets.log").read_text().splitlines()
    assert [line.split()[0] for line in stored] == [
        "BUILDER_APP_PRIVATE_KEY",
        "BUILDER_APP_ID",
        "REVIEWER_APP_PRIVATE_KEY",
        "REVIEWER_APP_ID",
    ]
    key_sizes = [int(line.split("stdin:")[1].split()[0]) for line in stored if "stdin:" in line]
    assert all(size > 1000 for size in key_sizes)
    assert all(line.split()[2:] == ["env:trazo-apps", "actions"] for line in stored)
    body = fake.pem.splitlines()[1]
    assert body not in result.stdout + result.stderr
    assert "BEGIN" not in result.stdout + result.stderr
    assert fake.bad_signature is False
    assert "Installed on o/r only." in result.stdout
    page = (tmp / "page.html").read_text()
    assert "manifest" in page and "settings/apps/new?state=" in page


def test_a_callback_with_the_wrong_state_is_ignored_and_nothing_is_stored(world) -> None:
    fake, env, tmp = world
    env = {**env, "FAKE_STATE": "wrong", "WAIT_SECONDS": "4"}
    result = _run(env, "--only", "builder")
    assert result.returncode != 0
    assert "Timed out" in result.stderr
    assert not (tmp / "secrets.log").exists()


def test_granted_permissions_that_differ_from_the_manifest_fail_loudly(world) -> None:
    fake, env, tmp = world
    fake.perms = {**PERMS, "trazo-builder": {**PERMS["trazo-builder"], "contents": "read"}}
    result = _run(env, "--only", "builder")
    assert result.returncode != 0
    assert "Granted permissions differ" in result.stderr


def test_an_app_installed_on_all_repositories_fails(world) -> None:
    fake, env, tmp = world
    fake.selection = "all"
    result = _run({**env, "WAIT_SECONDS": "4"}, "--only", "builder")
    assert result.returncode != 0
    assert "Done." not in result.stdout
    assert "all" in result.stderr


def test_existing_secrets_are_not_overwritten_without_force(world) -> None:
    fake, env, tmp = world
    (tmp / "existing.txt").write_text("BUILDER_APP_ID\nBUILDER_APP_PRIVATE_KEY\n")
    result = _run(env, "--only", "builder")
    assert result.returncode == 0
    assert "already exists" in result.stdout
    assert not (tmp / "secrets.log").exists()


def test_either_existing_secret_blocks_a_second_app(world) -> None:
    fake, env, tmp = world
    (tmp / "existing.txt").write_text("BUILDER_APP_PRIVATE_KEY\n")
    result = _run(env, "--only", "builder")
    assert "already exists" in result.stdout
    assert not (tmp / "secrets.log").exists()
    assert fake.created == []


def test_the_environment_is_created_limited_to_main_before_any_secret(world) -> None:
    fake, env, tmp = world
    result = _run(env, "--only", "builder")
    assert result.returncode == 0, result.stdout + result.stderr
    calls = (tmp / "api.log").read_text().splitlines()
    put = next(c for c in calls if c.startswith("PUT repos/o/r/environments/trazo-apps "))
    body = json.loads(put.split(" ", 2)[2])
    assert body["deployment_branch_policy"] == {
        "protected_branches": False,
        "custom_branch_policies": True,
    }
    post = next(c for c in calls if c.startswith("POST "))
    assert json.loads(post.split(" ", 2)[2]) == {"name": "main", "type": "branch"}
    policies = json.loads((tmp / "env" / "policies").read_text())
    assert policies == [{"name": "main", "type": "branch"}]


def test_an_environment_that_allows_another_branch_fails_before_any_app(world) -> None:
    fake, env, tmp = world
    (tmp / "env" / "policies").write_text('[{"name":"main","type":"branch"},{"name":"*"}]')
    result = _run(env, "--only", "builder")
    assert result.returncode != 0
    assert fake.created == []
    assert not (tmp / "secrets.log").exists()


def test_an_app_owned_by_someone_else_is_never_stored(world) -> None:
    fake, env, tmp = world
    fake.owner = "mallory"
    result = _run(env, "--only", "builder")
    assert result.returncode != 0
    assert "owner" in result.stderr
    assert not (tmp / "secrets.log").exists()


def test_an_app_with_an_unexpected_name_is_never_stored(world) -> None:
    fake, env, tmp = world
    fake.name_override = "evil-app"
    result = _run(env, "--only", "builder")
    assert result.returncode != 0
    assert not (tmp / "secrets.log").exists()


def test_a_callback_with_a_foreign_host_header_is_ignored(world) -> None:
    fake, env, tmp = world
    env = {**env, "FAKE_HOST": "evil.example", "WAIT_SECONDS": "4"}
    result = _run(env, "--only", "builder")
    assert result.returncode != 0
    assert not (tmp / "secrets.log").exists()


def test_the_start_page_is_served_only_once(world) -> None:
    fake, env, tmp = world
    result = _run({**env, "FAKE_START_TWICE": "1"}, "--only", "builder")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp / "second_start.txt").read_text() in {"403", "404", "410"}


def test_granted_extra_permissions_fail(world) -> None:
    fake, env, tmp = world
    fake.perms = {**PERMS, "trazo-builder": {**PERMS["trazo-builder"], "workflows": "write"}}
    result = _run(env, "--only", "builder")
    assert result.returncode != 0
    assert "Granted permissions differ" in result.stderr


def test_a_failed_second_secret_names_the_app_to_recover(world) -> None:
    fake, env, tmp = world
    result = _run({**env, "FAKE_SET_FAIL": "BUILDER_APP_ID"}, "--only", "builder")
    assert result.returncode != 0
    assert "settings/apps/trazo-builder" in result.stderr


def test_test_overrides_are_refused_outside_tests(world) -> None:
    fake, env, tmp = world
    env = {k: v for k, v in env.items() if k != "TRAZO_TEST"}
    result = _run(env, "--only", "builder")
    assert result.returncode != 0
    assert "TRAZO_TEST" in result.stderr
    assert fake.created == []


def test_ctrl_c_stops_the_helper_and_removes_the_workdir(world) -> None:
    fake, env, tmp = world
    env = {**env, "FAKE_NO_CALLBACK": "1", "WAIT_SECONDS": "60"}
    proc = subprocess.Popen(  # noqa: S603 - the script under test
        [ZSH, str(SCRIPT), "--repo", "o/r", "--only", "builder"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    tmpdir = tmp / "tmp"
    port = None
    for _ in range(100):
        ports = list(tmpdir.glob("*/port"))
        if ports and ports[0].read_text().strip():
            port = int(ports[0].read_text())
            break
        time.sleep(0.1)
    if port is None:
        proc.kill()
        out, err = proc.communicate()
        pytest.fail(f"helper never started: {out} {err} {list(tmpdir.rglob('*'))}")
    time.sleep(0.5)
    proc.send_signal(signal.SIGINT)
    try:
        proc.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        pytest.fail("script did not exit on SIGINT")
    assert proc.returncode == 130
    assert list(tmpdir.iterdir()) == []
    time.sleep(0.5)
    with pytest.raises(OSError), socket.create_connection(("127.0.0.1", port), timeout=1):
        pass
