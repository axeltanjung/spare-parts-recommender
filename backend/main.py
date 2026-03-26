"""
Industrial Spare Parts Recommendation System - FastAPI Backend
"""

import os
import sys
import time
import logging
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.hybrid_recommender import HybridRecommender
from backend.models.explainability import RecommendationExplainer
from backend.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

MODEL_PATH = os.environ.get(
    "MODEL_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts", "hybrid_model.pkl")
)

model: Optional[HybridRecommender] = None
explainer = RecommendationExplainer()
request_count = 0
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    logger.info(f"Loading model from {MODEL_PATH}...")
    try:
        model = HybridRecommender.load(MODEL_PATH)
        logger.info("Model loaded successfully.")
    except FileNotFoundError:
        logger.warning(f"Model not found at {MODEL_PATH}. Run train.py first.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Industrial Spare Parts Recommender",
    description="AI-powered recommendation system for industrial maintenance spare parts",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecommendRequest(BaseModel):
    machine_id: str = Field(..., description="Machine identifier (e.g., M0001)")
    n: int = Field(default=5, ge=1, le=20, description="Number of recommendations")
    include_explanation: bool = Field(default=True, description="Include SHAP explanations")


class SimulateRequest(BaseModel):
    temperature: float = Field(..., ge=20, le=200, description="Temperature in °C")
    vibration: float = Field(..., ge=0.5, le=25, description="Vibration level in mm/s")
    pressure: float = Field(..., ge=10, le=500, description="Pressure in PSI")
    machine_type: str = Field(default="pump", description="Machine type for context")
    n: int = Field(default=5, ge=1, le=20)
    include_explanation: bool = Field(default=True)


class PartRecommendation(BaseModel):
    part_id: str
    part_name: str
    category: str
    score: float
    cf_score: float
    cb_score: float
    cf_contribution: float
    cb_contribution: float
    cost_usd: Optional[float]
    criticality: str
    lead_time_days: int
    failure_rate: float
    explanation: dict
    shap_explanation: Optional[dict] = None


class RecommendResponse(BaseModel):
    machine_id: str
    machine_info: Optional[dict]
    recommendations: List[PartRecommendation]
    model_version: str = "1.0.0"
    inference_time_ms: float


class SimulateResponse(BaseModel):
    sensor_input: dict
    recommendations: List[PartRecommendation]
    model_version: str = "1.0.0"
    inference_time_ms: float


@app.get("/health")
async def health_check():
    global request_count
    uptime = time.time() - start_time
    return {
        "status": "healthy" if model is not None else "degraded",
        "model_loaded": model is not None,
        "uptime_seconds": round(uptime, 2),
        "total_requests": request_count,
        "version": "1.0.0",
    }


@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    global request_count
    request_count += 1

    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded. Run train.py first.")

    t0 = time.time()
    machine_info = model.get_machine_info(request.machine_id)
    recs = model.recommend(request.machine_id, n=request.n)

    if request.include_explanation and machine_info:
        recs = explainer.batch_explain(recs, machine_info, model.parts_df)

    inference_ms = (time.time() - t0) * 1000
    logger.info(f"Recommend {request.machine_id}: {len(recs)} results in {inference_ms:.1f}ms")

    return RecommendResponse(
        machine_id=request.machine_id,
        machine_info=machine_info,
        recommendations=recs,
        inference_time_ms=round(inference_ms, 2),
    )


@app.post("/simulate", response_model=SimulateResponse)
async def simulate(request: SimulateRequest):
    global request_count
    request_count += 1

    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    t0 = time.time()
    recs = model.recommend_from_sensors(
        temperature=request.temperature,
        vibration=request.vibration,
        pressure=request.pressure,
        machine_type=request.machine_type,
        n=request.n,
    )

    if request.include_explanation:
        dummy_info = {
            "machine_id": "simulated",
            "machine_type": request.machine_type,
            "age_years": 5,
            "usage_hours_per_day": 16,
            "sensor_data": {
                "avg_temperature": request.temperature,
                "avg_vibration": request.vibration,
                "avg_pressure": request.pressure,
                "max_anomaly": model.cb_model._compute_anomaly(
                    request.temperature, request.vibration, request.pressure
                ),
            },
        }
        recs = explainer.batch_explain(recs, dummy_info, model.parts_df)

    inference_ms = (time.time() - t0) * 1000
    logger.info(f"Simulate: {len(recs)} results in {inference_ms:.1f}ms")

    return SimulateResponse(
        sensor_input={
            "temperature": request.temperature,
            "vibration": request.vibration,
            "pressure": request.pressure,
            "machine_type": request.machine_type,
        },
        recommendations=recs,
        inference_time_ms=round(inference_ms, 2),
    )


@app.get("/machines")
async def list_machines():
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    machines = model.machines_df[["machine_id", "machine_type", "location"]].to_dict("records")
    return {"machines": machines, "total": len(machines)}


@app.get("/machines/{machine_id}")
async def get_machine(machine_id: str):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    info = model.get_machine_info(machine_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Machine {machine_id} not found.")
    return info


@app.get("/parts")
async def list_parts():
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    parts = model.parts_df[["part_id", "part_name", "category", "criticality", "cost_usd"]].to_dict("records")
    return {"parts": parts, "total": len(parts)}


@app.get("/metrics")
async def get_metrics():
    return {
        "request_count": request_count,
        "uptime_seconds": round(time.time() - start_time, 2),
        "model_loaded": model is not None,
        "model_version": "1.0.0",
    }
