from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "auto-gaming"
    environment: str = "dev"
    log_level: str = "INFO"

    # OCR
    ocr_language: str = "eng"

    # Parallelism
    parallel_mode: str = "async"  # "async" | "ray"

    # Hugging Face / LLM
    huggingface_hub_token: str | None = None
    hf_model_id_policy: str | None = None
    hf_model_id_judge: str | None = None
    hf_inference_endpoint_url: str | None = None


settings = Settings()  # type: ignore[call-arg]


