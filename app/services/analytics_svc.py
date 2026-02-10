from __future__ import annotations

import numpy as np


class HorizonAnalyticsService:
    """Implements sweet-spot scoring used by the radar workflow."""

    RESEARCH_FUNDING_DIVISOR = 1_000_000
    INVESTMENT_FUNDING_DIVISOR = 2_000_000
    MAINSTREAM_WEIGHT = 0.9
    NICHE_WEIGHT = 1.4

    def calculate_activity_score(self, research_funds: float, investment_funds: float) -> float:
        """Calculate activity score using original prototype divisors."""
        score = (research_funds / self.RESEARCH_FUNDING_DIVISOR) + (
            investment_funds / self.INVESTMENT_FUNDING_DIVISOR
        )
        return min(10.0, score)

    def calculate_attention_score(self, mainstream_count: int, niche_count: int) -> float:
        """Calculate attention score with fixed mainstream and niche weights."""
        score = (mainstream_count * self.MAINSTREAM_WEIGHT) + (niche_count * self.NICHE_WEIGHT)
        return min(10.0, score)

    def classify_sweet_spot(self, activity: float, attention: float) -> str:
        """Classify the signal profile into a horizon typology."""
        if activity > 6.0:
            return "Hidden Gem" if attention < 5.0 else "Established"
        return "Hype" if attention > 6.0 else "Nascent"

    def generate_sparkline(self, activity: float, attention: float) -> list[int]:
        """Generate sparkline points for UI cards."""
        base = max(1.0, min(10.0, (activity + attention) / 2))
        direction = 1 if attention >= activity else -1
        slope = 0.4 * direction
        values = np.linspace(base - slope * 4, base + slope * 4, 8)
        return [int(max(1, min(10, round(value)))) for value in values]
