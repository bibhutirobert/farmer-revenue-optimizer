import pytest
from core.models import FarmInput
from core.recommendation_engine import run
from core.report_generator import generate_pdf


def _make_result():
    farm = FarmInput(
        crop="wheat",
        acreage=3.0,
        current_yield_qtl_per_acre=16.0,
        irrigation_type="canal",
        state="Punjab",
        season="rabi",
    )
    return run(farm)


def test_pdf_returns_bytes():
    result = _make_result()
    pdf_bytes = generate_pdf(result, "Lat 30.1, Lng 75.5")
    assert isinstance(pdf_bytes, bytes)


def test_pdf_non_empty():
    result = _make_result()
    pdf_bytes = generate_pdf(result)
    assert len(pdf_bytes) > 5000


def test_pdf_starts_with_pdf_header():
    result = _make_result()
    pdf_bytes = generate_pdf(result)
    assert pdf_bytes[:4] == b"%PDF"


def test_pdf_with_risk_flag():
    farm = FarmInput(
        crop="rice",
        acreage=1.0,
        current_yield_qtl_per_acre=0.5,
        irrigation_type="borewell",
        state="Bihar",
        season="kharif",
    )
    result = run(farm)
    assert result.risk_flag is True
    pdf_bytes = generate_pdf(result)
    assert len(pdf_bytes) > 5000
