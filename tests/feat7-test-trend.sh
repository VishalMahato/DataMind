#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
CSV_PATH="${CSV_PATH:-sample.csv}"

echo "Feat 7 trend engine test"
echo "Backend: $BASE_URL"
echo "CSV:     $CSV_PATH"

if [ ! -f "$CSV_PATH" ]; then
  echo "ERROR: CSV file not found at $CSV_PATH"
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required but not installed."
  exit 1
fi

echo
echo "1) Calling /analyze..."
response_json="$(
  curl -s -X POST "$BASE_URL/analyze" \
    -F "file=@${CSV_PATH}" \
    -F "options={\"mode\":\"boardroom\",\"max_charts\":3}"
)"

available="$(echo "$response_json" | jq -r '.trend.available')"
pct_change="$(echo "$response_json" | jq -r '.trend.metrics.pct_change')"
trend_findings_count="$(echo "$response_json" | jq '[.wow_findings[] | select(.type=="trend_shift")] | length')"

echo "trend.available:          $available"
echo "trend.metrics.pct_change: $pct_change"
echo "trend_shift findings:     $trend_findings_count"

if [ "$available" != "true" ]; then
  echo "ERROR: trend.available is not true"
  exit 1
fi

if [ "$pct_change" = "null" ]; then
  echo "ERROR: trend.metrics.pct_change is null"
  exit 1
fi

echo
echo "✅ Feat 7 trend engine smoke test passed."

