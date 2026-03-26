"""
Evaluation metrics for recommendation system
"""

import numpy as np
import pandas as pd
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def precision_at_k(recommended: List[str], relevant: set, k: int) -> float:
    rec_k = recommended[:k]
    hits = len(set(rec_k) & relevant)
    return hits / k if k > 0 else 0.0


def recall_at_k(recommended: List[str], relevant: set, k: int) -> float:
    rec_k = recommended[:k]
    hits = len(set(rec_k) & relevant)
    return hits / len(relevant) if relevant else 0.0


def ndcg_at_k(recommended: List[str], relevant: set, k: int) -> float:
    rec_k = recommended[:k]
    dcg = sum(
        1.0 / np.log2(i + 2) for i, r in enumerate(rec_k) if r in relevant
    )
    ideal = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / ideal if ideal > 0 else 0.0


def mean_average_precision(all_recommended: List[List[str]],
                           all_relevant: List[set]) -> float:
    aps = []
    for recs, rels in zip(all_recommended, all_relevant):
        if not rels:
            continue
        hits = 0
        precision_sum = 0
        for i, rec in enumerate(recs):
            if rec in rels:
                hits += 1
                precision_sum += hits / (i + 1)
        ap = precision_sum / len(rels) if rels else 0
        aps.append(ap)
    return float(np.mean(aps)) if aps else 0.0


def coverage(all_recommended: List[List[str]], catalog_size: int) -> float:
    all_rec_items = set()
    for recs in all_recommended:
        all_rec_items.update(recs)
    return len(all_rec_items) / catalog_size if catalog_size > 0 else 0.0


def evaluate_model(model, test_df: pd.DataFrame, k_values: List[int] = None) -> Dict:
    if k_values is None:
        k_values = [3, 5, 10]

    machines = test_df["machine_id"].unique()
    results = {f"precision@{k}": [] for k in k_values}
    results.update({f"recall@{k}": [] for k in k_values})
    results.update({f"ndcg@{k}": [] for k in k_values})
    all_recs = []
    all_rels = []

    for mid in machines:
        actual = set(test_df[test_df["machine_id"] == mid]["part_id"].unique())
        if not actual:
            continue

        max_k = max(k_values)
        recs = model.recommend(mid, n=max_k)
        rec_ids = [r["part_id"] for r in recs]

        all_recs.append(rec_ids)
        all_rels.append(actual)

        for k in k_values:
            results[f"precision@{k}"].append(precision_at_k(rec_ids, actual, k))
            results[f"recall@{k}"].append(recall_at_k(rec_ids, actual, k))
            results[f"ndcg@{k}"].append(ndcg_at_k(rec_ids, actual, k))

    summary = {}
    for key, values in results.items():
        summary[key] = float(np.mean(values)) if values else 0.0

    summary["MAP"] = mean_average_precision(all_recs, all_rels)
    summary["coverage"] = coverage(all_recs, len(test_df["part_id"].unique()))
    summary["n_evaluated_machines"] = len(all_recs)

    return summary

