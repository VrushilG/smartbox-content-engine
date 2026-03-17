# Architecture — Smartbox Content Engine

## Overview

The Smartbox Content Engine is a single-container web application that takes a CSV of product rows
and generates brand-aligned content assets using a cascade of AI providers. The architecture is
async-first and provider-agnostic — every external dependency (LLM, image, video, database) is
resolved at runtime from environment variables, with graceful fallbacks when providers are absent.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Browser                                          │
│  ┌──────────────┐  drag-drop  ┌────────────────────────────────────────────┐ │
│  │  uploader.js │ ──────────> │              app.js                        │ │
│  └──────────────┘             │  (event coordinator, table, search, auth)  │ │
│                               └──────────────────┬─────────────────────────┘ │
│                                                  │ fetch + SSE stream        │
└──────────────────────────────────────────────────┼──────────────────────────┘
                                                   │
                              ┌────────────────────▼─────────────────────────┐
                              │       FastAPI  (Railway Docker, port 8000)    │
                              │                                               │
                              │  POST /process    GET /health    GET /config  │
                              │  GET /history     DELETE /assets/{id}         │
                              │  GET /status/{id}                             │
                              │  POST /generate/text|image|video              │
                              │                                               │
                              │  ┌─────────────────────────────────────────┐ │
                              │  │              csv_parser.py               │ │
                              │  │     (validates → list[ProductRow])       │ │
                              │  └──────────────────┬──────────────────────┘ │
                              │                     │                         │
                              │  ┌──────────────────▼──────────────────────┐ │
                              │  │            pipeline.py                   │ │
                              │  │   asyncio.Semaphore(ROW_CONCURRENCY=4)   │ │
                              │  │   up to 4 rows processed in parallel     │ │
                              │  └──────┬──────────────┬────────────────────┘ │
                              │         │              │                       │
                              │  ┌──────▼──────┐  ┌───▼────────────────────┐ │
                              │  │ llm_router  │  │  image_service.py       │ │
                              │  │  .py        │  │  Vertex Imagen 4 Fast   │ │
                              │  └──────┬──────┘  │  → Fal FLUX (fallback) │ │
                              │         │         └───┬────────────────────┘  │
                              │  ┌──────┴──────┐      │                       │
                              │  │             │  ┌───▼────────────────────┐  │
                              │  │  Claude     │  │  video_service.py       │  │
                              │  │  OpenRouter │  │  Vertex Veo 3.1 Fast    │  │
                              │  │  Ollama     │  │  → Fal Wan (fallback)  │  │
                              │  │             │  │  → Replicate Wan       │  │
                              │  └─────────────┘  └───┬────────────────────┘  │
                              │                       │                        │
                              │  ┌────────────────────▼──────────────────────┐│
                              │  │         supabase_service.py  (optional)    ││
                              │  │   DB: content_assets, content_jobs         ││
                              │  │   Storage: product-images, product-videos  ││
                              │  └────────────────────────────────────────────┘│
                              └──────────────────────────────────────────────┘
```

---

## Data flow

1. **Upload** — User drags a CSV onto the frontend. `uploader.js` validates the file extension and fires an event to `app.js`.

2. **POST /process** — `app.js` sends a `multipart/form-data` POST with the CSV file and an optional `X-User-ID` header. The response is a `text/event-stream`.

3. **CSV parsing** — `csv_parser.py` reads the uploaded bytes with pandas, detects encoding (UTF-8 → Windows-1252 → Latin-1), validates required columns and category values, and returns a `list[ProductRow]`.

4. **`job_started` SSE** — Pipeline emits the job ID and total row count immediately so the UI can show a progress bar.

5. **Parallel row processing** — `pipeline.py` uses `asyncio.Semaphore(ROW_CONCURRENCY)` to process up to 4 rows concurrently. For each row:

   a. **`row_started` SSE** — browser renders a skeleton card immediately.

   b. **LLM text generation** — `llm_router.py` selects the active provider and generates all text fields. On success: **`row_text_done` SSE** with the full text asset. On failure: `row_error` SSE; row is skipped.

   c. **Image generation** — `image_service.py` generates a 16:9 image from the LLM's `image_prompt`. **`row_image_generating` SSE** → generation → **`row_image_done` SSE**.

   d. **Video generation** — `video_service.py` generates a 4-second clip using the branded video template. **`row_video_generating` SSE** → generation (may take 1–3 min for Vertex Veo) → **`row_video_done` SSE**.

   e. **Persistence** — If Supabase is configured, `supabase_service.py` saves the complete asset to the DB and uploads media files to Storage buckets.

   f. **`row_done` SSE** — browser card is updated with the full finalised asset.

6. **`job_complete` SSE** — emitted once all rows finish; UI hides the progress bar.

---

## LLM routing

Three-way priority cascade — first configured provider wins:

```
ANTHROPIC_API_KEY set?
  → Yes: claude_service.py  (Anthropic SDK, claude-sonnet-4-5)
  → No:  OPENROUTER_API_KEY set?
           → Yes: openrouter_service.py  (free models: Qwen 2.5 72B / DeepSeek V3 / Llama 3.3 70B)
           → No:  ollama_service.py  (local Llama 3 via REST at OLLAMA_URL)
```

All three services expose the same interface:
```python
async def generate(row: ProductRow, system_prompt: str, user_prompt: str) -> GeneratedAsset
```

---

## Media generation cascade

**Image** (first configured provider wins, no fallback cascade):
```
VERTEXAI_PROJECT set? → Vertex AI Imagen 4 Fast  (16:9, saved to /static/images/)
FAL_API_KEY set?      → Fal.ai FLUX Schnell       (landscape_16_9, saved locally)
neither              → skipped
```

**Video** (first configured provider wins):
```
VERTEXAI_PROJECT set?   → Vertex AI Veo 3.1 Fast  (4 sec, 16:9, saved to /static/videos/)
FAL_API_KEY set?        → Fal.ai Wan T2V           (returns remote URL)
REPLICATE_API_KEY set?  → Replicate Wan 2.1        (returns remote URL)
none                   → skipped
```

> No fallback cascade by design — if the primary provider fails, the step is marked `failed`
> rather than silently attempting a second provider. This prevents unexpected cost escalation.

---

## Key design decisions

| Decision | Rationale |
|----------|-----------|
| SSE over WebSockets | One-directional; no upgrade handshake; works over standard HTTP; simpler client |
| `asyncio.Semaphore` over sequential loop | Bounded parallelism without OS threads; `ROW_CONCURRENCY` is tunable via env var |
| No media fallback cascade | Avoids unexpected charges when primary provider fails; status is surfaced clearly |
| Random GCP project selection | `random.choice(vertex_projects)` distributes load across two projects, doubling quota |
| In-memory job store | Appropriate for POC; swap for Redis when scaling to multiple workers |
| Module-level LLM routing | `pipeline.py` stays decoupled from LLM choice; new providers require no pipeline changes |
| No frontend build step | No Node.js in container; zero rebuild wait; changes take effect on page refresh |
| pydantic-settings BaseSettings | Single source of truth for config; type-safe, validated at startup |
| Structured logging (structlog) | Machine-readable logs from day one; easy to ship to Datadog/CloudWatch |
| Supabase for optional persistence | Stateless container with durable external storage; graceful no-op when unconfigured |

---

## Directory map

```
backend/
  app/
    main.py              — FastAPI app factory, CORS, static file serving, frontend resolution
    config.py            — pydantic-settings (all env vars, provider routing properties)
    api/
      routes.py          — /process (SSE), /health, /config, /history, /assets, /status
      generate.py        — /generate/text, /generate/image, /generate/video
    core/
      csv_parser.py      — CSV → list[ProductRow] (encoding detection, validation)
      pipeline.py        — async SSE generator, asyncio.Semaphore concurrency
      dam_naming.py      — DAM filename constructor (PROD-{id}_{CAT}_{LOCALE}_{DATE}.mp4)
    services/
      llm_router.py      — picks Claude, OpenRouter, or Ollama
      claude_service.py  — Anthropic SDK wrapper
      openrouter_service.py — OpenAI-compatible client for OpenRouter free models
      ollama_service.py  — Ollama REST wrapper (local fallback)
      image_service.py   — Vertex Imagen 4 / Fal FLUX cascade
      video_service.py   — Vertex Veo 3.1 / Fal Wan / Replicate Wan cascade
      supabase_service.py — optional DB + Storage persistence (no-op if unconfigured)
    models/
      product.py         — ProductRow + Category enum
      output.py          — GeneratedAsset (all text + media + status fields)
      job.py             — PipelineJob + JobStatus enum
    prompts/
      system_prompt.py   — SYSTEM_PROMPT (brand voice, JSON schema, field specs, forbidden words)
      content_prompt.py  — build_prompt(row, tone) → per-row user message
      category_tones.py  — CATEGORY_TONES dict (5 categories with creative direction)
      video_template.py  — SMARTBOX_VIDEO_TEMPLATE + build_video_prompt()
    utils/
      logger.py          — structlog setup, get_logger()
      sse.py             — format_sse(event, data) → SSE string
      exceptions.py      — CSVValidationError, LLMError, PipelineError

frontend/
  src/
    index.html           — app shell, prototype disclaimer banner, font imports
    css/
      main.css           — design tokens (CSS custom properties), base reset, layout
      components.css     — cards, buttons, pills, progress, upload zone, lightboxes, auth
    js/
      app.js             — entry point: initialises modules, wires events, table/pagination/export
      api.js             — fetch wrapper + manual SSE stream parser (ReadableStream)
      ui.js              — all DOM rendering: cards, lightboxes, progress bar, error banner
      uploader.js        — drag-drop + file input handler, .csv MIME validation
      auth.js            — Supabase auth: Google SSO + email/password, graceful no-op

docker/
  Dockerfile             — python:3.12-slim, non-root user, health check, Railway PORT support

tests/
  conftest.py            — pytest fixtures (ProductRow samples)
  test_csv_parser.py     — 8 tests: validation, encoding, missing columns
  test_dam_naming.py     — 8 tests: filename format, all categories, date handling
  test_pipeline.py       — 8 tests: SSE event sequence, image/video status, error handling
  test_routes.py         — 4 tests: /health, /process (happy path + errors), /status 404
```
