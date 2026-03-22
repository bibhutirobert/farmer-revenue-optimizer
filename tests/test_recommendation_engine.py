import pytest
from core.models import FarmInput
from core.recommendation_engine import run, MARGIN_WARNING_THRESHOLD_PER_ACRE


def _make_input(**kwargs) -> FarmInput:
    defaults = dict(
        crop="rice",
        acreage=2.0,
        current_yield_qtl_per_acre=12.0,
        irrigation_type="canal",
        state="West Bengal",
        season="kharif",
    )
    defaults.update(kwargs)
    return FarmInput(**defaults)


def test_result_fields_populated():
    result = run(_make_input())
    assert result.crop_name_en == "Rice (Paddy)"
    assert result.gross_revenue > 0
    assert result.total_cost > 0
    assert len(result.cost_items) == 6
    assert isinstance(result.narrative_en, str) and len(result.narrative_en) > 20
    assert isinstance(result.narrative_hi, str) and len(result.narrative_hi) > 20


def test_gross_revenue_formula():
    result = run(_make_input(acreage=2.0, current_yield_qtl_per_acre=12.0))
    assert result.gross_revenue == 2183 * 12 * 2


def test_net_margin_equals_revenue_minus_cost():
    result = run(_make_input())
    assert result.net_margin == result.gross_revenue - result.total_cost


def test_risk_flag_triggered_on_low_margin():
    result = run(_make_input(current_yield_qtl_per_acre=0.5, acreage=1.0))
    assert result.risk_flag is True


def test_risk_flag_not_triggered_on_good_margin():
    result = run(_make_input(crop="wheat", current_yield_qtl_per_acre=25.0,
                             acreage=5.0, season="rabi"))
    assert result.risk_flag is False


def test_intercrop_suggestions_for_rice_kharif():
    result = run(_make_input(crop="rice", season="kharif"))
    names = [s.companion_name_en for s in result.intercrop_suggestions]
    assert any("Moong" in n or "Green Gram" in n for n in names)


def test_intercrop_empty_for_unmatched_season():
    result = run(_make_input(crop="bajra", season="rabi"))
    assert result.intercrop_suggestions == []


def test_seasonal_tips_populated():
    result = run(_make_input(season="rabi"))
    assert len(result.seasonal_tips_en) >= 3
    assert len(result.seasonal_tips_hi) >= 3


def test_vertical_farming_tip_present():
    result = run(_make_input(crop="tomato", season="kharif"))
    assert (
        "polyhouse" in result.vertical_farming_en.lower()
        or "vertical" in result.vertical_farming_en.lower()
    )


def test_unknown_crop_raises():
    with pytest.raises(ValueError, match="Unknown crop key"):
        run(_make_input(crop="dragon_fruit_xyz"))


def test_acreage_scaling():
    result1 = run(_make_input(acreage=1.0))
    result2 = run(_make_input(acreage=3.0))
    assert abs(result2.gross_revenue - 3 * result1.gross_revenue) < 1


def test_sugarcane_frp_price_type():
    result = run(_make_input(crop="sugarcane", season="annual"))
    assert result.price_type == "frp"


def test_drip_irrigation_reduces_irrigation_cost():
    result_bore = run(_make_input(irrigation_type="borewell", acreage=1.0))
    result_drip = run(_make_input(irrigation_type="drip",     acreage=1.0))
    irr_bore = next(i for i in result_bore.cost_items if i.name_en == "Irrigation")
    irr_drip = next(i for i in result_drip.cost_items if i.name_en == "Irrigation")
    assert irr_drip.amount < irr_bore.amount


def test_reducible_cost_always_positive():
    for crop in ["rice", "wheat", "cotton", "mustard", "bajra"]:
        result = run(_make_input(crop=crop, season="kharif"))
        assert result.total_reducible_cost > 0


def test_user_cost_overrides_reflected_in_result():
    custom_seed = 9999.0
    result = run(_make_input(acreage=1.0, seed_cost=custom_seed))
    seed_item = next(i for i in result.cost_items if i.name_en == "Seed Cost")
    assert seed_item.amount == int(custom_seed)


def test_both_languages_differ():
    result = run(_make_input())
    assert result.narrative_en != result.narrative_hi


def test_intercrop_revenue_uplift_positive():
    result = run(_make_input(crop="maize", season="kharif"))
    for sugg in result.intercrop_suggestions:
        assert sugg.revenue_uplift_percent > 0
