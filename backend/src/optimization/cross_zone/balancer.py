"""
Cross-Zone Load Balancer
Production-grade implementation for multi-zone load balancing with spill-over detection and optimization.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

from ortools.linear_solver import pywraplp

try:
    from models.config import ModelConfig, get_config
except ImportError:
    ModelConfig = None
    def get_config(config_path=None):
        return None


@dataclass
class ZoneConnection:
    """Represents a connection between two zones."""

    from_zone_id: str
    to_zone_id: str
    distance_km: float
    transfer_capacity_mw: float
    transfer_efficiency: float = 0.90
    current_transfer_mw: float = 0.0


@dataclass
class LoadTransfer:
    """Represents a load transfer between zones."""

    transfer_id: str
    from_zone_id: str
    to_zone_id: str
    transfer_kw: float
    transfer_efficiency: float
    reason: str
    timestamp: datetime


@dataclass
class ZoneLoadState:
    """Represents the current load state of a zone."""

    zone_id: str
    current_load_kw: float
    capacity_kw: float
    headroom_kw: float
    headroom_percent: float
    status: str  # SAFE, CAUTION, CRITICAL
    can_receive: bool
    can_send: bool


class CrossZoneBalancer:
    """Production-grade cross-zone load balancer."""

    def __init__(
        self,
        config: Optional[ModelConfig] = None,
        max_transfer_distance_km: float = 10.0,
        min_headroom_for_transfer: float = 0.20,
        spill_over_threshold: float = 0.85
    ):
        self.config = config or get_config()

        self.max_transfer_distance_km = max_transfer_distance_km
        self.min_headroom_for_transfer = min_headroom_for_transfer
        self.spill_over_threshold = spill_over_threshold

        self.logger = logging.getLogger(__name__)

        # Zone connections
        self.connections: Dict[Tuple[str, str], ZoneConnection] = {}

        # Zone load states
        self.zone_states: Dict[str, ZoneLoadState] = {}

        # Transfer history
        self.transfer_history: List[LoadTransfer] = []

    def add_connection(self, connection: ZoneConnection) -> None:
        """
        Add a zone connection.

        Args:
            connection: Zone connection to add
        """
        key = (connection.from_zone_id, connection.to_zone_id)
        self.connections[key] = connection

        # Add reverse connection
        reverse_key = (connection.to_zone_id, connection.from_zone_id)
        self.connections[reverse_key] = ZoneConnection(
            from_zone_id=connection.to_zone_id,
            to_zone_id=connection.from_zone_id,
            distance_km=connection.distance_km,
            transfer_capacity_mw=connection.transfer_capacity_mw,
            transfer_efficiency=connection.transfer_efficiency
        )

        self.logger.info(f"Added connection: {connection.from_zone_id} <-> {connection.to_zone_id}")

    def update_zone_states(
        self,
        zone_loads: Dict[str, float],
        zone_capacities: Dict[str, float]
    ) -> None:
        """
        Update zone load states.

        Args:
            zone_loads: Dictionary of zone_id -> current load in kW
            zone_capacities: Dictionary of zone_id -> capacity in kW
        """
        for zone_id in zone_loads.keys():
            load = zone_loads[zone_id]
            capacity = zone_capacities.get(zone_id, 0)

            headroom = capacity - load
            headroom_percent = headroom / capacity if capacity > 0 else 0

            # Determine status
            if load / capacity >= 0.85:
                status = "CRITICAL"
            elif load / capacity >= 0.70:
                status = "CAUTION"
            else:
                status = "SAFE"

            # Determine transfer capability
            can_receive = headroom_percent >= self.min_headroom_for_transfer
            can_send = status in ["CAUTION", "CRITICAL"]

            self.zone_states[zone_id] = ZoneLoadState(
                zone_id=zone_id,
                current_load_kw=load,
                capacity_kw=capacity,
                headroom_kw=headroom,
                headroom_percent=headroom_percent,
                status=status,
                can_receive=can_receive,
                can_send=can_send
            )

        self.logger.info(f"Updated states for {len(self.zone_states)} zones")

    def detect_spill_over(self) -> List[str]:
        """
        Detect zones that need spill-over.

        Returns:
            List of zone IDs that need spill-over
        """
        spill_over_zones = []

        for zone_id, state in self.zone_states.items():
            if state.status == "CRITICAL" and state.can_send:
                spill_over_zones.append(zone_id)

        if spill_over_zones:
            self.logger.info(f"Detected spill-over zones: {spill_over_zones}")

        return spill_over_zones

    def find_receiving_zones(self, from_zone_id: str) -> List[Tuple[str, float]]:
        """
        Find zones that can receive load from a given zone.

        Args:
            from_zone_id: Zone ID to send from

        Returns:
            List of (zone_id, available_capacity) tuples
        """
        receiving_zones = []

        for (from_zone, to_zone), connection in self.connections.items():
            if from_zone == from_zone_id:
                to_state = self.zone_states.get(to_zone)

                if to_state and to_state.can_receive:
                    # Calculate available capacity considering transfer efficiency
                    available_capacity = (
                        to_state.headroom_kw * connection.transfer_efficiency
                    )

                    # Limit by transfer capacity
                    transfer_limit = connection.transfer_capacity_mw * 1000
                    available_capacity = min(available_capacity, transfer_limit)

                    if available_capacity > 0:
                        receiving_zones.append((to_zone, available_capacity))

        # Sort by available capacity (descending)
        receiving_zones.sort(key=lambda x: x[1], reverse=True)

        return receiving_zones

    def optimize_transfers(
        self,
        spill_over_zones: List[str],
        max_transfers: int = 10
    ) -> List[LoadTransfer]:
        """
        Optimize load transfers between zones.

        Args:
            spill_over_zones: List of zones that need to send load
            max_transfers: Maximum number of transfers

        Returns:
            List of load transfers
        """
        if not spill_over_zones:
            return []

        self.logger.info(f"Optimizing transfers for {len(spill_over_zones)} zones...")

        # Create solver
        solver = pywraplp.Solver.CreateSolver('GLOP')
        if not solver:
            raise RuntimeError("Could not create solver")

        # Decision variables: transfer[from_zone, to_zone] = amount to transfer
        transfer_vars = {}

        for from_zone in spill_over_zones:
            receiving_zones = self.find_receiving_zones(from_zone)

            for to_zone, capacity in receiving_zones:
                transfer_vars[(from_zone, to_zone)] = solver.NumVar(
                    0,
                    capacity,
                    f"transfer_{from_zone}_{to_zone}"
                )

        # Objective: Maximize total transfer
        objective = solver.Objective()

        for var in transfer_vars.values():
            objective.SetCoefficient(var, 1)

        objective.SetMaximization()

        # Constraint: Don't exceed available capacity in receiving zones
        for to_zone in self.zone_states.keys():
            if not self.zone_states[to_zone].can_receive:
                continue

            total_incoming = sum(
                transfer_vars.get((from_zone, to_zone), 0)
                for from_zone in spill_over_zones
            )

            max_incoming = self.zone_states[to_zone].headroom_kw
            solver.Add(total_incoming <= max_incoming)

        # Solve
        status = solver.Solve()

        transfers = []

        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            for (from_zone, to_zone), var in transfer_vars.items():
                amount = var.solution_value()

                if amount > 1.0:  # Minimum transfer of 1 kW
                    connection = self.connections.get((from_zone, to_zone))

                    transfer = LoadTransfer(
                        transfer_id=f"T{len(self.transfer_history) + 1:04d}",
                        from_zone_id=from_zone,
                        to_zone_id=to_zone,
                        transfer_kw=amount,
                        transfer_efficiency=connection.transfer_efficiency if connection else 0.9,
                        reason="SPILL_OVER_OPTIMIZATION",
                        timestamp=datetime.now()
                    )

                    transfers.append(transfer)

            self.logger.info(f"Optimized {len(transfers)} transfers")

        return transfers

    def apply_transfers(
        self,
        transfers: List[LoadTransfer]
    ) -> Dict[str, float]:
        """
        Apply load transfers and update zone states.

        Args:
            transfers: List of load transfers

        Returns:
            Dictionary of zone_id -> load change
        """
        load_changes = {}

        for transfer in transfers:
            from_zone = transfer.from_zone_id
            to_zone = transfer.to_zone_id
            amount = transfer.transfer_kw

            # Update load changes
            load_changes[from_zone] = load_changes.get(from_zone, 0) - amount
            load_changes[to_zone] = load_changes.get(to_zone, 0) + amount

            # Add to history
            self.transfer_history.append(transfer)

        # Update zone states
        for zone_id, change in load_changes.items():
            if zone_id in self.zone_states:
                state = self.zone_states[zone_id]
                state.current_load_kw += change
                state.headroom_kw = state.capacity_kw - state.current_load_kw
                state.headroom_percent = state.headroom_kw / state.capacity_kw if state.capacity_kw > 0 else 0

                # Update status
                if state.current_load_kw / state.capacity_kw >= 0.85:
                    state.status = "CRITICAL"
                elif state.current_load_kw / state.capacity_kw >= 0.70:
                    state.status = "CAUTION"
                else:
                    state.status = "SAFE"

                # Update transfer capability
                state.can_receive = state.headroom_percent >= self.min_headroom_for_transfer
                state.can_send = state.status in ["CAUTION", "CRITICAL"]

        self.logger.info(f"Applied {len(transfers)} transfers")

        return load_changes

    def balance_load(
        self,
        zone_loads: Dict[str, float],
        zone_capacities: Dict[str, float]
    ) -> Tuple[Dict[str, float], List[LoadTransfer]]:
        """
        Balance load across all zones.

        Args:
            zone_loads: Dictionary of zone_id -> current load
            zone_capacities: Dictionary of zone_id -> capacity

        Returns:
            Tuple of (updated loads, transfers)
        """
        self.logger.info("Starting cross-zone load balancing...")

        # Update zone states
        self.update_zone_states(zone_loads, zone_capacities)

        # Detect spill-over zones
        spill_over_zones = self.detect_spill_over()

        if not spill_over_zones:
            self.logger.info("No spill-over detected. No balancing needed.")
            return zone_loads.copy(), []

        # Optimize transfers
        transfers = self.optimize_transfers(spill_over_zones)

        if not transfers:
            self.logger.warning("No feasible transfers found.")
            return zone_loads.copy(), []

        # Apply transfers
        load_changes = self.apply_transfers(transfers)

        # Calculate updated loads
        updated_loads = zone_loads.copy()
        for zone_id, change in load_changes.items():
            updated_loads[zone_id] += change

        # Calculate metrics
        total_transferred = sum(t.transfer_kw for t in transfers)
        zones_affected = len(set([t.from_zone_id for t in transfers] + [t.to_zone_id for t in transfers]))

        self.logger.info(
            f"Balancing complete: {total_transferred:.2f} kW transferred "
            f"across {zones_affected} zones"
        )

        return updated_loads, transfers

    def get_transfer_summary(self) -> Dict[str, any]:
        """
        Get summary of transfer operations.

        Returns:
            Dictionary with transfer summary
        """
        if not self.transfer_history:
            return {
                "total_transfers": 0,
                "total_kw_transferred": 0,
                "zones_involved": []
            }

        total_kw = sum(t.transfer_kw for t in self.transfer_history)
        zones_involved = list(set(
            [t.from_zone_id for t in self.transfer_history] +
            [t.to_zone_id for t in self.transfer_history]
        ))

        # Recent transfers (last 24 hours)
        recent_time = datetime.now() - timedelta(hours=24)
        recent_transfers = [
            t for t in self.transfer_history
            if t.timestamp >= recent_time
        ]

        return {
            "total_transfers": len(self.transfer_history),
            "total_kw_transferred": total_kw,
            "zones_involved": zones_involved,
            "recent_transfers_24h": len(recent_transfers),
            "recent_kw_transferred_24h": sum(t.transfer_kw for t in recent_transfers)
        }

    def get_zone_connectivity_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Get zone connectivity matrix.

        Returns:
            Dictionary of from_zone -> {to_zone: capacity}
        """
        matrix = {}

        for (from_zone, to_zone), connection in self.connections.items():
            if from_zone not in matrix:
                matrix[from_zone] = {}

            matrix[from_zone][to_zone] = connection.transfer_capacity_mw * 1000  # Convert to kW

        return matrix


if __name__ == "__main__":
    # Example usage
    balancer = CrossZoneBalancer()

    # Add connections
    balancer.add_connection(ZoneConnection(
        from_zone_id="Z01",
        to_zone_id="Z05",
        distance_km=8.5,
        transfer_capacity_mw=5.0
    ))

    balancer.add_connection(ZoneConnection(
        from_zone_id="Z01",
        to_zone_id="Z06",
        distance_km=5.2,
        transfer_capacity_mw=8.0
    ))

    balancer.add_connection(ZoneConnection(
        from_zone_id="Z02",
        to_zone_id="Z03",
        distance_km=4.8,
        transfer_capacity_mw=6.0
    ))

    # Set up zone loads and capacities
    zone_loads = {
        "Z01": 45000.0,  # 45 MW - Critical
        "Z02": 28000.0,  # 28 MW - Safe
        "Z03": 24500.0,  # 24.5 MW - Safe
        "Z05": 35000.0,  # 35 MW - Safe
        "Z06": 30000.0   # 30 MW - Safe
    }

    zone_capacities = {
        "Z01": 50000.0,  # 50 MW
        "Z02": 40000.0,  # 40 MW
        "Z03": 35000.0,  # 35 MW
        "Z05": 45000.0,  # 45 MW
        "Z06": 38000.0   # 38 MW
    }

    # Balance load
    updated_loads, transfers = balancer.balance_load(zone_loads, zone_capacities)

    print("Load Balancing Results:")
    print(f"  Transfers: {len(transfers)}")
    for transfer in transfers:
        print(f"    {transfer.from_zone_id} -> {transfer.to_zone_id}: {transfer.transfer_kw:.2f} kW")

    print("\nUpdated Zone Loads:")
    for zone_id, load in updated_loads.items():
        capacity = zone_capacities[zone_id]
        utilization = load / capacity * 100
        print(f"  {zone_id}: {load:.2f} kW ({utilization:.1f}% of {capacity:.0f} kW)")

    print("\nTransfer Summary:")
    summary = balancer.get_transfer_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
