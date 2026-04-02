# Cal Tracker

Photograph a meal and get an instant nutritional breakdown. A lightweight Flask app powered by Claude vision and Open Food Facts.

## Features

- **Meal analysis** — take or upload a photo and get per-item macros (calories, protein, carbs, fat)
- **Live portion editing** — adjust quantities on any detected item and macros update in real time
- **Food diary** — log meals to a local SQLite database; navigate by date and delete entries
- **30-day history chart** — bar chart with per-macro toggle and clickable bars for date navigation
- **Daily targets** — animated progress bars showing intake vs. configurable goals
- **Rate limiting** — configurable request cap on the analyse endpoint
- **Docker support** — single-command deploy with Docker Compose

## Requirements

- Python 3.12+
- An [Anthropic API key](https://console.anthropic.com/) (Claude vision)
- Optionally a [USDA FoodData Central API key](https://fdc.nal.usda.gov/api-guide.html) for enhanced nutrition lookup

## Setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/orkr1st/cal_tracker.git
cd cal_tracker

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and fill in your API keys and a SECRET_KEY
# Generate SECRET_KEY with: python3 -c "import secrets; print(secrets.token_hex(32))"

# 5. Run
flask run
```

The app will be available at `http://localhost:5000`.

## Configuration

All settings are read from environment variables (or a `.env` file):

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Claude API key |
| `USDA_API_KEY` | — | Optional. Enables USDA nutrition lookup |
| `NUTRITION_SOURCE` | `openfoodfacts` | `openfoodfacts` or `usda` |
| `SECRET_KEY` | random | Flask session secret — set a stable value |
| `ANALYZE_RATE_LIMIT` | `30 per minute` | Rate limit for the analyse endpoint |
| `DATABASE_PATH` | `cal_tracker.db` | SQLite database file path |
| `DAILY_CALORIES` | `2000` | Daily calorie target (kcal) |
| `DAILY_PROTEIN_G` | `150` | Daily protein target (g) |
| `DAILY_CARBS_G` | `250` | Daily carbs target (g) |
| `DAILY_FAT_G` | `65` | Daily fat target (g) |
| `LOG_DIR` | `logs` | Directory for rotating log files |

## Docker

```bash
# Build and start
docker compose up --build

# Run in background
docker compose up -d --build
```

The app runs on port `5000`. Pass your secrets via the `.env` file — it is loaded automatically by `docker-compose.yml`.

## Running Tests

```bash
pytest
```

The test suite mocks all external API calls so no real keys are needed.

## Project Structure

```
cal_tracker/
├── app.py                   # Flask app, routes
├── config.py                # Settings from environment
├── services/
│   ├── claude_service.py    # Claude vision integration
│   ├── nutrition_service.py # Open Food Facts / USDA lookup
│   ├── diary_service.py     # SQLite food diary
│   ├── portion_parser.py    # Quantity string → multiplier
│   └── image_utils.py       # JPEG resize/normalisation
├── static/
│   ├── css/style.css
│   └── js/app.js
├── templates/index.html
└── tests/
```
