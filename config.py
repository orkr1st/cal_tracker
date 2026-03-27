import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
USDA_API_KEY = os.getenv("USDA_API_KEY", "")
NUTRITION_SOURCE = os.getenv("NUTRITION_SOURCE", "openfoodfacts")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
MAX_IMAGE_PX = 1024
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
