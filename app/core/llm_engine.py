"""
LLM Engine — GPT-4o-mini powered insight generation.

Accepts structured data context (profiling, trend, wow_findings, chart summaries)
and returns an InsightPack with executive_insights, risks, opportunities, and actions.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.api.schemas import (
    ActionItem,
    InsightItem,
    InsightPack,
    ProfilingSummary,
    TrendSummary,
    WowFinding,
)

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"
MAX_TOKENS = 2048
TEMPERATURE = 0.4

SYSTEM_PROMPT = """\
You are **Boardroom AI**, a senior data analyst that produces concise, actionable
business insights from structured data summaries.

You will receive a JSON object with the following sections:
- **dataset**: filename, row/column counts
- **profiling**: column types, missing values, outliers, top values
- **trend**: time-series direction, KPI, percentage change
- **wow_findings**: anomalies and notable patterns detected
- **chart_summaries**: types and titles of generated charts

Respond with **valid JSON only** (no markdown, no commentary) matching this schema:
{
  "executive_insights": [{"text": "...", "evidence": "..."}],
  "risks":              [{"text": "...", "evidence": "..."}],
  "opportunities":      [{"text": "...", "evidence": "..."}],
  "actions":            [{"text": "...", "priority": "low|medium|high"}]
}

Rules:
1. Return 2-5 items per section.
2. Keep each "text" under 80 words.
3. Ground every insight in evidence from the data context provided.
4. "priority" must be one of: "low", "medium", "high".
5. Do NOT invent data values that are not in the context.
"""


def _get_client() -> OpenAI:
    """Create an OpenAI client using the API key from environment."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set. "
            "Create a .env file in the project root with: OPENAI_API_KEY=sk-..."
        )
    return OpenAI(api_key=api_key)


def _build_data_context(
    filename: str,
    rows: int,
    columns: int,
    profiling: ProfilingSummary,
    trend: TrendSummary,
    wow_findings: List[WowFinding],
    chart_summaries: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Build a compact JSON-serialisable context dict for the LLM prompt."""

    # Compact profiling: just the essentials per column
    col_summaries = []
    for cp in profiling.column_profiles:
        entry: Dict[str, Any] = {"name": cp.name, "dtype": cp.dtype}
        if cp.stats:
            entry["stats"] = {
                "min": cp.stats.min,
                "max": cp.stats.max,
                "mean": round(cp.stats.mean, 2),
                "median": cp.stats.median,
            }
        if cp.outliers and cp.outliers.count > 0:
            entry["outliers"] = cp.outliers.count
        if cp.top_value:
            entry["top_value"] = f"{cp.top_value.value} ({cp.top_value.count})"
        col_summaries.append(entry)

    # Missing values — only columns with missing data
    missing = {
        col: count
        for col, count in profiling.missing_by_column.items()
        if count > 0
    }

    # Trend
    trend_ctx: Dict[str, Any] = {"available": trend.available}
    if trend.available and trend.metrics:
        trend_ctx.update({
            "date_column": trend.date_column,
            "kpi_column": trend.kpi_column,
            "pct_change": trend.metrics.pct_change,
            "start_value": trend.metrics.start_value,
            "end_value": trend.metrics.end_value,
            "summary": trend.summary,
        })

    # Wow findings
    wow = [
        {
            "type": f.type,
            "severity": f.severity,
            "title": f.title,
            "evidence": f.evidence,
        }
        for f in wow_findings
    ]

    return {
        "dataset": {"filename": filename, "rows": rows, "columns": columns},
        "profiling": {"columns": col_summaries, "missing": missing},
        "trend": trend_ctx,
        "wow_findings": wow,
        "chart_summaries": chart_summaries,
    }


def _parse_llm_response(raw: str) -> InsightPack:
    """Parse the LLM JSON response into an InsightPack, with fallback."""
    # Strip markdown code fences if the model wraps its response
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove opening ```json or ``` and closing ```
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    data = json.loads(cleaned)

    executive_insights = [
        InsightItem(text=item["text"], evidence=item.get("evidence", ""))
        for item in data.get("executive_insights", [])
    ]
    risks = [
        InsightItem(text=item["text"], evidence=item.get("evidence", ""))
        for item in data.get("risks", [])
    ]
    opportunities = [
        InsightItem(text=item["text"], evidence=item.get("evidence", ""))
        for item in data.get("opportunities", [])
    ]
    actions = [
        ActionItem(text=item["text"], priority=item.get("priority", "medium"))
        for item in data.get("actions", [])
    ]

    return InsightPack(
        executive_insights=executive_insights,
        risks=risks,
        opportunities=opportunities,
        actions=actions,
    )


def generate_insights(
    filename: str,
    rows: int,
    columns: int,
    profiling: ProfilingSummary,
    trend: TrendSummary,
    wow_findings: List[WowFinding],
    chart_summaries: List[Dict[str, str]],
) -> InsightPack:
    """
    Call GPT-4o-mini with the data context and return structured insights.

    Returns an empty InsightPack (with a warning log) if the API key is missing
    or the call fails, so the pipeline never crashes.
    """
    try:
        client = _get_client()
    except RuntimeError as exc:
        logger.warning("LLM skipped: %s", exc)
        return InsightPack(
            executive_insights=[
                InsightItem(
                    text="LLM insights unavailable — OPENAI_API_KEY not configured.",
                    evidence="Set the OPENAI_API_KEY environment variable to enable AI-powered insights.",
                )
            ],
            risks=[],
            opportunities=[],
            actions=[],
        )

    context = _build_data_context(
        filename, rows, columns, profiling, trend, wow_findings, chart_summaries
    )

    user_message = json.dumps(context, indent=2, default=str)

    try:
        logger.info("Calling %s for insights (context: %d chars)", MODEL, len(user_message))
        response = client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        logger.info("LLM response received (%d chars)", len(raw))
        return _parse_llm_response(raw)

    except Exception as exc:
        logger.error("LLM call failed: %s", exc, exc_info=True)
        return InsightPack(
            executive_insights=[
                InsightItem(
                    text="LLM insights could not be generated.",
                    evidence=f"Error: {exc}",
                )
            ],
            risks=[],
            opportunities=[],
            actions=[],
        )
