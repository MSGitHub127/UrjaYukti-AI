# UrjaYukti AI - EV Charging Optimization & Infrastructure Planning

AI-based decision-support system for BESCOM to predict EV charging demand, optimize charging schedules, and recommend infrastructure locations.

## Project Structure

```
UrjaYukti AI/
├── frontend/                      # Next.js 14 dashboard
│   ├── src/
│   │   ├── components/            # Reusable UI components
│   │   │   ├── charts/           # Recharts visualizations
│   │   │   ├── maps/             # Mapbox GL layers
│   │   │   └── cards/            # KPI, alert, explainability cards
│   │   ├── pages/                # Page components
│   │   │   ├── dashboard/        # Main dashboard
│   │   │   ├── forecast/         # Demand forecast panel
│   │   │   ├── vpp/              # VPP optimizer
│   │   │   ├── sites/            # Site ranker
│   │   │   └── alerts/           # Alert center
│   │   ├── hooks/                # Custom React hooks
│   │   ├── lib/                  # Utility libraries
│   │   ├── styles/               # Global styles
│   │   └── types/                # TypeScript types
│   └── public/                   # Static assets
├── backend/                      # Python FastAPI backend
│   ├── src/
│   │   ├── agents/               # LangGraph agents
│   │   │   ├── demand_agent.py   # Demand forecasting agent
│   │   │   ├── schedule_agent.py # VPP scheduling agent
│   │   │   ├── site_agent.py     # Site planning agent
│   │   │   └── coordinator.py    # Cross-zone coordinator
│   │   ├── models/               # ML models
│   │   │   ├── tft/              # Temporal Fusion Transformer
│   │   │   ├── lstm/             # LSTM anomaly detector
│   │   │   └── behavior/         # User behavior adoption model
│   │   ├── optimization/         # Optimization engines
│   │   │   ├── vpp/              # OR-Tools VPP scheduler
│   │   │   ├── spatial/          # HDBSCAN clustering
│   │   │   ├── mcda/             # Multi-criteria site ranking
│   │   │   └── cross_zone/       # Multi-zone load balancing
│   │   ├── api/                  # FastAPI endpoints
│   │   │   ├── forecast.py       # Forecast API
│   │   │   ├── schedule.py       # Schedule API
│   │   │   ├── sites.py          # Site ranking API
│   │   │   ├── alerts.py         # Alert API
│   │   │   └── grid.py           # Grid state API
│   │   ├── db/                   # Database connections
│   │   │   ├── postgres.py       # PostgreSQL + PostGIS
│   │   │   ├── timescale.py      # TimescaleDB
│   │   │   └── chroma.py         # ChromaDB RAG
│   │   ├── ingestion/            # Data ingestion
│   │   │   ├── bescom/           # BESCOM feeder API connector
│   │   │   ├── synthetic.py      # Synthetic data generator
│   │   │   └── stream.py         # Real-time stream processor
│   │   ├── retraining/           # Model retraining workflow
│   │   │   ├── detector.py       # Drift detection
│   │   │   ├── pipeline.py       # Retraining pipeline
│   │   │   └── validator.py      # Model validation
│   │   ├── roi/                  # ROI and cost-benefit analysis
│   │   │   ├── calculator.py     # Payback period calculator
│   │   │   └── utilization.py    # Utilization rate estimator
│   │   └── utils/                # Utilities
│   └── tests/                    # Backend tests
├── data/                         # Data storage
│   ├── synthetic/                # Agent-based model outputs
│   ├── osm/                      # OpenStreetMap data
│   ├── processed/                # Processed datasets
│   ├── models/                   # Trained model artifacts
│   └── feedback/                 # User compliance feedback
├── scripts/                      # Utility scripts
│   ├── data_prep/                # Data preparation
│   ├── training/                 # Model training
│   ├── deployment/               # Deployment scripts
│   └── retraining/                # Retraining automation
├── docs/                         # Documentation
│   ├── api/                      # API documentation
│   ├── architecture/             # Architecture docs
│   ├── evaluation/               # Evaluation reports
│   └── gaps/                     # Gap analysis and solutions
└── config/                       # Configuration files
    ├── model_config.yaml         # Model hyperparameters
    ├── grid_config.yaml          # Grid constraints
    └── incentive_config.yaml     # Incentive parameters
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, React 18, Mapbox GL JS, Recharts |
| Backend | Python, FastAPI, LangGraph |
| ML Models | Temporal Fusion Transformer, LSTM Autoencoder, Behavior Model |
| Optimization | Google OR-Tools, HDBSCAN, Cross-zone Load Balancing |
| Database | PostgreSQL + PostGIS, TimescaleDB, ChromaDB |
| LLM | Mistral 7B (private VPC) |
| Drift Detection | Evidently AI |
| ROI Analysis | Custom payback calculator |

## Refined Implementation Plan (6 Days)

### Day 1: Data Foundation
- Generate synthetic EV demand dataset (3 archetypes × 6 zones × 90 days)
- Set up PostGIS + TimescaleDB schema
- Ingest Bengaluru OSM road + POI data
- Build data confidence scoring system
- **NEW**: Define BESCOM feeder API integration spec
- **NEW**: Create user behavior baseline dataset

### Day 2: Forecasting Engine
- Train Temporal Fusion Transformer (72-hr horizon, 6-zone × hourly)
- Validate vs ARIMA baseline (target MAPE <12%)
- Build LSTM Anomaly Detector
- Implement multi-resolution prediction
- **NEW**: Train user behavior adoption model
- **NEW**: Define compliance probability framework

### Day 3: Optimization & Planning
- Implement OR-Tools VPP Scheduler (N-1 + 70% headroom constraints)
- Build HDBSCAN clustering pipeline
- MCDA Site Scoring Engine (6-dimension weighted scorer)
- Define dual peak load metrics (PLI + PLR)
- **NEW**: Implement cross-zone load balancing
- **NEW**: Add ROI calculator to site ranking

### Day 4: Agentic Layer
- Wire LangGraph agent graph (Demand → Schedule → Site agents)
- Deploy Mistral 7B on VPC
- Build ChromaDB RAG pipeline
- Implement GridStateMonitor (real-time feeder load)
- **NEW**: Add CrossZoneCoordinator agent
- **NEW**: Implement retraining workflow triggers

### Day 5: Command Center UI
- Build Next.js 14 dashboard shell
- Demand heatmap + forecast panel
- VPP panel + MCDA site ranker UI
- Add Action Cards with next steps
- **NEW**: Compliance probability visualization
- **NEW**: Cross-zone coordination view
- **NEW**: ROI and payback period cards

### Day 6: Integration & Demo
- End-to-end demo scenario
- Benchmark against baselines
- Implement Outcome Tracking Module
- Polish explainability outputs
- **NEW**: Demonstrate cross-zone load shifting
- **NEW**: Show ROI projections for new sites
- **NEW**: Validate retraining workflow

## Gap Analysis & Solutions

### 1. User Behavior Adoption
**Gap**: Plan assumes users follow recommended schedules; no incentive modeling.

**Solution**:
- Train behavior model on historical compliance data
- Implement compliance probability estimator (10-80% range)
- Add incentive calculator (₹/kWh rebate, time-of-use rates)
- Include compliance confidence in all recommendations
- Track actual vs. expected compliance for continuous learning

### 2. Real-Time Data Ingestion
**Gap**: BESCOM feeder API connection is mocked; no integration path.

**Solution**:
- Define BESCOM feeder API specification (REST/WebSocket)
- Create connector with fallback to synthetic data
- Implement data masking pipeline for PII protection
- Add data quality scoring and confidence badges
- Support batch and streaming ingestion modes

### 3. Model Retraining Strategy
**Gap**: Evidently AI flags drift, but retraining workflow is undefined.

**Solution**:
- Define drift thresholds (MAPE >15%, anomaly rate >5%)
- Implement automated retraining pipeline with human approval
- Add model validation before deployment (shadow mode testing)
- Create rollback mechanism for failed deployments
- Log all retraining decisions with audit trail

### 4. Multi-Zone Coordination
**Gap**: Optimization appears zone-by-zone; no cross-zone load balancing.

**Solution**:
- Implement CrossZoneCoordinator agent
- Add spill-over detection and routing
- Create zone-pair load transfer optimization
- Visualize cross-zone dependencies in UI
- Add cross-zone constraint violation alerts

### 5. Infrastructure ROI
**Gap**: Site ranking lacks payback period, utilization rate, or cost-benefit analysis.

**Solution**:
- Implement ROI calculator (CAPEX, OPEX, revenue projections)
- Add utilization rate estimator based on demand forecasts
- Include payback period in site ranking (target <3 years)
- Create sensitivity analysis for demand uncertainty
- Add cost-benefit comparison vs. baseline placement

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- PostgreSQL 15+ with PostGIS and TimescaleDB extensions
- Docker (for Mistral 7B)

### Installation

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

## Non-Negotiables

- Zero modification to BESCOM systems
- Decision-support layer only
- Synthetic/masked data only
- Explainable and actionable outputs
- Grid constraint awareness
- No hosted LLM on sensitive data
- Human-in-the-loop for all critical decisions

## Evaluation Metrics

| Metric | Target | Baseline |
|--------|--------|----------|
| Peak Load Reduction | ≥15% | 0% unmanaged |
| Forecast MAPE | <12% | ~22% ARIMA |
| Site Precision | ≥80% | Random placement |
| Compliance Rate | ≥60% | N/A |
| Cross-Zone Efficiency | ≥10% load transfer | Zone-isolated |
| ROI Payback | <3 years | N/A |
| Constraint Violations | 0 | N/A |

## License

Proprietary - BESCOM Hackathon Submission
