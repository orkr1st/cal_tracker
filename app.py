import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import (
    ANALYZE_RATE_LIMIT,
    DAILY_CALORIES,
    DAILY_CARBS_G,
    DAILY_FAT_G,
    DAILY_PROTEIN_G,
    DEBUG,
    LOG_BACKUP_COUNT,
    LOG_DIR,
    LOG_MAX_BYTES,
    MAX_UPLOAD_BYTES,
    SECRET_KEY,
)
from services.claude_service import identify_foods
from services.diary_service import add_entry, delete_entry, get_entries, get_history, init_db
from services.image_utils import resize_to_jpeg
from services.nutrition_service import get_macros
from services.portion_parser import parse_quantity

# ── Logging ───────────────────────────────────────────────────────────────────

os.makedirs(LOG_DIR, exist_ok=True)

_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

_file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "cal_tracker.log"),
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT,
)
_file_handler.setFormatter(_formatter)

# basicConfig is a no-op when handlers already exist (e.g., Werkzeug sets them up
# before this module loads). Use force=True so our config always wins.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), _file_handler],
    force=True,
)
logger = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

# ── Rate limiting ─────────────────────────────────────────────────────────────

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

# ── Database init ─────────────────────────────────────────────────────────────

init_db()

# ── Security headers ──────────────────────────────────────────────────────────


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' blob: data:; "
        "connect-src 'self'; "
        "media-src 'self' blob:;"
    )
    return response


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/analyze")
@limiter.limit(ANALYZE_RATE_LIMIT)
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image field in request"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    mime = file.mimetype or ""
    if not mime.startswith("image/") and mime != "application/octet-stream":
        return jsonify({"error": "Unsupported file type"}), 415

    try:
        jpeg_bytes = resize_to_jpeg(file)
    except Exception:
        logger.exception("Image processing failed")
        return jsonify({"error": "Could not process image — ensure it is a valid photo"}), 422

    try:
        foods = identify_foods(jpeg_bytes)
    except Exception:
        logger.exception("Food identification failed")
        return jsonify({"error": "Food identification failed — please try again"}), 502

    results = []
    for food in foods:
        search_term = food.get("search_term", food.get("name", ""))[:200]
        quantity = food.get("quantity", "")
        multiplier = parse_quantity(quantity)
        raw_macros = get_macros(search_term)
        estimated = False

        if raw_macros.get("calories") is not None:
            macros = _scale_macros(raw_macros, multiplier)
            per_100g = raw_macros
        else:
            macros = {
                "calories": _to_float(food.get("est_kcal")),
                "protein_g": _to_float(food.get("est_protein_g")),
                "carbs_g": _to_float(food.get("est_carbs_g")),
                "fat_g": _to_float(food.get("est_fat_g")),
            }
            estimated = True
            # Derive per-100g base by dividing the estimate by the original
            # portion multiplier so the client can proportionally rescale.
            m = max(multiplier, 0.01)
            per_100g = {
                k: (round(v / m, 1) if v is not None else None)
                for k, v in macros.items()
            }

        results.append(
            {
                "name": food.get("name", "Unknown"),
                "quantity": quantity,
                "search_term": search_term,
                "estimated": estimated,
                "per_100g": per_100g,
                **macros,
            }
        )

    logger.info("Analysed image: %d food items found", len(results))
    return jsonify({"foods": results})


# ── Food diary ────────────────────────────────────────────────────────────────


@app.get("/api/diary")
def diary_get():
    date_param = request.args.get("date")
    entries = get_entries(date_param)
    return jsonify({"entries": entries})


@app.post("/api/diary")
def diary_add():
    data = request.get_json(silent=True)
    if not data or "name" not in data:
        return jsonify({"error": "Missing required field: name"}), 400

    entry_id = add_entry(
        name=str(data["name"])[:200],
        quantity=str(data.get("quantity", ""))[:100] or None,
        calories=_to_float(data.get("calories")),
        protein_g=_to_float(data.get("protein_g")),
        carbs_g=_to_float(data.get("carbs_g")),
        fat_g=_to_float(data.get("fat_g")),
        estimated=bool(data.get("estimated", False)),
    )
    return jsonify({"id": entry_id}), 201


@app.delete("/api/diary/<int:entry_id>")
def diary_delete(entry_id):
    delete_entry(entry_id)
    return jsonify({"status": "deleted"})


@app.get("/api/diary/history")
def diary_history():
    try:
        days = min(max(int(request.args.get("days", 30)), 1), 90)
    except (TypeError, ValueError):
        days = 30
    return jsonify({"history": get_history(days)})


# ── Daily targets ─────────────────────────────────────────────────────────────


@app.get("/api/targets")
def targets():
    return jsonify(
        {
            "calories": DAILY_CALORIES,
            "protein_g": DAILY_PROTEIN_G,
            "carbs_g": DAILY_CARBS_G,
            "fat_g": DAILY_FAT_G,
        }
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _to_float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _scale_macros(macros: dict, multiplier: float) -> dict:
    if multiplier == 1.0:
        return macros
    return {
        k: round(v * multiplier, 1) if v is not None else None
        for k, v in macros.items()
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
