from typing import Dict, Any


class ProbabilityMatrix:
    """Return empirical probabilities only when a verified cohort is supplied."""

    @staticmethod
    def calculate_success_probability(engine_scores: Dict[str, float], market_regime: str) -> Dict[str, Any]:
        # A weighted technical score is not an observed success probability.
        return {
            "Probability_Percent": None,
            "Historical_Cases": 0,
            "Successful_Cases": 0,
            "Statement": "Doğrulanmış sonuç kohortu bulunmadığından başarı olasılığı hesaplanmadı.",
            "data_status": "NO_VERIFIED_OUTCOME_COHORT",
        }
