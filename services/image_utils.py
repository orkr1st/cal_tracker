import io
from PIL import Image
from config import MAX_IMAGE_PX


def resize_to_jpeg(file_storage) -> bytes:
    """Resize uploaded image to max MAX_IMAGE_PX on longest side, return JPEG bytes."""
    img = Image.open(file_storage.stream)

    # Convert to RGB (handles RGBA, palette, etc.)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize if needed
    w, h = img.size
    if max(w, h) > MAX_IMAGE_PX:
        scale = MAX_IMAGE_PX / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()
