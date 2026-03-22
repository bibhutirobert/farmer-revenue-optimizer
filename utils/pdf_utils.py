from core.models import RecommendationResult
from core.report_generator import generate_pdf


def build_pdf_bytes(result: RecommendationResult, farm_location: str = "") -> bytes:
    return generate_pdf(result, farm_location)
