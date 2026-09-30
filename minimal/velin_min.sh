#!/usr/bin/env bash
# Smallest useful VELIN client: curl + jq.  Usage: VELIN_API_KEY=... bash velin_min.sh "prompt" [model] [out.png]
set -euo pipefail
BASE=${VELIN_BASE_URL:-https://72agi.com}; AUTH="Authorization: Bearer $VELIN_API_KEY"
id=$(curl -sf -X POST "$BASE/api/generate" -H "$AUTH" \
  -F "prompt=$1" -F "model=${2:-nano-banana-pro}" -F size=1:1 -F resolution=1K | jq -r .id)
while :; do
  sleep 4; job=$(curl -sf "$BASE/api/task/$id" -H "$AUTH"); st=$(jq -r .status <<<"$job")
  [ "$st" = failed ] && { echo "failed: $(jq -r .error <<<"$job")" >&2; exit 1; }
  [ "$st" = succeeded ] && break
done
curl -sf -H "$AUTH" -o "${3:-out.png}" "$BASE$(jq -r .url <<<"$job")" && echo "saved ${3:-out.png}"
