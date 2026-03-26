"""
Collaborative Filtering using Alternating Least Squares (ALS)
Implicit feedback based on maintenance frequency / failure occurrence
"""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ALSCollaborativeFilter:
    def __init__(self, n_factors: int = 50, n_iterations: int = 20,
                 regularization: float = 0.1, alpha: float = 40):
        self.n_factors = n_factors
        self.n_iterations = n_iterations
        self.regularization = regularization
        self.alpha = alpha
        self.user_factors = None
        self.item_factors = None
        self.machine_idx_map: Dict[str, int] = {}
        self.part_idx_map: Dict[str, int] = {}
        self.idx_machine_map: Dict[int, str] = {}
        self.idx_part_map: Dict[int, str] = {}
        self.interaction_matrix: Optional[csr_matrix] = None
        self.is_fitted = False

    def _build_interaction_matrix(self, logs_df: pd.DataFrame) -> csr_matrix:
        interaction = logs_df.groupby(["machine_id", "part_id"]).agg(
            frequency=("log_id", "count"),
            avg_downtime=("downtime_hours", lambda x: x.mean() if x.notna().any() else 0),
        ).reset_index()

        interaction["score"] = (
            interaction["frequency"] * 0.7 +
            np.log1p(interaction["avg_downtime"]) * 0.3
        )

        machines = sorted(interaction["machine_id"].unique())
        parts = sorted(interaction["part_id"].unique())

        self.machine_idx_map = {m: i for i, m in enumerate(machines)}
        self.part_idx_map = {p: i for i, p in enumerate(parts)}
        self.idx_machine_map = {i: m for m, i in self.machine_idx_map.items()}
        self.idx_part_map = {i: p for p, i in self.part_idx_map.items()}

        rows = interaction["machine_id"].map(self.machine_idx_map).values
        cols = interaction["part_id"].map(self.part_idx_map).values
        vals = interaction["score"].values

        matrix = csr_matrix(
            (vals, (rows, cols)),
            shape=(len(machines), len(parts))
        )
        return matrix

    def fit(self, logs_df: pd.DataFrame):
        logger.info("Building interaction matrix...")
        self.interaction_matrix = self._build_interaction_matrix(logs_df)
        n_users, n_items = self.interaction_matrix.shape
        logger.info(f"Matrix shape: {n_users} machines x {n_items} parts")

        confidence = self.interaction_matrix.copy()
        confidence.data = 1 + self.alpha * np.log1p(confidence.data)

        np.random.seed(42)
        self.user_factors = np.random.normal(0, 0.01, (n_users, self.n_factors))
        self.item_factors = np.random.normal(0, 0.01, (n_items, self.n_factors))

        dense_conf = confidence.toarray()
        preference = (self.interaction_matrix.toarray() > 0).astype(float)

        lambda_eye = self.regularization * np.eye(self.n_factors)

        for iteration in range(self.n_iterations):
            for u in range(n_users):
                Cu = np.diag(dense_conf[u])
                pu = preference[u]
                YtCuY = self.item_factors.T @ Cu @ self.item_factors + lambda_eye
                YtCupu = self.item_factors.T @ Cu @ pu
                self.user_factors[u] = np.linalg.solve(YtCuY, YtCupu)

            for i in range(n_items):
                Ci = np.diag(dense_conf[:, i])
                pi = preference[:, i]
                XtCiX = self.user_factors.T @ Ci @ self.user_factors + lambda_eye
                XtCipi = self.user_factors.T @ Ci @ pi
                self.item_factors[i] = np.linalg.solve(XtCiX, XtCipi)

            if (iteration + 1) % 5 == 0:
                loss = self._compute_loss(preference, dense_conf)
                logger.info(f"  Iteration {iteration + 1}/{self.n_iterations}, loss={loss:.4f}")

        self.is_fitted = True
        logger.info("ALS training complete.")

    def _compute_loss(self, preference, confidence):
        pred = self.user_factors @ self.item_factors.T
        diff = confidence * (preference - pred) ** 2
        reg = self.regularization * (
            np.sum(self.user_factors ** 2) + np.sum(self.item_factors ** 2)
        )
        return diff.sum() + reg

    def recommend(self, machine_id: str, n: int = 10,
                  exclude_known: bool = True) -> List[Tuple[str, float]]:
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        if machine_id not in self.machine_idx_map:
            return []

        u_idx = self.machine_idx_map[machine_id]
        scores = self.user_factors[u_idx] @ self.item_factors.T

        if exclude_known:
            known = self.interaction_matrix[u_idx].toarray().flatten()
            scores[known > 0] = -np.inf

        top_indices = np.argsort(scores)[::-1][:n]
        results = []
        for idx in top_indices:
            if scores[idx] > -np.inf:
                results.append((self.idx_part_map[idx], float(scores[idx])))

        return results

    def get_similar_machines(self, machine_id: str, n: int = 5) -> List[Tuple[str, float]]:
        if machine_id not in self.machine_idx_map:
            return []

        u_idx = self.machine_idx_map[machine_id]
        user_vec = self.user_factors[u_idx]
        sims = self.user_factors @ user_vec
        sims[u_idx] = -np.inf

        top_indices = np.argsort(sims)[::-1][:n]
        return [(self.idx_machine_map[i], float(sims[i])) for i in top_indices]
