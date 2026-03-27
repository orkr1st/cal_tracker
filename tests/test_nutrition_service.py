"""Tests for services/nutrition_service.py — OpenFoodFacts + USDA lookups."""

from unittest.mock import MagicMock, patch

import pytest

from services.nutrition_service import (
    EMPTY_MACROS,
    _off_lookup,
    _usda_lookup,
    get_macros,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _off_response(products: list) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"products": products}
    return resp


def _usda_response(foods: list) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"foods": foods}
    return resp


OFF_APPLE_PRODUCT = {
    "product_name": "Apple",
    "nutriments": {
        "energy-kcal_100g": 52,
        "proteins_100g": 0.3,
        "carbohydrates_100g": 14.0,
        "fat_100g": 0.2,
    },
}

USDA_CHICKEN = {
    "description": "Chicken breast",
    "foodNutrients": [
        {"nutrientId": 1008, "value": 165},  # calories
        {"nutrientId": 1003, "value": 31.0},  # protein
        {"nutrientId": 1005, "value": 0.0},  # carbs
        {"nutrientId": 1004, "value": 3.6},  # fat
    ],
}


# ── OpenFoodFacts: happy paths ────────────────────────────────────────────────


def test_off_returns_macros_for_known_food():
    with patch("services.nutrition_service._session") as s:
        s.get.return_value = _off_response([OFF_APPLE_PRODUCT])
        result = _off_lookup("apple")

    assert result["calories"] == 52.0
    assert result["protein_g"] == 0.3
    assert result["carbs_g"] == 14.0
    assert result["fat_g"] == 0.2


def test_off_skips_products_without_kcal():
    products = [
        {"product_name": "Mystery", "nutriments": {"proteins_100g": 1}},
        OFF_APPLE_PRODUCT,
    ]
    with patch("services.nutrition_service._session") as s:
        s.get.return_value = _off_response(products)
        result = _off_lookup("apple")

    assert result["calories"] == 52.0


def test_off_falls_back_to_kj_when_kcal_missing():
    """If only energy_100g (kJ) is present, convert to kcal."""
    product = {
        "product_name": "Something",
        "nutriments": {
            "energy_100g": 217,  # ~52 kcal
            "proteins_100g": 0.3,
            "carbohydrates_100g": 14.0,
            "fat_100g": 0.2,
        },
    }
    with patch("services.nutrition_service._session") as s:
        s.get.return_value = _off_response([product])
        result = _off_lookup("something")

    assert result["calories"] == pytest.approx(52.0, abs=1)


def test_off_zero_calorie_product_not_skipped():
    """energy-kcal_100g == 0 is valid (e.g. Diet Coke) and must not be skipped."""
    product = {
        "product_name": "Diet Cola",
        "nutriments": {
            "energy-kcal_100g": 0,
            "proteins_100g": 0.0,
            "carbohydrates_100g": 0.0,
            "fat_100g": 0.0,
        },
    }
    with patch("services.nutrition_service._session") as s:
        s.get.return_value = _off_response([product])
        result = _off_lookup("diet cola")

    assert result["calories"] == 0.0
    assert result != EMPTY_MACROS


# ── OpenFoodFacts: empty / error paths ───────────────────────────────────────


def test_off_empty_products_returns_empty_macros():
    with patch("services.nutrition_service._session") as s:
        s.get.return_value = _off_response([])
        result = _off_lookup("unknown food xyz")

    assert result == EMPTY_MACROS


def test_off_network_error_returns_empty_macros():
    with patch("services.nutrition_service._session") as s:
        s.get.side_effect = Exception("Connection refused")
        result = _off_lookup("apple")

    assert result == EMPTY_MACROS


def test_off_http_error_returns_empty_macros():
    with patch("services.nutrition_service._session") as s:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404")
        s.get.return_value = mock_resp
        result = _off_lookup("apple")

    assert result == EMPTY_MACROS


# ── USDA: happy paths ─────────────────────────────────────────────────────────


def test_usda_returns_macros_for_known_food():
    with patch("services.nutrition_service._session") as s:
        s.get.return_value = _usda_response([USDA_CHICKEN])
        result = _usda_lookup("chicken breast")

    assert result["calories"] == 165.0
    assert result["protein_g"] == 31.0
    assert result["carbs_g"] == 0.0
    assert result["fat_g"] == 3.6


def test_usda_skips_food_without_calories():
    foods = [
        {
            "description": "No energy",
            "foodNutrients": [{"nutrientId": 1003, "value": 5}],
        },
        USDA_CHICKEN,
    ]
    with patch("services.nutrition_service._session") as s:
        s.get.return_value = _usda_response(foods)
        result = _usda_lookup("chicken")

    assert result["calories"] == 165.0


# ── USDA: empty / error paths ─────────────────────────────────────────────────


def test_usda_empty_results_returns_empty_macros():
    with patch("services.nutrition_service._session") as s:
        s.get.return_value = _usda_response([])
        result = _usda_lookup("unknown xyz")

    assert result == EMPTY_MACROS


def test_usda_network_error_returns_empty_macros():
    with patch("services.nutrition_service._session") as s:
        s.get.side_effect = Exception("Timeout")
        result = _usda_lookup("chicken")

    assert result == EMPTY_MACROS


# ── get_macros dispatcher ─────────────────────────────────────────────────────


def test_get_macros_tries_usda_demo_key_first(monkeypatch):
    """Default path: USDA DEMO_KEY is tried before OpenFoodFacts."""
    monkeypatch.setattr("services.nutrition_service.NUTRITION_SOURCE", "openfoodfacts")
    usda_result = {"calories": 52.0, "protein_g": 0.3, "carbs_g": 14.0, "fat_g": 0.2}
    with (
        patch(
            "services.nutrition_service._usda_request", return_value=usda_result
        ) as mock_usda,
        patch("services.nutrition_service._off_lookup") as mock_off,
    ):
        result = get_macros("apple")
    mock_usda.assert_called_once()
    mock_off.assert_not_called()
    assert result == usda_result


def test_get_macros_falls_back_to_off_when_usda_demo_empty(monkeypatch):
    """When USDA DEMO_KEY returns nothing, OFF is tried as fallback."""
    monkeypatch.setattr("services.nutrition_service.NUTRITION_SOURCE", "openfoodfacts")
    off_result = {"calories": 42.0, "protein_g": 0.0, "carbs_g": 11.0, "fat_g": 0.0}
    with (
        patch("services.nutrition_service._usda_request", return_value=EMPTY_MACROS),
        patch(
            "services.nutrition_service._off_lookup", return_value=off_result
        ) as mock_off,
    ):
        result = get_macros("coca cola")
    mock_off.assert_called_once_with("coca cola")
    assert result == off_result


def test_get_macros_uses_configured_usda_key_when_set(monkeypatch):
    """When NUTRITION_SOURCE=usda and a key is provided, that key is used."""
    monkeypatch.setattr("services.nutrition_service.NUTRITION_SOURCE", "usda")
    monkeypatch.setattr("services.nutrition_service.USDA_API_KEY", "my-real-key")
    usda_result = {"calories": 165.0, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6}
    with (
        patch(
            "services.nutrition_service._usda_request", return_value=usda_result
        ) as mock_usda,
        patch("services.nutrition_service._off_lookup") as mock_off,
    ):
        result = get_macros("chicken breast")
    mock_usda.assert_called_once_with("chicken breast", "my-real-key")
    mock_off.assert_not_called()
    assert result == usda_result


def test_get_macros_returns_empty_when_all_sources_fail(monkeypatch):
    monkeypatch.setattr("services.nutrition_service.NUTRITION_SOURCE", "openfoodfacts")
    with (
        patch("services.nutrition_service._usda_request", return_value=EMPTY_MACROS),
        patch("services.nutrition_service._off_lookup", return_value=EMPTY_MACROS),
    ):
        result = get_macros("unknown xyz")
    assert result == EMPTY_MACROS
