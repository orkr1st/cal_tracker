import logging

from flask import Flask, jsonify, render_template, request

from config import DEBUG, MAX_UPLOAD_BYTES, SECRET_KEY
from services.claude_service import identify_foods
from services.image_utils import resize_to_jpeg
from services.nutrition_service import get_macros

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


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


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/analyze")
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
        macros = get_macros(search_term)
        estimated = False

        if macros.get("calories") is None:
            macros = {
                "calories": _to_float(food.get("est_kcal")),
                "protein_g": _to_float(food.get("est_protein_g")),
                "carbs_g": _to_float(food.get("est_carbs_g")),
                "fat_g": _to_float(food.get("est_fat_g")),
            }
            estimated = True

        results.append(
            {
                "name": food.get("name", "Unknown"),
                "quantity": food.get("quantity", ""),
                "search_term": search_term,
                "estimated": estimated,
                **macros,
            }
        )

    logger.info("Analysed image: %d food items found", len(results))
    return jsonify({"foods": results})


def _to_float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
