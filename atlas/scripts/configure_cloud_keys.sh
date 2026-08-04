#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"

printf 'Keys are entered silently and are never printed.\n'
read -r -s -p 'Deepgram API key: ' deepgram_key
printf '\n'
read -r -s -p 'Cartesia API key: ' cartesia_key
printf '\n'

if [[ -z "$deepgram_key" || -z "$cartesia_key" ]]; then
  printf 'Both keys are required; .env was not changed.\n' >&2
  exit 1
fi

umask 077
tmp_file="$(mktemp "$PROJECT_DIR/.env.tmp.XXXXXX")"
trap 'rm -f "$tmp_file"' EXIT

if [[ -f "$ENV_FILE" ]]; then
  grep -v -E '^(DEEPGRAM_API_KEY|CARTESIA_API_KEY)=' "$ENV_FILE" > "$tmp_file" || true
fi
printf 'DEEPGRAM_API_KEY=%s\n' "$deepgram_key" >> "$tmp_file"
printf 'CARTESIA_API_KEY=%s\n' "$cartesia_key" >> "$tmp_file"
chmod 600 "$tmp_file"
mv "$tmp_file" "$ENV_FILE"
trap - EXIT
unset deepgram_key cartesia_key

printf 'Cloud speech keys saved securely to %s (mode 600).\n' "$ENV_FILE"
printf 'Run ./scripts/preflight_device.sh to verify provider readiness.\n'
