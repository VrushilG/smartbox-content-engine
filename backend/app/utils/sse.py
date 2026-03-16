import json
from typing import Any


def format_sse(event: str, data: Any) -> str:
    """Format a Server-Sent Events message string.

    Args:
        event: The SSE event name (e.g. "row_done", "job_complete").
        data: Any JSON-serialisable value to send as the event data.

    Returns:
        A properly formatted SSE string ending with a double newline.

    Example:
        >>> format_sse("row_done", {"product_id": "001"})
        'event: row_done\\ndata: {"product_id": "001"}\\n\\n'
    """
    json_data = json.dumps(data, default=str)
    return f"event: {event}\ndata: {json_data}\n\n"
