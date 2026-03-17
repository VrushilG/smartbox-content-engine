import io

import pandas as pd
from fastapi import UploadFile

from app.models.product import ProductRow
from app.utils.exceptions import CSVValidationError
from app.utils.logger import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = {"id", "name", "location", "price", "category", "key_selling_point"}


async def parse_csv(file: UploadFile) -> list[ProductRow]:
    """Read and validate an uploaded CSV file, returning a list of ProductRow objects.

    Args:
        file: FastAPI UploadFile containing the CSV data.

    Returns:
        A list of validated ProductRow instances.

    Raises:
        CSVValidationError: If the file is empty, missing required columns,
            contains invalid category values, or has any other data issues.
    """
    raw = await file.read()
    if not raw.strip():
        raise CSVValidationError("Uploaded CSV file is empty.")

    try:
        # Try UTF-8 first, then fall back to Windows-1252 (common for Excel-exported CSVs)
        for encoding in ("utf-8-sig", "windows-1252", "latin-1"):
            try:
                df = pd.read_csv(io.BytesIO(raw), dtype=str, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise CSVValidationError("Could not decode CSV — please save it as UTF-8.")
    except CSVValidationError:
        raise
    except Exception as exc:
        raise CSVValidationError(f"Could not parse CSV: {exc}") from exc

    df.columns = [c.strip().lower() for c in df.columns]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise CSVValidationError(
            f"CSV is missing required columns: {', '.join(sorted(missing))}"
        )

    if df.empty:
        raise CSVValidationError("CSV has no data rows.")

    rows: list[ProductRow] = []
    for idx, raw_row in df.iterrows():
        row_dict = {k: v.strip() if isinstance(v, str) else v for k, v in raw_row.items()}
        try:
            row_dict["price"] = float(row_dict["price"])
            rows.append(ProductRow.model_validate(row_dict, strict=False))
        except Exception as exc:
            raise CSVValidationError(f"Invalid data in row {idx + 2}: {exc}") from exc

    logger.info("csv_parsed", row_count=len(rows))
    return rows
