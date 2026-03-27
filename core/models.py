from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FarmInput:
    crop: str
    acreage: float
    current_yield_qtl_per_acre: float
    irrigation_type: str
    state: str
    season: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    # Geo-intelligence fields (auto-populated from soil_service)
    soil_type: Optional[str] = None        # soil_code e.g. "black", "alluvial"
    soil_name: Optional[str] = None        # human-readable e.g. "Black Cotton Soil"
    climate_zone: Optional[str] = None     # e.g. "Tropical Semi-Arid"
    # Cost overrides (optional, user-supplied)
    seed_cost: Optional[float] = None
    fertilizer_cost: Optional[float] = None
    pesticide_cost: Optional[float] = None
    labour_cost: Optional[float] = None
    irrigation_cost: Optional[float] = None
    other_cost: Optional[float] = None


@dataclass
class CostItem:
    name_en: str
    name_hi: str
    amount: float
    reduction_tip_en: str = ""
    reduction_tip_hi: str = ""
    reducible_by: float = 0


@dataclass
class InterCropSuggestion:
    companion_name_en: str
    companion_name_hi: str
    benefit_en: str
    benefit_hi: str
    row_ratio: str
    revenue_uplift_percent: float


@dataclass
class RecommendationResult:
    crop_name_en: str
    crop_name_hi: str
    acreage: float
    gross_revenue: float
    total_cost: float
    net_margin: float
    cost_items: List[CostItem]
    total_reducible_cost: float
    intercrop_suggestions: List[InterCropSuggestion]
    low_cost_tips_en: List[str]
    low_cost_tips_hi: List[str]
    seasonal_tips_en: List[str]
    seasonal_tips_hi: List[str]
    vertical_farming_en: str
    vertical_farming_hi: str
    narrative_en: str
    narrative_hi: str
    risk_flag: bool
    price_per_quintal: float
    price_type: str
    # V3 additions — price provenance
    price_source: str = "default"          # "live" | "cache" | "default"
    price_updated_at: str = "hardcoded"    # ISO date or "hardcoded"
    # V3 additions — geo-intelligence
    soil_code: str = "unknown"
    soil_name_en: str = ""
    climate_zone: str = ""
