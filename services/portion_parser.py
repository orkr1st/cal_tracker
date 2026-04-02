"""Parse a quantity string into a multiplier relative to 100 g."""

import re

# Map unit names → grams per unit
_UNIT_GRAMS: dict[str, float] = {
    "g": 1,
    "gram": 1,
    "grams": 1,
    "kg": 1000,
    "kilogram": 1000,
    "kilograms": 1000,
    "oz": 28.35,
    "ounce": 28.35,
    "ounces": 28.35,
    "lb": 453.59,
    "lbs": 453.59,
    "pound": 453.59,
    "pounds": 453.59,
    "ml": 1,
    "milliliter": 1,
    "milliliters": 1,
    "millilitre": 1,
    "millilitres": 1,
    "l": 1000,
    "liter": 1000,
    "liters": 1000,
    "litre": 1000,
    "litres": 1000,
    "cup": 240,
    "cups": 240,
    "tbsp": 15,
    "tablespoon": 15,
    "tablespoons": 15,
    "tsp": 5,
    "teaspoon": 5,
    "teaspoons": 5,
    "slice": 30,
    "slices": 30,
    "piece": 50,
    "pieces": 50,
    "serving": 100,
    "servings": 100,
}

_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+)", re.IGNORECASE)


def parse_quantity(quantity: str) -> float:
    """Return a multiplier relative to 100 g.

    Examples
    --------
    "300g"    → 3.0
    "150 g"   → 1.5
    "2 cups"  → 4.8
    "1 slice" → 0.3
    "large"   → 1.0  (unknown → default)
    ""        → 1.0
    """
    if not quantity:
        return 1.0

    m = _PATTERN.search(quantity.strip())
    if not m:
        return 1.0

    amount = float(m.group(1).replace(",", "."))
    unit = m.group(2).lower()

    grams_per_unit = _UNIT_GRAMS.get(unit)
    if grams_per_unit is None:
        return 1.0

    return (amount * grams_per_unit) / 100.0
