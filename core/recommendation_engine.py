"""
Recommendation Engine — V3
Extended to:
- Accept soil_type and climate_zone from FarmInput
- Use price_service for dynamic price resolution
- Return price provenance metadata
- Include ranked crop suggestions in narrative
"""
from typing import List
from core.models import FarmInput, RecommendationResult, InterCropSuggestion, CostItem
from core.crop_data import get_crop, get_intercrop_rules_for
from core.cost_calculator import compute_cost_items, total_cost, total_reducible
from core.price_service import resolve_price

MARGIN_WARNING_THRESHOLD_PER_ACRE = 5000

SEASONAL_TIPS = {
    "kharif": {
        "en": [
            "Kharif season: Sow after the first reliable monsoon rains (June 15 - July 15 in most states).",
            "Pre-sow deep ploughing (May-June) to expose and kill soil pests naturally.",
            "Keep field drains clear — waterlogging is the #1 yield killer in kharif.",
            "Ancient technique: Inter-plant drumstick (moringa) trees at 30-ft spacing on bunds — leaves are free fertilizer.",
        ],
        "hi": [
            "खरीफ मौसम: पहली विश्वसनीय मानसून बारिश के बाद बुवाई (अधिकांश राज्यों में 15 जून - 15 जुलाई)।",
            "मई-जून में गहरी जुताई से मिट्टी के कीट प्राकृतिक रूप से नष्ट होते हैं।",
            "खेत की नालियां साफ रखें — जलजमाव खरीफ में #1 उपज हानि कारण।",
            "प्राचीन तकनीक: मेड़ों पर 30 फीट की दूरी पर सहजन (मोरिंगा) के पेड़ — पत्तियां मुफ्त उर्वरक।",
        ],
    },
    "rabi": {
        "en": [
            "Rabi season: Sow between October 15 - November 30 for most states. Late sowing sharply cuts yield.",
            "Pre-irrigate (palewa) 7-10 days before sowing to ensure uniform germination.",
            "Frost risk: Cover nursery beds with straw mulch in Dec-Jan in northern plains.",
            "Ancient technique: Grow coriander/methi on bunds — they repel aphids and are sold at market.",
        ],
        "hi": [
            "रबी मौसम: अधिकांश राज्यों में 15 अक्टूबर - 30 नवंबर के बीच बुवाई। देरी से उपज तेजी से घटती है।",
            "एकसमान अंकुरण के लिए बुवाई से 7-10 दिन पहले पलेवा (पूर्व-सिंचाई)।",
            "पाला जोखिम: उत्तरी मैदानों में दिसंबर-जनवरी में पुआल मल्चिंग से नर्सरी बेड ढकें।",
            "प्राचीन तकनीक: मेड़ों पर धनिया/मेथी — एफिड्स दूर करते हैं और बाजार में बिकते हैं।",
        ],
    },
    "zaid": {
        "en": [
            "Zaid season (Feb-June): Short-duration crops only — moong, watermelon, cucumber, fodder.",
            "Extreme heat risk in May-June: use shade nets for vegetables and frequent light irrigations.",
            "Excellent season for green manure crops (sunhemp, dhaincha) to improve soil before kharif.",
        ],
        "hi": [
            "जायद मौसम (फरवरी-जून): केवल अल्पकालिक फसलें — मूंग, तरबूज, खीरा, चारा।",
            "मई-जून में अत्यधिक गर्मी — सब्जियों के लिए शेड नेट और बार-बार हल्की सिंचाई।",
            "खरीफ से पहले मिट्टी सुधार के लिए हरी खाद फसलें (सनई, ढैंचा) के लिए उत्तम मौसम।",
        ],
    },
    "annual": {
        "en": [
            "Annual crops: Ensure ratoon / plant crop decision is made before March for best seasonal alignment.",
            "Test soil pH and EC at start of each season — correcting imbalance costs less than losing yield.",
            "Keep field records of input costs, yield, and prices to make better decisions next year.",
        ],
        "hi": [
            "वार्षिक फसलें: सर्वोत्तम मौसमी संरेखण के लिए मार्च से पहले रतून/मूल फसल का निर्णय लें।",
            "प्रत्येक मौसम की शुरुआत में मिट्टी का pH और EC परीक्षण — असंतुलन सुधारना उपज खोने से सस्ता।",
            "अगले वर्ष बेहतर निर्णय के लिए इनपुट लागत, उपज और भाव का रिकॉर्ड रखें।",
        ],
    },
}

VERTICAL_FARMING = {
    "tomato": {
        "en": "Tomato is one of the best vertical farming candidates. A polyhouse with drip + trellis system yields 80-150 qtl/acre vs 50-80 in open field, at 2-5x farm-gate price premium for off-season production. Investment: Rs. 4-6 lakh/acre (50% subsidy available under NHM). Payback: 2-3 seasons.",
        "hi": "टमाटर ऊर्ध्वाधर खेती के लिए सर्वोत्तम फसलों में। पॉलीहाउस + ड्रिप + ट्रेलिस से 80-150 क्विंटल/एकड़। ऑफ-सीजन पर 2-5 गुना मूल्य प्रीमियम। निवेश: Rs. 4-6 लाख/एकड़ (NHM के तहत 50% सब्सिडी)। भुगतान: 2-3 मौसम।",
    },
    "chilli": {
        "en": "Chilli in polyhouse/net house gives 2x yield, near-zero pesticide cost (insect exclusion), and premium clean chilli price. Best suited for export-quality Guntur Sannam or Byadagi varieties.",
        "hi": "पॉलीहाउस/नेट हाउस में मिर्च से 2 गुना उपज, शून्य कीटनाशक लागत (कीट बहिष्करण), और प्रीमियम स्वच्छ मिर्च मूल्य।",
    },
    "turmeric": {
        "en": "Not directly suited to vertical farming, but a vertically-integrated value chain (farm to drying to grinding to branded packaging) multiplies farm-gate revenue by 3-5x. A small processing unit costs Rs. 1-2 lakh.",
        "hi": "ऊर्ध्वाधर खेती के लिए सीधे उपयुक्त नहीं, लेकिन लंबवत एकीकृत मूल्य श्रृंखला खेत-गेट राजस्व 3-5 गुना बढ़ाती है।",
    },
    "default": {
        "en": "Vertical farming / polyhouse is most impactful for high-value vegetables (tomato, chilli, leafy greens, capsicum) and off-season flowers. For field crops like yours, the best strategy is value-addition: grading, cleaning, packaging, and direct-to-consumer or FPO-channel selling.",
        "hi": "ऊर्ध्वाधर खेती उच्च-मूल्य सब्जियों के लिए सबसे प्रभावशाली। आपकी जैसी फसल के लिए, सर्वोत्तम रणनीति है: ग्रेडिंग, सफाई, पैकेजिंग, और FPO चैनल से सीधी बिक्री।",
    },
}


def _get_vertical_farming_tip(crop_key: str) -> dict:
    return VERTICAL_FARMING.get(crop_key, VERTICAL_FARMING["default"])


def _generate_narrative(
    crop_name: str,
    acreage: float,
    gross_revenue: float,
    net_margin: float,
    total_cost_val: float,
    reducible: float,
    risk_flag: bool,
    soil_name: str = "",
    climate_zone: str = "",
    lang: str = "en",
) -> str:
    soil_line = f" on {soil_name} soil ({climate_zone})" if soil_name else ""
    soil_line_hi = f" {soil_name} मिट्टी पर ({climate_zone})" if soil_name else ""

    if lang == "hi":
        risk_line = (
            "⚠️ चेतावनी: आपका शुद्ध मार्जिन कम है। नीचे दिए लागत-कटौती सुझाव तत्काल लागू करें।"
            if risk_flag
            else "✅ आपका मार्जिन स्वस्थ दिखता है। नीचे दिए सुझाव इसे और बेहतर बना सकते हैं।"
        )
        return (
            f"आपके {acreage:.1f} एकड़{soil_line_hi} {crop_name} खेत की अनुमानित सकल आय "
            f"Rs.{gross_revenue:,.0f} है। कुल लागत Rs.{total_cost_val:,.0f} घटाने के बाद "
            f"अनुमानित शुद्ध लाभ Rs.{net_margin:,.0f} है। "
            f"यदि आप नीचे दिए सभी लागत-बचत सुझाव अपनाएं, तो आप लगभग Rs.{reducible:,.0f} "
            f"और बचा सकते हैं। {risk_line}"
        )
    else:
        risk_line = (
            "⚠️ Warning: Your net margin is low. Implement the cost-reduction tips below urgently."
            if risk_flag
            else "✅ Your margin looks healthy. The suggestions below can make it even stronger."
        )
        return (
            f"Your {acreage:.1f}-acre {crop_name} farm{soil_line} is estimated to generate "
            f"a gross revenue of Rs.{gross_revenue:,.0f}. After total costs of "
            f"Rs.{total_cost_val:,.0f}, your estimated net margin is Rs.{net_margin:,.0f}. "
            f"If you apply all the cost-saving tips below, you could save an additional "
            f"Rs.{reducible:,.0f}. {risk_line}"
        )


def run(farm_input: FarmInput) -> RecommendationResult:
    """
    Main recommendation function.
    V3: uses price_service for dynamic price resolution.
    V3: includes soil/climate in narrative.
    """
    crop_data = get_crop(farm_input.crop)
    if not crop_data:
        raise ValueError(f"Unknown crop key: {farm_input.crop}")

    # --- Price resolution (V3: dynamic, with provenance) ---
    price_info = resolve_price(farm_input.crop, farm_input.state)
    price = price_info["price_per_quintal"]
    price_source = price_info["source"]
    price_updated_at = price_info["updated_at"]
    price_type = price_info.get("price_type", crop_data.get("price_type", "default"))

    # --- Revenue ---
    gross_revenue = round(price * farm_input.current_yield_qtl_per_acre * farm_input.acreage)

    # --- Costs ---
    cost_items: List[CostItem] = compute_cost_items(farm_input)
    total_cost_val = total_cost(cost_items)
    reducible = total_reducible(cost_items)
    net_margin = gross_revenue - total_cost_val

    # --- Risk ---
    margin_per_acre = net_margin / farm_input.acreage if farm_input.acreage > 0 else 0
    risk_flag = margin_per_acre < MARGIN_WARNING_THRESHOLD_PER_ACRE

    # --- Intercrop suggestions ---
    raw_rules = get_intercrop_rules_for(farm_input.crop, farm_input.season)
    intercrop_suggestions = [
        InterCropSuggestion(
            companion_name_en=r["companion_name_en"],
            companion_name_hi=r["companion_name_hi"],
            benefit_en=r["benefit_en"],
            benefit_hi=r["benefit_hi"],
            row_ratio=r["row_ratio"],
            revenue_uplift_percent=r["revenue_uplift_percent"],
        )
        for r in raw_rules
    ]

    # --- Seasonal tips ---
    season_key = farm_input.season if farm_input.season in SEASONAL_TIPS else "kharif"
    seasonal_tips_en = SEASONAL_TIPS[season_key]["en"]
    seasonal_tips_hi = SEASONAL_TIPS[season_key]["hi"]

    # --- Tips ---
    low_cost_tips_en = crop_data.get("low_cost_tips_en", [])
    low_cost_tips_hi = crop_data.get("low_cost_tips_hi", [])

    # --- Vertical farming ---
    vf = _get_vertical_farming_tip(farm_input.crop)

    # --- Soil/climate for narrative ---
    soil_name = farm_input.soil_name or ""
    climate = farm_input.climate_zone or ""

    # --- Narratives ---
    narrative_en = _generate_narrative(
        crop_name=crop_data["name_en"],
        acreage=farm_input.acreage,
        gross_revenue=gross_revenue,
        net_margin=net_margin,
        total_cost_val=total_cost_val,
        reducible=reducible,
        risk_flag=risk_flag,
        soil_name=soil_name,
        climate_zone=climate,
        lang="en",
    )
    narrative_hi = _generate_narrative(
        crop_name=crop_data["name_hi"],
        acreage=farm_input.acreage,
        gross_revenue=gross_revenue,
        net_margin=net_margin,
        total_cost_val=total_cost_val,
        reducible=reducible,
        risk_flag=risk_flag,
        soil_name=farm_input.soil_name or "",
        climate_zone=climate,
        lang="hi",
    )

    return RecommendationResult(
        crop_name_en=crop_data["name_en"],
        crop_name_hi=crop_data["name_hi"],
        acreage=farm_input.acreage,
        gross_revenue=gross_revenue,
        total_cost=round(total_cost_val),
        net_margin=round(net_margin),
        cost_items=cost_items,
        total_reducible_cost=round(reducible),
        intercrop_suggestions=intercrop_suggestions,
        low_cost_tips_en=low_cost_tips_en,
        low_cost_tips_hi=low_cost_tips_hi,
        seasonal_tips_en=seasonal_tips_en,
        seasonal_tips_hi=seasonal_tips_hi,
        vertical_farming_en=vf["en"],
        vertical_farming_hi=vf["hi"],
        narrative_en=narrative_en,
        narrative_hi=narrative_hi,
        risk_flag=risk_flag,
        price_per_quintal=price,
        price_type=price_type,
        price_source=price_source,
        price_updated_at=price_updated_at,
        soil_code=farm_input.soil_type or "unknown",
        soil_name_en=soil_name,
        climate_zone=climate,
    )
