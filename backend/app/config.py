from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"  # backend/.env regardless of the cwd


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str = "postgresql+psycopg://causetrace:causetrace_dev@localhost:5433/causetrace"
    groq_api_key: str = ""
    # Groq's free tier caps each model at 8k tokens/min (and qwen/safeguard are capped far lower), so work is
    # split over two buckets: 120b for the heavy reasoning, 20b for extraction, edits, routing and the critic.
    groq_model: str = "openai/gpt-oss-120b"       # heavy: hypotheses, 5 Whys, gaps + CAPA
    groq_model_alt: str = "openai/gpt-oss-20b"    # extraction + the critic pass
    groq_model_fast: str = "openai/gpt-oss-20b"   # routing, edits, short answers
    groq_reasoning_effort: str = "low"  # low | medium | high (gpt-oss models only)
    mock_llm: bool = True
    cors_origins: str = "http://localhost:5173"

    @property
    def use_mock(self) -> bool:
        # Fall back to mock automatically when no key is configured.
        return self.mock_llm or not self.groq_api_key


settings = Settings()
