"""
Agentic API
Production-grade FastAPI endpoints for agent-based decision support with plain-language outputs.
"""

import logging
import sys
import os

# Ensure the `src` directory is on sys.path so sibling packages
# (agents, models, db, etc.) are importable when this file is
# executed directly (e.g. `python backend/src/api/agents.py`).
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic BaseModel, Field
import uvicorn

# Create a simple config class for fallback
class SimpleConfig:
    def __init__(self):
        self.log_level = "INFO"
        self.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.device = "auto"
        self.num_workers = 4
        self.pin_memory = True

# Try imports
try:
    from models.config import ModelConfig, get_config
    from agents.agent_graph import AgentGraph, AgentState, AgentType
    from agents.grid_monitor import GridStateMonitor, ZoneStatus
    from agents.rag_pipeline import ChromaRAGPipeline, PlanningDecision
    from agents.outcome_tracker import OutcomeTracker, ShiftOutcome
    from optimization.vpp.scheduler import VPPScheduler, ChargingSession, ZoneConstraint
    from optimization.mcda.site_scorer import MCDAEngine, SiteCandidate
    from optimization.spatial.clustering import HDBSCANPipeline
    from optimization.cross_zone.balancer import CrossZoneBalancer, ZoneConnection
    from optimization.metrics import PeakLoadCalculator
except ImportError:
    # Fallback for direct execution
    ModelConfig = None
    def get_config(config_path=None):
        return None
    AgentGraph = None
    AgentState = None
    AgentType = None
    GridStateMonitor = None
    ZoneStatus = None
    ChromaRAGPipeline = None
    PlanningDecision = None
    OutcomeTracker = None
    ShiftOutcome = None
    VPPScheduler = None
    ChargingSession = None
    ZoneConstraint = None
    MCDAEngine = None
    SiteCandidate = None
    HDBSCANPipeline = None
    CrossZoneBalancer = None
    ZoneConnection = None
    PeakLoadCalculator = None


# Pydantic models for API requests/responses
class AgentRequest(BaseModel):
    """Request model for agent processing."""

    zone_id: str = Field(..., description="Zone ID")
    request_type: str = Field(..., description="Request type: forecast, schedule, site")
    input_data: Dict[str, Any] = Field(..., description="Input data for the request")


class AgentResponse(BaseModel):
    """Response model for agent processing."""

    request_id: str = Field(..., description="Request ID")
    zone_id: str = Field(..., description="Zone ID")
    request_type: str = Field(..., description="Request type")
    status: str = Field(..., description="Status: success, error")
    iterations: int = Field(..., description="Number of iterations")
    final_output: str = Field(..., description="Plain-language output")
    demand_forecast: Optional[Dict[str, Any]] = None
    schedule_result: Optional[Dict[str, Any]] = None
    site_recommendation: Optional[Dict[str, Any]] = None
    validation_results: List[Dict[str, any]] = Field(default_factory=list)
    explanation: Optional[str] = None
    timestamp: str = Field(..., description="Processing timestamp")


class ExplainabilityRequest(BaseModel):
    """Request model for explainability."""

    zone_id: str = Field(..., description="Zone ID")
    decision_type: str = Field(..., description="Decision type")
    context: Dict[str, Any] = Field(..., description="Decision context")
    include_similar: bool = Field(True, description="Include similar past decisions")


class ExplainabilityResponse(BaseModel):
    """Response model for explainability."""

    explanation: str = Field(..., description="Plain-language explanation")
    similar_decisions: List[Dict[str, any]] = Field(default_factory=list)
    confidence: str = Field(..., description="Confidence level")
    context_summary: Dict[str, any] = Field(default_factory=dict)


class AgenticAPI:
    """Production-grade Agentic API for decision support."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_config() or SimpleConfig()

        self.app = FastAPI(
            title="UrjaYukti AI Agentic API",
            description="AI-based decision support with plain-language outputs",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )

        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.agent_graph = AgentGraph() if AgentGraph else None
        self.grid_monitor = GridStateMonitor() if GridStateMonitor else None
        self.rag_pipeline = ChromaRAGPipeline() if ChromaRAGPipeline else None
        self.outcome_tracker = OutcomeTracker() if OutcomeTracker else None

        # Initialize optimization components
        self.vpp_scheduler = VPPScheduler(self.config) if VPPScheduler else None
        self.mcda_engine = MCDAEngine() if MCDAEngine else None
        self.clustering_pipeline = HDBSCANPipeline() if HDBSCANPipeline else None
        self.cross_zone_balancer = CrossZoneBalancer(self.config) if CrossZoneBalancer else None
        self.peak_load_calculator = PeakLoadCalculator() if PeakLoadCalculator else None

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
                "name": "UrjaYukti AI Agentic API",
                "version": "1.0.0",
                "status": "operational",
                "endpoints": {
                    "agent": "/api/agent",
                    "explainability": "/api/explainability",
                    "grid_state": "/api/grid_state",
                    "outcomes": "/api/outcomes",
                    "compliance": "/api/compliance"
                }
            }

        @self.app.post("/api/agent", response_model=AgentResponse)
        async def process_agent_request(request: AgentRequest):
            """
            Process a request through the agent graph.

            - **zone_id**: Zone ID
            - **request_type**: Type of request (forecast, schedule, site)
            - **input_data**: Input data for the request
            """
            if not self.agent_graph:
                raise HTTPException(
                    status_code=503,
                    detail="Agent graph not initialized"
                )

            try:
                # Process request through agent graph
                result = self.agent_graph.process_request(
                    zone_id=request.zone_id,
                    request_type=request.request_type,
                    input_data=request.input_data
                )

                # Generate explanation using RAG
                explanation = self._generate_explanation(
                    zone_id=request.zone_id,
                    request_type=request.request_type,
                    result=result
                )

                response = AgentResponse(
                    request_id=f"{request.zone_id}_{request_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    zone_id=request.zone_id,
                    request_type=request.request_type,
                    status="success" if result["status"] == "success" else "error",
                    iterations=result.get("iterations", 0),
                    final_output=result.get("final_output", ""),
                    demand_forecast=result.get("demand_forecast"),
                    schedule_result=result.get("schedule_result"),
                    site_recommendation=result.get("site_recommendation"),
                    validation_results=result.get("validation_results", []),
                    explanation=explanation
                )

                return response

            except Exception as e:
                self.logger.error(f"Error processing agent request: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/explainability", response_model=ExplainabilityResponse)
        async def get_explainability(request: ExplainabilityRequest):
            """
            Get explainability for a decision using RAG.

            - **zone_id**: Zone ID
            - **decision_type**: Decision type
            - **context**: Decision context
            - **include_similar**: Whether to include similar past decisions
            """
            if not self.rag_pipeline:
                raise HTTPException(
                    status_code=503,
                    detail="RAG pipeline not initialized"
                )

            try:
                # Create planning decision from context
                decision = PlanningDecision(
                    decision_id=f"D_{request.zone_id}_{request.decision_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    timestamp=datetime.now(),
                    zone_id=request.zone_id,
                    decision_type=request.decision_type,
                    context=request.context,
                    rationale="Generated from explainability request",
                    outcome="PENDING",
                    metrics={},
                    tags=[request.decision_type, request.zone_id]
                )

                # Add to RAG pipeline
                doc_id = self.rag_pipeline.add_decision(decision)

                # Query similar decisions
                similar = self.rag_pipeline.query_decisions(
                    query=f"{request.decision_type} {request.zone_id}",
                    zone_id=request.zone_id,
                    decision_type=request.decision_type,
                    n_results=3 if request.include_similar else 0
                )

                # Generate explanation
                explanation = self.rag_pipeline.generate_explanation(
                    decision,
                    include_similar=request.include_similar
                )

                # Get context summary
                context_summary = self.rag_pipeline.get_decision_context(
                    request.zone_id,
                    request.decision_type
                )

                # Get confidence
                confidence = "HIGH" if context_summary.get("status") == "available" else "MEDIUM"

                response = ExplainabilityResponse(
                    explanation=explanation,
                    similar_decisions=similar,
                    confidence=confidence,
                    context_summary=context_summary
                )

                return response

            except Exception as e:
                self.logger.error(f"Error getting explainability: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/grid_state")
        async def get_grid_state(
            zone_id: Optional[str] = Query(None, description="Zone ID filter"),
            hours_back: int = Query(24, ge=1, le=168, description="Hours to look back")
        ):
            """
            Get current grid state for zones.

            - **zone_id**: Optional zone ID filter
            - **hours_back**: Hours to look back
            """
            if not self.grid_monitor:
                raise HTTPException(
                    status_code=503,
                    detail="Grid monitor not initialized"
                )

            try:
                # Get zone status
                if zone_id:
                    zone_status = self.grid_monitor.get_zone_status(zone_id)
                    if zone_status:
                        return {
                            "zone_id": zone_id,
                            "status": zone_status.status.value,
                            "total_load_kw": zone_status.total_load_kw,
                            "ev_load_kw": zone_status.ev_load_kw,
                            "headroom_percent": zone_status.headroom_percent,
                            "capacity_kw": zone_status.capacity_kw,
                            "feeder_count": zone_status.feeder_count,
                            "critical_feeders": zone_status.critical_feeders,
                            "caution_feeders": zone_status.caution_feeders,
                            "safe_feeders": zone_status.safe_feeders,
                            "timestamp": zone_status.timestamp.isoformat()
                        }

                # Get all zone statuses
                all_statuses = self.grid_monitor.get_all_zone_statuses()

                # Get alerts
                alerts = []
                if zone_id:
                    alerts = self.grid_monitor.check_alert_conditions(zone_id=zone_id)
                else:
                    # Get critical zones
                    critical_zones = self.grid_monitor.get_critical_zones()
                    for zid in critical_zones:
                        zone_alerts = self.grid_monitor.check_alert_conditions(zid)
                        alerts.extend(zone_alerts)

                # Get load trends
                trends = {}
                if zone_id:
                    trends[zone_id] = self.grid_monitor.get_load_trend(zone_id, hours_back)
                else:
                    for zid in all_statuses.keys():
                        trends[zid] = self.grid_monitor.get_load_trend(zid, hours_back)

                return {
                    "timestamp": datetime.now().isoformat(),
                    "zone_id": zone_id,
                    "all_zones": list(all_statuses.keys()),
                    "alerts": alerts,
                    "trends": trends
                }

            except Exception as e:
                self.logger.error(f"Error getting grid state: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/outcomes")
        async def get_outcomes(
            zone_id: Optional[str] = Query(None, description="Zone ID filter"),
            archetype_id: Optional[str] = Query(None, description="Archetype ID filter"),
            hours_back: int = Query(24, ge=1, le=168, description="Hours to look back")
        ):
            """
            Get shift outcome statistics.

            - **zone_id**: Optional zone ID filter
            - **archetype_id**: Optional archetype ID filter
            - **hours_back**: Hours to look back
            """
            if not self.outcome_tracker:
                raise HTTPException(
                    status_code=503,
                    detail="Outcome tracker not initialized"
                )

            try:
                # Get zone stats
                if zone_id:
                    stats = self.outcome_tracker.get_zone_compliance_stats(zone_id, hours_back)
                else:
                    stats = {"status": "no_data"}

                # Get archetype stats
                if archetype_id:
                    arch_stats = self.outcome_tracker.get_archetype_compliance_stats(archetype_id, hours_back)
                else:
                    arch_stats = {"status": "no_data"}

                # Get global stats
                global_stats = self.outcome_tracker.get_global_stats()

                return {
                    "timestamp": datetime.now().isoformat(),
                    "zone_id": zone_id,
                    "archetype_id": archetype_id,
                    "hours_back": hours_back,
                    "zone_stats": stats,
                    "archetype_stats": arch_stats,
                    "global_stats": global_stats
                }

            except Exception as e:
                self.logger.error(f"Error getting outcomes: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/compliance")
        async def get_compliance(
            user_id: Optional[str] = Query(None, description="User ID filter"),
            limit: int = Query(50, ge=1, le=100, description="Maximum records to return")
        ):
            """
            Get compliance history for a user.

            - **user_id**: Optional user ID filter
            - **limit**: Maximum records to return
            """
            if not self.outcome_tracker:
                raise HTTPException(
                    status_code=503,
                    detail="Outcome tracker not initialized"
                )

            try:
                if user_id:
                    history = self.outcome_tracker.get_user_compliance_history(user_id, limit)
                    return {
                        "user_id": user_id,
                        "history": [
                            {
                                "timestamp": h[0].isoformat(),
                                "compliance_probability": h[1],
                                "outcome": h[2].value
                            }
                            for h in history
                        ]
                    }
                else:
                    # Get global stats
                    stats = self.outcome_tracker.get_global_stats()
                    return stats

            except Exception as e:
                self.logger.error(f"Error getting compliance: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _generate_explanation(
        self,
        zone_id: str,
        request_type: str,
        result: Dict[str, any]
    ) -> str:
        """Generate explanation for agent result."""
        explanation_parts = []

        explanation_parts.append(f"Zone: {zone_id}")
        explanation_parts.append(f"Request Type: {request_type}")
        explanation_parts.append(f"Status: {result['status']}")

        # Add forecast information
        if result.get("demand_forecast"):
            forecast = result["demand_forecast"]
            explanation_parts.append(f"Demand Forecast: {forecast.get('confidence', 'UNKNOWN')}")

        # Add schedule information
        if result.get("schedule_result"):
            schedule = result["schedule_result"]
            sessions = schedule.get("sessions", [])
            explanation_parts.append(f"Scheduled Sessions: {len(sessions)}")

        # Add site recommendation
        if result.get("site_recommendation"):
            site = result["site_recommendation"]
            explanation_parts.append(f"Top Site: {site.get('name', 'N/A')}")

        # Add validation results
        if result.get("validation_results"):
            validations = result["validation_results"]
            violations = sum(len(v.get("violations", [])) for v in validations)
            explanation_parts.append(f"Constraint Violations: {violations}")

        # Add final output
        if result.get("final_output"):
            explanation_parts.append(f"Output: {result['final_output']}")

        return "\n".join(explanation_parts)

    def _initialize_constraints(self):
        """Initialize default zone constraints."""
        if not self.vpp_scheduler:
            return

        constraints = [
            ZoneConstraint("Z01", 50.0, 42.5, 7.5),
            ZoneConstraint("Z02", 40.0, 28.0, 12.0),
            ZoneConstraint("Z03", 35.0, 24.5, 10.5),
            ZoneConstraint("Z04", 30.0, 19.5, 10.5),
            ZoneConstraint("Z05", 45.0, 31.5, 13.5),
            ZoneConstraint("Z06", 38.0, 26.6, 11.4)
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


if __name__ == "__main__":
    # Example usage
    api = AgenticAPI()

    print("Agentic API initialized successfully")
    print(f"Agent graph available: {api.agent_graph is not None}")
    print(f"Grid monitor available: {api.grid_monitor is not None}")
    print(f"RAG pipeline available: {api.rag_pipeline is not None}")
    print(f"Outcome tracker available: {api.outcome_tracker is not None}")

    # Start server
    print("\nStarting Agentic API on port 8002...")
    # api.run(host="0.0.0.0", port=8002)
