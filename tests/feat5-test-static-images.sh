#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
CSV_PATH="${CSV_PATH:-sample.csv}"

echo "Feat 5 static image test"
echo "Backend: $BASE_URL"
echo "CSV:     $CSV_PATH"

if [ ! -f "$CSV_PATH" ]; then
  echo "ERROR: CSV file not found at $CSV_PATH"
  exit 1
fi

echo
echo "1) Calling /analyze..."
response_json="$(
  curl -s -X POST "$BASE_URL/analyze" \
    -F "file=@${CSV_PATH}" \
    -F "options={\"mode\":\"boardroom\",\"max_charts\":3}"
)"

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required but not installed. Please install jq and re-run."
  exit 1
fi

report_id="$(echo "$response_json" | jq -r '.report_id')"
first_image_url="$(echo "$response_json" | jq -r '.charts[0].image_url')"

if [ -z "$report_id" ] || [ "$report_id" = "null" ]; then
  echo "ERROR: report_id not found in /analyze response"
  exit 1
fi

if [ -z "$first_image_url" ] || [ "$first_image_url" = "null" ]; then
  echo "ERROR: charts[0].image_url not found in /analyze response"
  exit 1
fi

echo "report_id:      $report_id"
echo "first imageURL: $first_image_url"

full_image_url="$BASE_URL$first_image_url"
tmp_image="$(mktemp /tmp/feat5_chart_XXXXXX.png)"

echo
echo "2) Fetching image from $full_image_url ..."
http_code="$(
  curl -s -o "$tmp_image" -w "%{http_code}" "$full_image_url"
)"

if [ "$http_code" != "200" ]; then
  echo "ERROR: image request failed with HTTP $http_code"
  echo "Saved any error body to: $tmp_image"
  exit 1
fi

size_bytes="$(wc -c < "$tmp_image" | tr -d ' ')"

if [ "$size_bytes" -le 0 ]; then
  echo "ERROR: downloaded image is empty (0 bytes)"
  exit 1
fi

echo "Image downloaded successfully (${size_bytes} bytes)"
echo "Temporary file: $tmp_image"

echo
echo "✅ Feat 5 static images smoke test passed."

