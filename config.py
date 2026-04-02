import os
import secrets
import warnings

from dotenv import load_dotenv

load_dotenv()

# ── API keys ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
USDA_API_KEY = os.getenv("USDA_API_KEY", "")

# ── App behaviour ─────────────────────────────────────────────────────────────
NUTRITION_SOURCE = os.getenv("NUTRITION_SOURCE", "openfoodfacts")
MAX_IMAGE_PX = 1024
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# ── Secret key ────────────────────────────────────────────────────────────────
_SECRET_KEY = os.getenv("SECRET_KEY", "")
if not _SECRET_KEY:
    _SECRET_KEY = secrets.token_hex(32)
    warnings.warn(
        "SECRET_KEY is not set — using a random key. Sessions will be "
        "invalidated on restart. Set SECRET_KEY in your .env file.",
        stacklevel=1,
    )
elif len(_SECRET_KEY) < 32:
    warnings.warn(
        "SECRET_KEY is shorter than 32 characters. Use a longer random value.",
        stacklevel=1,
    )
SECRET_KEY = _SECRET_KEY

# ── Rate limiting ─────────────────────────────────────────────────────────────
ANALYZE_RATE_LIMIT = os.getenv("ANALYZE_RATE_LIMIT", "30 per minute")

# ── Nutrition cache ───────────────────────────────────────────────────────────
MACRO_CACHE_TTL = int(os.getenv("MACRO_CACHE_TTL", "3600"))  # seconds

# ── Food diary ────────────────────────────────────────────────────────────────
DATABASE_PATH = os.getenv("DATABASE_PATH", "cal_tracker.db")

# ── Daily macro targets ───────────────────────────────────────────────────────
DAILY_CALORIES = float(os.getenv("DAILY_CALORIES", "2000"))
DAILY_PROTEIN_G = float(os.getenv("DAILY_PROTEIN_G", "150"))
DAILY_CARBS_G = float(os.getenv("DAILY_CARBS_G", "250"))
DAILY_FAT_G = float(os.getenv("DAILY_FAT_G", "65"))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(5 * 1024 * 1024)))  # 5 MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
