#!/usr/bin/env zsh
# Create the two GitHub Apps from #252 (trazo-builder and trazo-reviewer), store each App's id and
# private key as repository secrets, and check the result. YOU run this; an agent never should.
#
#   scripts/setup_github_apps.zsh --dry-run          # print the two App manifests, change nothing
#   scripts/setup_github_apps.zsh                    # create both Apps, store the secrets, check
#   scripts/setup_github_apps.zsh --only reviewer    # just one of them
#
# How it works (GitHub's "register a GitHub App from a manifest" flow):
#   1. A tiny web server on 127.0.0.1 hands your browser a form that posts the App's manifest to GitHub.
#   2. You click "Create GitHub App" on GitHub's page. GitHub redirects back to this server with a
#      one-time code.
#   3. The script exchanges the code for the App id and the private key, and pipes the key straight into
#      `gh secret set`. The key is never printed and never written to a file.
#   4. It signs a short-lived token with the key to prove the key works and to read back the permissions
#      GitHub granted, then sends you to GitHub's page to install the App on this repository only.
#
# Secrets set: BUILDER_APP_ID, BUILDER_APP_PRIVATE_KEY, REVIEWER_APP_ID, REVIEWER_APP_PRIVATE_KEY.
# Needs: zsh, gh (logged in as the repository owner), jq, openssl, curl, python3.
#
# UNVERIFIED against live GitHub: the permission names in the manifests, and the conversion response
# fields (`id`, `slug`, `pem`). The script checks the granted permissions and fails loudly if they differ.

emulate -L zsh
setopt err_exit no_unset pipe_fail

# Overrides exist so the tests can run this against a fake GitHub; leave them alone otherwise.
GH_BIN=${GH_BIN:-gh}
API=${GITHUB_API:-https://api.github.com}
WEB=${GITHUB_WEB:-https://github.com}
OPEN=${OPEN_CMD:-open}
WAIT_SECONDS=${WAIT_SECONDS:-600}

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
    --repo) shift; repo=${1:-} ;;
    *) print -u2 "Unknown argument: $1 (use --dry-run, --force, --only builder|reviewer, --repo owner/name)"; exit 2 ;;
  esac
  shift
done

for tool in jq openssl curl python3 $GH_BIN; do
  command -v $tool >/dev/null || { print -u2 "Missing required tool: $tool"; exit 1 }
done
[[ -n $repo ]] || repo=$($GH_BIN repo view --json nameWithOwner -q .nameWithOwner)
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

api_get() {  # $1 = path, $2 = jwt
  curl -fsS -H "Authorization: Bearer $2" -H "Accept: application/vnd.github+json" "$API$1"
}

workdir=$(mktemp -d)
chmod 700 $workdir
server_pid=""
cleanup() {
  [[ -z $server_pid ]] || kill $server_pid 2>/dev/null || true
  rm -f $workdir/manifest.json $workdir/port $workdir/code $workdir/server.py 2>/dev/null || true
  rmdir $workdir 2>/dev/null || true
}
trap cleanup EXIT

cat > $workdir/server.py <<'PY'
import html, http.server, os, sys, time, urllib.parse

state, workdir = sys.argv[1], sys.argv[2]
web = os.environ["GITHUB_WEB"]


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
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/start":
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
            if query.get("state", [""])[0] != state or not code:
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
    server.handle_request()
PY

existing=$($GH_BIN secret list -R $repo --json name -q '.[].name')

for app in $apps; do
  upper=${(U)app}
  if [[ $existing == *${upper}_APP_ID* && $force -eq 0 ]]; then
    print "${upper}_APP_ID already exists in $repo; skipping trazo-$app (use --force to create another App)."
    continue
  fi
  print "\n== trazo-$app =="
  state=$(openssl rand -hex 16)
  rm -f $workdir/code $workdir/port
  GITHUB_WEB=$WEB WAIT_SECONDS=$WAIT_SECONDS python3 $workdir/server.py $state $workdir &
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
  kill $server_pid 2>/dev/null || true
  wait $server_pid 2>/dev/null || true
  server_pid=""

  resp=$(curl -fsS -X POST -H "Accept: application/vnd.github+json" "$API/app-manifests/$code/conversions")
  app_id=$(print -rn -- "$resp" | jq -r '.id // empty')
  slug=$(print -rn -- "$resp" | jq -r '.slug // empty')
  pem=$(print -rn -- "$resp" | jq -r '.pem // empty')
  unset resp code
  [[ -n $app_id && -n $slug && $pem == *"PRIVATE KEY"* ]] || { print -u2 "GitHub's reply did not contain an App id, slug and key."; exit 1 }

  print -rn -- "$pem" | $GH_BIN secret set ${upper}_APP_PRIVATE_KEY -R $repo
  $GH_BIN secret set ${upper}_APP_ID -R $repo --body "$app_id"
  print "Stored ${upper}_APP_ID and ${upper}_APP_PRIVATE_KEY in $repo (App id $app_id, $slug)."

  jwt=$(make_jwt $app_id "$pem")
  granted=$(api_get /app $jwt) || { print -u2 "The new key did not authenticate as the App."; exit 1 }
  print -rn -- "$granted" | jq -e --argjson want "${PERMS[$app]}" \
    '.permissions as $have | $want | to_entries | all(.[]; $have[.key] == .value)' >/dev/null \
    || { print -u2 "Granted permissions differ from the manifest. Granted: $(print -rn -- "$granted" | jq -c .permissions). Fix them at $WEB/settings/apps/$slug/permissions"; exit 1 }
  print "Key works. Granted permissions: $(print -rn -- "$granted" | jq -c .permissions)"

  print "Now install it: on the page that opens, choose 'Only select repositories' and pick ${repo:t} only."
  $OPEN "$WEB/apps/$slug/installations/new" || print "Open $WEB/apps/$slug/installations/new yourself."
  installed=0
  for _ in {1..$WAIT_SECONDS}; do
    jwt=$(make_jwt $app_id "$pem")
    if info=$(api_get /repos/$repo/installation $jwt 2>/dev/null); then installed=1; break; fi
    sleep 2
  done
  unset pem jwt
  (( installed )) || { print -u2 "trazo-$app is not installed on $repo yet. Install it at $WEB/apps/$slug/installations/new, then run again with --force only if you want a new App."; exit 1 }
  selection=$(print -rn -- "$info" | jq -r '.repository_selection // "unknown"')
  if [[ $selection == selected ]]; then
    print "Installed on $repo only."
  else
    print "WARNING: installation covers '$selection' repositories, not only $repo. Narrow it in the App's installation settings."
  fi
done

print "\nDone. Secrets in $repo: $($GH_BIN secret list -R $repo --json name -q '[.[].name | select(test("_APP_(ID|PRIVATE_KEY)$"))] | join(", ")')"
print "Next: tell the engineer session the secrets exist. Delete nothing locally: no key file was written."
