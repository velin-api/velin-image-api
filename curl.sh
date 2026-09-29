#!/usr/bin/env bash
# VELIN image generation with curl + jq: submit, poll, download.
# Check balance:  curl https://72agi.com/api/credits -H "Authorization: Bearer $VELIN_API_KEY"
#   export VELIN_API_KEY=your_key
#   ./curl.sh "a quiet room, cream light" [model] [size] [resolution]
set -euo pipefail

BASE_URL="${VELIN_BASE_URL:-https://72agi.com}"
: "${VELIN_API_KEY:?Set VELIN_API_KEY first}"
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }

PROMPT="${1:?Usage: $0 \"prompt\" [model] [size] [resolution]}"
MODEL="${2:-gpt-image-2.5-flare}"
SIZE="${3:-1:1}"
RES="${4:-1K}"

# 1) Create task (multipart form). Add  -F "refs=@./source.png"  (repeatable, max 14) for reference images.
for attempt in 1 2 3 4 5; do
  RESP=$(curl -sS -w '\n%{http_code}' -X POST "$BASE_URL/api/generate" \
    -H "Authorization: Bearer $VELIN_API_KEY" \
    -F "prompt=$PROMPT" -F "model=$MODEL" -F "size=$SIZE" -F "resolution=$RES")
  CODE=$(tail -n1 <<<"$RESP"); BODY=$(sed '$d' <<<"$RESP")
  if [[ "$CODE" == 429 ]]; then            # rate limited (8 single generations/min): back off
    echo "429 rate limited, retrying in $((attempt * 10))s" >&2; sleep $((attempt * 10)); continue
  fi
  break
done
if [[ "$CODE" == 402 ]]; then
  echo "Insufficient credits: need $(jq -r '.need' <<<"$BODY"), have $(jq -r '.have' <<<"$BODY")" >&2; exit 1
fi
if [[ "$CODE" != 2* ]]; then echo "Submit failed (HTTP $CODE): $BODY" >&2; exit 1; fi
ID=$(jq -r '.id' <<<"$BODY")
echo "task $ID queued" >&2

# 2) Poll every 5 s until succeeded / failed (give up after 15 min)
for _ in $(seq 1 180); do
  sleep 5
  JOB=$(curl -sS "$BASE_URL/api/task/$ID" -H "Authorization: Bearer $VELIN_API_KEY") || continue
  STATUS=$(jq -r '.status // empty' <<<"$JOB")
  echo "status: ${STATUS:-?}" >&2
  case "$STATUS" in
    succeeded)
      URL="$BASE_URL$(jq -r '.url' <<<"$JOB")"   # url is site-relative, e.g. /outputs/<id>.png
      # 3) Download
      curl -sS -o "$ID.png" "$URL" -H "Authorization: Bearer $VELIN_API_KEY"
      echo "saved $ID.png ($URL)"; exit 0 ;;
    failed)
      echo "failed (not charged): $(jq -r '.error' <<<"$JOB")" >&2; exit 1 ;;
  esac
done
echo "timed out waiting for task $ID" >&2; exit 1
