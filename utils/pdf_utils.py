from core.models import RecommendationResult
from core.report_generator import generate_pdf


def build_pdf_bytes(
    result: RecommendationResult,
    farm_location: str = "",
    llm_advisory_en: str = "",
    llm_advisory_hi: str = "",
) -> bytes:
    """
    Thin wrapper around generate_pdf.
    Pass llm_advisory_en / llm_advisory_hi when available.
    Leave empty strings to omit the AI section from the PDF.
    """
    return generate_pdf(
        result,
        farm_location=farm_location,
        llm_advisory_en=llm_advisory_en,
        llm_advisory_hi=llm_advisory_hi,
    )
