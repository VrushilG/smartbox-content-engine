# API Reference — Smartbox Content Engine

Base URL: `http://localhost:8000` (development)

All endpoints return JSON unless noted. The `/process` endpoint returns a Server-Sent Events stream.

---

## GET /health

Health check endpoint. Used by Docker and load balancers.

**Response** `200 OK`

```json
{ "status": "ok" }
```

---

## POST /process

Upload a CSV file and receive a Server-Sent Events stream of generated content assets.

**Request**

`Content-Type: multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | CSV file with product rows |

**CSV format**

Required columns (order-independent):

| Column | Type | Example |
|--------|------|---------|
| `id` | string | `001` |
| `name` | string | `Weekend Spa Escape` |
| `location` | string | `Wicklow Mountains` |
| `price` | number | `149` |
| `category` | enum | `wellness` |
| `key_selling_point` | string | `Two-night stay with full-day spa access` |

Valid `category` values: `getaways`, `wellness`, `adventure`, `gastronomy`, `pampering`

**Response** `200 OK`

`Content-Type: text/event-stream`

The response body is a stream of SSE events in the format:

```
event: <event_name>
data: <json_object>

```

### SSE events

#### `job_started`

Emitted once when the job begins.

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "rows_total": 5
}
```

#### `row_started`

Emitted when processing begins for each product row.

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "product_id": "001",
  "name": "Weekend Spa Escape"
}
```

#### `row_done`

Emitted when a row is successfully processed. Contains the full generated asset.

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "product_id": "001",
  "asset": {
    "product_id": "001",
    "video_script": "Picture this: misty mountains...",
    "voiceover_copy": "Slip away to the Wicklow Mountains...",
    "image_prompt": "Aerial view of a luxury mountain spa at golden hour...",
    "hashtags": ["spaWeekend", "wicklowMountains", "selfCare"],
    "dam_filename": "PROD-001_WELLNESS_IE_20240315.mp4"
  }
}
```

#### `row_error`

Emitted when a row fails to process (LLM error, etc.).

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "product_id": "002",
  "error": "Claude API error: rate limit exceeded"
}
```

#### `job_complete`

Emitted once when all rows have been processed.

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "rows_done": 5
}
```

**Error responses**

| Status | Condition |
|--------|-----------|
| `422 Unprocessable Entity` | CSV is empty, missing required columns, invalid category, or malformed data |
| `500 Internal Server Error` | Unexpected server error |

**Example error body** `422`

```json
{
  "detail": "CSV is missing required columns: category, key_selling_point"
}
```

---

## GET /status/{job_id}

Retrieve the current status of a processing job.

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | UUID string | Job ID received in the `job_started` SSE event |

**Response** `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2024-03-15T10:30:00Z",
  "rows_total": 5,
  "rows_done": 2
}
```

**Status values**

| Value | Meaning |
|-------|---------|
| `pending` | Job created, not yet started |
| `processing` | Job currently running |
| `complete` | All rows processed |
| `failed` | Job encountered a fatal error |

**Error responses**

| Status | Condition |
|--------|-----------|
| `404 Not Found` | Job ID does not exist |

---

## GeneratedAsset schema

Returned inside `row_done` events and the `/status` endpoint.

| Field | Type | Description |
|-------|------|-------------|
| `product_id` | string | Source product ID from the CSV |
| `video_script` | string | ~75-word 30-second video script |
| `voiceover_copy` | string | 40–60 word spoken-word paragraph |
| `image_prompt` | string | 50–80 word AI image generation prompt |
| `hashtags` | string[] | 5–8 hashtags (no # symbol, camelCase) |
| `dam_filename` | string | `PROD-{id}_{CATEGORY}_{LOCALE}_{YYYYMMDD}.mp4` |
