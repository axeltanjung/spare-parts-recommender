"""
Content-Based Recommender
Uses machine features + spare part compatibility to generate recommendations
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ContentBasedRecommender:
    def __init__(self):
        self.machine_features: Optional[np.ndarray] = None
        self.part_features: Optional[np.ndarray] = None
        self.machines_df: Optional[pd.DataFrame] = None
        self.parts_df: Optional[pd.DataFrame] = None
        self.sensor_df: Optional[pd.DataFrame] = None
        self.machine_scaler = StandardScaler()
        self.is_fitted = False

    def fit(self, machines_df: pd.DataFrame, parts_df: pd.DataFrame,
            sensor_df: pd.DataFrame, logs_df: pd.DataFrame):
        self.machines_df = machines_df.copy()
        self.parts_df = parts_df.copy()
        self.sensor_df = sensor_df.copy()

        sensor_agg = sensor_df.groupby("machine_id").agg(
            avg_temperature=("avg_temperature", "mean"),
            avg_vibration=("vibration_level", "mean"),
            avg_pressure=("pressure_psi", "mean"),
            max_anomaly=("anomaly_score", "max"),
            avg_anomaly=("anomaly_score", "mean"),
        ).reset_index()

        failure_counts = logs_df.groupby("machine_id").agg(
            total_failures=("log_id", "count"),
            avg_downtime=("downtime_hours", "mean"),
        ).reset_index()

        self.machines_df = self.machines_df.merge(sensor_agg, on="machine_id", how="left")
        self.machines_df = self.machines_df.merge(failure_counts, on="machine_id", how="left")

        self.machines_df["age_years"] = self.machines_df["age_years"].fillna(
            self.machines_df["age_years"].median()
        )
        numeric_cols = ["avg_temperature", "avg_vibration", "avg_pressure",
                       "max_anomaly", "avg_anomaly", "total_failures", "avg_downtime"]
        for col in numeric_cols:
            if col in self.machines_df.columns:
                self.machines_df[col] = self.machines_df[col].fillna(0)

        self._build_machine_features()
        self._build_part_features()
        self._build_compatibility_matrix()

        self.is_fitted = True
        logger.info("Content-based model fitted.")

    def _build_machine_features(self):
        type_dummies = pd.get_dummies(self.machines_df["machine_type"], prefix="type")
        location_dummies = pd.get_dummies(self.machines_df["location"], prefix="loc")

        numeric = self.machines_df[
            ["age_years", "usage_hours_per_day", "avg_temperature", "avg_vibration",
             "avg_pressure", "max_anomaly", "avg_anomaly", "total_failures", "avg_downtime"]
        ].fillna(0)

        numeric_scaled = self.machine_scaler.fit_transform(numeric)

        self.machine_features = np.hstack([
            numeric_scaled,
            type_dummies.values,
            location_dummies.values,
        ])

    def _build_part_features(self):
        cat_dummies = pd.get_dummies(self.parts_df["category"], prefix="cat")
        crit_dummies = pd.get_dummies(self.parts_df["criticality"], prefix="crit")

        numeric = self.parts_df[["failure_rate", "cost_usd", "lead_time_days"]].copy()
        numeric["cost_usd"] = numeric["cost_usd"].fillna(numeric["cost_usd"].median())
        numeric = numeric.fillna(0)

        scaler = StandardScaler()
        numeric_scaled = scaler.fit_transform(numeric)

        for mtype in ["crusher", "conveyor", "pump", "compressor", "motor", "turbine"]:
            self.parts_df[f"compat_{mtype}"] = self.parts_df[
                "compatible_machine_types"
            ].str.contains(mtype, na=False).astype(int)

        compat_cols = [f"compat_{mt}" for mt in
                      ["crusher", "conveyor", "pump", "compressor", "motor", "turbine"]]

        self.part_features = np.hstack([
            numeric_scaled,
            cat_dummies.values,
            crit_dummies.values,
            self.parts_df[compat_cols].values,
        ])

    def _build_compatibility_matrix(self):
        n_machines = len(self.machines_df)
        n_parts = len(self.parts_df)
        self.compat_matrix = np.zeros((n_machines, n_parts))

        for i, (_, machine) in enumerate(self.machines_df.iterrows()):
            mtype = machine["machine_type"]
            for j, (_, part) in enumerate(self.parts_df.iterrows()):
                compat_types = str(part.get("compatible_machine_types", "")).split(",")
                if mtype in compat_types:
                    self.compat_matrix[i, j] = 1.0

    def recommend(self, machine_id: str, n: int = 10,
                  sensor_override: Optional[Dict] = None) -> List[Tuple[str, float, Dict]]:
        if not self.is_fitted:
            raise ValueError("Model not fitted.")

        machine_row = self.machines_df[self.machines_df["machine_id"] == machine_id]
        if machine_row.empty:
            return self._cold_start_recommend(machine_id, n)

        m_idx = machine_row.index[0]
        compat_scores = self.compat_matrix[m_idx]

        machine_type = machine_row.iloc[0]["machine_type"]
        age = machine_row.iloc[0]["age_years"]
        anomaly = machine_row.iloc[0].get("avg_anomaly", 0)

        risk_scores = np.zeros(len(self.parts_df))
        for j, (_, part) in enumerate(self.parts_df.iterrows()):
            fr = part.get("failure_rate", 0.1)
            if pd.isna(fr):
                fr = 0.1
            risk = fr * (1 + 0.05 * age) * (1 + anomaly)
            risk_scores[j] = risk

        if sensor_override:
            temp = sensor_override.get("temperature", 60)
            vib = sensor_override.get("vibration", 5)
            press = sensor_override.get("pressure", 100)
            anomaly_override = sensor_override.get("anomaly_score", 0.5)

            temp_factor = max(0, (temp - 60) / 60)
            vib_factor = max(0, (vib - 5) / 10)
            press_factor = max(0, abs(press - 150) / 150)

            sensor_boost = 1 + 0.3 * temp_factor + 0.4 * vib_factor + 0.2 * press_factor + 0.3 * anomaly_override
            risk_scores *= sensor_boost

        risk_scores = risk_scores / (risk_scores.max() + 1e-8)

        combined = 0.5 * compat_scores + 0.5 * risk_scores

        top_indices = np.argsort(combined)[::-1][:n]
        results = []
        for idx in top_indices:
            part_row = self.parts_df.iloc[idx]
            explanation = {
                "compatibility": float(compat_scores[idx]),
                "risk_score": float(risk_scores[idx]),
                "failure_rate": float(part_row.get("failure_rate", 0)),
                "category": part_row["category"],
                "criticality": part_row.get("criticality", "unknown"),
                "reason": self._generate_reason(
                    machine_type, part_row, compat_scores[idx], risk_scores[idx]
                ),
            }
            results.append((part_row["part_id"], float(combined[idx]), explanation))

        return results

    def _cold_start_recommend(self, machine_id: str, n: int) -> List[Tuple[str, float, Dict]]:
        logger.info(f"Cold start for {machine_id}: using popularity-based fallback")

        popular_parts = self.parts_df.sort_values("failure_rate", ascending=False).head(n)
        results = []
        for _, part in popular_parts.iterrows():
            explanation = {
                "compatibility": 0.5,
                "risk_score": float(part["failure_rate"]),
                "failure_rate": float(part["failure_rate"]),
                "category": part["category"],
                "criticality": part.get("criticality", "unknown"),
                "reason": "Popular spare part (cold-start fallback)",
            }
            results.append((part["part_id"], float(part["failure_rate"]), explanation))
        return results

    def _generate_reason(self, machine_type, part, compat, risk):
        reasons = []
        if compat > 0:
            reasons.append(f"Compatible with {machine_type}")
        if risk > 0.5:
            reasons.append(f"High failure risk ({risk:.0%})")
        if part.get("criticality") == "high":
            reasons.append("Critical component")
        if not reasons:
            reasons.append("General maintenance recommendation")
        return "; ".join(reasons)

    def recommend_from_sensors(self, temperature: float, vibration: float,
                               pressure: float, machine_type: str = "pump",
                               n: int = 10) -> List[Tuple[str, float, Dict]]:
        if not self.is_fitted:
            raise ValueError("Model not fitted.")

        similar = self.machines_df[self.machines_df["machine_type"] == machine_type]
        if similar.empty:
            similar = self.machines_df

        temp_diff = (similar["avg_temperature"] - temperature).abs()
        closest_idx = temp_diff.idxmin()
        closest_machine = self.machines_df.loc[closest_idx, "machine_id"]

        sensor_override = {
            "temperature": temperature,
            "vibration": vibration,
            "pressure": pressure,
            "anomaly_score": self._compute_anomaly(temperature, vibration, pressure),
        }

        return self.recommend(closest_machine, n, sensor_override)

    def _compute_anomaly(self, temp, vib, press):
        temp_score = max(0, (temp - 70) / 70)
        vib_score = max(0, (vib - 5) / 10)
        press_score = max(0, abs(press - 150) / 150)
        return np.clip(0.3 * temp_score + 0.4 * vib_score + 0.2 * press_score, 0, 1)
