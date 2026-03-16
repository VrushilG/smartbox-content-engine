# Smartbox Content Engine

## What this project is
A content automation POC for Smartbox Group — Europe's leading experience gift company (HQ Dublin, Ireland). The app takes a CSV of product rows and generates brand-aligned video scripts, voiceover copy, image prompts, and DAM-ready filenames using the Claude API.

## Project structure
- backend/        FastAPI Python app (app/, core/, services/, models/, prompts/, utils/)
- frontend/src/   Vanilla JS SPA with Smartbox brand CSS
- data/           Sample CSV and reference output JSON
- tests/          pytest test suite
- scripts/        Dev utilities
- docker/         Dockerfile and .dockerignore
- docs/           Architecture, brand guidelines, API reference

See backend/CLAUDE.md and frontend/CLAUDE.md for layer-specific rules.

## Commands

### Local development
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

### Run tests
cd backend && pytest tests/ -v

### Lint and format
cd backend && ruff check . && black .

### Docker
docker build -f docker/Dockerfile -t smartbox-content-engine .
docker run -p 8000:8000 --env-file .env smartbox-content-engine

### Docker Compose
docker-compose up --build

## Environment variables
Copy .env.example to .env before running. Required:
- ANTHROPIC_API_KEY — Claude API key
- DEFAULT_LOCALE — defaults to IE
- LLM_MODEL — defaults to claude-sonnet-4-5
- OLLAMA_URL — defaults to http://localhost:11434

## Critical rules
- NEVER commit .env — it is gitignored
- NEVER hardcode API keys anywhere in code
- ALWAYS load secrets from config.py using python-dotenv
- ALWAYS run tests before marking any task complete
- NEVER modify files in data/ — they are reference fixtures
- The frontend has NO build step — it runs as static HTML served by FastAPI
