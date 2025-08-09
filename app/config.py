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

    # Memory & knowledge
    db_path: str = Field(default="data/app.sqlite3", alias="DB_PATH")
    embedding_model_id: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL_ID"
    )

    # Safety
    hard_block_iap: bool = Field(default=True, alias="HARD_BLOCK_IAP")
    risk_quarantine: bool = Field(default=True, alias="RISK_QUARANTINE")
    risk_score_threshold: float = Field(default=0.5, alias="RISK_SCORE_THRESHOLD")
    safety_templates_dir: str = Field(default="app/safety/templates", alias="SAFETY_TEMPLATES_DIR")


settings = Settings()
