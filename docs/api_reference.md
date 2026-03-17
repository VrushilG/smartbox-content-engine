# API Reference — Smartbox Content Engine

Base URLs:
- **Production**: `https://smartbox-content-engine-production.up.railway.app`
- **Local development**: `http://localhost:8000`

All endpoints return JSON unless noted. The `/process` endpoint returns a Server-Sent Events stream.

---

## GET /health

Health check endpoint. Used by Docker, Railway, and load balancers.

**Response** `200 OK`

```json
{ "status": "ok" }
```

---

## GET /config

Returns public configuration values needed by the frontend to initialise Supabase auth.
Safe to call unauthenticated — returns empty strings when Supabase is not configured.

**Response** `200 OK`

```json
{
  "supabase_url": "https://xxxx.supabase.co",
  "supabase_anon_key": "eyJ..."
}
```

---

## GET /history

Returns the full generation history for a user from Supabase. Returns an empty list if
Supabase is not configured or the user has no prior generations.

**Query parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Supabase user UUID |

**Response** `200 OK`

```json
[
  {
    "product_id": "001",
    "video_script": "...",
    "voiceover_copy": "...",
    "image_url": "https://...",
    "video_url": "https://...",
    "dam_filename": "PROD-001_WELLNESS_IE_20260317.mp4",
    ...
  }
]
```

Results are ordered newest first.

---

## POST /process

Upload a CSV file and receive a Server-Sent Events stream of generated content assets.
Up to `ROW_CONCURRENCY` rows (default 4) are processed in parallel.

**Request**

`Content-Type: multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | CSV file with product rows |

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `X-User-ID` | No | Supabase user UUID — if provided, assets are persisted to the user's history |

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

#### `row_text_done`

Emitted when LLM text generation completes for a row. Contains all text fields.
The UI renders the content immediately — image and video generation continue in background.

```json
{
  "product_id": "001",
  "asset": {
    "product_id": "001",
    "video_script": "Picture this: the Wicklow mist clears...",
    "voiceover_copy": "Slip away to the mountains...",
    "product_description": "A two-night stay deep in the Wicklow Mountains...",
    "image_prompt": "A woman in a white robe steps onto a wooden spa terrace...",
    "video_prompt": "Woman unwrapping a gift box, then stepping into a mountain hot spring...",
    "hashtags": ["spaweekend", "wicklow", "selfcare", "gifting", "weekendaway"],
    "dam_filename": "PROD-001_WELLNESS_IE_20260317.mp4"
  }
}
```

#### `row_image_generating`

Emitted just before image generation begins, so the UI can show a spinner.

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "product_id": "001"
}
```

#### `row_image_done`

Emitted when image generation completes (or fails/skips).

```json
{
  "product_id": "001",
  "image_url": "/static/images/001.jpg",
  "image_status": "done"
}
```

`image_status` values: `"done"` | `"failed"` | `"skipped"`

#### `row_video_generating`

Emitted just before video generation begins.

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "product_id": "001"
}
```

#### `row_video_done`

Emitted when video generation completes (or fails/skips).

```json
{
  "product_id": "001",
  "video_url": "/static/videos/001.mp4",
  "video_status": "done",
  "video_error": ""
}
```

`video_status` values: `"done"` | `"failed"` | `"skipped"`

On failure, `video_error` contains a human-readable reason (e.g. `"Veo QPM limit — ..."`)

#### `row_done`

Emitted when a row is fully processed. Contains the complete generated asset including
all text, image, and video fields.

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "product_id": "001",
  "asset": {
    "product_id": "001",
    "video_script": "Picture this: the Wicklow mist clears...",
    "voiceover_copy": "Slip away to the mountains...",
    "product_description": "A two-night stay deep in the Wicklow Mountains...",
    "image_prompt": "A woman in a white robe steps onto a wooden spa terrace...",
    "video_prompt": "Woman unwrapping a gift box, then stepping into a mountain hot spring...",
    "hashtags": ["spaweekend", "wicklow", "selfcare", "gifting", "weekendaway"],
    "dam_filename": "PROD-001_WELLNESS_IE_20260317.mp4",
    "image_url": "/static/images/001.jpg",
    "video_url": "/static/videos/001.mp4",
    "image_status": "done",
    "video_status": "done",
    "image_error": "",
    "video_error": ""
  }
}
```

#### `row_error`

Emitted when text generation fails for a row. The job continues with remaining rows.

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "product_id": "002",
  "error": "LLM API error: rate limit exceeded"
}
```

#### `job_complete`

Emitted once when all rows have finished processing.

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

Retrieve the current status of a processing job. Uses the in-memory job store
(jobs are lost on server restart).

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | UUID string | Job ID received in the `job_started` SSE event |

**Response** `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2026-03-17T10:30:00Z",
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

## DELETE /assets/{product_id}

Delete a generated asset from Supabase DB and Storage. No-op if Supabase is not configured.

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `product_id` | string | Product ID from the original CSV |

**Query parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Supabase user UUID |

**Response** `200 OK`

```json
{ "ok": true }
```

---

## POST /generate/text

Generate text assets only (no image or video) for all rows in a CSV.
Returns a synchronous JSON response — no SSE stream.

**Request**

`Content-Type: multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | CSV file with product rows |

**Response** `200 OK`

```json
[
  {
    "product_id": "001",
    "video_script": "...",
    "voiceover_copy": "...",
    "product_description": "...",
    "image_prompt": "...",
    "video_prompt": "...",
    "hashtags": ["..."],
    "dam_filename": "PROD-001_WELLNESS_IE_20260317.mp4",
    "image_url": "", "video_url": "",
    "image_status": "skipped", "video_status": "skipped"
  }
]
```

---

## POST /generate/image

Generate a single image for a product. Synchronous — waits for the image to be ready.

**Request** `Content-Type: application/json`

```json
{
  "product_id": "001",
  "image_prompt": "A woman in a white robe steps onto a spa terrace..."
}
```

**Response** `200 OK`

```json
{
  "product_id": "001",
  "image_url": "/static/images/001.jpg",
  "image_status": "done"
}
```

---

## POST /generate/video

Generate a single video clip for a product. Synchronous — may take 1–4 minutes while
Vertex AI Veo polls for completion.

**Request** `Content-Type: application/json`

```json
{
  "product_id": "001",
  "video_prompt": "Woman unwrapping a gift box on a spa terrace in Wicklow mountains..."
}
```

**Response** `200 OK`

```json
{
  "product_id": "001",
  "video_url": "/static/videos/001.mp4",
  "video_status": "done",
  "video_error": ""
}
```

---

## GeneratedAsset schema

Returned inside `row_done` events, `/generate/text` responses, and `/history`.

| Field | Type | Description |
|-------|------|-------------|
| `product_id` | string | Source product ID from the CSV |
| `video_script` | string | ~75-word 30-second video script; mid-experience candid moment |
| `voiceover_copy` | string | 40–60 word spoken-word paragraph; written for the ear |
| `product_description` | string | 2–3 sentences, 40–60 words; evergreen, feeling-focused |
| `image_prompt` | string | 60–80 word AI image brief; photorealistic, camera spec, real setting |
| `video_prompt` | string | 15–25 word scene brief for video generation; no camera instructions |
| `hashtags` | string[] | 5–8 lowercase hashtags, no `#` symbol |
| `dam_filename` | string | `PROD-{id}_{CATEGORY}_{LOCALE}_{YYYYMMDD}.mp4` |
| `image_url` | string | Local path (`/static/images/{id}.jpg`) or Supabase CDN URL |
| `video_url` | string | Local path (`/static/videos/{id}.mp4`) or remote provider URL |
| `image_status` | string | `"skipped"` \| `"generating"` \| `"done"` \| `"failed"` |
| `video_status` | string | `"skipped"` \| `"generating"` \| `"done"` \| `"failed"` |
| `image_error` | string | Error message if `image_status == "failed"`, else empty string |
| `video_error` | string | Error message if `video_status == "failed"`, else empty string |
