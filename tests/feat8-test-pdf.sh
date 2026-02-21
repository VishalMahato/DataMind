#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
CSV_PATH="${CSV_PATH:-tests/sample.csv}"
OUTPUT_PDF="${OUTPUT_PDF:-feat8-test-report.pdf}"

echo "Feat 8 HTML/PDF test"
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
report_json="$(
  curl -s -X POST "$BASE_URL/analyze" \
    -F "file=@${CSV_PATH}" \
    -F "options={\"mode\":\"boardroom\",\"max_charts\":3}"
)"

report_id="$(echo "$report_json" | jq -r '.report_id')"

echo "report_id: $report_id"

echo
echo "2) Calling /pdf..."
pdf_bytes="$(
  curl -s -X POST "$BASE_URL/pdf" \
    -H "Content-Type: application/json" \
    -d "{\"report\": $report_json}"
)"

echo "$pdf_bytes" > "$OUTPUT_PDF"

size_bytes=$(wc -c < "$OUTPUT_PDF")
echo "PDF size: $size_bytes bytes"

if [ "$size_bytes" -lt 1000 ]; then
  echo "ERROR: PDF file size looks too small"
  exit 1
fi

echo
echo "✅ Feat 8 HTML/PDF smoke test passed. Output: $OUTPUT_PDF"

