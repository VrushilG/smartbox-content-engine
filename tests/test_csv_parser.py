import io
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.csv_parser import parse_csv
from app.models.product import Category
from app.utils.exceptions import CSVValidationError

VALID_CSV = b"""id,name,location,price,category,key_selling_point
001,Weekend Spa Escape,Wicklow Mountains,149,wellness,Two-night stay with full-day spa access
002,Helicopter Tour,Dublin,199,adventure,30-minute aerial tour
"""

MISSING_COL_CSV = b"""id,name,location,price
001,Spa Escape,Wicklow,149
"""

EMPTY_CSV = b""

HEADER_ONLY_CSV = b"id,name,location,price,category,key_selling_point\n"

INVALID_CATEGORY_CSV = b"""id,name,location,price,category,key_selling_point
001,Spa Escape,Wicklow,149,unknown_cat,Some feature
"""

INVALID_PRICE_CSV = b"""id,name,location,price,category,key_selling_point
001,Spa Escape,Wicklow,not_a_price,wellness,Some feature
"""


def make_upload_file(content: bytes, filename: str = "test.csv") -> MagicMock:
    mock = MagicMock()
    mock.filename = filename
    mock.read = AsyncMock(return_value=content)
    return mock


@pytest.mark.asyncio
async def test_parse_valid_csv():
    upload = make_upload_file(VALID_CSV)
    rows = await parse_csv(upload)
    assert len(rows) == 2
    assert rows[0].id == "001"
    assert rows[0].category == Category.wellness
    assert rows[1].id == "002"
    assert rows[1].category == Category.adventure


@pytest.mark.asyncio
async def test_parse_csv_missing_columns():
    upload = make_upload_file(MISSING_COL_CSV)
    with pytest.raises(CSVValidationError, match="missing required columns"):
        await parse_csv(upload)


@pytest.mark.asyncio
async def test_parse_empty_file():
    upload = make_upload_file(EMPTY_CSV)
    with pytest.raises(CSVValidationError, match="empty"):
        await parse_csv(upload)


@pytest.mark.asyncio
async def test_parse_header_only():
    upload = make_upload_file(HEADER_ONLY_CSV)
    with pytest.raises(CSVValidationError, match="no data rows"):
        await parse_csv(upload)


@pytest.mark.asyncio
async def test_parse_invalid_category():
    upload = make_upload_file(INVALID_CATEGORY_CSV)
    with pytest.raises(CSVValidationError, match="row"):
        await parse_csv(upload)


@pytest.mark.asyncio
async def test_parse_invalid_price():
    upload = make_upload_file(INVALID_PRICE_CSV)
    with pytest.raises((CSVValidationError, ValueError)):
        await parse_csv(upload)


@pytest.mark.asyncio
async def test_parse_csv_strips_whitespace():
    csv_with_spaces = b"id , name , location , price , category , key_selling_point\n001 , Spa , Wicklow , 149 , wellness , Nice stay\n"
    upload = make_upload_file(csv_with_spaces)
    rows = await parse_csv(upload)
    assert len(rows) == 1
    assert rows[0].id == "001"
