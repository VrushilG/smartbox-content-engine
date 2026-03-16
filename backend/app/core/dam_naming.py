from datetime import date


def generate_dam_filename(
    product_id: str,
    category: str,
    locale: str,
    asset_date: date | None = None,
) -> str:
    """Return a DAM-ready filename for a generated video asset.

    Format: PROD-{id}_{CATEGORY}_{LOCALE}_{YYYYMMDD}.mp4

    Args:
        product_id: The product identifier from the CSV.
        category: Category string (e.g. "wellness"). Uppercased automatically.
        locale: Locale code (e.g. "IE"). Uppercased automatically.
        asset_date: Date to embed in filename. Defaults to today.

    Returns:
        A DAM-compliant filename string.
    """
    if asset_date is None:
        asset_date = date.today()
    date_str = asset_date.strftime("%Y%m%d")
    return f"PROD-{product_id}_{category.upper()}_{locale.upper()}_{date_str}.mp4"
