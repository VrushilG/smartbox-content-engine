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

    # ---- Vertex AI (primary media provider) ----
    # Set VERTEXAI_PROJECT to your GCP project ID to enable Vertex AI.
    # Auth via GOOGLE_APPLICATION_CREDENTIALS (service account JSON path)
    # or via `gcloud auth application-default login` (leave blank).
    vertexai_project: str = ""
    vertexai_location: str = "us-central1"
    google_application_credentials: str = ""

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
        """Return absolute path to the credentials JSON, resolving relative paths from project root."""
        if not self.google_application_credentials:
            return ""
        p = Path(self.google_application_credentials)
        if p.is_absolute():
            return str(p)
        # Relative path — resolve from project root (parent of backend/)
        return str((_ENV_FILE.parent / p).resolve())

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
