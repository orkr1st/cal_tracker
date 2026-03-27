from flask import Flask, request, jsonify, render_template
from config import SECRET_KEY, MAX_UPLOAD_BYTES
from services.image_utils import resize_to_jpeg
from services.claude_service import identify_foods
from services.nutrition_service import get_macros

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

ALLOWED_MIMETYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}


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
    # Accept any image/* mimetype (browsers vary on HEIC reporting)
    if not mime.startswith("image/") and mime != "application/octet-stream":
        return jsonify({"error": f"Unsupported file type: {mime}"}), 415

    try:
        jpeg_bytes = resize_to_jpeg(file)
    except Exception as e:
        return jsonify({"error": f"Image processing failed: {e}"}), 422

    try:
        foods = identify_foods(jpeg_bytes)
    except Exception as e:
        return jsonify({"error": f"Food identification failed: {e}"}), 502

    results = []
    for food in foods:
        macros = get_macros(food.get("search_term", food.get("name", "")))
        estimated = False

        if macros.get("calories") is None:
            # Both USDA and OpenFoodFacts failed — use Claude's own estimates
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
                "search_term": food.get("search_term", ""),
                "estimated": estimated,
                **macros,
            }
        )

    return jsonify({"foods": results})


def _to_float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
