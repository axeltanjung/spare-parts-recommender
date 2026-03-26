"""
Hybrid Recommendation Engine
Combines ALS Collaborative Filtering + Content-Based scores
Includes SHAP-based explainability
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
import pickle
import os

from backend.models.collaborative_filter import ALSCollaborativeFilter
from backend.models.content_based import ContentBasedRecommender

logger = logging.getLogger(__name__)


class HybridRecommender:
    def __init__(self, cf_weight: float = 0.4, cb_weight: float = 0.6):
        self.cf_weight = cf_weight
        self.cb_weight = cb_weight
        self.cf_model = ALSCollaborativeFilter(
            n_factors=30, n_iterations=15, regularization=0.1, alpha=40
        )
        self.cb_model = ContentBasedRecommender()
        self.machines_df: Optional[pd.DataFrame] = None
        self.parts_df: Optional[pd.DataFrame] = None
        self.logs_df: Optional[pd.DataFrame] = None
        self.sensor_df: Optional[pd.DataFrame] = None
        self.is_fitted = False

    def fit(self, machines_df: pd.DataFrame, parts_df: pd.DataFrame,
            logs_df: pd.DataFrame, sensor_df: pd.DataFrame):
        self.machines_df = machines_df
        self.parts_df = parts_df
        self.logs_df = logs_df
        self.sensor_df = sensor_df

        logger.info("Training collaborative filtering model...")
        self.cf_model.fit(logs_df)

        logger.info("Training content-based model...")
        self.cb_model.fit(machines_df, parts_df, sensor_df, logs_df)

        self.is_fitted = True
        logger.info("Hybrid recommender training complete.")

    def recommend(self, machine_id: str, n: int = 5,
                  sensor_override: Optional[Dict] = None) -> List[Dict]:
        if not self.is_fitted:
            raise ValueError("Model not fitted.")

        cf_recs = self.cf_model.recommend(machine_id, n=n * 3)
        cb_recs = self.cb_model.recommend(machine_id, n=n * 3, sensor_override=sensor_override)

        cf_dict = {part_id: score for part_id, score in cf_recs}
        cb_dict = {part_id: (score, explanation) for part_id, score, explanation in cb_recs}

        all_parts = set(cf_dict.keys()) | set(cb_dict.keys())
        if not all_parts:
            return self._fallback_recommend(machine_id, n)

        cf_scores = np.array([cf_dict.get(p, 0) for p in all_parts])
        cb_scores = np.array([cb_dict.get(p, (0, {}))[0] for p in all_parts])

        cf_max = cf_scores.max() if cf_scores.max() > 0 else 1
        cb_max = cb_scores.max() if cb_scores.max() > 0 else 1
        cf_norm = cf_scores / cf_max
        cb_norm = cb_scores / cb_max

        hybrid_scores = self.cf_weight * cf_norm + self.cb_weight * cb_norm

        results = []
        for i, part_id in enumerate(all_parts):
            part_info = self.parts_df[self.parts_df["part_id"] == part_id]
            if part_info.empty:
                continue

            part = part_info.iloc[0]
            _, explanation = cb_dict.get(part_id, (0, {}))

            cf_contribution = self.cf_weight * cf_norm[i]
            cb_contribution = self.cb_weight * cb_norm[i]

            results.append({
                "part_id": part_id,
                "part_name": part.get("part_name", part_id),
                "category": part.get("category", "unknown"),
                "score": float(hybrid_scores[i]),
                "cf_score": float(cf_norm[i]),
                "cb_score": float(cb_norm[i]),
                "cf_contribution": float(cf_contribution),
                "cb_contribution": float(cb_contribution),
                "cost_usd": float(part.get("cost_usd", 0)) if pd.notna(part.get("cost_usd")) else None,
                "criticality": part.get("criticality", "unknown"),
                "lead_time_days": int(part.get("lead_time_days", 7)),
                "failure_rate": float(part.get("failure_rate", 0)),
                "explanation": {
                    **(explanation if isinstance(explanation, dict) else {}),
                    "cf_weight": self.cf_weight,
                    "cb_weight": self.cb_weight,
                    "weighting_logic": (
                        f"Hybrid score = {self.cf_weight}×CF({cf_norm[i]:.3f}) + "
                        f"{self.cb_weight}×CB({cb_norm[i]:.3f}) = {hybrid_scores[i]:.3f}"
                    ),
                },
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:n]

    def recommend_from_sensors(self, temperature: float, vibration: float,
                                pressure: float, machine_type: str = "pump",
                                n: int = 5) -> List[Dict]:
        if not self.is_fitted:
            raise ValueError("Model not fitted.")

        cb_recs = self.cb_model.recommend_from_sensors(
            temperature, vibration, pressure, machine_type, n * 2
        )

        results = []
        for part_id, score, explanation in cb_recs:
            part_info = self.parts_df[self.parts_df["part_id"] == part_id]
            if part_info.empty:
                continue

            part = part_info.iloc[0]
            anomaly = self.cb_model._compute_anomaly(temperature, vibration, pressure)

            results.append({
                "part_id": part_id,
                "part_name": part.get("part_name", part_id),
                "category": part.get("category", "unknown"),
                "score": float(score),
                "cf_score": 0.0,
                "cb_score": float(score),
                "cf_contribution": 0.0,
                "cb_contribution": float(score),
                "cost_usd": float(part.get("cost_usd", 0)) if pd.notna(part.get("cost_usd")) else None,
                "criticality": part.get("criticality", "unknown"),
                "lead_time_days": int(part.get("lead_time_days", 7)),
                "failure_rate": float(part.get("failure_rate", 0)),
                "explanation": {
                    **explanation,
                    "sensor_input": {
                        "temperature": temperature,
                        "vibration": vibration,
                        "pressure": pressure,
                        "computed_anomaly": float(anomaly),
                    },
                    "weighting_logic": "Sensor-based simulation (content-based only)",
                },
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:n]

    def _fallback_recommend(self, machine_id: str, n: int) -> List[Dict]:
        logger.warning(f"Fallback for {machine_id}")
        machine_row = self.machines_df[self.machines_df["machine_id"] == machine_id]
        if machine_row.empty:
            popular = self.logs_df["part_id"].value_counts().head(n).index.tolist()
        else:
            mtype = machine_row.iloc[0]["machine_type"]
            compatible = self.parts_df[
                self.parts_df["compatible_machine_types"].str.contains(mtype, na=False)
            ]
            popular = compatible["part_id"].tolist()[:n]

        results = []
        for pid in popular:
            part_info = self.parts_df[self.parts_df["part_id"] == pid]
            if part_info.empty:
                continue
            part = part_info.iloc[0]
            results.append({
                "part_id": pid,
                "part_name": part.get("part_name", pid),
                "category": part.get("category", "unknown"),
                "score": 0.5,
                "cf_score": 0.0,
                "cb_score": 0.5,
                "cf_contribution": 0.0,
                "cb_contribution": 0.5,
                "cost_usd": float(part.get("cost_usd", 0)) if pd.notna(part.get("cost_usd")) else None,
                "criticality": part.get("criticality", "unknown"),
                "lead_time_days": int(part.get("lead_time_days", 7)),
                "failure_rate": float(part.get("failure_rate", 0)),
                "explanation": {"reason": "Popularity-based fallback (cold-start)"},
            })
        return results

    def evaluate(self, test_logs: pd.DataFrame, k: int = 5) -> Dict[str, float]:
        machines = test_logs["machine_id"].unique()
        precisions = []
        recalls = []

        for machine_id in machines:
            actual = set(test_logs[test_logs["machine_id"] == machine_id]["part_id"].unique())
            if not actual:
                continue

            recs = self.recommend(machine_id, n=k)
            predicted = set(r["part_id"] for r in recs)

            hits = len(actual & predicted)
            precision = hits / k if k > 0 else 0
            recall = hits / len(actual) if actual else 0

            precisions.append(precision)
            recalls.append(recall)

        return {
            "precision_at_k": float(np.mean(precisions)) if precisions else 0,
            "recall_at_k": float(np.mean(recalls)) if recalls else 0,
            "n_evaluated": len(precisions),
            "k": k,
        }

    def get_machine_info(self, machine_id: str) -> Optional[Dict]:
        machine = self.machines_df[self.machines_df["machine_id"] == machine_id]
        if machine.empty:
            return None
        m = machine.iloc[0]
        sensor = self.sensor_df[self.sensor_df["machine_id"] == machine_id]
        sensor_agg = {}
        if not sensor.empty:
            sensor_agg = {
                "avg_temperature": float(sensor["avg_temperature"].mean()),
                "avg_vibration": float(sensor["vibration_level"].mean()),
                "avg_pressure": float(sensor["pressure_psi"].mean()),
                "max_anomaly": float(sensor["anomaly_score"].max()),
            }
        logs = self.logs_df[self.logs_df["machine_id"] == machine_id]
        return {
            "machine_id": machine_id,
            "machine_type": m["machine_type"],
            "age_years": float(m["age_years"]) if pd.notna(m["age_years"]) else None,
            "location": m["location"],
            "usage_hours_per_day": float(m["usage_hours_per_day"]),
            "sensor_data": sensor_agg,
            "total_maintenance_events": len(logs),
            "avg_downtime": float(logs["downtime_hours"].mean()) if not logs.empty else 0,
        }

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info(f"Model saved to {path}")

    @staticmethod
    def load(path: str) -> "HybridRecommender":
        with open(path, "rb") as f:
            model = pickle.load(f)
        logger.info(f"Model loaded from {path}")
        return model
