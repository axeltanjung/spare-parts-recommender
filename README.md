# Industrial Spare Parts Recommendation System

<img width="1917" height="904" alt="image" src="https://github.com/user-attachments/assets/29e94b78-4a80-4f21-93a1-ff5e5c9ef250" />

> AI-powered recommendation engine for industrial maintenance spare parts, combining collaborative filtering and content-based approaches with real-time sensor simulation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  ┌──────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │Dashboard │  │Recommendation    │  │Simulation Panel       │  │
│  │- Machine │  │View              │  │- Sensor sliders       │  │
│  │  selector│  │- Part cards      │  │- Real-time updates    │  │
│  │- Metrics │  │- Score viz       │  │- Risk assessment      │  │
│  │- Charts  │  │- SHAP explain    │  │- History tracking     │  │
│  └──────────┘  └──────────────────┘  └───────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
┌────────────────────────────┴────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │/recommend│  │/simulate │  │/machines │  │/health         │  │
│  │          │  │          │  │/parts    │  │/metrics        │  │
│  └────┬─────┘  └────┬─────┘  └──────────┘  └────────────────┘  │
│       │              │                                           │
│  ┌────┴──────────────┴──────────────────────────────────────┐   │
│  │              HYBRID RECOMMENDATION ENGINE                 │   │
│  │  ┌─────────────────┐  ┌─────────────────┐               │   │
│  │  │ ALS Collaborative│  │ Content-Based   │               │   │
│  │  │ Filtering (0.4)  │  │ Recommender(0.6)│               │   │
│  │  │                  │  │                  │               │   │
│  │  │ Machine-Part     │  │ Machine features│               │   │
│  │  │ interaction      │  │ Part compat     │               │   │
│  │  │ matrix (implicit)│  │ Sensor risk     │               │   │
│  │  └─────────────────┘  └─────────────────┘               │   │
│  │                                                           │   │
│  │  ┌─────────────────────────────────────────────────┐     │   │
│  │  │ SHAP Explainability Engine                       │     │   │
│  │  │ Feature contributions + natural language reasons │     │   │
│  │  └─────────────────────────────────────────────────┘     │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│                    SYNTHETIC DATA LAYER                          │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌─────────────┐  │
│  │ machines │  │spare_parts│  │maintenance │  │sensor_data  │  │
│  │ (200)    │  │ (150)     │  │_logs(8000) │  │ (3000)      │  │
│  └──────────┘  └───────────┘  └────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Problem Statement

Industrial facilities spend **15-40% of their maintenance budget** on spare parts inventory. Key challenges:

1. **Reactive ordering** — Parts ordered after failure, causing extended downtime
2. **Over-stocking** — Holding excess inventory ties up capital
3. **Wrong parts** — Technicians select suboptimal replacement parts
4. **No predictive capability** — Sensor data not leveraged for proactive ordering

This system addresses all four by recommending the most relevant spare parts based on:
- **Historical patterns** (which parts were used for similar machines)
- **Machine characteristics** (type, age, usage profile)
- **Real-time sensor conditions** (temperature, vibration, pressure anomalies)

---

## Business Impact

| Metric | Before | After (Projected) |
|--------|--------|-------------------|
| Unplanned downtime | 12% | 5% |
| Parts inventory cost | $2.4M/yr | $1.6M/yr |
| Mean time to repair | 8.5 hrs | 4.2 hrs |
| First-time fix rate | 68% | 89% |
| Parts waste | 15% | 4% |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML Models | NumPy, SciPy, scikit-learn (ALS, Content-Based, Hybrid) |
| Backend | FastAPI, Pydantic, Uvicorn |
| Frontend | React 18, Recharts, Framer Motion |
| Explainability | Custom SHAP-inspired feature attribution |
| Deployment | Docker, docker-compose, Nginx |
| Data | Synthetic generator with realistic industrial distributions |

---

## Dataset Overview

**Total: 11,350+ rows across 4 tables**

- **machines** (200): 6 machine types, Weibull-distributed age, location-based
- **spare_parts** (150): 15 categories, compatibility mapping, lognormal cost
- **maintenance_logs** (8,000): Seasonal patterns, correlated failure types, noise/missing values
- **sensor_data** (3,000+): Physics-based sensor readings correlated to machine type and age

---

## ML Approach

### A. Collaborative Filtering (ALS)
- Implicit feedback from maintenance frequency
- Confidence-weighted matrix factorization
- 30 latent factors, 15 iterations

### B. Content-Based Filtering
- Machine feature vectors (type, age, sensor aggregates, failure history)
- Part feature vectors (category, compatibility, failure rate, criticality)
- Risk scoring based on sensor anomalies

### C. Hybrid Engine
- **Score = 0.4 × CF_normalized + 0.6 × CB_normalized**
- CB weighted higher (industrial domain: compatibility is critical)
- Cold-start fallback to popularity-based recommendations

### D. Evaluation
- Precision@K, Recall@K, NDCG@K
- Coverage metric
- Mean Average Precision (MAP)

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
git clone <repo-url>
cd spare-parts-recommender

# Build and run
docker-compose up --build

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m backend.train          # Generate data + train model
uvicorn backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm start                        # http://localhost:3000
```

---

## API Endpoints

### POST /recommend
```json
// Request
{ "machine_id": "M0001", "n": 5, "include_explanation": true }

// Response
{
  "machine_id": "M0001",
  "machine_info": { "machine_type": "crusher", "age_years": 7.2, ... },
  "recommendations": [
    {
      "part_id": "P0042",
      "part_name": "bearing_042",
      "category": "bearing",
      "score": 0.847,
      "cf_score": 0.72,
      "cb_score": 0.93,
      "explanation": { "reason": "Compatible with crusher; High failure risk (82%)", ... },
      "shap_explanation": { "feature_contributions": {...}, "top_reasons": [...] }
    }
  ]
}
```

### POST /simulate
```json
// Request
{ "temperature": 95, "vibration": 12.5, "pressure": 280, "machine_type": "pump" }

// Response: Same structure as /recommend with sensor-driven scoring
```

### GET /health
```json
{ "status": "healthy", "model_loaded": true, "uptime_seconds": 3600.5 }
```

---

## Monitoring

The system includes:
- **Request counting** at `/metrics` endpoint
- **Inference time tracking** per request
- **Structured logging** to stdout + file
- **Health checks** for Docker orchestration
- **Model versioning** in all API responses

For production deployment, integrate with:
- Prometheus + Grafana for metrics visualization
- ELK stack for centralized logging
- Model drift detection via periodic evaluation against held-out data

---

## Project Structure

```
spare-parts-recommender/
├── backend/
│   ├── data/
│   │   ├── generate_dataset.py    # Synthetic data generator
│   │   └── __init__.py
│   ├── models/
│   │   ├── collaborative_filter.py # ALS implicit feedback
│   │   ├── content_based.py        # Feature-based recommender
│   │   ├── hybrid_recommender.py   # Combined scoring engine
│   │   ├── evaluation.py           # Precision/Recall/NDCG metrics
│   │   ├── explainability.py       # SHAP-inspired explanations
│   │   └── __init__.py
│   ├── main.py                     # FastAPI application
│   ├── train.py                    # Training pipeline
│   ├── logging_config.py           # Logging setup
│   ├── requirements.txt
│   └── __init__.py
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.js
│   │   │   ├── MetricCard.js
│   │   │   └── RecommendationCard.js
│   │   ├── pages/
│   │   │   ├── Dashboard.js
│   │   │   ├── RecommendationView.js
│   │   │   └── SimulationPanel.js
│   │   ├── api.js
│   │   ├── App.js
│   │   ├── index.js
│   │   └── index.css
│   └── package.json
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── nginx.conf
└── README.md
```
