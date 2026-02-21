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
    ChatContext,
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


# ── KPI Tile suggestion ────────────────────────────────────────────────

KPI_SYSTEM_PROMPT = """\
You are **Boardroom AI**, a senior data analyst. Given a list of columns with their
data types and summary statistics, decide which columns deserve a KPI tile on a
dashboard and **what aggregation makes sense** for each.

Respond with **valid JSON only** (no markdown, no commentary) matching this schema:
{
  "tiles": [
    {
      "column": "column_name",
      "agg": "sum | mean | median | max | min | count | count_distinct | latest | range",
      "label": "Human-friendly tile label",
      "sublabel_agg": "mean | min | max | null"
    }
  ]
}

Guidelines (use column NAME and MEANING to decide):
- Monetary / additive quantities (revenue, sales, cost, amount, profit, income, spend,
  budget, price × quantity) → **sum**, sublabel_agg "mean".
- Rates / percentages / ratios (margin_pct, conversion_rate, score, rating, growth_rate,
  discount_pct) → **mean** (or **median**), sublabel_agg "max".
- Counts / discrete units (units, orders, visits, users, tickets, items) → **sum**,
  sublabel_agg "mean".
- IDs, codes, serial numbers → **SKIP** (never create a tile for these).
- Categorical text columns → You MAY create one tile with agg "count_distinct" if
  it represents an important entity (e.g. "region", "product", "customer").
- Date/datetime columns → **SKIP** (dates are not KPI-worthy).
- If a column name is ambiguous, pick the most reasonable aggregation.
- Return 3-8 tiles, ordered by business importance (most important first).
- Do NOT invent column names that are not in the input.
"""


def generate_kpi_suggestions(
    profiling: ProfilingSummary,
    rows: int,
) -> Optional[List[Dict[str, Any]]]:
    """
    Ask GPT-4o-mini which columns deserve KPI tiles and what aggregation to use.

    Returns a list of dicts like:
        [{"column": "revenue", "agg": "sum", "label": "Total Revenue", "sublabel_agg": "mean"}, ...]
    Returns None if LLM is unavailable.
    """
    try:
        client = _get_client()
    except RuntimeError as exc:
        logger.warning("KPI suggestions skipped: %s", exc)
        return None

    # Build compact column info for the LLM
    col_info = []
    for cp in profiling.column_profiles:
        entry: Dict[str, Any] = {"name": cp.name, "dtype": cp.dtype}
        if cp.stats:
            entry["stats"] = {
                "min": cp.stats.min,
                "max": cp.stats.max,
                "mean": round(cp.stats.mean, 2),
                "median": cp.stats.median,
                "std": round(cp.stats.std, 2),
            }
        if cp.top_value:
            entry["top_value"] = f"{cp.top_value.value} ({cp.top_value.count})"
        entry["unique_count"] = profiling.unique_by_column.get(cp.name, 0)
        col_info.append(entry)

    user_msg = json.dumps({"rows": rows, "columns": col_info}, indent=2)

    try:
        logger.info("Calling %s for KPI tile suggestions", MODEL)
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.2,
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": KPI_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        tiles = data.get("tiles", [])
        logger.info("LLM suggested %d KPI tiles", len(tiles))
        return tiles
    except Exception as exc:
        logger.error("KPI suggestion LLM call failed: %s", exc, exc_info=True)
        return None


# ── Chat Context generation ──────────────────────────────────────────

CHAT_SYSTEM_PROMPT = """\
You are **Boardroom AI**, a senior data analyst. Given a structured data summary,
produce a chat context that helps a user ask follow-up questions about their dataset.

Respond with **valid JSON only** (no markdown, no commentary) matching this schema:
{
  "dataset_brief": "A 2-3 sentence plain-English summary of the dataset.",
  "evidence_pack": ["key fact 1", "key fact 2", ...],
  "suggested_questions": ["question 1?", "question 2?", ...]
}

Rules:
1. dataset_brief: 2-3 sentences summarising what the data contains and its key characteristics.
2. evidence_pack: 4-8 bullet facts drawn directly from the data context (trends, outliers, top values).
3. suggested_questions: 4-6 natural-language questions a business user might ask about this data.
4. Do NOT invent data values that are not in the context.
"""


def generate_chat_context(
    filename: str,
    rows: int,
    columns: int,
    profiling: ProfilingSummary,
    trend: TrendSummary,
    wow_findings: List[WowFinding],
    chart_summaries: List[Dict[str, str]],
) -> ChatContext:
    """
    Call GPT-4o-mini to generate a ChatContext with dataset_brief,
    evidence_pack, and suggested_questions.

    Returns a fallback ChatContext if the API key is missing or the call fails.
    """
    try:
        client = _get_client()
    except RuntimeError as exc:
        logger.warning("Chat context skipped: %s", exc)
        return ChatContext(
            dataset_brief="Chat context unavailable — OPENAI_API_KEY not configured.",
            evidence_pack=[],
            suggested_questions=[],
        )

    context = _build_data_context(
        filename, rows, columns, profiling, trend, wow_findings, chart_summaries
    )
    user_message = json.dumps(context, indent=2, default=str)

    try:
        logger.info("Calling %s for chat context", MODEL)
        response = client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        return ChatContext(
            dataset_brief=data.get("dataset_brief", ""),
            evidence_pack=data.get("evidence_pack", []),
            suggested_questions=data.get("suggested_questions", []),
        )
    except Exception as exc:
        logger.error("Chat context LLM call failed: %s", exc, exc_info=True)
        return ChatContext(
            dataset_brief=f"Could not generate chat context: {exc}",
            evidence_pack=[],
            suggested_questions=[],
        )


# ── Conversational Chat ───────────────────────────────────────────

CHAT_CONVERSATION_PROMPT = """\
You are **Boardroom AI**, a helpful data analyst chatbot. You answer questions
about a dataset the user has uploaded and analysed.

You are given:
- A brief description of the dataset.
- An evidence pack of key facts.
- The conversation history so far.

Rules:
1. Answer ONLY based on the evidence provided. If you don\'t know, say so.
2. Keep answers concise (under 150 words) unless the user asks for detail.
3. Be professional but friendly.
4. At the end, suggest 2-3 natural follow-up questions in a JSON field.

Respond with **valid JSON only**:
{
  "reply": "Your answer here...",
  "suggested_followups": ["follow-up 1?", "follow-up 2?"]
}
"""


def chat_with_data(
    message: str,
    dataset_brief: str,
    evidence_pack: List[str],
    history: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Have a conversation about the dataset using GPT-4o-mini.

    Returns {"reply": str, "suggested_followups": list[str]}.
    """
    try:
        client = _get_client()
    except RuntimeError as exc:
        return {
            "reply": f"Chat unavailable: {exc}",
            "suggested_followups": [],
        }

    # Build the system context with dataset info
    context_block = f"""Dataset Summary:\n{dataset_brief}\n\nKey Facts:\n"""
    for i, fact in enumerate(evidence_pack, 1):
        context_block += f"{i}. {fact}\n"

    messages = [
        {"role": "system", "content": CHAT_CONVERSATION_PROMPT + "\n\n" + context_block},
    ]

    # Add conversation history (max last 20 turns)
    for turn in history[-20:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    # Add the current user message
    messages.append({"role": "user", "content": message})

    try:
        logger.info("Chat call to %s (%d history turns)", MODEL, len(history))
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.5,
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=messages,
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        return {
            "reply": data.get("reply", ""),
            "suggested_followups": data.get("suggested_followups", []),
        }
    except Exception as exc:
        logger.error("Chat LLM call failed: %s", exc, exc_info=True)
        return {
            "reply": f"Sorry, I couldn't process your question: {exc}",
            "suggested_followups": [],
        }
