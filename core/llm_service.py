"""
LLM Advisory Service — OpenAI Integration
==========================================
Uses GPT to enrich the advisory narrative with:
- Deeper explanation of why this crop/strategy is recommended
- Non-obvious crop alternatives beyond the standard dataset
- Region-specific traditional and modern techniques
- Risk-specific guidance

ARCHITECTURE RULE (enforced in prompt):
  The LLM receives ONLY structured outputs from the rule engine.
  It NEVER decides prices, yield estimates, margin numbers, or risk classifications.
  It ONLY enriches explanation and suggests strategy on top of computed facts.
  This prevents hallucination from contaminating financial advisory output.

FALLBACK:
  If API key is missing, API call fails, or response is malformed,
  the existing template narrative is used silently. App never breaks.
"""

import os
from typing import Optional
from core.models import RecommendationResult

# ── Config ─────────────────────────────────────────────────────────────────────

def _get_openai_client():
    """Lazy-load OpenAI client — returns None if not configured."""
    try:
        import streamlit as st
        api_key = st.secrets.get("openai", {}).get("api_key", "")
        if not api_key or api_key.startswith("sk-your"):
            return None, None
        model = st.secrets.get("openai", {}).get("model", "gpt-4o-mini")
        from openai import OpenAI
        return OpenAI(api_key=api_key), model
    except Exception:
        return None, None


# ── Prompt template ────────────────────────────────────────────────────────────

def _build_prompt(
    result: RecommendationResult,
    soil_name: str,
    climate_zone: str,
    state: str,
    lang: str,
) -> str:
    """
    Builds a controlled, structured prompt.
    Every number comes from the engine — LLM only explains and advises.
    """
    intercrop_names = ", ".join(
        s.companion_name_en for s in result.intercrop_suggestions
    ) if result.intercrop_suggestions else "none identified"

    risk_status = "HIGH RISK — margin below Rs. 5000/acre" if result.risk_flag else "healthy margin"

    language_instruction = (
        "Respond in simple Hindi (Devanagari script). Keep it farmer-friendly."
        if lang == "hi"
        else "Respond in simple English. Keep it farmer-friendly."
    )

    prompt = f"""You are an expert Indian agricultural advisor. A farmer has submitted their farm data and our rule-based engine has calculated the following. Your job is to provide ADDITIONAL advisory value — deeper insights, non-obvious strategies, and region-specific recommendations.

STRICT RULES:
1. Do NOT invent or change any numbers (revenue, cost, margin, yield).
2. Do NOT contradict the risk classification provided.
3. Base recommendations ONLY on the structured data below.
4. If you are unsure about something, say "consult your local KVK" instead of guessing.
5. {language_instruction}

FARM DATA (calculated by rule engine — treat as facts):
- State: {state}
- Crop: {result.crop_name_en}
- Acreage: {result.acreage:.1f} acres
- Gross Revenue: Rs. {result.gross_revenue:,}
- Total Cost: Rs. {result.total_cost:,}
- Net Margin: Rs. {result.net_margin:,}
- Risk Status: {risk_status}
- Potential Cost Savings: Rs. {result.total_reducible_cost:,}
- Soil Type: {soil_name}
- Climate Zone: {climate_zone}
- Intercropping Options Identified: {intercrop_names}
- Price Basis: {result.price_type.upper()}

YOUR TASK — provide 3 to 5 advisory points covering:
1. One non-obvious crop that could perform better than {result.crop_name_en} on {soil_name} soil in {climate_zone} climate — with a realistic reason why
2. One specific technique (ancient or modern) suited to this exact soil type and climate
3. One market/value-chain suggestion specific to {state}
4. If risk is HIGH: one urgent practical intervention the farmer can do THIS season
5. One observation about this soil-crop combination that most farmers in this region overlook

Keep each point to 2-3 sentences. Be specific, not generic. Avoid repeating what the engine already said.

FORMAT: Start each numbered point on a new line. Do NOT run them together in one paragraph."""

    return prompt


# ── Main public function ───────────────────────────────────────────────────────

def enrich_advisory(
    result: RecommendationResult,
    soil_name: str = "Alluvial",
    climate_zone: str = "Tropical",
    state: str = "India",
    lang: str = "en",
) -> Optional[str]:
    """
    Returns LLM-enriched advisory string, or None if API unavailable.

    The caller (3_Recommendations.py) shows this BELOW the engine output,
    clearly labelled as "AI-Powered Additional Advisory".
    If None is returned, the section is simply hidden — no error shown.
    """
    client, model = _get_openai_client()
    if not client:
        return None

    try:
        prompt = _build_prompt(result, soil_name, climate_zone, state, lang)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a knowledgeable Indian agricultural advisor. "
                        "You provide practical, specific, and honest advice. "
                        "You never invent data. You always recommend consulting "
                        "local experts (KVK) for verification."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
            temperature=0.4,  # lower = more consistent, less creative
        )

        content = response.choices[0].message.content
        if content and len(content.strip()) > 50:
            return content.strip()
        return None

    except Exception:
        # Silent fallback — never break the app due to LLM failure
        return None


def translate_advisory(english_advisory: str) -> Optional[str]:
    """
    Translate an English advisory to Hindi (Devanagari).
    Returns the same content in Hindi, or None on failure.
    This ensures Hindi and English PDF sections have identical advisory content.
    """
    if not english_advisory or not english_advisory.strip():
        return None

    client, model = _get_openai_client()
    if not client:
        return None

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional Hindi translator for Indian farmers. "
                        "Translate the following English agricultural advisory into "
                        "simple, farmer-friendly Hindi (Devanagari script). "
                        "Keep the same numbered structure. Do not add or remove any points. "
                        "Do not change any numbers, crop names, or technical terms. "
                        "Keep Rs. amounts as-is. Start each numbered point on a new line."
                    ),
                },
                {"role": "user", "content": english_advisory},
            ],
            max_tokens=800,
            temperature=0.3,
        )

        content = response.choices[0].message.content
        if content and len(content.strip()) > 50:
            return content.strip()
        return None

    except Exception:
        return None


def is_llm_available() -> bool:
    """Returns True if OpenAI is configured and callable."""
    client, _ = _get_openai_client()
    return client is not None
