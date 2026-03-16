# Smartbox Content Engine

> From data to stories. At scale.

A content automation POC for **Smartbox Group** — Europe's leading experience gift company. Upload a CSV of product rows and receive brand-aligned video scripts, voiceover copy, image prompts, and DAM-ready filenames — all generated via the Claude API.

---

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- An Anthropic API key **or** a local [Ollama](https://ollama.ai) instance

---

## Quick start

```bash
# 1. Clone and enter the repo
git clone <repo-url>
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

The app automatically routes to the best available LLM:

| Condition | Service used |
|-----------|-------------|
| `ANTHROPIC_API_KEY` set | Claude API (claude-sonnet-4-5 by default) |
| No API key | Ollama local fallback (requires Ollama running) |

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | _(none)_ | Anthropic API key. If unset, Ollama fallback is used. |
| `DEFAULT_LOCALE` | `IE` | Locale code appended to DAM filenames |
| `LLM_MODEL` | `claude-sonnet-4-5` | Claude model ID |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama base URL for local fallback |
