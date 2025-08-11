from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import settings


@dataclass(frozen=True)
class SelfCheckResult:
    ok: bool
    issues: list[str]
    details: dict[str, Any]


def run_self_check() -> SelfCheckResult:
    issues: list[str] = []
    details: dict[str, Any] = {}

    # Tesseract
    tess = str(settings.tesseract_cmd or "").strip()
    if not tess:
        issues.append("TESSERACT_CMD not set; OCR may fail")
    else:
        details["tesseract_cmd"] = tess
        try:
            if not Path(tess).exists():
                issues.append("TESSERACT_CMD path does not exist")
        except Exception:
            issues.append("TESSERACT_CMD path could not be validated")

    # Window / capture dims
    for k in ("window_client_width", "window_client_height", "input_base_width", "input_base_height"):
        v = int(getattr(settings, k, 0) or 0)
        details[k] = v
        if v <= 0:
            issues.append(f"{k} should be > 0")

    # Title hint
    if not str(settings.window_title_hint or "").strip():
        issues.append("WINDOW_TITLE_HINT missing; may not find emulator window")

    # Backends
    details["capture_backend"] = settings.capture_backend or "auto"
    details["input_backend"] = settings.input_backend or "auto"

    ok = len(issues) == 0
    return SelfCheckResult(ok=ok, issues=issues, details=details)


def suggestions_for(result: SelfCheckResult) -> list[dict[str, str]]:
    """Return human-friendly suggestions for known issues."""
    suggestions: list[dict[str, str]] = []
    for issue in result.issues:
        s = ""
        if issue.startswith("TESSERACT_CMD not set"):
            s = "Set TESSERACT_CMD in .env, e.g. TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
        elif issue.startswith("TESSERACT_CMD path does not exist"):
            s = "Verify Tesseract installation path and update TESSERACT_CMD in .env"
        elif "WINDOW_TITLE_HINT" in issue:
            s = "Set WINDOW_TITLE_HINT to include 'Epic Seven|Google Play Games' in .env"
        elif "window_client_width" in issue or "window_client_height" in issue:
            s = "Set WINDOW_CLIENT_WIDTH/HEIGHT to emulator client size, e.g. 882/496"
            details["window_dims"] = f"{settings.window_client_width}x{settings.window_client_height}"
        elif "input_base_width" in issue or "input_base_height" in issue:
            s = "Set INPUT_BASE_WIDTH/HEIGHT to logical base (e.g. 882/496)"
        if s:
            suggestions.append({"issue": issue, "suggestion": s})
    return suggestions


