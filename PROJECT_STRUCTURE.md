# UrjaYukti AI - Updated Project Structure

## Project Structure

```
UrjaYukti AI/
├── frontend/                      # Next.js 14 dashboard
│   ├── src/
│   │   ├── app/                   # Next.js App Router pages
│   │   │   ├── globals.css        # Global styles + Tailwind + Mapbox CSS
│   │   │   ├── layout.tsx         # Root layout
│   │   │   └── page.tsx           # Main page with view routing
│   │   ├── components/            # Reusable UI components
│   │   │   ├── layout/            # Layout components
│   │   │   │   └── DashboardLayout.tsx  # App shell with Sidebar, TopBar, LiveTicker
│   │   │   ├── maps/              # Mapbox GL components
│   │   │   │   ├── ZoneHeatMap.tsx      # Core Mapbox canvas (raw mapbox-gl)
│   │   │   │   ├── ZoneSelectorBar.tsx  # Zone selection controls
│   │   │   │   ├── StatsPanel.tsx       # Zone detail panel
│   │   │   │   └── Legend.tsx           # Color legend
│   │   │   ├── views/              # Page-level view components
│   │   │   │   └── HeatmapView.tsx      # Master heatmap view assembly
│   │   │   ├── ui/                 # shadcn/ui components
│   │   │   │   ├── card.tsx
│   │   │   │   ├── badge.tsx
│   │   │   │   ├── button.tsx
│   │   │   │   ├── progress.tsx
│   │   │   │   ├── slider.tsx
│   │   │   │   ├── switch.tsx
│   │   │   │   ├── table.tsx
│   │   │   │   └── scroll-area.tsx
│   │   │   ├── alert-center.tsx    # Alert center component
│   │   │   ├── compliance-probability.tsx
│   │   │   ├── cross-zone-view.tsx
│   │   │   ├── forecast-panel.tsx   # Forecast panel component
│   │   │   ├── roi-payback-cards.tsx
│   │   │   ├── site-ranker.tsx      # Site ranking component
│   │   │   └── vpp-panel.tsx        # VPP optimizer component
│   │   ├── data/                   # GeoJSON and data files
│   │   │   │   ├── demand-nodes.json    # Demand node GeoJSON
│   │   │   │   └── bengaluru-zones.json # Zone boundary GeoJSON
│   │   ├── lib/                    # Utility libraries
│   │   │   ├── api.ts               # API client
│   │   │   ├── mockData.ts         # Mock data + TypeScript types
│   │   │   └── mapLayers.ts        # Mapbox layer definitions
│   │   └── types/                  # TypeScript type definitions
│   ├── public/                     # Static assets
│   ├── tailwind.config.ts          # Tailwind config with design tokens
│   ├── next.config.js              # Next.js configuration
│   ├── tsconfig.json              # TypeScript configuration
│   └── package.json               # Frontend dependencies
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

## Key Changes from Original Structure

### Frontend Updates
- **Added `src/app/`** - Next.js App Router structure (was `src/pages/`)
- **Added `src/components/views/`** - Page-level view components
- **Added `src/components/layout/`** - Layout components
- **Added `src/components/maps/`** - Mapbox GL components
- **Added `src/data/`** - GeoJSON and data files (was in root `data/`)
- **Added `src/lib/mapLayers.ts`** - Mapbox layer definitions
- **Added `src/lib/mockData.ts`** - Mock data with TypeScript types
- **Added `tailwind.config.ts`** - Tailwind configuration with design tokens
- **Added `globals.css`** - Global styles with Mapbox CSS import

### Component Organization
- **Layout Components**: `DashboardLayout.tsx` (Sidebar, TopBar, LiveTicker)
- **Map Components**: `ZoneHeatMap.tsx`, `ZoneSelectorBar.tsx`, `StatsPanel.tsx`, `Legend.tsx`
- **View Components**: `HeatmapView.tsx` (master view assembly)
- **UI Components**: Existing components (alert-center, forecast-panel, vpp-panel, site-ranker, etc.)
- **Data Files**: `demand-nodes.json`, `bengaluru-zones.json`

### Dependencies
- **Frontend**: `mapbox-gl`, `@turf/turf` (Mapbox GL JS + Turf.js for geospatial operations)
- **Backend**: Python, FastAPI, LangGraph, OR-Tools, HDBSCAN, PostgreSQL, TimescaleDB, ChromaDB

### Design System
- **Tailwind Config**: Custom design tokens (bg, panel, card, primary, teal, cyan, etc.)
- **Global CSS**: Custom animations (fade-up, draw-perim, ripple, dot-beat, etc.)
- **Font Stack**: Inter (body), Rajdhani (display), JetBrains Mono (monospace)
