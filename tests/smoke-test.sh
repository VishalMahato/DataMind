#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Boardroom AI — Full Workflow Smoke Test
# Tests: health, analyze (happy + error paths), charts, PDF stub
# ─────────────────────────────────────────────────────────────
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV_PATH="${CSV_PATH:-$SCRIPT_DIR/sample.csv}"
PASS=0
FAIL=0

# ── helpers ──────────────────────────────────────────────────
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
red()    { printf "\033[31m%s\033[0m\n" "$*"; }
bold()   { printf "\033[1m%s\033[0m\n" "$*"; }

pass() { PASS=$((PASS + 1)); green "  ✅ $1"; }
fail() { FAIL=$((FAIL + 1)); red   "  ❌ $1"; }

assert_eq() {
  local label="$1" actual="$2" expected="$3"
  if [ "$actual" = "$expected" ]; then
    pass "$label (got: $actual)"
  else
    fail "$label (expected: $expected, got: $actual)"
  fi
}

assert_ne() {
  local label="$1" actual="$2" forbidden="$3"
  if [ "$actual" != "$forbidden" ]; then
    pass "$label (got: $actual)"
  else
    fail "$label (should NOT be: $forbidden)"
  fi
}

assert_gt() {
  local label="$1" actual="$2" threshold="$3"
  if [ "$actual" -gt "$threshold" ] 2>/dev/null; then
    pass "$label ($actual > $threshold)"
  else
    fail "$label (expected > $threshold, got: $actual)"
  fi
}

# ── pre-flight checks ───────────────────────────────────────
bold "═══════════════════════════════════════════"
bold " Boardroom AI — Full Workflow Smoke Test"
bold "═══════════════════════════════════════════"
echo "Backend: $BASE_URL"
echo "CSV:     $CSV_PATH"
echo

if [ ! -f "$CSV_PATH" ]; then
  red "ERROR: CSV file not found at $CSV_PATH"; exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  red "ERROR: jq is required but not installed."; exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  red "ERROR: curl is required but not installed."; exit 1
fi

# ─────────────────────────────────────────────────────────────
# 1. Health check
# ─────────────────────────────────────────────────────────────
bold "1) GET /health"
health_code="$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")"
assert_eq "HTTP 200" "$health_code" "200"

health_status="$(curl -s "$BASE_URL/health" | jq -r '.status')"
assert_eq "status=ok" "$health_status" "ok"

# ─────────────────────────────────────────────────────────────
# 2. Upload CSV → /analyze (happy path)
# ─────────────────────────────────────────────────────────────
bold ""
bold "2) POST /analyze — happy path (sample.csv)"
response_json="$(
  curl -s -w "\n%{http_code}" -X POST "$BASE_URL/analyze" \
    -F "file=@${CSV_PATH}" \
    -F 'options={"mode":"boardroom","max_charts":3}'
)"
http_body="$(echo "$response_json" | sed '$d')"
http_code="$(echo "$response_json" | tail -1)"
assert_eq "HTTP 200" "$http_code" "200"

# ── report_version & meta ────────────────────────────────────
report_version="$(echo "$http_body" | jq -r '.report_version')"
assert_eq "report_version=v1" "$report_version" "v1"

report_id="$(echo "$http_body" | jq -r '.report_id')"
assert_ne "report_id not null" "$report_id" "null"

generated_at="$(echo "$http_body" | jq -r '.generated_at')"
assert_ne "generated_at set" "$generated_at" "null"

mode="$(echo "$http_body" | jq -r '.mode')"
assert_eq "mode=boardroom" "$mode" "boardroom"

# ── dataset_meta ─────────────────────────────────────────────
filename="$(echo "$http_body" | jq -r '.dataset_meta.filename')"
assert_eq "filename=sample.csv" "$filename" "sample.csv"

rows="$(echo "$http_body" | jq -r '.dataset_meta.rows')"
assert_gt "rows > 0" "$rows" 0

columns="$(echo "$http_body" | jq -r '.dataset_meta.columns')"
assert_gt "columns > 0" "$columns" 0

size_bytes="$(echo "$http_body" | jq -r '.dataset_meta.size_bytes')"
assert_gt "size_bytes > 0" "$size_bytes" 0

# ── data_preview ─────────────────────────────────────────────
preview_col_count="$(echo "$http_body" | jq '.data_preview.columns | length')"
assert_gt "preview columns > 0" "$preview_col_count" 0

preview_row_count="$(echo "$http_body" | jq '.data_preview.rows | length')"
assert_gt "preview rows > 0" "$preview_row_count" 0

# ── cleaning_log ─────────────────────────────────────────────
cleaning_count="$(echo "$http_body" | jq '.cleaning_log | length')"
assert_gt "cleaning_log has entries" "$cleaning_count" 0

first_cleaning_action="$(echo "$http_body" | jq -r '.cleaning_log[0].action')"
assert_ne "cleaning_log[0].action set" "$first_cleaning_action" "null"

# ── profiling ────────────────────────────────────────────────
profile_count="$(echo "$http_body" | jq '.profiling.column_profiles | length')"
assert_gt "column_profiles > 0" "$profile_count" 0

missing_keys="$(echo "$http_body" | jq '.profiling.missing_by_column | keys | length')"
assert_gt "missing_by_column populated" "$missing_keys" 0

unique_keys="$(echo "$http_body" | jq '.profiling.unique_by_column | keys | length')"
assert_gt "unique_by_column populated" "$unique_keys" 0

# check a numeric column has stats
has_stats="$(echo "$http_body" | jq '[.profiling.column_profiles[] | select(.stats != null)] | length')"
assert_gt "at least 1 numeric column with stats" "$has_stats" 0

# ── trend ────────────────────────────────────────────────────
trend_available="$(echo "$http_body" | jq -r '.trend.available')"
assert_eq "trend.available=true" "$trend_available" "true"

trend_date_col="$(echo "$http_body" | jq -r '.trend.date_column')"
assert_ne "trend.date_column set" "$trend_date_col" "null"

trend_kpi_col="$(echo "$http_body" | jq -r '.trend.kpi_column')"
assert_ne "trend.kpi_column set" "$trend_kpi_col" "null"

pct_change="$(echo "$http_body" | jq -r '.trend.metrics.pct_change')"
assert_ne "trend.metrics.pct_change set" "$pct_change" "null"

# ── wow_findings ─────────────────────────────────────────────
wow_count="$(echo "$http_body" | jq '.wow_findings | length')"
assert_gt "wow_findings >= 1" "$wow_count" 0

first_wow_type="$(echo "$http_body" | jq -r '.wow_findings[0].type')"
assert_ne "wow_findings[0].type set" "$first_wow_type" "null"

# ── charts ───────────────────────────────────────────────────
chart_count="$(echo "$http_body" | jq '.charts | length')"
assert_gt "charts >= 1" "$chart_count" 0

first_chart_type="$(echo "$http_body" | jq -r '.charts[0].chart_type')"
assert_ne "charts[0].chart_type set" "$first_chart_type" "null"

first_image_url="$(echo "$http_body" | jq -r '.charts[0].image_url')"
assert_ne "charts[0].image_url set" "$first_image_url" "null"

# ── insights structure ───────────────────────────────────────
has_insights="$(echo "$http_body" | jq 'has("insights")')"
assert_eq "insights key present" "$has_insights" "true"

has_exec="$(echo "$http_body" | jq '.insights | has("executive_insights")')"
assert_eq "insights.executive_insights present" "$has_exec" "true"

has_risks="$(echo "$http_body" | jq '.insights | has("risks")')"
assert_eq "insights.risks present" "$has_risks" "true"

has_opps="$(echo "$http_body" | jq '.insights | has("opportunities")')"
assert_eq "insights.opportunities present" "$has_opps" "true"

has_actions="$(echo "$http_body" | jq '.insights | has("actions")')"
assert_eq "insights.actions present" "$has_actions" "true"

# ─────────────────────────────────────────────────────────────
# 3. Fetch chart images
# ─────────────────────────────────────────────────────────────
bold ""
bold "3) Fetch chart images from /static"
chart_urls="$(echo "$http_body" | jq -r '.charts[].image_url')"

for url in $chart_urls; do
  full_url="$BASE_URL$url"
  tmp_img="$(mktemp /tmp/smoke_chart_XXXXXXXX)"
  img_code="$(curl -s -o "$tmp_img" -w "%{http_code}" "$full_url")"
  assert_eq "GET $url → 200" "$img_code" "200"

  img_size="$(wc -c < "$tmp_img" | tr -d ' ')"
  assert_gt "image $url > 0 bytes" "$img_size" 0
  rm -f "$tmp_img"
done

# ─────────────────────────────────────────────────────────────
# 4. Error path — upload non-CSV file
# ─────────────────────────────────────────────────────────────
bold ""
bold "4) POST /analyze — error: non-CSV file"
tmp_txt="$(mktemp /tmp/smoke_bad_XXXXXXXX)"
echo "this is not a csv" > "$tmp_txt"
err_code="$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/analyze" \
  -F "file=@${tmp_txt};filename=bad_file.txt")"
assert_eq "non-CSV → HTTP 400" "$err_code" "400"
rm -f "$tmp_txt"

# ─────────────────────────────────────────────────────────────
# 5. Error path — upload malformed CSV
# ─────────────────────────────────────────────────────────────
bold ""
bold "5) POST /analyze — error: empty CSV"
tmp_bad_csv="$(mktemp /tmp/smoke_malformed_XXXXXXXX)"
: > "$tmp_bad_csv"  # truncate to 0 bytes
bad_csv_code="$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/analyze" \
  -F "file=@${tmp_bad_csv};filename=empty.csv")"
assert_eq "empty CSV → HTTP 422" "$bad_csv_code" "422"
rm -f "$tmp_bad_csv"

# ─────────────────────────────────────────────────────────────
# 6. POST /pdf — requires report body (expect 400 without it)
# ─────────────────────────────────────────────────────────────
bold ""
bold "6) POST /pdf — missing report body (400 expected)"
pdf_code="$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/pdf" \
  -H "Content-Type: application/json" \
  -d "{\"report_id\":\"$report_id\"}")"
assert_eq "PDF missing report → HTTP 400" "$pdf_code" "400"

# ─────────────────────────────────────────────────────────────
# 7. Response schema completeness
# ─────────────────────────────────────────────────────────────
bold ""
bold "7) Schema completeness — verify all top-level keys"
required_keys="report_version report_id generated_at mode dataset_meta data_preview cleaning_log profiling trend wow_findings charts insights"
for key in $required_keys; do
  has_key="$(echo "$http_body" | jq "has(\"$key\")")"
  assert_eq "key '$key' present" "$has_key" "true"
done

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
echo
bold "═══════════════════════════════════════════"
total=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
  green " ALL $total TESTS PASSED ✅"
else
  red   " $FAIL / $total TESTS FAILED ❌"
fi
bold "═══════════════════════════════════════════"

exit "$FAIL"
