"""
Model Training Pipeline
Generates data, trains hybrid model, evaluates, and saves artifacts.
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data.generate_dataset import generate_all
from backend.models.hybrid_recommender import HybridRecommender
from backend.models.evaluation import evaluate_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def train():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "generated")
    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")

    logger.info("Step 1: Generating synthetic dataset...")
    machines, parts, logs, sensors = generate_all(data_dir)

    split_idx = int(len(logs) * 0.8)
    logs_sorted = logs.sort_values("timestamp")
    train_logs = logs_sorted.iloc[:split_idx]
    test_logs = logs_sorted.iloc[split_idx:]
    logger.info(f"Train: {len(train_logs)} logs, Test: {len(test_logs)} logs")

    logger.info("Step 2: Training hybrid recommender...")
    model = HybridRecommender(cf_weight=0.4, cb_weight=0.6)
    model.fit(machines, parts, train_logs, sensors)

    logger.info("Step 3: Evaluating model...")
    metrics = evaluate_model(model, test_logs, k_values=[3, 5, 10])
    for metric, value in metrics.items():
        logger.info(f"  {metric}: {value:.4f}" if isinstance(value, float) else f"  {metric}: {value}")

    logger.info("Step 4: Saving model...")
    model_path = os.path.join(model_dir, "hybrid_model.pkl")
    model.save(model_path)

    logger.info("Step 5: Quick smoke test...")
    sample_machine = machines.iloc[0]["machine_id"]
    recs = model.recommend(sample_machine, n=3)
    logger.info(f"  Recommendations for {sample_machine}:")
    for r in recs:
        logger.info(f"    {r['part_id']} ({r['category']}): score={r['score']:.3f}")

    logger.info("Training pipeline complete!")
    return model, metrics


if __name__ == "__main__":
    train()
