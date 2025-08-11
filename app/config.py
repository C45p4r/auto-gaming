from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="auto-gaming", alias="APP_NAME")
    environment: str = Field(default="dev", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    logs_dir: str = Field(default="logs", alias="LOGS_DIR")

    # OCR (maximize text signal for mobile games)
    ocr_language: str = Field(default="eng+kor", alias="OCR_LANGUAGE")
    tesseract_cmd: str | None = Field(default="C:\\Program Files\\Tesseract-OCR\\tesseract.exe", alias="TESSERACT_CMD")
    ocr_preprocess: str = Field(default="sharpness", alias="OCR_PREPROCESS")  # none|grayscale|binary|auto|sharpness
    ocr_scale: float = Field(default=2.0, alias="OCR_SCALE")
    ocr_preprocess_intensity: float = Field(default=2.5, alias="OCR_PREPROCESS_INTENSITY")
    ocr_psm: int = Field(default=7, alias="OCR_PSM")
    ocr_oem: int = Field(default=3, alias="OCR_OEM")
    ocr_multi_pass: bool = Field(default=True, alias="OCR_MULTI_PASS")
    ocr_ensemble: bool = Field(default=True, alias="OCR_ENSEMBLE")
    ocr_engines: str = Field(default="paddle,tesseract_batched,tesseract", alias="OCR_ENGINES")

    # AVD / ADB Configuration
    avd_name: str = Field(default="Pixel_9a", alias="AVD_NAME")
    avd_resolution: str = Field(default="1080x2424", alias="AVD_RESOLUTION")
    adb_path: str = Field(default="adb", alias="ADB_PATH")
    adb_timeout: int = Field(default=10, alias="ADB_TIMEOUT")
    adb_retry_count: int = Field(default=3, alias="ADB_RETRY_COUNT")

    # Capture / Window (AVD-optimized positioning and size)
    capture_fps: float = Field(default=2.0, alias="CAPTURE_FPS")
    capture_backend: str | None = Field(
        default="window", alias="CAPTURE_BACKEND"
    )  # "auto" | "adb" | "window"
    window_title_hint: str | None = Field(
        default=r"Pixel_9a|Android|Emulator|AVD", alias="WINDOW_TITLE_HINT"
    )
    window_force_foreground: bool = Field(default=True, alias="WINDOW_FORCE_FOREGROUND")
    window_enforce_topmost: bool = Field(default=True, alias="WINDOW_ENFORCE_TOPMOST")
    window_left: int = Field(default=5, alias="WINDOW_LEFT")
    window_top: int = Field(default=20, alias="WINDOW_TOP")
    window_client_width: int = Field(default=1395, alias="WINDOW_CLIENT_WIDTH")
    window_client_height: int = Field(default=999, alias="WINDOW_CLIENT_HEIGHT")

    # Input (ADB-based - most reliable for Android emulators)
    input_backend: str | None = Field(
        default="adb", alias="INPUT_BACKEND"
    )  # "adb" (recommended) | "window" (fallback)
    input_base_width: int = Field(default=1080, alias="INPUT_BASE_WIDTH")
    input_base_height: int = Field(default=2424, alias="INPUT_BASE_HEIGHT")
    # Exclude a bottom margin from tap targets (AVD: 0, Windows: 40)
    input_exclude_bottom_px: int = Field(default=0, alias="INPUT_EXCLUDE_BOTTOM_PX")

    # Parallelism
    parallel_mode: str = Field(default="async", alias="PARALLEL_MODE")  # "async" | "ray"
    max_agents: int = Field(default=3, alias="MAX_AGENTS")
    agent_timeout_s: float = Field(default=1.5, alias="AGENT_TIMEOUT_S")
    debate_rounds: int = Field(default=1, alias="DEBATE_ROUNDS")

    # Logging
    log_to_ws: bool = Field(default=True, alias="LOG_TO_WS")
    log_ring_size: int = Field(default=1000, alias="LOG_RING_SIZE")

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

    # Game-Specific Settings (Epic Seven)
    game_name: str = Field(default="Epic Seven", alias="GAME_NAME")
    game_language: str = Field(default="eng+kor", alias="GAME_LANGUAGE")
    game_safety_enabled: bool = Field(default=True, alias="GAME_SAFETY_ENABLED")
    game_iap_blocking: bool = Field(default=True, alias="GAME_IAP_BLOCKING")

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
    rl_eps_start: float = Field(default=0.35, alias="RL_EPS_START")
    rl_eps_end: float = Field(default=0.15, alias="RL_EPS_END")
    rl_persist_path: str = Field(default="data/policy.json", alias="RL_PERSIST_PATH")


settings = Settings()
