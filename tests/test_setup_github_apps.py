"""scripts/setup_github_apps.zsh creates the Apps, stores the secrets and checks them (#252).

It runs against a fake GitHub (a local API server), a fake `gh` that records what it is asked to
store (never the key itself) and a fake `open` that plays GitHub's side of the manifest redirect.
No real GitHub, no real key and no browser are involved.
"""

import base64
import json
import os
import shutil
import subprocess
import threading
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
# Fake gh: records secret names and sizes, never values.
case "$1 $2" in
  "secret list") cat "$FAKE_EXISTING" 2>/dev/null; exit 0 ;;
  "secret set")
    name="$3"
    if [[ " $* " == *" --body "* ]]; then value_len=body
    else value_len="stdin:$(wc -c | tr -d ' ')"; fi
    echo "$name $value_len" >> "$FAKE_LOG"; exit 0 ;;
  "repo view") echo "o/r"; exit 0 ;;
esac
exit 1
"""

# Plays GitHub: fetch the helper's /start form, read the state off its action URL, then call back.
FAKE_OPEN = """#!/usr/bin/env bash
url="$1"
case "$url" in
  */start)
    page="$(curl -fsS "$url")"
    state="$(printf '%s' "$page" | sed -n 's/.*state=\\([0-9a-f]*\\)".*/\\1/p' | head -1)"
    base="${url%/start}"
    printf '%s' "$page" > "$FAKE_PAGE"
    curl -fsS "$base/callback?code=${FAKE_CODE:-testcode}&state=${FAKE_STATE:-$state}" >/dev/null
    ;;
esac
exit 0
"""


@pytest.fixture
def world(tmp_path: Path):
    fake = FakeGitHub(tmp_path, PERMS)
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
    key_sizes = [int(line.split("stdin:")[1]) for line in stored if "stdin:" in line]
    assert all(size > 1000 for size in key_sizes)
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


def test_an_app_installed_on_all_repositories_is_warned_about(world) -> None:
    fake, env, tmp = world
    fake.selection = "all"
    result = _run(env, "--only", "builder")
    assert result.returncode == 0
    assert "WARNING" in result.stdout


def test_existing_secrets_are_not_overwritten_without_force(world) -> None:
    fake, env, tmp = world
    (tmp / "existing.txt").write_text("BUILDER_APP_ID\nBUILDER_APP_PRIVATE_KEY\n")
    result = _run(env, "--only", "builder")
    assert result.returncode == 0
    assert "already exists" in result.stdout
    assert not (tmp / "secrets.log").exists()
