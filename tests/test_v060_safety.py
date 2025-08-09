from PIL import Image

from app.safety.guards import detect_purchase_text
from app.safety.risk import RiskAssessment, assess_risk


def test_assess_risk_flags_large_change() -> None:
    a = Image.new("RGB", (10, 10), color="black")
    b = Image.new("RGB", (10, 10), color="white")
    ra = assess_risk(a, b)
    assert isinstance(ra, RiskAssessment)
    assert ra.risk_score >= 0.2


def test_detect_purchase_text_keywords() -> None:
    assert detect_purchase_text("Confirm Purchase now!")
