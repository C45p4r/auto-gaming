from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="auto-gaming", alias="APP_NAME")
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # OCR
    ocr_language: str = Field(default="eng", alias="OCR_LANGUAGE")
    tesseract_cmd: str | None = Field(default=None, alias="TESSERACT_CMD")
    ocr_preprocess: str = Field(default="auto", alias="OCR_PREPROCESS")  # none|grayscale|binary|auto
    ocr_scale: float = Field(default=1.5, alias="OCR_SCALE")
    ocr_psm: int = Field(default=6, alias="OCR_PSM")
    ocr_oem: int = Field(default=3, alias="OCR_OEM")
    ocr_multi_pass: bool = Field(default=True, alias="OCR_MULTI_PASS")
    ocr_ensemble: bool = Field(default=True, alias="OCR_ENSEMBLE")
    ocr_engines: str = Field(default="tesseract,tesseract_batched,paddle", alias="OCR_ENGINES")

    # Emulator / ADB
    adb_path: str = Field(default="adb", alias="ADB_PATH")

    # Capture
    capture_fps: float = Field(default=1.0, alias="CAPTURE_FPS")
    capture_backend: str | None = Field(
        default=None, alias="CAPTURE_BACKEND"
    )  # "auto" | "adb" | "window"
    window_title_hint: str | None = Field(
        default=r"Google Play Games|Epic Seven|Epic 7", alias="WINDOW_TITLE_HINT"
    )
    window_force_foreground: bool = Field(default=True, alias="WINDOW_FORCE_FOREGROUND")
    window_enforce_topmost: bool = Field(default=True, alias="WINDOW_ENFORCE_TOPMOST")
    window_left: int = Field(default=100, alias="WINDOW_LEFT")
    window_top: int = Field(default=100, alias="WINDOW_TOP")
    window_client_width: int = Field(default=1280, alias="WINDOW_CLIENT_WIDTH")
    window_client_height: int = Field(default=720, alias="WINDOW_CLIENT_HEIGHT")
    # Exclude a bottom margin from tap targets to avoid taskbar if overlapping (pixels)
    input_exclude_bottom_px: int = Field(default=0, alias="INPUT_EXCLUDE_BOTTOM_PX")

    # Input
    input_backend: str | None = Field(
        default=None, alias="INPUT_BACKEND"
    )  # "auto" | "adb" | "window"
    input_base_width: int = Field(default=1080, alias="INPUT_BASE_WIDTH")
    input_base_height: int = Field(default=1920, alias="INPUT_BASE_HEIGHT")

    # Parallelism
    parallel_mode: str = Field(default="async", alias="PARALLEL_MODE")  # "async" | "ray"
    max_agents: int = Field(default=3, alias="MAX_AGENTS")
    agent_timeout_s: float = Field(default=1.5, alias="AGENT_TIMEOUT_S")
    debate_rounds: int = Field(default=1, alias="DEBATE_ROUNDS")

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
    hard_block_item_changes: bool = Field(
        default=True, alias="HARD_BLOCK_ITEM_CHANGES"
    )  # do not sell/remove heroes or equipment

    # Routing preferences
    prefer_events: bool = Field(default=False, alias="PREFER_EVENTS")

    # Stability & testing
    dry_run: bool = Field(default=False, alias="DRY_RUN")
    max_consec_errors: int = Field(default=5, alias="MAX_CONSEC_ERRORS")
    error_backoff_s: float = Field(default=2.0, alias="ERROR_BACKOFF_S")

    # Reinforcement Learning (bandit)
    rl_enabled: bool = Field(default=True, alias="RL_ENABLED")
    rl_method: str = Field(default="bandit", alias="RL_METHOD")  # bandit|off
    rl_eps_start: float = Field(default=0.2, alias="RL_EPS_START")
    rl_eps_end: float = Field(default=0.05, alias="RL_EPS_END")
    rl_persist_path: str = Field(default="data/policy.json", alias="RL_PERSIST_PATH")


settings = Settings()
