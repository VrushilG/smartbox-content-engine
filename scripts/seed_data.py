#!/usr/bin/env python3
"""seed_data.py — utility to validate and preview the sample CSV fixture.

Usage:
    cd backend
    python ../scripts/seed_data.py

Reads data/sample_products.csv, parses each row into a ProductRow model,
and prints a summary table. Does NOT make any API calls or modify any files.
"""

import sys
from pathlib import Path

# Allow running from project root or scripts/ directory
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

import pandas as pd  # noqa: E402

from app.models.product import Category, ProductRow  # noqa: E402

CSV_PATH = project_root / "data" / "sample_products.csv"


def main() -> None:
    if not CSV_PATH.exists():
        print(f"ERROR: sample CSV not found at {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(CSV_PATH, dtype=str)
    print(f"Loaded {len(df)} rows from {CSV_PATH.name}\n")

    rows: list[ProductRow] = []
    for idx, raw in df.iterrows():
        try:
            row = ProductRow(
                id=raw["id"].strip(),
                name=raw["name"].strip(),
                location=raw["location"].strip(),
                price=float(raw["price"]),
                category=Category(raw["category"].strip()),
                key_selling_point=raw["key_selling_point"].strip(),
            )
            rows.append(row)
        except Exception as exc:
            print(f"Row {idx + 2}: INVALID — {exc}", file=sys.stderr)
            continue

    if not rows:
        print("No valid rows found.", file=sys.stderr)
        sys.exit(1)

    col_w = [4, 35, 25, 8, 12]
    header = (
        f"{'ID':<{col_w[0]}}  {'Name':<{col_w[1]}}  {'Location':<{col_w[2]}}  "
        f"{'Price':>{col_w[3]}}  {'Category':<{col_w[4]}}"
    )
    print(header)
    print("-" * (sum(col_w) + 8))

    for row in rows:
        print(
            f"{row.id:<{col_w[0]}}  {row.name:<{col_w[1]}}  {row.location:<{col_w[2]}}  "
            f"€{row.price:>{col_w[3] - 1}.0f}  {row.category.value:<{col_w[4]}}"
        )

    print(f"\n✓ {len(rows)} valid product rows ready for processing.")


if __name__ == "__main__":
    main()
