from datetime import date

import pytest

from app.core.dam_naming import generate_dam_filename


def test_basic_filename():
    d = date(2024, 3, 15)
    result = generate_dam_filename("001", "wellness", "IE", d)
    assert result == "PROD-001_WELLNESS_IE_20240315.mp4"


def test_category_is_uppercased():
    d = date(2024, 1, 1)
    result = generate_dam_filename("002", "adventure", "IE", d)
    assert "ADVENTURE" in result


def test_locale_is_uppercased():
    d = date(2024, 1, 1)
    result = generate_dam_filename("003", "gastronomy", "fr", d)
    assert "_FR_" in result


def test_all_categories():
    d = date(2024, 6, 20)
    categories = ["getaways", "wellness", "adventure", "gastronomy", "pampering"]
    for cat in categories:
        result = generate_dam_filename("001", cat, "IE", d)
        assert cat.upper() in result
        assert result.startswith("PROD-001_")
        assert result.endswith(".mp4")


def test_date_format_yyyymmdd():
    d = date(2024, 12, 5)
    result = generate_dam_filename("010", "wellness", "IE", d)
    assert "20241205" in result


def test_defaults_to_today():
    result = generate_dam_filename("001", "wellness", "IE")
    today_str = date.today().strftime("%Y%m%d")
    assert today_str in result


def test_extension_is_mp4():
    result = generate_dam_filename("001", "wellness", "IE", date(2024, 1, 1))
    assert result.endswith(".mp4")


def test_format_structure():
    d = date(2024, 7, 4)
    result = generate_dam_filename("ABC", "pampering", "GB", d)
    parts = result.replace(".mp4", "").split("_")
    assert parts[0] == "PROD-ABC"
    assert parts[1] == "PAMPERING"
    assert parts[2] == "GB"
    assert parts[3] == "20240704"
