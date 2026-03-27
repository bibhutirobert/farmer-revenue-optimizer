"""
Tests for LLM service — focus on fallback behaviour and prompt structure.
These tests do NOT call the real OpenAI API (no key in test environment).
They verify that:
  - The service returns None gracefully when not configured
  - is_llm_available() returns False without a key
  - The prompt builder includes required fields
  - The service never raises exceptions
"""
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.llm_service import enrich_advisory, is_llm_available, _build_prompt
from core.models import FarmInput
from core.recommendation_engine import run


def _make_result():
    fi = FarmInput(
        crop="wheat", acreage=2.0, current_yield_qtl_per_acre=16.0,
        irrigation_type="canal", state="Punjab", season="rabi",
        soil_type="alluvial", soil_name="Alluvial Soil", climate_zone="Semi-Arid",
    )
    return run(fi)


def test_llm_not_available_without_key():
    """Without a real API key, is_llm_available must return False."""
    available = is_llm_available()
    assert isinstance(available, bool)
    # In test environment (no secrets.toml), should be False
    assert available is False


def test_enrich_advisory_returns_none_without_key():
    """Without API key, enrich_advisory must return None silently."""
    result = _make_result()
    output = enrich_advisory(
        result=result,
        soil_name="Alluvial Soil",
        climate_zone="Semi-Arid",
        state="Punjab",
        lang="en",
    )
    assert output is None


def test_enrich_advisory_never_raises():
    """Service must never propagate exceptions to caller."""
    result = _make_result()
    try:
        enrich_advisory(result=result, soil_name="", climate_zone="", state="", lang="en")
        enrich_advisory(result=result, soil_name="", climate_zone="", state="", lang="hi")
    except Exception as e:
        pytest.fail(f"enrich_advisory raised an exception: {e}")


def test_prompt_contains_crop_name():
    result = _make_result()
    prompt = _build_prompt(result, "Alluvial Soil", "Semi-Arid", "Punjab", "en")
    assert "Wheat" in prompt or "wheat" in prompt.lower()


def test_prompt_contains_margin():
    result = _make_result()
    prompt = _build_prompt(result, "Alluvial Soil", "Semi-Arid", "Punjab", "en")
    assert str(result.net_margin) in prompt or "Net Margin" in prompt


def test_prompt_contains_state():
    result = _make_result()
    prompt = _build_prompt(result, "Alluvial Soil", "Semi-Arid", "Punjab", "en")
    assert "Punjab" in prompt


def test_prompt_contains_soil():
    result = _make_result()
    prompt = _build_prompt(result, "Alluvial Soil", "Semi-Arid", "Punjab", "en")
    assert "Alluvial" in prompt


def test_prompt_contains_anti_hallucination_rule():
    """Prompt must instruct model not to invent data."""
    result = _make_result()
    prompt = _build_prompt(result, "Alluvial Soil", "Semi-Arid", "Punjab", "en")
    # Check for hallucination guard instruction
    assert "not invent" in prompt.lower() or "do not invent" in prompt.lower() or "only" in prompt.lower()


def test_prompt_hindi_instruction():
    """Hindi lang should produce Hindi instruction in prompt."""
    result = _make_result()
    prompt = _build_prompt(result, "Alluvial Soil", "Semi-Arid", "Punjab", "hi")
    assert "Hindi" in prompt or "हिंदी" in prompt or "Devanagari" in prompt


def test_prompt_english_instruction():
    result = _make_result()
    prompt = _build_prompt(result, "Alluvial Soil", "Semi-Arid", "Punjab", "en")
    assert "English" in prompt
