"""Tests for services/portion_parser.py."""

import pytest

from services.portion_parser import parse_quantity


def test_grams():
    assert parse_quantity("300g") == pytest.approx(3.0)
    assert parse_quantity("150 g") == pytest.approx(1.5)
    assert parse_quantity("100g") == pytest.approx(1.0)
    assert parse_quantity("50 grams") == pytest.approx(0.5)


def test_kilograms():
    assert parse_quantity("1kg") == pytest.approx(10.0)
    assert parse_quantity("0.5 kg") == pytest.approx(5.0)


def test_ounces():
    assert parse_quantity("2oz") == pytest.approx(2 * 28.35 / 100, rel=1e-3)
    assert parse_quantity("1 ounce") == pytest.approx(28.35 / 100, rel=1e-3)


def test_pounds():
    assert parse_quantity("1 lb") == pytest.approx(453.59 / 100, rel=1e-3)


def test_millilitres():
    assert parse_quantity("200ml") == pytest.approx(2.0)


def test_cups():
    assert parse_quantity("1 cup") == pytest.approx(240 / 100)
    assert parse_quantity("2 cups") == pytest.approx(480 / 100)


def test_tablespoon():
    assert parse_quantity("1 tbsp") == pytest.approx(0.15)
    assert parse_quantity("2 tablespoons") == pytest.approx(0.30)


def test_teaspoon():
    assert parse_quantity("1 tsp") == pytest.approx(0.05)
    assert parse_quantity("3 teaspoons") == pytest.approx(0.15)


def test_slice():
    assert parse_quantity("1 slice") == pytest.approx(0.30)
    assert parse_quantity("2 slices") == pytest.approx(0.60)


def test_piece():
    assert parse_quantity("1 piece") == pytest.approx(0.50)


def test_serving():
    assert parse_quantity("1 serving") == pytest.approx(1.0)


def test_unknown_unit_returns_one():
    assert parse_quantity("1 medium") == pytest.approx(1.0)
    assert parse_quantity("large") == pytest.approx(1.0)
    assert parse_quantity("a handful") == pytest.approx(1.0)


def test_empty_returns_one():
    assert parse_quantity("") == pytest.approx(1.0)


def test_comma_decimal():
    assert parse_quantity("1,5 cups") == pytest.approx(1.5 * 240 / 100)


def test_no_numeric_part_returns_one():
    assert parse_quantity("some") == pytest.approx(1.0)
