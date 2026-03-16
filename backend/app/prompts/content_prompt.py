from app.models.product import ProductRow


def build_prompt(row: ProductRow, tone: str) -> str:
    return f"""Generate brand content for the following Smartbox experience product.

## Product details
- Name: {row.name}
- Location: {row.location}
- Category: {row.category.value}
- Key selling point: {row.key_selling_point}

## Tone for this category
{tone}

## Your task
Generate the content assets described in the system prompt.

Ground every asset in this specific product — name the location, reference the key selling point,
and make the content feel like it was written for this experience only, not a generic template.

The tone must reflect the category guidance above. Be irreverently fun where appropriate,
always warm, always human. One well-chosen experience can change everything — write like you believe that.

Output ONLY valid JSON."""