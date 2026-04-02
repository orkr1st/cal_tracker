"""Tests for services/diary_service.py."""

import sqlite3
from datetime import date

import pytest

import config
from services import diary_service


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Each test gets a fresh in-process SQLite database."""
    db_path = str(tmp_path / "test_diary.db")
    monkeypatch.setattr(config, "DATABASE_PATH", db_path)
    diary_service.init_db()
    yield db_path


def test_init_creates_table(isolated_db):
    conn = sqlite3.connect(isolated_db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    conn.close()
    assert any("diary" in t[0] for t in tables)


def test_add_and_get_entry():
    entry_id = diary_service.add_entry("apple", "1 medium", 52.0, 0.3, 14.0, 0.2)
    assert isinstance(entry_id, int)

    entries = diary_service.get_entries()
    assert len(entries) == 1
    e = entries[0]
    assert e["name"] == "apple"
    assert e["quantity"] == "1 medium"
    assert e["calories"] == pytest.approx(52.0)
    assert e["protein_g"] == pytest.approx(0.3)
    assert e["carbs_g"] == pytest.approx(14.0)
    assert e["fat_g"] == pytest.approx(0.2)
    assert e["estimated"] == 0


def test_add_entry_estimated_flag():
    diary_service.add_entry("mystery food", "100g", 200.0, 10.0, 30.0, 5.0, estimated=True)
    entries = diary_service.get_entries()
    assert entries[0]["estimated"] == 1


def test_delete_entry():
    entry_id = diary_service.add_entry("rice", "200g", 260.0, 5.0, 55.0, 1.0)
    diary_service.delete_entry(entry_id)
    assert diary_service.get_entries() == []


def test_get_entries_empty():
    assert diary_service.get_entries() == []


def test_get_entries_returns_only_today():
    diary_service.add_entry("egg", "2 eggs", 140.0, 12.0, 1.0, 10.0)
    # Manually insert an old entry
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.execute(
        "INSERT INTO diary (date, name, quantity, calories, protein_g, carbs_g, fat_g) "
        "VALUES ('2000-01-01', 'old food', '100g', 100, 5, 20, 3)"
    )
    conn.commit()
    conn.close()

    entries = diary_service.get_entries()
    assert len(entries) == 1
    assert entries[0]["name"] == "egg"


def test_get_entries_specific_date():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.execute(
        "INSERT INTO diary (date, name, quantity, calories, protein_g, carbs_g, fat_g) "
        "VALUES ('2024-06-15', 'banana', '1 medium', 89, 1.1, 23.0, 0.3)"
    )
    conn.commit()
    conn.close()

    entries = diary_service.get_entries("2024-06-15")
    assert len(entries) == 1
    assert entries[0]["name"] == "banana"


def test_add_multiple_entries_ordering():
    diary_service.add_entry("first", "100g", 100.0, 5.0, 15.0, 3.0)
    diary_service.add_entry("second", "100g", 200.0, 10.0, 25.0, 5.0)
    entries = diary_service.get_entries()
    assert len(entries) == 2
    assert entries[0]["name"] == "first"
    assert entries[1]["name"] == "second"


# ── get_history ────────────────────────────────────────────────────────────────


def test_get_history_empty():
    assert diary_service.get_history(7) == []


def test_get_history_aggregates_daily():
    diary_service.add_entry("apple",  "100g", 52.0, 0.3, 14.0, 0.2)
    diary_service.add_entry("banana", "100g", 89.0, 1.1, 23.0, 0.3)
    result = diary_service.get_history(7)
    assert len(result) == 1
    r = result[0]
    assert r["date"] == date.today().isoformat()
    assert r["calories"]  == pytest.approx(141.0)
    assert r["protein_g"] == pytest.approx(1.4)
    assert r["entry_count"] == 2


def test_get_history_excludes_entries_outside_window():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.execute(
        "INSERT INTO diary (date, name, calories, protein_g, carbs_g, fat_g) "
        "VALUES ('2000-01-01', 'ancient food', 500, 20, 60, 15)"
    )
    conn.commit()
    conn.close()
    # 7-day window should not include the year-2000 entry
    result = diary_service.get_history(7)
    assert result == []


def test_get_history_groups_by_day():
    diary_service.add_entry("breakfast", "100g", 300.0, 10.0, 45.0, 8.0)
    diary_service.add_entry("lunch",     "100g", 600.0, 30.0, 70.0, 15.0)
    diary_service.add_entry("dinner",    "100g", 500.0, 25.0, 60.0, 12.0)
    result = diary_service.get_history(7)
    assert len(result) == 1
    assert result[0]["calories"] == pytest.approx(1400.0)
    assert result[0]["entry_count"] == 3
