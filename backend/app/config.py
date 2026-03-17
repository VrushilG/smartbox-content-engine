from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from project root (two levels up from this file: app/ → backend/ → root/)
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ---- Text LLM providers ----
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-5"

    openrouter_api_key: str = ""
    openrouter_model: str = "arcee-ai/trinity-large-preview:free"

    ollama_url: str = "http://localhost:11434"

    # ---- Image generation ----
    # Pollinations.ai works with no key — always available.
    # Set HF_API_KEY to enable HuggingFace FLUX fallback.
    hf_api_key: str = ""

    # ---- Video generation ----
    # Set GOOGLE_API_KEY for Google Veo (AI Studio fallback).
    # Set FAL_API_KEY for Fal.ai (Wan 2.1) — fallback.
    # Set REPLICATE_API_KEY for Replicate (Wan 2.1) — second fallback.
    google_api_key: str = ""
    fal_api_key: str = ""
    replicate_api_key: str = ""

    # ---- Vertex AI project 1 (primary media provider) ----
    # Set VERTEXAI_PROJECT to your GCP project ID to enable Vertex AI.
    # Auth — choose one:
    #   Local dev:  GOOGLE_APPLICATION_CREDENTIALS=vertex/key.json  (file path)
    #   Railway:    GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}  (JSON content)
    vertexai_project: str = ""
    vertexai_location: str = "us-central1"
    google_application_credentials: str = ""
    google_credentials_json: str = ""  # Full service account JSON for Railway / containerised deploys

    # ---- Vertex AI project 2 (optional, for load balancing) ----
    # Add a second GCP project to distribute Vertex AI calls and double the credit pool.
    vertexai_project_2: str = ""
    vertexai_location_2: str = "us-central1"
    google_application_credentials_2: str = ""
    google_credentials_json_2: str = ""  # Full service account JSON for second project on Railway

    # ---- Concurrency ----
    # Number of CSV rows processed in parallel per upload.
    row_concurrency: int = 4

    # ---- App settings ----
    default_locale: str = "IE"

    # ---- Supabase persistence (optional) ----
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_anon_key: str = ""  # Public key used by the browser JS client

    # ---- Routing properties ----
    @property
    def use_claude(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def use_openrouter(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def use_google_veo(self) -> bool:
        return bool(self.google_api_key)

    @property
    def use_vertexai(self) -> bool:
        return bool(self.vertexai_project)

    @property
    def resolved_google_credentials(self) -> str:
        """Return absolute path to the credentials JSON.

        Supports two auth modes:
          Railway / containers: set GOOGLE_APPLICATION_CREDENTIALS_JSON to the full
            service account JSON string — it is written to a temp file automatically.
          Local dev: set GOOGLE_APPLICATION_CREDENTIALS to a file path (absolute or
            relative to the project root).
        """
        # Option A: JSON content provided directly (Railway / containerised deployment)
        if self.google_credentials_json:
            creds_path = Path("/tmp/gcp-creds-1.json")
            creds_path.write_text(self.google_credentials_json)
            return str(creds_path)
        # Option B: File path provided (local development)
        if not self.google_application_credentials:
            return ""
        p = Path(self.google_application_credentials)
        if p.is_absolute():
            return str(p)
        return str((_ENV_FILE.parent / p).resolve())

    @property
    def resolved_google_credentials_2(self) -> str:
        """Return absolute path to the second credentials JSON (same logic as above)."""
        if self.google_credentials_json_2:
            creds_path = Path("/tmp/gcp-creds-2.json")
            creds_path.write_text(self.google_credentials_json_2)
            return str(creds_path)
        if not self.google_application_credentials_2:
            return ""
        p = Path(self.google_application_credentials_2)
        if p.is_absolute():
            return str(p)
        return str((_ENV_FILE.parent / p).resolve())

    @property
    def vertex_projects(self) -> list[dict]:
        """Return all configured Vertex AI projects for load balancing.

        Returns a list of dicts with keys: project, location, credentials.
        Image/video services pick randomly from this list to distribute load.
        """
        projects = []
        if self.vertexai_project:
            projects.append({
                "project": self.vertexai_project,
                "location": self.vertexai_location,
                "credentials": self.resolved_google_credentials,
            })
        if self.vertexai_project_2:
            projects.append({
                "project": self.vertexai_project_2,
                "location": self.vertexai_location_2,
                "credentials": self.resolved_google_credentials_2,
            })
        return projects

    @property
    def use_fal(self) -> bool:
        return bool(self.fal_api_key)

    @property
    def use_replicate(self) -> bool:
        return bool(self.replicate_api_key)

    @property
    def use_hf(self) -> bool:
        return bool(self.hf_api_key)

    @property
    def use_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)


settings = Settings()
