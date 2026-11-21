#!/usr/bin/env bash
# Store a secret in AWS Secrets Manager. YOU run this; the value is never echoed or logged.
# Usage: scripts/put_secret.sh <secret-name> [aws-profile] [region]
set -euo pipefail
name="${1:?usage: put_secret.sh <secret-name> [profile] [region]}"
profile="${2:-${AWS_PROFILE:-default}}"
region="${3:-${AWS_REGION:-us-east-2}}"
read -r -s -p "Value for ${name} (input hidden; for a file, leave empty and set FILE=path): " value; echo
if [[ -z "${value}" && -n "${FILE:-}" ]]; then value="$(cat "${FILE}")"; fi
[[ -n "${value}" ]] || { echo "empty value, aborting" >&2; exit 1; }
tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT; chmod 600 "$tmp"
printf '%s' "$value" > "$tmp"; unset value
if aws secretsmanager describe-secret --secret-id "$name" --profile "$profile" --region "$region" >/dev/null 2>&1; then
  aws secretsmanager put-secret-value --secret-id "$name" --secret-string "file://$tmp" --profile "$profile" --region "$region" >/dev/null
else
  aws secretsmanager create-secret --name "$name" --secret-string "file://$tmp" --profile "$profile" --region "$region" >/dev/null
fi
echo "stored ${name} in ${region} (value not shown)"
