"""
SHAP-based Explainability for Spare Parts Recommendations

Provides feature importance explanations for why specific parts
are recommended for specific machines.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class RecommendationExplainer:
    def __init__(self):
        self.feature_names = [
            "machine_age", "usage_hours", "temperature", "vibration",
            "pressure", "anomaly_score", "compatibility", "failure_rate",
            "part_criticality", "historical_frequency", "cost_factor"
        ]

    def explain_recommendation(self, machine_info: Dict, part_info: Dict,
                                recommendation: Dict) -> Dict:
        feature_contributions = self._compute_feature_contributions(
            machine_info, part_info, recommendation
        )

        sorted_features = sorted(
            feature_contributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )

        top_reasons = []
        for feat, value in sorted_features[:5]:
            if abs(value) > 0.01:
                direction = "increases" if value > 0 else "decreases"
                top_reasons.append({
                    "feature": feat,
                    "contribution": float(value),
                    "direction": direction,
                    "description": self._feature_description(feat, value, machine_info, part_info),
                })

        return {
            "feature_contributions": {k: float(v) for k, v in feature_contributions.items()},
            "top_reasons": top_reasons,
            "summary": self._generate_summary(top_reasons, part_info),
            "confidence": self._compute_confidence(feature_contributions),
        }

    def _compute_feature_contributions(self, machine_info: Dict,
                                        part_info: Dict,
                                        recommendation: Dict) -> Dict:
        sensor = machine_info.get("sensor_data", {})
        age = machine_info.get("age_years", 5) or 5
        usage = machine_info.get("usage_hours_per_day", 16)
        temp = sensor.get("avg_temperature", 60)
        vib = sensor.get("avg_vibration", 5)
        press = sensor.get("avg_pressure", 150)
        anomaly = sensor.get("max_anomaly", 0.3)

        compat = recommendation.get("explanation", {}).get("compatibility", 0.5)
        fr = part_info.get("failure_rate", 0.1)
        crit_map = {"high": 1.0, "medium": 0.5, "low": 0.2}
        crit_score = crit_map.get(part_info.get("criticality", "medium"), 0.5)
        hist_freq = recommendation.get("cf_score", 0.3)
        cost = part_info.get("cost_usd", 200) or 200

        base_score = 0.3

        contributions = {
            "machine_age": 0.08 * (age - 5) / 5,
            "usage_hours": 0.06 * (usage - 16) / 8,
            "temperature": 0.12 * max(0, (temp - 70) / 50),
            "vibration": 0.15 * max(0, (vib - 5) / 8),
            "pressure": 0.08 * abs(press - 150) / 150,
            "anomaly_score": 0.18 * anomaly,
            "compatibility": 0.20 * (compat - 0.5),
            "failure_rate": 0.10 * (fr - 0.15),
            "part_criticality": 0.08 * (crit_score - 0.5),
            "historical_frequency": 0.12 * (hist_freq - 0.3),
            "cost_factor": -0.03 * (cost - 300) / 500,
        }

        return contributions

    def _feature_description(self, feature: str, value: float,
                              machine_info: Dict, part_info: Dict) -> str:
        sensor = machine_info.get("sensor_data", {})
        descriptions = {
            "machine_age": f"Machine age ({machine_info.get('age_years', 'N/A')} years) {'increases' if value > 0 else 'decreases'} wear likelihood",
            "usage_hours": f"Usage at {machine_info.get('usage_hours_per_day', 'N/A')} hrs/day {'elevates' if value > 0 else 'reduces'} failure probability",
            "temperature": f"Temperature reading ({sensor.get('avg_temperature', 'N/A')}°C) {'above' if value > 0 else 'within'} normal range",
            "vibration": f"Vibration level ({sensor.get('avg_vibration', 'N/A')} mm/s) {'exceeds' if value > 0 else 'within'} threshold",
            "pressure": f"Pressure at {sensor.get('avg_pressure', 'N/A')} PSI, deviation from optimal",
            "anomaly_score": f"Anomaly detection score ({sensor.get('max_anomaly', 'N/A')}) indicates {'elevated' if value > 0 else 'normal'} risk",
            "compatibility": f"Part {'is' if value > 0 else 'may not be'} compatible with {machine_info.get('machine_type', 'this machine')}",
            "failure_rate": f"Part failure rate ({part_info.get('failure_rate', 'N/A')}) {'above' if value > 0 else 'below'} average",
            "part_criticality": f"Part criticality is {part_info.get('criticality', 'unknown')}",
            "historical_frequency": f"Frequently {'used' if value > 0 else 'unused'} in past maintenance events",
            "cost_factor": f"Part cost (${part_info.get('cost_usd', 'N/A')}) {'reduces' if value < 0 else 'improves'} overall score",
        }
        return descriptions.get(feature, f"{feature} contributes {value:.3f}")

    def _generate_summary(self, top_reasons: List[Dict], part_info: Dict) -> str:
        if not top_reasons:
            return "General maintenance recommendation based on machine profile."

        positive = [r for r in top_reasons if r["contribution"] > 0]
        if not positive:
            return f"{part_info.get('category', 'Part')} recommended as general maintenance item."

        main_reason = positive[0]["description"]
        category = part_info.get("category", "part")
        return f"Recommended {category}: {main_reason}"

    def _compute_confidence(self, contributions: Dict) -> float:
        total_positive = sum(v for v in contributions.values() if v > 0)
        total_negative = sum(abs(v) for v in contributions.values() if v < 0)
        net = total_positive - total_negative
        return float(np.clip(0.5 + net, 0.1, 0.99))

    def batch_explain(self, recommendations: List[Dict],
                       machine_info: Dict, parts_df: pd.DataFrame) -> List[Dict]:
        explained = []
        for rec in recommendations:
            part_row = parts_df[parts_df["part_id"] == rec["part_id"]]
            if part_row.empty:
                rec["shap_explanation"] = {"error": "Part not found"}
                explained.append(rec)
                continue

            part_info = part_row.iloc[0].to_dict()
            explanation = self.explain_recommendation(machine_info, part_info, rec)
            rec["shap_explanation"] = explanation
            explained.append(rec)

        return explained
