import os
import secrets
import warnings
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
USDA_API_KEY = os.getenv("USDA_API_KEY", "")
NUTRITION_SOURCE = os.getenv("NUTRITION_SOURCE", "openfoodfacts")
MAX_IMAGE_PX = 1024
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

_SECRET_KEY = os.getenv("SECRET_KEY", "")
if not _SECRET_KEY:
    _SECRET_KEY = secrets.token_hex(32)
    warnings.warn(
        "SECRET_KEY is not set — using a random key. Sessions will be invalidated on restart. "
        "Set SECRET_KEY in your .env file.",
        stacklevel=1,
    )
elif len(_SECRET_KEY) < 32:
    warnings.warn(
        "SECRET_KEY is shorter than 32 characters. Use a longer random value.",
        stacklevel=1,
    )

SECRET_KEY = _SECRET_KEY
