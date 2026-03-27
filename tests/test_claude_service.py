"""Tests for services/claude_service.py — vision API call + JSON parsing."""

import json
from unittest.mock import MagicMock, patch

import anthropic
import pytest

from services.claude_service import identify_foods


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    return resp


SAMPLE_FOODS = [
    {
        "name": "grilled chicken breast",
        "quantity": "200g",
        "search_term": "chicken breast",
        "est_kcal": 330,
        "est_protein_g": 62,
        "est_carbs_g": 0,
        "est_fat_g": 7,
    },
    {
        "name": "steamed broccoli",
        "quantity": "100g",
        "search_term": "broccoli",
        "est_kcal": 35,
        "est_protein_g": 2,
        "est_carbs_g": 7,
        "est_fat_g": 0,
    },
]


# ── JSON parsing ──────────────────────────────────────────────────────────────


def test_parses_clean_json():
    with patch("services.claude_service._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(
            json.dumps(SAMPLE_FOODS)
        )
        result = identify_foods(b"fake-jpeg")
    assert len(result) == 2
    assert result[0]["name"] == "grilled chicken breast"
    assert result[1]["search_term"] == "broccoli"


def test_strips_json_code_fence():
    payload = f"```json\n{json.dumps(SAMPLE_FOODS)}\n```"
    with patch("services.claude_service._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(payload)
        result = identify_foods(b"fake-jpeg")
    assert len(result) == 2


def test_strips_plain_code_fence():
    payload = f"```\n{json.dumps(SAMPLE_FOODS)}\n```"
    with patch("services.claude_service._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(payload)
        result = identify_foods(b"fake-jpeg")
    assert len(result) == 2


def test_empty_array_for_no_food():
    with patch("services.claude_service._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response("[]")
        result = identify_foods(b"fake-jpeg")
    assert result == []


def test_single_food_item():
    single = [{"name": "banana", "quantity": "1 medium", "search_term": "banana"}]
    with patch("services.claude_service._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(json.dumps(single))
        result = identify_foods(b"fake-jpeg")
    assert len(result) == 1
    assert result[0]["name"] == "banana"


# ── API call parameters ───────────────────────────────────────────────────────


def test_uses_correct_model():
    with patch("services.claude_service._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response("[]")
        identify_foods(b"fake-jpeg")
        call_kwargs = mock_client.messages.create.call_args
    assert call_kwargs.kwargs["model"] == "claude-sonnet-4-6"


def test_image_sent_as_base64_jpeg():
    with patch("services.claude_service._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response("[]")
        identify_foods(b"fake-jpeg-data")
        call_kwargs = mock_client.messages.create.call_args

    messages = call_kwargs.kwargs["messages"]
    image_block = messages[0]["content"][0]
    assert image_block["type"] == "image"
    assert image_block["source"]["media_type"] == "image/jpeg"
    assert image_block["source"]["type"] == "base64"


def test_max_tokens_is_1024():
    with patch("services.claude_service._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response("[]")
        identify_foods(b"x")
        call_kwargs = mock_client.messages.create.call_args
    assert call_kwargs.kwargs["max_tokens"] == 1024


# ── Error propagation ─────────────────────────────────────────────────────────


def test_raises_on_api_error():
    with patch("services.claude_service._client") as mock_client:
        mock_client.messages.create.side_effect = RuntimeError("API down")
        with pytest.raises(RuntimeError, match="API down"):
            identify_foods(b"fake-jpeg")


def test_raises_on_invalid_json():
    with patch("services.claude_service._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response("not json at all")
        with pytest.raises(json.JSONDecodeError):
            identify_foods(b"fake-jpeg")


# ── Retry logic ───────────────────────────────────────────────────────────────


def _make_overload_error() -> anthropic.APIStatusError:
    response = MagicMock()
    response.status_code = 529
    return anthropic.APIStatusError("Overloaded", response=response, body={})


def test_retries_on_529_then_succeeds():
    """Two overload errors followed by success → result returned normally."""
    with (
        patch("services.claude_service._client") as mock_client,
        patch("services.claude_service.time.sleep"),
    ):
        mock_client.messages.create.side_effect = [
            _make_overload_error(),
            _make_overload_error(),
            _mock_response("[]"),
        ]
        result = identify_foods(b"fake-jpeg")

    assert result == []
    assert mock_client.messages.create.call_count == 3


def test_raises_after_max_retries_exceeded():
    """Persistent 529s exhaust retries and re-raise the error."""
    with (
        patch("services.claude_service._client") as mock_client,
        patch("services.claude_service.time.sleep"),
    ):
        mock_client.messages.create.side_effect = _make_overload_error()
        with pytest.raises(anthropic.APIStatusError):
            identify_foods(b"fake-jpeg")

    assert mock_client.messages.create.call_count == 3  # _MAX_RETRIES


def test_non_retryable_error_raises_immediately():
    """A 400 Bad Request is not retried."""
    response = MagicMock()
    response.status_code = 400
    exc = anthropic.APIStatusError("Bad request", response=response, body={})

    with (
        patch("services.claude_service._client") as mock_client,
        patch("services.claude_service.time.sleep") as mock_sleep,
    ):
        mock_client.messages.create.side_effect = exc
        with pytest.raises(anthropic.APIStatusError):
            identify_foods(b"fake-jpeg")

    assert mock_client.messages.create.call_count == 1
    mock_sleep.assert_not_called()
