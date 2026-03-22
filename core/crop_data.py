import json
import os
from functools import lru_cache
from typing import Dict, Any, List, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@lru_cache(maxsize=1)
def load_crops() -> Dict[str, Any]:
    path = os.path.join(DATA_DIR, "crops.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["crops"]


@lru_cache(maxsize=1)
def load_intercrop_rules() -> List[Dict[str, Any]]:
    path = os.path.join(DATA_DIR, "intercrop_rules.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["rules"]


def get_crop(crop_key: str) -> Optional[Dict[str, Any]]:
    return load_crops().get(crop_key)


def list_crop_keys() -> List[str]:
    return list(load_crops().keys())


def get_crop_display_name(crop_key: str, lang: str = "en") -> str:
    crop = get_crop(crop_key)
    if not crop:
        return crop_key.title()
    return crop.get(f"name_{lang}", crop.get("name_en", crop_key.title()))


def get_intercrop_rules_for(crop_key: str, season: str) -> List[Dict[str, Any]]:
    rules = load_intercrop_rules()
    return [
        r for r in rules
        if r["primary_crop"] == crop_key
        and (
            season in r["seasons"]
            or r["seasons"] == ["annual"]
            or "annual" in r["seasons"]
        )
    ]
