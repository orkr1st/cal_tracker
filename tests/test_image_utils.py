"""Tests for services/image_utils.py — Pillow resize + JPEG conversion."""

import io

from PIL import Image

from services.image_utils import resize_to_jpeg


# ── Fake FileStorage ──────────────────────────────────────────────────────────


class FakeFileStorage:
    """Minimal stand-in for werkzeug FileStorage."""

    def __init__(self, img: Image.Image, fmt: str = "PNG"):
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        buf.seek(0)
        self.stream = buf


# ── Output format ─────────────────────────────────────────────────────────────


def test_output_is_valid_jpeg():
    fs = FakeFileStorage(Image.new("RGB", (100, 100)))
    result = resize_to_jpeg(fs)
    # JPEG magic bytes
    assert result[:2] == b"\xff\xd8"
    # Pillow should be able to re-open it
    out = Image.open(io.BytesIO(result))
    assert out.format == "JPEG"


# ── Size constraints ──────────────────────────────────────────────────────────


def test_large_landscape_image_resized():
    fs = FakeFileStorage(Image.new("RGB", (3000, 2000)))
    result = resize_to_jpeg(fs)
    out = Image.open(io.BytesIO(result))
    assert max(out.size) <= 1024


def test_large_portrait_image_resized():
    fs = FakeFileStorage(Image.new("RGB", (800, 2400)))
    result = resize_to_jpeg(fs)
    out = Image.open(io.BytesIO(result))
    assert max(out.size) <= 1024


def test_small_image_not_upscaled():
    fs = FakeFileStorage(Image.new("RGB", (200, 150)))
    result = resize_to_jpeg(fs)
    out = Image.open(io.BytesIO(result))
    assert out.size == (200, 150)


def test_exact_boundary_image_not_resized():
    """An image whose longest side is exactly 1024 should not be resized."""
    fs = FakeFileStorage(Image.new("RGB", (1024, 768)))
    result = resize_to_jpeg(fs)
    out = Image.open(io.BytesIO(result))
    assert out.size == (1024, 768)


# ── Color mode conversion ─────────────────────────────────────────────────────


def test_rgba_converted_to_rgb():
    fs = FakeFileStorage(Image.new("RGBA", (100, 100), (255, 0, 0, 128)))
    result = resize_to_jpeg(fs)
    out = Image.open(io.BytesIO(result))
    assert out.mode == "RGB"


def test_palette_image_converted():
    img = Image.new("P", (100, 100))
    fs = FakeFileStorage(img)
    result = resize_to_jpeg(fs)
    out = Image.open(io.BytesIO(result))
    assert out.mode == "RGB"


def test_grayscale_converted_to_rgb():
    fs = FakeFileStorage(Image.new("L", (100, 100)))
    result = resize_to_jpeg(fs)
    out = Image.open(io.BytesIO(result))
    assert out.mode == "RGB"


# ── Aspect ratio preservation ─────────────────────────────────────────────────


def test_aspect_ratio_preserved_after_resize():
    w, h = 2048, 1024
    fs = FakeFileStorage(Image.new("RGB", (w, h)))
    result = resize_to_jpeg(fs)
    out = Image.open(io.BytesIO(result))
    ow, oh = out.size
    original_ratio = w / h
    result_ratio = ow / oh
    assert abs(original_ratio - result_ratio) < 0.02
