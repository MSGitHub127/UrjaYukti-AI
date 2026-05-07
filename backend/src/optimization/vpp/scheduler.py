"""
OR-Tools VPP (Virtual Power Plant) Scheduler
Production-grade implementation for EV charging load optimization with grid constraints.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
import pandas as pd

from ortools.linear_solver import pywraplp
from ortools.sat.python import cp_model

try:
    from models.config import ModelConfig, get_config
except ImportError:
    # Fallback for direct execution
    ModelConfig = None
    def get_config(config_path=None):
        return None


@dataclass
class ChargingSession:
    """Represents a single EV charging session."""

    session_id: str
    user_id: str
    zone_id: str
    archetype_id: str
    preferred_start_hour: int
    preferred_end_hour: int
    energy_kwh: float
    power_kw: float
    flexibility_hours: int
    compliance_probability: float
    incentive_eligible: bool


@dataclass
class ScheduleResult:
    """Result of scheduling optimization."""

    session_id: str
    zone_id: str
    original_start_hour: int
    scheduled_start_hour: int
    shift_hours: float
    energy_kwh: float
    power_kw: float
    compliance_probability: float
    incentive_amount: float


@dataclass
class ZoneConstraint:
    """Grid constraint for a zone."""

    zone_id: str
    transformer_capacity_mw: float
    current_load_mw: float
    headroom_mw: float
    n_minus_1_required: bool = True
    min_headroom_percent: float = 0.30  # 30% headroom required


class VPPScheduler:
    """Production-grade VPP scheduler for EV charging optimization."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_config()

        self.logger = logging.getLogger(__name__)

        # Optimization parameters
        self.horizon_hours = 24  # 24-hour optimization window
        self.time_resolution_hours = 1  # 1-hour resolution

        # Grid constraints
        self.zone_constraints: Dict[str, ZoneConstraint] = {}

        # Incentive parameters
        self.incentive_rate_per_kwh = 2.0  # ₹/kWh for off-peak shift

        # Target metrics
        self.target_pli = 0.85  # Peak Load Index target
        self.target_plr = 0.15  # Peak Load Reduction target

    def set_zone_constraints(self, constraints: List[ZoneConstraint]) -> None:
        """
        Set grid constraints for zones.

        Args:
            constraints: List of zone constraints
        """
        for constraint in constraints:
            self.zone_constraints[constraint.zone_id] = constraint

        self.logger.info(f"Set constraints for {len(constraints)} zones")

    def optimize_schedule(
        self,
        sessions: List[ChargingSession],
        forecast_demand: pd.DataFrame,
        use_compliance: bool = True
    ) -> Tuple[List[ScheduleResult], Dict[str, float]]:
        """
        Optimize charging schedule using linear programming.

        Args:
            sessions: List of charging sessions to schedule
            forecast_demand: Forecasted demand by zone and hour
            use_compliance: Whether to consider compliance probability

        Returns:
            Tuple of (scheduled sessions, optimization metrics)
        """
        self.logger.info(f"Optimizing schedule for {len(sessions)} sessions...")

        # Create solver
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            # Fallback to GLOP if SCIP not available
            solver = pywraplp.Solver.CreateSolver('GLOP')
            if not solver:
                raise RuntimeError("Could not create solver")

        # Decision variables: x[session_id, hour] = 1 if session charges at hour
        x = {}
        for session in sessions:
            for hour in range(self.horizon_hours):
                x[(session.session_id, hour)] = solver.BoolVar(f"x_{session.session_id}_{hour}")

        # Load variables: load[zone_id, hour] = total load at zone and hour
        load = {}
        for zone_id in self.zone_constraints.keys():
            for hour in range(self.horizon_hours):
                load[(zone_id, hour)] = solver.NumVar(
                    0,
                    solver.infinity(),
                    f"load_{zone_id}_{hour}"
                )

        # Peak load variable
        peak_load = solver.NumVar(0, solver.infinity(), "peak_load")

        # Constraint: Each session charges exactly once
        for session in sessions:
            session_hours = range(
                max(0, session.preferred_start_hour - session.flexibility_hours),
                min(self.horizon_hours, session.preferred_end_hour + session.flexibility_hours)
            )

            solver.Add(
                sum(x[(session.session_id, hour)] for hour in session_hours) == 1,
                f"one_charge_{session.session_id}"
            )

        # Constraint: Calculate load at each zone and hour
        for zone_id in self.zone_constraints.keys():
            for hour in range(self.horizon_hours):
                # Base load from forecast
                base_load = self._get_forecast_load(forecast_demand, zone_id, hour)

                # Add EV charging load
                ev_load = sum(
                    x[(session.session_id, hour)] * session.power_kw
                    for session in sessions
                    if session.zone_id == zone_id
                )

                solver.Add(
                    load[(zone_id, hour)] == base_load + ev_load,
                    f"load_calc_{zone_id}_{hour}"
                )

        # Constraint: Peak load definition
        for zone_id in self.zone_constraints.keys():
            for hour in range(self.horizon_hours):
                solver.Add(load[(zone_id, hour)] <= peak_load)

        # Constraint: Grid headroom
        for zone_id, constraint in self.zone_constraints.items():
            max_load = constraint.transformer_capacity_mw * 1000 * (1 - constraint.min_headroom_percent)

            for hour in range(self.horizon_hours):
                solver.Add(
                    load[(zone_id, hour)] <= max_load,
                    f"headroom_{zone_id}_{hour}"
                )

        # Objective: Minimize peak load and maximize user satisfaction
        objective = solver.Objective()

        # Minimize peak load (primary objective)
        objective.SetCoefficient(peak_load, 1000)

        # Maximize user satisfaction (secondary objective)
        for session in sessions:
            for hour in range(self.horizon_hours):
                # Calculate satisfaction score
                satisfaction = self._calculate_satisfaction(session, hour)

                if use_compliance:
                    # Weight by compliance probability
                    weight = satisfaction * session.compliance_probability
                else:
                    weight = satisfaction

                objective.SetCoefficient(x[(session.session_id, hour)], -weight)

        # Solve
        status = solver.Solve()

        if status != pywraplp.Solver.OPTIMAL and status != pywraplp.Solver.FEASIBLE:
            self.logger.warning(f"Solver status: {status}")
            # Return feasible solution if available
            if status == pywraplp.Solver.INFEASIBLE:
                raise RuntimeError("No feasible solution found")

        # Extract results
        scheduled_sessions = []
        for session in sessions:
            for hour in range(self.horizon_hours):
                if x[(session.session_id, hour)].solution_value() > 0.5:
                    shift_hours = hour - session.preferred_start_hour

                    # Calculate incentive
                    incentive_amount = 0.0
                    if session.incentive_eligible and shift_hours > 0:
                        incentive_amount = self.incentive_rate_per_kwh * session.energy_kwh

                    scheduled_sessions.append(ScheduleResult(
                        session_id=session.session_id,
                        zone_id=session.zone_id,
                        original_start_hour=session.preferred_start_hour,
                        scheduled_start_hour=hour,
                        shift_hours=shift_hours,
                        energy_kwh=session.energy_kwh,
                        power_kw=session.power_kw,
                        compliance_probability=session.compliance_probability,
                        incentive_amount=incentive_amount
                    ))
                    break

        # Calculate metrics
        metrics = self._calculate_metrics(scheduled_sessions, forecast_demand, solver)

        self.logger.info(f"Optimization complete. Scheduled {len(scheduled_sessions)} sessions")
        self.logger.info(f"Metrics: {metrics}")

        return scheduled_sessions, metrics

    def _get_forecast_load(self, forecast_demand: pd.DataFrame, zone_id: str, hour: int) -> float:
        """Get forecasted base load for zone and hour."""
        if forecast_demand.empty:
            return 0.0

        # Filter by zone and hour
        zone_data = forecast_demand[forecast_demand["zone_id"] == zone_id]

        if zone_data.empty:
            return 0.0

        # Get load for specific hour
        hour_data = zone_data[zone_data["time"].dt.hour == hour]

        if hour_data.empty:
            return 0.0

        return hour_data["prediction"].mean()

    def _calculate_satisfaction(self, session: ChargingSession, hour: int) -> float:
        """Calculate user satisfaction score for a given hour."""
        # Distance from preferred time
        distance = abs(hour - session.preferred_start_hour)

        # Satisfaction decreases with distance
        if distance == 0:
            return 1.0
        elif distance <= session.flexibility_hours:
            return 1.0 - (distance / (session.flexibility_hours * 2))
        else:
            return max(0.0, 1.0 - distance / 10)

    def _calculate_metrics(
        self,
        scheduled_sessions: List[ScheduleResult],
        forecast_demand: pd.DataFrame,
        solver: pywraplp.Solver
    ) -> Dict[str, float]:
        """Calculate optimization metrics."""
        metrics = {}

        # Peak Load Index (PLI)
        peak_load = solver.variables()[0].solution_value()  # peak_load variable
        total_capacity = sum(
            c.transformer_capacity_mw * 1000
            for c in self.zone_constraints.values()
        )
        metrics["peak_load_kw"] = peak_load
        metrics["peak_load_index"] = peak_load / total_capacity if total_capacity > 0 else 0

        # Peak Load Reduction (PLR)
        # Calculate unmanaged peak load
        unmanaged_peak = self._calculate_unmanaged_peak(scheduled_sessions, forecast_demand)
        metrics["unmanaged_peak_kw"] = unmanaged_peak
        metrics["peak_load_reduction"] = (unmanaged_peak - peak_load) / unmanaged_peak if unmanaged_peak > 0 else 0

        # Shift statistics
        shifts = [s.shift_hours for s in scheduled_sessions]
        metrics["avg_shift_hours"] = np.mean(shifts) if shifts else 0
        metrics["max_shift_hours"] = max(shifts) if shifts else 0
        metrics["total_shifted_sessions"] = sum(1 for s in scheduled_sessions if s.shift_hours != 0)

        # Compliance statistics
        compliance_probs = [s.compliance_probability for s in scheduled_sessions]
        metrics["avg_compliance_probability"] = np.mean(compliance_probs) if compliance_probs else 0

        # Incentive statistics
        incentives = [s.incentive_amount for s in scheduled_sessions]
        metrics["total_incentive_amount"] = sum(incentives)
        metrics["avg_incentive_amount"] = np.mean(incentives) if incentives else 0

        # Constraint violations
        metrics["constraint_violations"] = 0  # OR-Tools ensures no violations

        # Target achievement
        metrics["pli_target_met"] = metrics["peak_load_index"] <= self.target_pli
        metrics["plr_target_met"] = metrics["peak_load_reduction"] >= self.target_plr

        return metrics

    def _calculate_unmanaged_peak(
        self,
        scheduled_sessions: List[ScheduleResult],
        forecast_demand: pd.DataFrame
    ) -> float:
        """Calculate peak load without optimization."""
        hourly_loads = {}

        for hour in range(self.horizon_hours):
            total_load = 0.0

            # Add base load
            for zone_id in self.zone_constraints.keys():
                total_load += self._get_forecast_load(forecast_demand, zone_id, hour)

            # Add unmanaged EV load (at preferred times)
            for session in scheduled_sessions:
                if session.original_start_hour == hour:
                    total_load += session.power_kw

            hourly_loads[hour] = total_load

        return max(hourly_loads.values()) if hourly_loads else 0.0

    def optimize_with_cross_zone(
        self,
        sessions: List[ChargingSession],
        forecast_demand: pd.DataFrame,
        zone_connectivity: Dict[Tuple[str, str], float],
        use_compliance: bool = True
    ) -> Tuple[List[ScheduleResult], Dict[str, float]]:
        """
        Optimize schedule with cross-zone load balancing.

        Args:
            sessions: List of charging sessions
            forecast_demand: Forecasted demand
            zone_connectivity: Zone connectivity with transfer capacities
            use_compliance: Whether to consider compliance

        Returns:
            Tuple of (scheduled sessions, metrics)
        """
        self.logger.info("Optimizing with cross-zone load balancing...")

        # First, run standard optimization
        scheduled_sessions, metrics = self.optimize_schedule(
            sessions, forecast_demand, use_compliance
        )

        # Check for zones exceeding constraints
        overloaded_zones = self._identify_overloaded_zones(scheduled_sessions, forecast_demand)

        if not overloaded_zones:
            return scheduled_sessions, metrics

        # Try to shift load to connected zones
        balanced_sessions = self._balance_cross_zone(
            scheduled_sessions,
            overloaded_zones,
            zone_connectivity,
            forecast_demand
        )

        # Recalculate metrics
        balanced_metrics = self._calculate_metrics(
            balanced_sessions,
            forecast_demand,
            None  # No solver available for recalculation
        )

        self.logger.info(f"Cross-zone balancing complete. {len(balanced_sessions)} sessions scheduled")

        return balanced_sessions, balanced_metrics

    def _identify_overloaded_zones(
        self,
        sessions: List[ScheduleResult],
        forecast_demand: pd.DataFrame
    ) -> List[str]:
        """Identify zones that exceed their constraints."""
        overloaded = []

        for zone_id, constraint in self.zone_constraints.items():
            max_load = constraint.transformer_capacity_mw * 1000 * (1 - constraint.min_headroom_percent)

            for hour in range(self.horizon_hours):
                total_load = self._get_forecast_load(forecast_demand, zone_id, hour)

                # Add scheduled EV load
                ev_load = sum(
                    s.power_kw for s in sessions
                    if s.zone_id == zone_id and s.scheduled_start_hour == hour
                )

                if total_load + ev_load > max_load:
                    overloaded.append(zone_id)
                    break

        return overloaded

    def _balance_cross_zone(
        self,
        sessions: List[ScheduleResult],
        overloaded_zones: List[str],
        zone_connectivity: Dict[Tuple[str, str], float],
        forecast_demand: pd.DataFrame
    ) -> List[ScheduleResult]:
        """Balance load across connected zones."""
        balanced = sessions.copy()

        for zone_id in overloaded_zones:
            # Find connected zones with headroom
            connected_zones = [
                (to_zone, capacity)
                for (from_zone, to_zone), capacity in zone_connectivity.items()
                if from_zone == zone_id and to_zone not in overloaded_zones
            ]

            if not connected_zones:
                continue

            # Find sessions that can be shifted
            shiftable = [
                s for s in balanced
                if s.zone_id == zone_id and s.shift_hours > 0
            ]

            if not shiftable:
                continue

            # Shift sessions to connected zones
            for session in shiftable[:5]:  # Limit to 5 sessions per zone
                # Find best connected zone
                best_zone = max(
                    connected_zones,
                    key=lambda z: z[1]  # Max transfer capacity
                )[0]

                # Update session zone
                for i, s in enumerate(balanced):
                    if s.session_id == session.session_id:
                        balanced[i] = ScheduleResult(
                            session_id=s.session_id,
                            zone_id=best_zone,
                            original_start_hour=s.original_start_hour,
                            scheduled_start_hour=s.scheduled_start_hour,
                            shift_hours=s.shift_hours,
                            energy_kwh=s.energy_kwh,
                            power_kw=s.power_kw,
                            compliance_probability=s.compliance_probability * 0.9,  # Slightly lower compliance
                            incentive_amount=s.incentive_amount
                        )
                        break

        return balanced


if __name__ == "__main__":
    # Example usage
    scheduler = VPPScheduler()

    # Set up zone constraints
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
        )
    ]

    scheduler.set_zone_constraints(constraints)

    # Create sample sessions
    sessions = [
        ChargingSession(
            session_id="S001",
            user_id="U001",
            zone_id="Z01",
            archetype_id="A01",
            preferred_start_hour=18,
            preferred_end_hour=20,
            energy_kwh=25.0,
            power_kw=7.2,
            flexibility_hours=2,
            compliance_probability=0.6,
            incentive_eligible=True
        ),
        ChargingSession(
            session_id="S002",
            user_id="U002",
            zone_id="Z01",
            archetype_id="A01",
            preferred_start_hour=19,
            preferred_end_hour=21,
            energy_kwh=30.0,
            power_kw=7.2,
            flexibility_hours=3,
            compliance_probability=0.5,
            incentive_eligible=True
        )
    ]

    # Create sample forecast
    forecast_data = pd.DataFrame({
        "time": pd.date_range(start=datetime.now(), periods=48, freq="h"),
        "zone_id": ["Z01"] * 24 + ["Z02"] * 24,
        "prediction": [100.0] * 24 + [80.0] * 24
    })

    # Optimize schedule
    scheduled, metrics = scheduler.optimize_schedule(sessions, forecast_data)

    print(f"Scheduled {len(scheduled)} sessions")
    print(f"Metrics: {metrics}")
