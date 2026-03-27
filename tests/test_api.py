"""Tests for Flask API routes (/api/health, /api/analyze, GET /)."""

import io
from unittest.mock import patch

from PIL import Image


# ── Helpers ───────────────────────────────────────────────────────────────────


def _jpeg_bytes(w=200, h=200) -> io.BytesIO:
    """Return a BytesIO containing a minimal valid JPEG."""
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color=(100, 149, 237)).save(buf, format="JPEG")
    buf.seek(0)
    return buf


MOCK_FOODS = [
    {
        "name": "apple",
        "quantity": "1 medium",
        "search_term": "apple",
        "est_kcal": 95,
        "est_protein_g": 0,
        "est_carbs_g": 25,
        "est_fat_g": 0,
    }
]
MOCK_MACROS = {"calories": 52.0, "protein_g": 0.3, "carbs_g": 14.0, "fat_g": 0.2}
EMPTY_MACROS = {"calories": None, "protein_g": None, "carbs_g": None, "fat_g": None}


# ── Health check ──────────────────────────────────────────────────────────────


def test_health_returns_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


# ── Index page ────────────────────────────────────────────────────────────────


def test_index_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Cal Tracker" in resp.data


# ── /api/analyze: input validation ───────────────────────────────────────────


def test_analyze_no_image_field(client):
    resp = client.post("/api/analyze")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_analyze_empty_filename(client):
    data = {"image": (io.BytesIO(b""), "", "image/jpeg")}
    resp = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_analyze_non_image_mimetype(client):
    data = {"image": (io.BytesIO(b"hello"), "file.txt", "text/plain")}
    resp = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 415


# ── /api/analyze: happy path ──────────────────────────────────────────────────


def test_analyze_returns_food_list(client):
    with (
        patch("app.identify_foods", return_value=MOCK_FOODS),
        patch("app.get_macros", return_value=MOCK_MACROS),
    ):
        data = {"image": (_jpeg_bytes(), "food.jpg", "image/jpeg")}
        resp = client.post(
            "/api/analyze", data=data, content_type="multipart/form-data"
        )

    assert resp.status_code == 200
    body = resp.get_json()
    assert "foods" in body
    assert len(body["foods"]) == 1

    food = body["foods"][0]
    assert food["name"] == "apple"
    assert food["quantity"] == "1 medium"
    assert food["calories"] == 52.0
    assert food["protein_g"] == 0.3
    assert food["carbs_g"] == 14.0
    assert food["fat_g"] == 0.2
    assert food["estimated"] is False


def test_analyze_falls_back_to_claude_estimates_when_db_fails(client):
    """When both USDA and OFF return None, Claude's est_ fields are used."""
    with (
        patch("app.identify_foods", return_value=MOCK_FOODS),
        patch("app.get_macros", return_value=EMPTY_MACROS),
    ):
        data = {"image": (_jpeg_bytes(), "food.jpg", "image/jpeg")}
        resp = client.post(
            "/api/analyze", data=data, content_type="multipart/form-data"
        )

    assert resp.status_code == 200
    food = resp.get_json()["foods"][0]
    assert food["calories"] == 95.0
    assert food["carbs_g"] == 25.0
    assert food["estimated"] is True


def test_analyze_empty_plate_returns_empty_list(client):
    with (
        patch("app.identify_foods", return_value=[]),
        patch("app.get_macros", return_value=MOCK_MACROS),
    ):
        data = {"image": (_jpeg_bytes(), "empty.jpg", "image/jpeg")}
        resp = client.post(
            "/api/analyze", data=data, content_type="multipart/form-data"
        )

    assert resp.status_code == 200
    assert resp.get_json()["foods"] == []


def test_analyze_multiple_foods(client):
    foods = [
        {
            "name": "rice",
            "quantity": "150g",
            "search_term": "white rice",
            "est_kcal": 195,
            "est_protein_g": 4,
            "est_carbs_g": 43,
            "est_fat_g": 0,
        },
        {
            "name": "chicken",
            "quantity": "200g",
            "search_term": "chicken breast",
            "est_kcal": 330,
            "est_protein_g": 62,
            "est_carbs_g": 0,
            "est_fat_g": 7,
        },
    ]
    macros = {"calories": 165.0, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6}

    with (
        patch("app.identify_foods", return_value=foods),
        patch("app.get_macros", return_value=macros),
    ):
        data = {"image": (_jpeg_bytes(), "meal.jpg", "image/jpeg")}
        resp = client.post(
            "/api/analyze", data=data, content_type="multipart/form-data"
        )

    assert resp.status_code == 200
    assert len(resp.get_json()["foods"]) == 2


# ── /api/analyze: upstream error handling ────────────────────────────────────


def test_analyze_claude_error_returns_502(client):
    with patch("app.identify_foods", side_effect=Exception("API unavailable")):
        data = {"image": (_jpeg_bytes(), "food.jpg", "image/jpeg")}
        resp = client.post(
            "/api/analyze", data=data, content_type="multipart/form-data"
        )

    assert resp.status_code == 502
    assert "error" in resp.get_json()


def test_analyze_bad_image_returns_422(client):
    data = {"image": (io.BytesIO(b"not an image"), "bad.jpg", "image/jpeg")}
    resp = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert resp.status_code == 422
