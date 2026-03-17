# Smartbox Content Engine

> From data to stories. At scale.

A content automation POC for **Smartbox Group** — Europe's leading experience gift company. Upload a CSV of product rows and receive brand-aligned video scripts, voiceover copy, image prompts, and DAM-ready filenames — all generated via the Claude API.

---

## Prerequisites

- Python 3.12+
- Docker & Docker Compose (optional)
- An Anthropic API key **or** a local [Ollama](https://ollama.ai) instance

---

## Quick start

```bash
# 1. Clone and enter the repo
git clone https://github.com/VrushilG/smartbox-content-engine.git
cd smartbox-content-engine

# 2. Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Install backend dependencies
cd backend
pip install -r requirements.txt

# 4. Start the server
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Docker

```bash
# Build and run with Docker Compose
docker-compose up --build
```

Or manually:

```bash
docker build -f docker/Dockerfile -t smartbox-content-engine .
docker run -p 8000:8000 --env-file .env smartbox-content-engine
```

---

## Usage

1. Open the web UI at [http://localhost:8000](http://localhost:8000)
2. Drag and drop (or click to select) a CSV file matching the format in `data/sample_products.csv`
3. Click **Generate Content**
4. Watch real-time progress as each product row is processed
5. Download or copy the generated assets for each product

### CSV format

Required columns: `id`, `name`, `location`, `price`, `category`, `key_selling_point`

Valid categories: `getaways`, `wellness`, `adventure`, `gastronomy`, `pampering`

See `data/sample_products.csv` for a complete example.

---

## Development

```bash
# Run tests
cd backend && pytest tests/ -v --tb=short

# Lint and format
cd backend && ruff check . && black .
```

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for a full system overview.

## API Reference

See [docs/api_reference.md](docs/api_reference.md) for endpoint documentation.

## Brand Guidelines

See [docs/brand_guidelines.md](docs/brand_guidelines.md) for Smartbox brand tokens and voice rules.

---

## LLM routing

| Condition | Service used |
|-----------|-------------|
| `ANTHROPIC_API_KEY` set | Claude API (claude-sonnet-4-5 by default) |
| `OPENROUTER_API_KEY` set | OpenRouter (Qwen, DeepSeek, Llama free models) |
| Neither set | Ollama local fallback |

---

## Media generation

| Step | Primary | Fallback |
|------|---------|---------|
| Image | Vertex AI Imagen 4 Fast | Fal.ai FLUX → Lorem Picsum |
| Video | Vertex AI Veo 3.1 Fast | Fal.ai Wan → Replicate Wan |

Up to `ROW_CONCURRENCY` rows are processed in parallel (default 4).

---

## Environment variables

### Required (pick at least one LLM)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENROUTER_API_KEY` | OpenRouter API key (free models available) |

### Vertex AI (image + video)

| Variable | Description |
|----------|-------------|
| `VERTEXAI_PROJECT` | GCP project ID |
| `VERTEXAI_LOCATION` | Region (default `us-central1`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON (local dev) |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Full service account JSON string (Railway / containers) |
| `VERTEXAI_PROJECT_2` | Second GCP project for load balancing (optional) |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON_2` | Credentials for second project (optional) |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_LOCALE` | `IE` | Locale code appended to DAM filenames |
| `LLM_MODEL` | `claude-sonnet-4-5` | Claude model ID |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama base URL |
| `ROW_CONCURRENCY` | `4` | Max rows processed in parallel |
| `FAL_API_KEY` | _(none)_ | Fal.ai key for image/video fallback |
| `REPLICATE_API_KEY` | _(none)_ | Replicate key for video fallback |
| `SUPABASE_URL` | _(none)_ | Supabase URL for asset persistence |
| `SUPABASE_SERVICE_KEY` | _(none)_ | Supabase service key |
| `SUPABASE_ANON_KEY` | _(none)_ | Supabase public key |
