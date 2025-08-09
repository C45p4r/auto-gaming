from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from app.config import settings
from app.safety.guards import detect_purchase_ui, screen_change


@dataclass
class RiskAssessment:
    risk_score: float
    reasons: list[str]
    quarantined: bool


def assess_risk(prev_image: Image.Image, cur_image: Image.Image) -> RiskAssessment:
    reasons: list[str] = []
    score = 0.0
    if detect_purchase_ui(cur_image):
        reasons.append("purchase_ui")
        score += 1.0
    if screen_change(prev_image, cur_image, diff_threshold=0.90):
        reasons.append("large_screen_change")
        score += 0.2
    quarantined = settings.risk_quarantine and score >= settings.risk_score_threshold
    return RiskAssessment(risk_score=score, reasons=reasons, quarantined=quarantined)
