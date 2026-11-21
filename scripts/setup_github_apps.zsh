#!/usr/bin/env zsh
# Create the two GitHub Apps from #252 (trazo-builder and trazo-reviewer), store each App's id and
# private key as secrets of the `trazo-apps` environment (deployment branches: main only; owner
# decision on #252, 2026-11-17), and check the result. YOU run this; an agent never should.
#
#   scripts/setup_github_apps.zsh --dry-run          # print the two App manifests, change nothing
#   scripts/setup_github_apps.zsh                    # create both Apps, store the secrets, check
#   scripts/setup_github_apps.zsh --only reviewer    # just one of them
#
# How it works (GitHub's "register a GitHub App from a manifest" flow):
#   1. It creates the `trazo-apps` environment, limited to the branch main, before any key exists.
#   2. A tiny web server on 127.0.0.1 hands your browser a form that posts the App's manifest to GitHub.
#   3. You click "Create GitHub App" on GitHub's page. GitHub redirects back to this server with a
#      one-time code.
#   4. The script exchanges the code, checks the App is yours and named trazo-<role>, and pipes the key
#      straight into `gh secret set --env trazo-apps`. The key is never printed or written to a file.
#   5. It signs a short-lived token with the key to prove the key works and to read back the permissions
#      GitHub granted, then sends you to GitHub's page to install the App on this repository only.
#
# Secrets set (environment trazo-apps): BUILDER_APP_ID, BUILDER_APP_PRIVATE_KEY, REVIEWER_APP_ID,
# REVIEWER_APP_PRIVATE_KEY.
# Needs: zsh, gh (logged in as the repository owner, with admin on the repo), jq, openssl, curl, python3.
#
# UNVERIFIED against live GitHub: that omitting `hook_attributes` leaves no webhook (the script checks
# `events` is empty and the permissions match exactly), that GitHub accepts an http://127.0.0.1
# redirect_url, and that `gh secret set --env ... --app actions` is accepted together.

emulate -L zsh
setopt err_exit no_unset pipe_fail
unsetopt xtrace verbose   # a traced run would print the private key

# Overrides exist so the tests can run this against a fake GitHub. A real run refuses them: they
# could send the private key to a fake `gh` or a proxy.
if [[ ${TRAZO_TEST:-} != 1 ]]; then
  for v in GH_BIN GITHUB_API GITHUB_WEB OPEN_CMD; do
    if [[ -n ${(P)v:-} ]]; then
      print -u2 "Refusing to run: $v is set. These overrides are for tests only (TRAZO_TEST=1)."
      exit 2
    fi
  done
fi
GH_BIN=${GH_BIN:-gh}
API=${GITHUB_API:-https://api.github.com}
WEB=${GITHUB_WEB:-https://github.com}
OPEN=${OPEN_CMD:-open}
WAIT_SECONDS=${WAIT_SECONDS:-600}
ENV_NAME=trazo-apps

typeset -A PERMS
PERMS[builder]='{"metadata":"read","contents":"write","pull_requests":"write","issues":"write"}'
PERMS[reviewer]='{"metadata":"read","contents":"read","pull_requests":"write","issues":"read","statuses":"write"}'

dry_run=0
force=0
only=""
repo=""
while (( $# )); do
  case $1 in
    --dry-run) dry_run=1 ;;
    --force) force=1 ;;
    --only) shift; only=${1:-}; [[ $only == builder || $only == reviewer ]] || { print -u2 -- "--only takes builder or reviewer"; exit 2 }; ;;
    --repo) shift; repo=${1:-}; [[ -n $repo ]] || { print -u2 -- "--repo takes owner/name"; exit 2 }; ;;
    *) print -u2 "Unknown argument: $1 (use --dry-run, --force, --only builder|reviewer, --repo owner/name)"; exit 2 ;;
  esac
  shift
done

for tool in jq openssl curl python3 $GH_BIN; do
  command -v $tool >/dev/null || { print -u2 "Missing required tool: $tool"; exit 1 }
done
[[ -n $repo ]] || repo=$($GH_BIN repo view --json nameWithOwner -q .nameWithOwner)
owner=${repo%%/*}
homepage="https://github.com/$repo"
apps=(builder reviewer)
[[ -z $only ]] || apps=($only)

manifest_for() {  # $1 = builder|reviewer, $2 = redirect port
  jq -n --arg name "trazo-$1" --arg url "$homepage" --arg redirect "http://127.0.0.1:$2/callback" \
    --argjson perms "${PERMS[$1]}" \
    '{name: $name, url: $url, redirect_url: $redirect, public: false, default_permissions: $perms, default_events: []}'
}

if (( dry_run )); then
  print "Dry run for $repo: nothing will be created or changed.\n"
  for app in $apps; do
    print "== trazo-$app (redirect port is chosen at run time; shown as 0) =="
    manifest_for $app 0
    print
  done
  print "Each App: webhook off, private (installable only on your account), no Workflows/Actions/Secrets/Administration."
  print "Secrets go to the '$ENV_NAME' environment of $repo, deployment branches limited to main."
  exit 0
fi

b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '=' }

make_jwt() {  # $1 = app id, $2 = private key (PEM text)
  local now=$(date +%s) header payload signature
  header=$(print -rn -- '{"alg":"RS256","typ":"JWT"}' | b64url)
  payload=$(print -rn -- "{\"iat\":$((now - 60)),\"exp\":$((now + 300)),\"iss\":\"$1\"}" | b64url)
  signature=$(print -rn -- "$header.$payload" | openssl dgst -sha256 -sign <(print -rn -- "$2") | b64url)
  print -rn -- "$header.$payload.$signature"
}

api_get() {  # $1 = path, $2 = jwt. The token goes in on stdin, never in argv where `ps` shows it.
  print -r -- "header = \"Authorization: Bearer $2\"" | curl -fsS -K - -H "Accept: application/vnd.github+json" "$API$1"
}

workdir=$(mktemp -d "${TMPDIR:-/tmp}/trazo-apps.XXXXXX")
chmod 700 $workdir
server_pid=""
recover_slug=""
recover_id=""
cleanup() {
  local rc=$?
  trap - EXIT
  [[ -z $server_pid ]] || kill $server_pid 2>/dev/null || true
  rm -f $workdir/manifest.json $workdir/port $workdir/code $workdir/server.py 2>/dev/null || true
  rmdir $workdir 2>/dev/null || true
  if (( rc != 0 )) && [[ -n $recover_slug ]]; then
    print -u2 "\nINCOMPLETE: $recover_slug (App id $recover_id) exists at $WEB/settings/apps/$recover_slug and may hold a live key."
    print -u2 "Check the $ENV_NAME secrets. If either is missing, generate a new private key there or delete the App, then run again."
  fi
}
# By default a signal skips the EXIT trap; turn each into an exit so cleanup always runs.
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

ensure_environment() {  # create trazo-apps limited to the branch main; refuse to go on unless that holds
  local pol env_json
  print -r -- '{"deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}' \
    | $GH_BIN api -X PUT repos/$repo/environments/$ENV_NAME --input - >/dev/null
  pol=$($GH_BIN api repos/$repo/environments/$ENV_NAME/deployment-branch-policies)
  if [[ $(print -rn -- "$pol" | jq '.branch_policies | length') == 0 ]]; then
    print -r -- '{"name":"main","type":"branch"}' \
      | $GH_BIN api -X POST repos/$repo/environments/$ENV_NAME/deployment-branch-policies --input - >/dev/null
    pol=$($GH_BIN api repos/$repo/environments/$ENV_NAME/deployment-branch-policies)
  fi
  print -rn -- "$pol" | jq -e '[.branch_policies[] | [.name, (.type // "branch")]] == [["main","branch"]]' >/dev/null \
    || { print -u2 "Environment $ENV_NAME must allow the branch main and nothing else. Fix it in $repo settings > Environments."; exit 1 }
  env_json=$($GH_BIN api repos/$repo/environments/$ENV_NAME)
  print -rn -- "$env_json" | jq -e '.deployment_branch_policy.custom_branch_policies == true and .deployment_branch_policy.protected_branches == false' >/dev/null \
    || { print -u2 "Environment $ENV_NAME is not limited to selected branches. Fix it in $repo settings > Environments."; exit 1 }
  print "Environment $ENV_NAME: deployment branches limited to main."
}

cat > $workdir/server.py <<'PY'
import html, http.server, os, sys, time, urllib.parse

state, workdir, parent = sys.argv[1], sys.argv[2], int(sys.argv[3])
web = os.environ["GITHUB_WEB"]
started = False


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, body):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        global started
        # Only our own browser tab may talk to us: refuse any other Host (DNS rebinding).
        if self.headers.get("Host") != f"127.0.0.1:{self.server.server_address[1]}":
            self._send(403, "Forbidden")
            return
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/start":
            if started:
                self._send(410, "Already used.")
                return
            started = True
            with open(os.path.join(workdir, "manifest.json"), encoding="utf-8") as handle:
                manifest = handle.read()
            action = f"{web}/settings/apps/new?state={state}"
            self._send(200, (
                '<!doctype html><title>Create GitHub App</title><p>Sending you to GitHub...</p>'
                f'<form id="f" method="post" action="{html.escape(action, quote=True)}">'
                f'<input type="hidden" name="manifest" value="{html.escape(manifest, quote=True)}">'
                '<noscript><button>Continue to GitHub</button></noscript></form>'
                '<script>document.getElementById("f").submit()</script>'))
        elif parsed.path == "/callback":
            code = query.get("code", [""])[0]
            if query.get("state", [""])[0] != state or not code or not code.isascii() or not code.isalnum():
                self._send(400, "Wrong or missing state; ignored.")
                return
            fd = os.open(os.path.join(workdir, "code"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as handle:
                handle.write(code)
            self._send(200, "Done. You can close this tab and go back to the terminal.")
        else:
            self._send(404, "Not found")


server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
server.timeout = 1
fd = os.open(os.path.join(workdir, "port"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as handle:
    handle.write(str(server.server_address[1]))
deadline = time.time() + float(os.environ.get("WAIT_SECONDS", "600"))
while time.time() < deadline and not os.path.exists(os.path.join(workdir, "code")):
    if os.getppid() != parent:  # the script that started us is gone: stop serving
        break
    server.handle_request()
PY

ensure_environment
existing=($($GH_BIN secret list -R $repo --env $ENV_NAME --json name -q '.[].name'))

for app in $apps; do
  upper=${(U)app}
  if (( ${existing[(Ie)${upper}_APP_ID]} || ${existing[(Ie)${upper}_APP_PRIVATE_KEY]} )); then
    if (( ! force )); then
      print "${upper}_APP_ID or ${upper}_APP_PRIVATE_KEY already exists in $ENV_NAME of $repo; skipping trazo-$app (use --force to create another App)."
      continue
    fi
    print "--force: the existing ${upper} secrets will be overwritten. The old trazo-$app App keeps a valid key until you delete it or revoke its key at $WEB/settings/apps."
  fi
  print "\n== trazo-$app =="
  state=$(openssl rand -hex 16)
  rm -f $workdir/code $workdir/port
  GITHUB_WEB=$WEB WAIT_SECONDS=$WAIT_SECONDS python3 $workdir/server.py $state $workdir $$ &
  server_pid=$!
  for _ in {1..50}; do [[ -s $workdir/port ]] && break; sleep 0.1; done
  [[ -s $workdir/port ]] || { print -u2 "The local helper server did not start."; exit 1 }
  port=$(<$workdir/port)
  manifest_for $app $port > $workdir/manifest.json
  print "Opening your browser. On GitHub's page, check the name and click 'Create GitHub App'."
  $OPEN "http://127.0.0.1:$port/start" || print "If the browser did not open, go to http://127.0.0.1:$port/start"
  for _ in {1..$WAIT_SECONDS}; do [[ -s $workdir/code ]] && break; sleep 1; done
  [[ -s $workdir/code ]] || { print -u2 "Timed out waiting for GitHub. Nothing was stored for trazo-$app."; exit 1 }
  code=$(<$workdir/code)
  rm -f $workdir/code
  kill $server_pid 2>/dev/null || true
  wait $server_pid 2>/dev/null || true
  server_pid=""

  [[ $code =~ '^[A-Za-z0-9]+$' ]] || { print -u2 "The code GitHub sent back has an unexpected shape; not using it."; exit 1 }
  resp=$(print -r -- "url = \"$API/app-manifests/$code/conversions\"" | curl -fsS -K - -X POST -H "Accept: application/vnd.github+json")
  app_id=$(print -rn -- "$resp" | jq -r '.id // empty')
  app_name=$(print -rn -- "$resp" | jq -r '.name // empty')
  app_owner=$(print -rn -- "$resp" | jq -r '.owner.login // empty')
  slug=$(print -rn -- "$resp" | jq -r '.slug // .name // empty')
  pem=$(print -rn -- "$resp" | jq -r '.pem // empty')
  events_ok=0
  if print -rn -- "$resp" | jq -e '(.events // []) | length == 0' >/dev/null; then events_ok=1; fi
  unset resp code
  [[ -n $app_id && -n $slug && $pem == *"PRIVATE KEY"* ]] || { print -u2 "GitHub's reply did not contain an App id, slug and key."; exit 1 }
  # A forged callback could hand us someone else's App. Store nothing unless it is ours.
  [[ ${(L)app_owner} == ${(L)owner} ]] || { print -u2 "The App's owner is '$app_owner', not '$owner'. Nothing was stored. If you did not create it, ignore it."; exit 1 }
  [[ $app_name == trazo-$app* ]] || { print -u2 "The App is named '$app_name', not trazo-$app. Nothing was stored."; exit 1 }
  recover_slug=$slug; recover_id=$app_id
  (( events_ok )) || { print -u2 "The App subscribes to webhook events; the manifest asked for none. Fix it at $WEB/settings/apps/$slug"; exit 1 }

  print -rn -- "$pem" | $GH_BIN secret set ${upper}_APP_PRIVATE_KEY -R $repo --env $ENV_NAME --app actions
  $GH_BIN secret set ${upper}_APP_ID -R $repo --env $ENV_NAME --app actions --body "$app_id"
  print "Stored ${upper}_APP_ID and ${upper}_APP_PRIVATE_KEY in the $ENV_NAME environment of $repo (App id $app_id, $slug)."

  jwt=$(make_jwt $app_id "$pem")
  granted=$(api_get /app $jwt) || { print -u2 "The new key did not authenticate as the App."; exit 1 }
  print -rn -- "$granted" | jq -e --argjson want "${PERMS[$app]}" '.permissions == $want' >/dev/null \
    || { print -u2 "Granted permissions differ from the manifest. Granted: $(print -rn -- "$granted" | jq -c .permissions). Fix them at $WEB/settings/apps/$slug/permissions"; exit 1 }
  print "Key works. Granted permissions: $(print -rn -- "$granted" | jq -c .permissions)"

  print "Now install it: on the page that opens, choose 'Only select repositories' and pick ${repo:t} only."
  $OPEN "$WEB/apps/$slug/installations/new" || print "Open $WEB/apps/$slug/installations/new yourself."
  installed=0 selection=none warned=0
  deadline=$((SECONDS + WAIT_SECONDS))
  while (( SECONDS < deadline )); do
    jwt=$(make_jwt $app_id "$pem")
    if info=$(api_get /repos/$repo/installation $jwt 2>/dev/null); then
      selection=$(print -rn -- "$info" | jq -r '.repository_selection // "unknown"')
      if [[ $selection == selected ]]; then installed=1; break; fi
      (( warned )) || { print "The installation covers '$selection' repositories. Change it to 'Only select repositories' and pick ${repo:t} only."; warned=1 }
    fi
    sleep 2
  done
  unset pem jwt
  if (( ! installed )); then
    if [[ $selection == none ]]; then
      print -u2 "trazo-$app is not installed on $repo yet. The secrets ARE stored. Install it at $WEB/apps/$slug/installations/new, choosing only ${repo:t}."
    else
      print -u2 "trazo-$app is installed on '$selection' repositories, not only $repo. Narrow it at $WEB/settings/installations: its key reaches everything it is installed on."
    fi
    exit 1
  fi
  print "Installed on $repo only."
  recover_slug=""
done

print "\nDone. Secrets in the $ENV_NAME environment of $repo: $($GH_BIN secret list -R $repo --env $ENV_NAME --json name -q '[.[].name | select(test("_APP_(ID|PRIVATE_KEY)$"))] | join(", ")')"
print "Next: tell the engineer session the secrets exist. Delete nothing locally: no key file was written."
