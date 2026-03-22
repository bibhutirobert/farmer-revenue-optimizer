import pytest
from core.models import FarmInput
from core.cost_calculator import compute_cost_items, total_cost, total_reducible


def _make_input(**kwargs) -> FarmInput:
    defaults = dict(
        crop="wheat",
        acreage=2.0,
        current_yield_qtl_per_acre=18.0,
        irrigation_type="borewell",
        state="Punjab",
        season="rabi",
    )
    defaults.update(kwargs)
    return FarmInput(**defaults)


def test_cost_items_count():
    items = compute_cost_items(_make_input())
    assert len(items) == 6


def test_cost_items_positive():
    items = compute_cost_items(_make_input(acreage=3.0))
    for item in items:
        assert item.amount > 0


def test_irrigation_multiplier_rainfed():
    items_bore = compute_cost_items(_make_input(irrigation_type="borewell", acreage=1.0))
    items_rain = compute_cost_items(_make_input(irrigation_type="rainfed",  acreage=1.0))
    irr_bore = next(i for i in items_bore if i.name_en == "Irrigation")
    irr_rain = next(i for i in items_rain if i.name_en == "Irrigation")
    assert irr_rain.amount < irr_bore.amount


def test_irrigation_multiplier_drip():
    items_bore = compute_cost_items(_make_input(irrigation_type="borewell", acreage=1.0))
    items_drip = compute_cost_items(_make_input(irrigation_type="drip",     acreage=1.0))
    irr_bore = next(i for i in items_bore if i.name_en == "Irrigation")
    irr_drip = next(i for i in items_drip if i.name_en == "Irrigation")
    assert irr_drip.amount < irr_bore.amount


def test_user_override_seed():
    items = compute_cost_items(_make_input(acreage=1.0, seed_cost=5000.0))
    seed_item = next(i for i in items if i.name_en == "Seed Cost")
    assert seed_item.amount == 5000


def test_acreage_scales_linearly():
    cost1 = total_cost(compute_cost_items(_make_input(acreage=1.0)))
    cost2 = total_cost(compute_cost_items(_make_input(acreage=2.0)))
    assert abs(cost2 - 2 * cost1) < 1


def test_reducible_less_than_total():
    items = compute_cost_items(_make_input(acreage=5.0))
    assert total_reducible(items) < total_cost(items)


def test_unknown_crop_returns_empty():
    items = compute_cost_items(_make_input(crop="nonexistent_crop_xyz"))
    assert items == []
