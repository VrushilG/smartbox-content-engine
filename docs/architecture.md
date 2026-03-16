# Architecture — Smartbox Content Engine

## Overview

The Smartbox Content Engine is a single-container web application that takes a CSV of product rows and generates brand-aligned content assets using an LLM. The architecture prioritises simplicity for the POC phase while being structured for easy production migration.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser                                   │
│  ┌──────────────┐   drag-drop    ┌────────────────────────────┐ │
│  │  uploader.js │ ─────────────> │         app.js             │ │
│  └──────────────┘                │   (event coordinator)      │ │
│                                  └────────────┬───────────────┘ │
│                                               │ fetch + SSE     │
└───────────────────────────────────────────────┼─────────────────┘
                                                │
                              ┌─────────────────▼───────────────┐
                              │         FastAPI (port 8000)      │
                              │                                  │
                              │  POST /process  GET /health      │
                              │  GET /status/{job_id}            │
                              │                                  │
                              │  ┌──────────────────────────┐   │
                              │  │      csv_parser.py        │   │
                              │  │   (validates, returns     │   │
                              │  │    list[ProductRow])       │   │
                              │  └────────────┬─────────────┘   │
                              │               │                  │
                              │  ┌────────────▼─────────────┐   │
                              │  │       pipeline.py         │   │
                              │  │   (async generator,       │   │
                              │  │    yields SSE events)     │   │
                              │  └────────────┬─────────────┘   │
                              │               │                  │
                              │  ┌────────────▼─────────────┐   │
                              │  │      llm_router.py        │   │
                              │  │  (selects service based   │   │
                              │  │   on ANTHROPIC_API_KEY)   │   │
                              │  └────────────┬─────────────┘   │
                              │               │                  │
                              │    ┌──────────┴────────────┐    │
                              │    │                        │    │
                              │ ┌──▼──────────┐  ┌─────────▼──┐ │
                              │ │claude_service│  │ollama_srv  │ │
                              │ │(Anthropic   │  │(local LLM  │ │
                              │ │  SDK)       │  │ fallback)  │ │
                              │ └─────────────┘  └────────────┘ │
                              └─────────────────────────────────┘
```

## Data flow

1. **Upload** — User drags a CSV onto the frontend. `uploader.js` validates the file extension and fires an event.
2. **POST /process** — `app.js` sends a `multipart/form-data` POST with the CSV file. The response is a `text/event-stream`.
3. **CSV parsing** — `csv_parser.py` reads the uploaded bytes with pandas, validates required columns and category values, and returns a `list[ProductRow]`.
4. **Pipeline** — `pipeline.py` iterates rows, calls the LLM service for each, and yields SSE events: `job_started`, `row_started`, `row_done`/`row_error`, `job_complete`.
5. **LLM routing** — `llm_router.py` checks `settings.use_claude`. If `ANTHROPIC_API_KEY` is set, it returns `claude_service`; otherwise `ollama_service`.
6. **Generation** — The selected service sends the system prompt + per-row user prompt to the LLM and returns a `GeneratedAsset`.
7. **DAM filename** — `pipeline.py` calls `dam_naming.generate_dam_filename()` after generation and attaches it to the asset.
8. **SSE stream** — Each `row_done` event carries the full `GeneratedAsset` as JSON. The browser `api.js` parses each event and calls `ui.js` to render or update a card.

## Key design decisions

| Decision | Rationale |
|----------|-----------|
| SSE over WebSockets | Simpler — SSE is one-directional, no upgrade handshake, works over standard HTTP |
| In-memory job store | Appropriate for POC; swap for Redis when scaling to multiple workers |
| Module-level LLM routing | Keeps `pipeline.py` decoupled from LLM choice; easy to add new providers |
| No frontend build step | Reduces ops complexity for the POC; no Node.js required in production container |
| pydantic-settings BaseSettings | Single source of truth for config; type-safe, validated at startup |
| Structured logging (structlog) | Machine-readable logs from day one; easy to ship to Datadog/CloudWatch later |

## Directory map

```
backend/
  app/
    main.py         — FastAPI app factory
    config.py       — pydantic-settings (env vars)
    api/routes.py   — HTTP endpoints
    core/
      csv_parser.py — CSV → list[ProductRow]
      pipeline.py   — async SSE generator
      dam_naming.py — DAM filename constructor
    services/
      llm_router.py      — picks Claude or Ollama
      claude_service.py  — Anthropic SDK wrapper
      ollama_service.py  — Ollama REST wrapper
    models/         — Pydantic schemas (no logic)
    prompts/        — prompt strings and tone config
    utils/          — logger, SSE formatter, exceptions
frontend/
  src/
    index.html       — app shell
    css/             — design tokens + component styles
    js/              — ES modules: app, api, ui, uploader
```
