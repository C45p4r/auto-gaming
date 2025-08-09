from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="auto-gaming", alias="APP_NAME")
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # OCR
    ocr_language: str = Field(default="eng", alias="OCR_LANGUAGE")

    # Emulator / ADB
    adb_path: str = Field(default="adb", alias="ADB_PATH")

    # Capture
    capture_fps: float = Field(default=1.0, alias="CAPTURE_FPS")

    # Parallelism
    parallel_mode: str = Field(default="async", alias="PARALLEL_MODE")  # "async" | "ray"

    # Logging
    logs_dir: str = Field(default="logs", alias="LOGS_DIR")

    # Hugging Face / LLM
    huggingface_hub_token: str | None = Field(default=None, alias="HUGGINGFACE_HUB_TOKEN")
    hf_model_id_policy: str | None = Field(default=None, alias="HF_MODEL_ID_POLICY")
    hf_model_id_judge: str | None = Field(default=None, alias="HF_MODEL_ID_JUDGE")
    hf_inference_endpoint_url: str | None = Field(default=None, alias="HF_INFERENCE_ENDPOINT_URL")


settings = Settings()
