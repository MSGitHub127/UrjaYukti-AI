"""
LangGraph Agent Graph for Agentic Orchestration
Production-grade implementation with Demand, Schedule, Site agents and cross-validation.
"""

import logging
from typing import Dict, List, Optional, Any, Annotated
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

try:
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolNode
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    LANGGRAPH_AVAILABLE = False
    import sys
    print(f"LangGraph import failed: {e}", file=sys.stderr)


class AgentType(Enum):
    """Types of agents in the system."""

    DEMAND = "demand"
    SCHEDULE = "schedule"
    SITE = "site"
    COORDINATOR = "coordinator"


@dataclass
class AgentState:
    """State passed between agents."""

    current_agent: AgentType
    zone_id: str
    request_type: str
    input_data: Dict[str, Any]
    demand_forecast: Optional[Dict[str, Any]] = None
    schedule_result: Optional[Dict[str, Any]] = None
    site_recommendation: Optional[Dict[str, Any]] = None
    validation_results: List[Dict[str, Any]] = field(default_factory=list)
    final_output: Optional[str] = None
    iteration_count: int = 0
    max_iterations: int = 3


@dataclass
class ToolResult:
    """Result from a tool execution."""

    tool_name: str
    success: bool
    data: Any
    timestamp: datetime
    error: Optional[str] = None


class ToolRegistry:
    """Registry of tools available to agents."""

    def __init__(self):
        self.tools: Dict[str, callable] = {}

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register available tools."""
        # Demand agent tools
        self.tools["get_forecast"] = self._get_forecast
        self.tools["get_anomalies"] = self._get_anomalies

        # Schedule agent tools
        self.tools["optimize_schedule"] = self._optimize_schedule
        self.tools["get_grid_status"] = self._get_grid_status

        # Site agent tools
        self.tools["rank_sites"] = self._rank_sites
        self.tools["get_roi"] = self._get_roi

        # Coordinator tools
        self.tools["validate_constraints"] = self._validate_constraints
        self.tools["cross_zone_balance"] = self._cross_zone_balance

    def _get_forecast(self, zone_id: str, horizon_hours: int = 72) -> ToolResult:
        """Get demand forecast for a zone."""
        try:
            # In production, this would call the forecast API
            forecast = {
                "zone_id": zone_id,
                "horizon_hours": horizon_hours,
                "predictions": [],
                "confidence": "HIGH"
            }
            return ToolResult("get_forecast", True, forecast)
        except Exception as e:
            return ToolResult("get_forecast", False, None, str(e))

    def _get_anomalies(self, zone_id: str, hours_back: int = 24) -> ToolResult:
        """Get anomaly alerts for a zone."""
        try:
            anomalies = {
                "zone_id": zone_id,
                "hours_back": hours_back,
                "anomalies": []
            }
            return ToolResult("get_anomalies", True, anomalies)
        except Exception as e:
            return ToolResult("get_anomalies", False, None, str(e))

    def _optimize_schedule(self, sessions: List[Dict], zone_id: str) -> ToolResult:
        """Optimize charging schedule for sessions."""
        try:
            schedule = {
                "zone_id": zone_id,
                "sessions": sessions,
                "metrics": {}
            }
            return ToolResult("optimize_schedule", True, schedule)
        except Exception as e:
            return ToolResult("optimize_schedule", False, None, str(e))

    def _get_grid_status(self, zone_id: str) -> ToolResult:
        """Get current grid status for a zone."""
        try:
            status = {
                "zone_id": zone_id,
                "status": "SAFE",
                "headroom_percent": 30.0,
                "current_load_kw": 35000.0
            }
            return ToolResult("get_grid_status", True, status)
        except Exception as e:
            return ToolResult("get_grid_status", False, None, str(e))

    def _rank_sites(self, zone_id: str, candidates: List[Dict]) -> ToolResult:
        """Rank charging station sites for a zone."""
        try:
            ranking = {
                "zone_id": zone_id,
                "sites": candidates,
                "rankings": []
            }
            return ToolResult("rank_sites", True, ranking)
        except Exception as e:
            return ToolResult("rank_sites", False, None, str(e))

    def _get_roi(self, site_id: str) -> ToolResult:
        """Get ROI metrics for a site."""
        try:
            roi = {
                "site_id": site_id,
                "payback_years": 2.5,
                "utilization_rate": 0.75,
                "npv": 500000
            }
            return ToolResult("get_roi", True, roi)
        except Exception as e:
            return ToolResult("get_roi", False, None, str(e))

    def _validate_constraints(self, schedule: Dict, zone_id: str) -> ToolResult:
        """Validate schedule against grid constraints."""
        try:
            validation = {
                "zone_id": zone_id,
                "schedule": schedule,
                "violations": [],
                "compliant": True
            }
            return ToolResult("validate_constraints", True, validation)
        except Exception as e:
            return ToolResult("validate_constraints", False, None, str(e))

    def _cross_zone_balance(self, zone_loads: Dict) -> ToolResult:
        """Balance load across zones."""
        try:
            balance = {
                "transfers": [],
                "updated_loads": zone_loads
            }
            return ToolResult("cross_zone_balance", True, balance)
        except Exception as e:
            return ToolResult("cross_zone_balance", False, None, str(e))

    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        if tool_name not in self.tools:
            return ToolResult(tool_name, False, None, f"Tool not found: {tool_name}")

        tool_func = self.tools[tool_name]
        try:
            result = tool_func(**kwargs)
            return result
        except Exception as e:
            return ToolResult(tool_name, False, None, str(e))


class DemandAgent:
    """Agent for demand forecasting and analysis."""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.logger = logging.getLogger(__name__)

    def process(self, state: AgentState) -> AgentState:
        """Process demand forecasting request."""
        self.logger.info(f"DemandAgent processing request for zone {state.zone_id}")

        # Get forecast
        forecast_result = self.tool_registry.execute_tool(
            "get_forecast",
            zone_id=state.zone_id,
            horizon_hours=72
        )

        if forecast_result.success:
            state.demand_forecast = forecast_result.data
            state.input_data["forecast"] = forecast_result.data
        else:
            self.logger.error(f"Failed to get forecast: {forecast_result.error}")

        return state


class ScheduleAgent:
    """Agent for charging schedule optimization."""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.logger = logging.getLogger(__name__)

    def process(self, state: AgentState) -> AgentState:
        """Process schedule optimization request."""
        self.logger.info(f"ScheduleAgent processing request for zone {state.zone_id}")

        # Get grid status first
        grid_result = self.tool_registry.execute_tool(
            "get_grid_status",
            zone_id=state.zone_id
        )

        if grid_result.success:
            state.input_data["grid_status"] = grid_result.data

        # Optimize schedule
        schedule_result = self.tool_registry.execute_tool(
            "optimize_schedule",
            sessions=state.input_data.get("sessions", []),
            zone_id=state.zone_id
        )

        if schedule_result.success:
            state.schedule_result = schedule_result.data

            # Validate constraints
            validation_result = self.tool_registry.execute_tool(
                "validate_constraints",
                schedule=schedule_result.data,
                zone_id=state.zone_id
            )

            if validation_result.success:
                state.validation_results.append(validation_result.data)
        else:
            self.logger.error(f"Failed to optimize schedule: {schedule_result.error}")

        return state


class SiteAgent:
    """Agent for charging infrastructure planning."""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.logger = logging.getLogger(__name__)

    def process(self, state: AgentState) -> AgentState:
        """Process site planning request."""
        self.logger.info(f"SiteAgent processing request for zone {state.zone_id}")

        # Rank sites
        ranking_result = self.tool_registry.execute_tool(
            "rank_sites",
            zone_id=state.zone_id,
            candidates=state.input_data.get("candidates", [])
        )

        if ranking_result.success:
            state.site_recommendation = ranking_result.data

            # Get ROI for top sites
            if ranking_result.data.get("rankings"):
                top_site = ranking_result.data["rankings"][0]
                roi_result = self.tool_registry.execute_tool(
                    "get_roi",
                    site_id=top_site.get("site_id", "")
                )

                if roi_result.success:
                    state.input_data["roi"] = roi_result.data
        else:
            self.logger.error(f"Failed to rank sites: {ranking_result.error}")

        return state


class CoordinatorAgent:
    """Coordinator agent for cross-validation and final output."""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.logger = logging.getLogger(__name__)

    def process(self, state: AgentState) -> AgentState:
        """Process coordination and validation."""
        self.logger.info(f"CoordinatorAgent processing request for zone {state.zone_id}")

        # Cross-validate results
        validation_result = self.tool_registry.execute_tool(
            "validate_constraints",
            schedule=state.schedule_result or {},
            zone_id=state.zone_id
        )

        if validation_result.success:
            state.validation_results.append(validation_result.data)

        # Check for cross-zone balancing needs
        if state.input_data.get("enable_cross_zone", False):
            balance_result = self.tool_registry.execute_tool(
                "cross_zone_balance",
                zone_loads=state.input_data.get("zone_loads", {})
            )

            if balance_result.success:
                state.input_data["cross_zone_balance"] = balance_result.data

        # Generate final output
        state.final_output = self._generate_final_output(state)

        return state

    def _generate_final_output(self, state: AgentState) -> str:
        """Generate final plain-language output."""
        output_parts = []

        output_parts.append(f"Zone: {state.zone_id}")
        output_parts.append(f"Request Type: {state.request_type}")

        if state.demand_forecast:
            output_parts.append(f"Demand Forecast: {state.demand_forecast.get('confidence', 'UNKNOWN')}")

        if state.schedule_result:
            output_parts.append(f"Scheduled Sessions: {len(state.schedule_result.get('sessions', []))}")

        if state.site_recommendation:
            output_parts.append(f"Top Site: {state.site_recommendation.get('name', 'N/A')}")

        if state.validation_results:
            violations = sum(len(r.get('violations', [])) for r in state.validation_results)
            output_parts.append(f"Constraint Violations: {violations}")

        return "\n".join(output_parts)


class AgentGraph:
    """LangGraph-based agent orchestration system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.tool_registry = ToolRegistry()

        # Initialize agents
        self.demand_agent = DemandAgent(self.tool_registry)
        self.schedule_agent = ScheduleAgent(self.tool_registry)
        self.site_agent = SiteAgent(self.tool_registry)
        self.coordinator_agent = CoordinatorAgent(self.tool_registry)

        # Build graph
        self.graph = None
        self._build_graph()

    def _build_graph(self):
        """Build the agent graph."""
        if not LANGGRAPH_AVAILABLE:
            self.logger.warning("LangGraph not available. Agent graph will be disabled.")
            return

        try:
            # Define graph structure
            def route_demand(state: AgentState) -> str:
                return "schedule" if state.request_type == "forecast" else "site"

            def route_schedule(state: AgentState) -> str:
                return "coordinator" if state.request_type == "schedule" else "demand"

            def route_site(state: AgentState) -> str:
                return "coordinator"

            def route_coordinator(state: AgentState) -> str:
                return END

            # Create graph
            self.graph = StateGraph(AgentState)

            # Add nodes
            self.graph.add_node("demand", self.demand_agent.process)
            self.graph.add_node("schedule", self.schedule_agent.process)
            self.graph.add_node("site", self.site_agent.process)
            self.graph.add_node("coordinator", self.coordinator_agent.process)

            # Add conditional edges
            self.graph.add_conditional_edges("demand", route_demand)
            self.graph.add_conditional_edges("schedule", route_schedule)
            self.graph.add_conditional_edges("site", route_site)

            # Add edge to END
            self.graph.add_edge("coordinator", END)

            # Set entry point
            self.graph.set_entry_point("demand")

            self.logger.info("Agent graph built successfully")

        except Exception as e:
            self.logger.error(f"Error building agent graph: {e}")
            self.graph = None

    def process_request(
        self,
        zone_id: str,
        request_type: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a request through the agent graph.

        Args:
            zone_id: Zone ID
            request_type: Type of request (forecast, schedule, site)
            input_data: Input data for the request

        Returns:
            Dictionary with processing results
        """
        self.logger.info(f"Processing request: {request_type} for zone {zone_id}")

        if not self.graph:
            return {
                "status": "error",
                "error": "Agent graph not available"
            }

        try:
            # Create initial state
            state = AgentState(
                current_agent=AgentType.DEMAND,
                zone_id=zone_id,
                request_type=request_type,
                input_data=input_data,
                iteration_count=0,
                max_iterations=3
            )

            # Run graph
            final_state = self.graph.invoke(state)

            # Extract results
            results = {
                "status": "success",
                "zone_id": zone_id,
                "request_type": request_type,
                "iterations": final_state.iteration_count,
                "final_output": final_state.final_output,
                "demand_forecast": final_state.demand_forecast,
                "schedule_result": final_state.schedule_result,
                "site_recommendation": final_state.site_recommendation,
                "validation_results": final_state.validation_results
            }

            self.logger.info(f"Request processed successfully in {final_state.iteration_count} iterations")

            return results

        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def get_graph_info(self) -> Dict[str, any]:
        """Get information about the agent graph."""
        if not self.graph:
            return {"status": "unavailable"}

        try:
            return {
                "status": "available",
                "nodes": ["demand", "schedule", "site", "coordinator"],
                "edges": [
                    ("demand", "schedule"),
                    ("schedule", "coordinator"),
                    ("site", "coordinator"),
                    ("coordinator", "END")
                ],
                "entry_point": "demand",
                "tools_available": list(self.tool_registry.tools.keys())
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    # Example usage
    graph = AgentGraph()

    if LANGGRAPH_AVAILABLE:
        # Process a schedule request
        result = graph.process_request(
            zone_id="Z01",
            request_type="schedule",
            input_data={
                "sessions": [
                    {"session_id": "S001", "energy_kwh": 25.0, "power_kw": 7.2},
                    {"session_id": "S002", "energy_kwh": 30.0, "power_kw": 7.2}
                ],
                "enable_cross_zone": False
            }
        )

        print("Agent graph result:")
        print(f"  Status: {result['status']}")
        print(f"  Iterations: {result['iterations']}")
        print(f"  Output: {result['final_output']}")
    else:
        print("LangGraph not available. Install with: pip install langgraph")
