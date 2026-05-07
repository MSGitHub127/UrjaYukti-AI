"""
Optimization API
Production-grade FastAPI endpoints for VPP scheduling, site ranking, and constraint validation.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import asdict

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Create a simple config class for fallback
class SimpleConfig:
    def __init__(self):
        self.log_level = "INFO"
        self.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.device = "auto"
        self.num_workers = 4
        self.pin_memory = True

try:
    from models.config import ModelConfig, get_config
    from optimization.vpp.scheduler import VPPScheduler, ChargingSession, ZoneConstraint
    from optimization.mcda.site_scorer import MCDAEngine, SiteCandidate, ScoringWeights
    from optimization.spatial.clustering import HDBSCANPipeline
    from optimization.cross_zone.balancer import CrossZoneBalancer, ZoneConnection
    from optimization.metrics import PeakLoadCalculator, PeakLoadMetrics
except ImportError:
    # Fallback for direct execution
    ModelConfig = None
    def get_config(config_path=None):
        return None
    VPPScheduler = None
    ChargingSession = None
    ZoneConstraint = None
    MCDAEngine = None
    SiteCandidate = None
    ScoringWeights = None
    HDBSCANPipeline = None
    CrossZoneBalancer = None
    ZoneConnection = None
    PeakLoadCalculator = None
    PeakLoadMetrics = None


# Pydantic models for API requests/responses
class ChargingSessionRequest(BaseModel):
    """Request model for charging session."""

    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    zone_id: str = Field(..., description="Zone ID")
    archetype_id: str = Field(..., description="Archetype ID")
    preferred_start_hour: int = Field(..., ge=0, le=23, description="Preferred start hour (0-23)")
    preferred_end_hour: int = Field(..., ge=0, le=23, description="Preferred end hour (0-23)")
    energy_kwh: float = Field(..., gt=0, description="Energy required in kWh")
    power_kw: float = Field(..., gt=0, description="Charging power in kW")
    flexibility_hours: int = Field(2, ge=0, le=12, description="Flexibility in hours")
    compliance_probability: float = Field(0.5, ge=0, le=1, description="Compliance probability")
    incentive_eligible: bool = Field(True, description="Eligible for incentives")


class ScheduleRequest(BaseModel):
    """Request model for schedule optimization."""

    sessions: List[ChargingSessionRequest]
    use_compliance: bool = Field(True, description="Consider compliance probability")
    enable_cross_zone: bool = Field(False, description="Enable cross-zone balancing")


class ScheduleResponse(BaseModel):
    """Response model for schedule result."""

    session_id: str
    zone_id: str
    original_start_hour: int
    scheduled_start_hour: int
    shift_hours: float
    energy_kwh: float
    power_kw: float
    compliance_probability: float
    incentive_amount: float


class ScheduleMetricsResponse(BaseModel):
    """Response model for schedule metrics."""

    peak_load_kw: float
    peak_load_index: float
    peak_load_reduction: float
    avg_shift_hours: float
    total_shifted_sessions: int
    avg_compliance_probability: float
    total_incentive_amount: float
    constraint_violations: int
    pli_target_met: bool
    plr_target_met: bool


class SiteCandidateRequest(BaseModel):
    """Request model for site candidate."""

    site_id: str = Field(..., description="Site ID")
    name: str = Field(..., description="Site name")
    zone_id: str = Field(..., description="Zone ID")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")


class SiteRankingRequest(BaseModel):
    """Request model for site ranking."""

    candidates: List[SiteCandidateRequest]
    weights: Optional[Dict[str, float]] = Field(None, description="Scoring weights")


class SiteRankingResponse(BaseModel):
    """Response model for site ranking."""

    rank: int
    site_id: str
    name: str
    zone_id: str
    total_score: float
    dimension_scores: Dict[str, float]
    red_flags: List[str]
    recommendation: str
    payback_years: Optional[float] = None
    utilization_rate: Optional[float] = None


class OptimizationAPI:
    """Production-grade Optimization API."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_config() or SimpleConfig()

        self.app = FastAPI(
            title="UrjaYukti AI Optimization API",
            description="EV Charging Optimization and Site Planning API",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )

        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.vpp_scheduler = VPPScheduler(self.config) if VPPScheduler else None
        self.mcda_engine = MCDAEngine() if MCDAEngine else None
        self.clustering_pipeline = HDBSCANPipeline() if HDBSCANPipeline else None
        self.cross_zone_balancer = CrossZoneBalancer(self.config)if CrossZoneBalancer else None
        self.peak_load_calculator = PeakLoadCalculator()if PeakLoadCalculator else None

        # Setup routes
        self._setup_routes()

        # Initialize default constraints
        self._initialize_constraints()

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint with API information."""
            return {
                "name": "UrjaYukti AI Optimization API",
                "version": "1.0.0",
                "status": "operational",
                "endpoints": {
                    "schedule": "/api/schedule",
                    "site_ranking": "/api/sites/rank",
                    "clustering": "/api/clustering",
                    "cross_zone": "/api/cross_zone/balance",
                    "metrics": "/api/metrics",
                    "weights": "/api/weights"
                }
            }

        @self.app.post("/api/schedule", response_model=List[ScheduleResponse])
        async def optimize_schedule(request: ScheduleRequest):
            """
            Optimize EV charging schedule.

            - **sessions**: List of charging sessions
            - **use_compliance**: Whether to consider compliance probability
            - **enable_cross_zone**: Whether to enable cross-zone balancing
            """
            try:
                # Convert request to ChargingSession objects
                sessions = [
                    ChargingSession(
                        session_id=s.session_id,
                        user_id=s.user_id,
                        zone_id=s.zone_id,
                        archetype_id=s.archetype_id,
                        preferred_start_hour=s.preferred_start_hour,
                        preferred_end_hour=s.preferred_end_hour,
                        energy_kwh=s.energy_kwh,
                        power_kw=s.power_kw,
                        flexibility_hours=s.flexibility_hours,
                        compliance_probability=s.compliance_probability,
                        incentive_eligible=s.incentive_eligible
                    )
                    for s in request.sessions
                ]

                # Create sample forecast demand
                forecast_demand = self._create_sample_forecast()

                # Optimize schedule
                if request.enable_cross_zone:
                    scheduled, metrics = self.vpp_scheduler.optimize_with_cross_zone(
                        sessions,
                        forecast_demand,
                        self.cross_zone_balancer.get_zone_connectivity_matrix(),
                        request.use_compliance
                    )
                else:
                    scheduled, metrics = self.vpp_scheduler.optimize_schedule(
                        sessions,
                        forecast_demand,
                        request.use_compliance
                    )

                # Convert to response format
                response = [
                    ScheduleResponse(
                        session_id=s.session_id,
                        zone_id=s.zone_id,
                        original_start_hour=s.original_start_hour,
                        scheduled_start_hour=s.scheduled_start_hour,
                        shift_hours=s.shift_hours,
                        energy_kwh=s.energy_kwh,
                        power_kw=s.power_kw,
                        compliance_probability=s.compliance_probability,
                        incentive_amount=s.incentive_amount
                    )
                    for s in scheduled
                ]

                return response

            except Exception as e:
                self.logger.error(f"Error optimizing schedule: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/schedule/metrics", response_model=ScheduleMetricsResponse)
        async def get_schedule_metrics(request: ScheduleRequest):
            """Get optimization metrics for a schedule request."""
            try:
                # Convert request to ChargingSession objects
                sessions = [
                    ChargingSession(
                        session_id=s.session_id,
                        user_id=s.user_id,
                        zone_id=s.zone_id,
                        archetype_id=s.archetype_id,
                        preferred_start_hour=s.preferred_start_hour,
                        preferred_end_hour=s.preferred_end_hour,
                        energy_kwh=s.energy_kwh,
                        power_kw=s.power_kw,
                        flexibility_hours=s.flexibility_hours,
                        compliance_probability=s.compliance_probability,
                        incentive_eligible=s.incentive_eligible
                    )
                    for s in request.sessions
                ]

                # Create sample forecast demand
                forecast_demand = self._create_sample_forecast()

                # Optimize schedule
                scheduled, metrics = self.vpp_scheduler.optimize_schedule(
                    sessions,
                    forecast_demand,
                    request.use_compliance
                )

                return ScheduleMetricsResponse(**metrics)

            except Exception as e:
                self.logger.error(f"Error getting schedule metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/sites/rank", response_model=List[SiteRankingResponse])
        async def rank_sites(request: SiteRankingRequest):
            """
            Rank charging station sites using MCDA.

            - **candidates**: List of site candidates
            - **weights**: Optional scoring weights
            """
            try:
                # Update weights if provided
                if request.weights:
                    self.mcda_engine.update_weights(request.weights)

                # Convert request to SiteCandidate objects
                candidates = [
                    SiteCandidate(
                        site_id=c.site_id,
                        name=c.name,
                        zone_id=c.zone_id,
                        location=(c.lat, c.lon)
                    )
                    for c in request.candidates
                ]

                # Create sample data
                demand_data = self._create_sample_demand()
                grid_data = self._create_sample_grid_data()

                # Rank sites
                results = self.mcda_engine.rank_sites(candidates, demand_data, grid_data)

                # Convert to response format
                response = [
                    SiteRankingResponse(
                        rank=r.rank,
                        site_id=r.site_id,
                        name=r.name,
                        zone_id=r.zone_id,
                        total_score=r.total_score,
                        dimension_scores=r.dimension_scores,
                        red_flags=r.red_flags,
                        recommendation=r.recommendation,
                        payback_years=r.payback_years,
                        utilization_rate=r.utilization_rate
                    )
                    for r in results
                ]

                return response

            except Exception as e:
                self.logger.error(f"Error ranking sites: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/weights")
        async def get_weights():
            """Get current scoring weights."""
            return self.mcda_engine.get_weights()

        @self.app.put("/api/weights")
        async def update_weights(weights: Dict[str, float]):
            """Update scoring weights."""
            try:
                self.mcda_engine.update_weights(weights)
                return {"status": "success", "weights": self.mcda_engine.get_weights()}
            except Exception as e:
                self.logger.error(f"Error updating weights: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/clustering")
        async def cluster_demand(
            zone_id: Optional[str] = Query(None, description="Zone ID filter"),
            min_cluster_size: int = Query(10, description="Minimum cluster size")
        ):
            """Cluster demand points to identify hotspots."""
            try:
                # Update pipeline parameters
                self.clustering_pipeline.min_cluster_size = min_cluster_size

                # Create sample demand data
                demand_data = self._create_sample_demand_points()

                # Cluster demand
                result = self.clustering_pipeline.cluster_demand_points(demand_data, zone_id)

                # Get summary
                summary = self.clustering_pipeline.get_cluster_summary(result)

                return summary

            except Exception as e:
                self.logger.error(f"Error clustering demand: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/cross_zone/balance")
        async def balance_cross_zone(
            zone_loads: Dict[str, float],
            zone_capacities: Dict[str, float]
        ):
            """Balance load across zones."""
            try:
                # Balance load
                updated_loads, transfers = self.cross_zone_balancer.balance_load(
                    zone_loads,
                    zone_capacities
                )

                return {
                    "updated_loads": updated_loads,
                    "transfers": [
                        {
                            "from_zone": t.from_zone_id,
                            "to_zone": t.to_zone_id,
                            "transfer_kw": t.transfer_kw,
                            "efficiency": t.transfer_efficiency,
                            "reason": t.reason
                        }
                        for t in transfers
                    ],
                    "summary": self.cross_zone_balancer.get_transfer_summary()
                }

            except Exception as e:
                self.logger.error(f"Error balancing cross-zone: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/metrics")
        async def get_metrics(
            zone_id: Optional[str] = Query(None, description="Zone ID filter")
        ):
            """Get peak load metrics."""
            try:
                # Create sample hourly load data
                hourly_load = self._create_sample_hourly_load(zone_id)
                capacity = 50000.0  # 50 MW default

                # Calculate metrics
                metrics = self.peak_load_calculator.calculate_metrics(
                    hourly_load,
                    capacity
                )

                return metrics.to_dict()

            except Exception as e:
                self.logger.error(f"Error getting metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _initialize_constraints(self):
        """Initialize default zone constraints."""
        # Skip if imports failed                 
        if not VPPScheduler or not ZoneConstraint or not ZoneConnection:                 
            return
        constraints = [
            ZoneConstraint(
                zone_id="Z01",
                transformer_capacity_mw=50.0,
                current_load_mw=42.5,
                headroom_mw=7.5
            ),
            ZoneConstraint(
                zone_id="Z02",
                transformer_capacity_mw=40.0,
                current_load_mw=28.0,
                headroom_mw=12.0
            ),
            ZoneConstraint(
                zone_id="Z03",
                transformer_capacity_mw=35.0,
                current_load_mw=24.5,
                headroom_mw=10.5
            ),
            ZoneConstraint(
                zone_id="Z04",
                transformer_capacity_mw=30.0,
                current_load_mw=19.5,
                headroom_mw=10.5
            ),
            ZoneConstraint(
                zone_id="Z05",
                transformer_capacity_mw=45.0,
                current_load_mw=31.5,
                headroom_mw=13.5
            ),
            ZoneConstraint(
                zone_id="Z06",
                transformer_capacity_mw=38.0,
                current_load_mw=26.6,
                headroom_mw=11.4
            )
        ]

        self.vpp_scheduler.set_zone_constraints(constraints)

        # Initialize cross-zone connections
        if self.cross_zone_balancer and ZoneConnection:
            connections = [
                ZoneConnection("Z01", "Z05", 8.5, 5.0),
                ZoneConnection("Z01", "Z06", 5.2, 8.0),
                ZoneConnection("Z02", "Z03", 4.8, 6.0),
                ZoneConnection("Z02", "Z04", 6.1, 4.0),
                ZoneConnection("Z03", "Z04", 3.2, 7.0),
                ZoneConnection("Z05", "Z06", 7.3, 5.0)
            ]

            for connection in connections:
                self.cross_zone_balancer.add_connection(connection)

    def _create_sample_forecast(self) -> pd.DataFrame:
        """Create sample forecast demand data."""
        hours = list(range(24))
        zones = ["Z01", "Z02", "Z03", "Z04", "Z05", "Z06"]

        data = []
        for zone in zones:
            for hour in hours:
                # Create realistic demand pattern
                base = 100.0
                if 7 <= hour <= 10:  # Morning peak
                    base += 200.0
                elif 18 <= hour <= 21:  # Evening peak
                    base += 300.0

                data.append({
                    "time": datetime.now() + timedelta(hours=hour),
                    "zone_id": zone,
                    "prediction": base + np.random.normal(0, 20)
                })

        return pd.DataFrame(data)

    def _create_sample_demand(self) -> pd.DataFrame:
        """Create sample demand data for site ranking."""
        hours = list(range(24))
        zones = ["Z01", "Z02", "Z03", "Z04", "Z05", "Z06"]

        data = []
        for zone in zones:
            for hour in hours:
                base = 100.0
                if 18 <= hour <= 21:
                    base += 250.0

                data.append({
                    "zone_id": zone,
                    "prediction": base + np.random.normal(0, 15)
                })

        return pd.DataFrame(data)

    def _create_sample_grid_data(self) -> Dict[str, Dict]:
        """Create sample grid data."""
        return {
            "Z01": {
                "headroom_percent": 0.15,
                "power_available": True,
                "road_access": True,
                "fiber_available": True,
                "installation_cost": 800000
            },
            "Z02": {
                "headroom_percent": 0.30,
                "power_available": True,
                "road_access": True,
                "fiber_available": False,
                "installation_cost": 600000
            },
            "Z03": {
                "headroom_percent": 0.30,
                "power_available": True,
                "road_access": True,
                "fiber_available": True,
                "installation_cost": 700000
            },
            "Z04": {
                "headroom_percent": 0.35,
                "power_available": True,
                "road_access": True,
                "fiber_available": False,
                "installation_cost": 550000
            },
            "Z05": {
                "headroom_percent": 0.30,
                "power_available": True,
                "road_access": True,
                "fiber_available": True,
                "installation_cost": 750000
            },
            "Z06": {
                "headroom_percent": 0.30,
                "power_available": True,
                "road_access": True,
                "fiber_available": False,
                "installation_cost": 650000
            }
        }

    def _create_sample_demand_points(self) -> pd.DataFrame:
        """Create sample demand point data for clustering."""
        np.random.seed(42)

        # Create clusters around zone centers
        zone_centers = {
            "Z01": (12.9698, 77.7499),
            "Z02": (12.9138, 77.6374),
            "Z03": (12.9740, 77.6408)
        }

        data = []
        for zone_id, (center_lat, center_lon) in zone_centers.items():
            for _ in range(30):
                lat = center_lat + np.random.normal(0, 0.01)
                lon = center_lon + np.random.normal(0, 0.01)
                demand = np.random.uniform(20, 50)

                data.append({
                    "lat": lat,
                    "lon": lon,
                    "demand_kw": demand,
                    "zone_id": zone_id
                })

        # Add some noise points
        for _ in range(10):
            lat = np.random.uniform(12.8, 13.0)
            lon = np.random.uniform(77.5, 77.8)
            demand = np.random.uniform(5, 15)

            data.append({
                "lat": lat,
                "lon": lon,
                "demand_kw": demand,
                "zone_id": "Z01"
            })

        return pd.DataFrame(data)

    def _create_sample_hourly_load(self, zone_id: Optional[str] = None) -> pd.DataFrame:
        """Create sample hourly load data."""
        hours = list(range(24))
        zones = [zone_id] if zone_id else ["Z01", "Z02", "Z03", "Z04", "Z05", "Z06"]

        data = []
        for zone in zones:
            for hour in hours:
                base = 100.0
                if 7 <= hour <= 10:
                    base += 200.0
                elif 18 <= hour <= 21:
                    base += 300.0

                data.append({
                    "hour": hour,
                    "load_kw": base + np.random.normal(0, 20)
                })

        return pd.DataFrame(data)

    def run(self, host: str = "0.0.0.0", port: int = 8001):
        """Run the API server."""
        self.logger.info(f"Starting Optimization API on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create and run API
    api = OptimizationAPI()
    api.run()