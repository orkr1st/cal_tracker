import requests
from config import NUTRITION_SOURCE, USDA_API_KEY

_session = requests.Session()
_session.headers.update({"User-Agent": "CalTracker/1.0 (food macro tracker)"})

EMPTY_MACROS = {"calories": None, "protein_g": None, "carbs_g": None, "fat_g": None}

# USDA FoodData Central public key — works without user registration,
# rate-limited to 30 req/hour / 50 req/day (fine for personal use).
_USDA_DEMO_KEY = "DEMO_KEY"


def get_macros(search_term: str) -> dict:
    """Return macro dict for search_term.

    Lookup order:
    1. USDA (configured key, or free DEMO_KEY) — reliable, great for generics
    2. OpenFoodFacts — good for branded products
    Returns EMPTY_MACROS only if both sources fail.
    """
    if NUTRITION_SOURCE == "usda" and USDA_API_KEY:
        result = _usda_request(search_term, USDA_API_KEY)
        if result != EMPTY_MACROS:
            return result
        # fall through to OFF if USDA key returns nothing
    else:
        # Always try USDA DEMO_KEY first — more reliable than OFF for generic foods
        result = _usda_request(search_term, _USDA_DEMO_KEY)
        if result != EMPTY_MACROS:
            return result

    # Secondary: OpenFoodFacts (good for branded/packaged products)
    return _off_lookup(search_term)


# ── USDA FoodData Central ─────────────────────────────────────────────────────


def _usda_request(search_term: str, api_key: str) -> dict:
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "query": search_term,
        "api_key": api_key,
        "pageSize": 5,
        "dataType": "SR Legacy,Foundation,Branded",
    }
    try:
        resp = _session.get(url, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return EMPTY_MACROS

    nutrient_ids = {
        1008: "calories",
        1003: "protein_g",
        1005: "carbs_g",
        1004: "fat_g",
    }

    for food in data.get("foods", []):
        macros = {}
        for n in food.get("foodNutrients", []):
            nid = n.get("nutrientId")
            if nid in nutrient_ids:
                macros[nutrient_ids[nid]] = round(float(n.get("value", 0)), 1)
        if "calories" in macros:
            return macros
    return EMPTY_MACROS


# Keep the named wrappers so existing tests and the USDA_API_KEY path still work
def _usda_lookup(search_term: str) -> dict:
    return _usda_request(search_term, USDA_API_KEY)


# ── OpenFoodFacts ─────────────────────────────────────────────────────────────


def _off_lookup(search_term: str) -> dict:
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": search_term,
        "action": "process",
        "json": 1,
        "page_size": 25,
        "sort_by": "unique_scans_n",  # most-scanned = best data quality
        "lc": "en",
        "fields": "product_name,nutriments",
    }
    try:
        resp = _session.get(url, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return EMPTY_MACROS

    for product in data.get("products", []):
        n = product.get("nutriments", {})

        # Explicit None checks — 0 is a valid calorie value (e.g. Diet Coke)
        kcal_direct = n.get("energy-kcal_100g")
        if kcal_direct is not None:
            kcal = float(kcal_direct)
        else:
            kj = n.get("energy_100g")
            if kj is None:
                continue
            kcal = float(kj) / 4.184  # kJ → kcal

        return {
            "calories": round(kcal, 1),
            "protein_g": _safe(n.get("proteins_100g")),
            "carbs_g": _safe(n.get("carbohydrates_100g")),
            "fat_g": _safe(n.get("fat_100g")),
        }
    return EMPTY_MACROS


def _safe(val) -> float | None:
    try:
        return round(float(val), 1)
    except (TypeError, ValueError):
        return None
