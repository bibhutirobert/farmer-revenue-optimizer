from typing import List
from core.models import CostItem, FarmInput
from core.crop_data import get_crop

IRRIGATION_MULTIPLIERS = {
    "rainfed":  0.1,
    "canal":    0.5,
    "borewell": 1.0,
    "drip":     0.65,
}

REDUCTION_TIPS = {
    "seed": {
        "en": "Use farm-saved/certified seed with proper treatment to cut seed costs by 40-60%.",
        "hi": "फार्म-सेव्ड/प्रमाणित बीज का उपयोग करें — 40-60% बीज लागत कम।",
        "reducible_pct": 0.45,
    },
    "fertilizer": {
        "en": "Use FYM/compost and green manure to reduce chemical fertilizer by 25-30%.",
        "hi": "FYM/कंपोस्ट और हरी खाद से रासायनिक उर्वरक 25-30% कम करें।",
        "reducible_pct": 0.28,
    },
    "pesticide": {
        "en": "Adopt IPM (bio-pesticides + sticky traps + resistant varieties) to cut pesticide cost by 30-40%.",
        "hi": "IPM अपनाएं (जैव-कीटनाशक + चिपचिपे जाल) — 30-40% कीटनाशक बचत।",
        "reducible_pct": 0.35,
    },
    "labour": {
        "en": "Rent-share farm equipment through FPO to reduce manual labour cost by 20-30%.",
        "hi": "FPO के माध्यम से यंत्र किराया-साझा — 20-30% श्रम लागत कम।",
        "reducible_pct": 0.25,
    },
    "irrigation": {
        "en": "Switch to drip/sprinkler irrigation to cut water and electricity costs by 30-40%.",
        "hi": "ड्रिप/स्प्रिंकलर सिंचाई से पानी और बिजली लागत 30-40% कम।",
        "reducible_pct": 0.35,
    },
    "other": {
        "en": "Join a Farmer Producer Organization (FPO) for bulk purchase discounts on inputs (15-20% saving).",
        "hi": "FPO से जुड़ें — थोक खरीद पर 15-20% इनपुट लागत बचत।",
        "reducible_pct": 0.18,
    },
}


def compute_cost_items(farm_input: FarmInput) -> List[CostItem]:
    crop_data = get_crop(farm_input.crop)
    if not crop_data:
        return []

    base = crop_data["base_cost_per_acre"]
    irr_mult = IRRIGATION_MULTIPLIERS.get(farm_input.irrigation_type, 1.0)
    acres = farm_input.acreage

    def resolve(user_val, default_val, category):
        val = user_val if user_val is not None else default_val
        if category == "irrigation":
            val = val * irr_mult
        return val * acres

    raw = {
        "seed":       resolve(farm_input.seed_cost,       base["seed"],       "seed"),
        "fertilizer": resolve(farm_input.fertilizer_cost, base["fertilizer"], "fertilizer"),
        "pesticide":  resolve(farm_input.pesticide_cost,  base["pesticide"],  "pesticide"),
        "labour":     resolve(farm_input.labour_cost,     base["labour"],     "labour"),
        "irrigation": resolve(farm_input.irrigation_cost, base["irrigation"], "irrigation"),
        "other":      resolve(farm_input.other_cost,      base["other"],      "other"),
    }

    label_map = {
        "seed":       ("Seed Cost",       "बीज लागत"),
        "fertilizer": ("Fertilizer",      "उर्वरक"),
        "pesticide":  ("Pesticide / IPM", "कीटनाशक / IPM"),
        "labour":     ("Labour",          "श्रम"),
        "irrigation": ("Irrigation",      "सिंचाई"),
        "other":      ("Other / Misc",    "अन्य / विविध"),
    }

    items = []
    for cat, amount in raw.items():
        tip = REDUCTION_TIPS[cat]
        label_en, label_hi = label_map[cat]
        reducible = round(amount * tip["reducible_pct"])
        items.append(
            CostItem(
                name_en=label_en,
                name_hi=label_hi,
                amount=round(amount),
                reduction_tip_en=tip["en"],
                reduction_tip_hi=tip["hi"],
                reducible_by=reducible,
            )
        )
    return items


def total_cost(items: List[CostItem]) -> float:
    return sum(item.amount for item in items)


def total_reducible(items: List[CostItem]) -> float:
    return sum(item.reducible_by for item in items)
