"""
CrossZoneCoordinator Agent
Production-grade implementation for multi-zone load balancing and coordination.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd


class ZoneState(Enum):
    """Zone state classification."""

    SAFE = "safe"
    CAUTION = "caution"
    CRITICAL = "critical"
    OVERLOADED = "overloaded"


@dataclass
class ZoneLoadInfo:
    """Load information for a zone."""

    zone_id: str
    current_load_kw: float
    capacity_kw: float
    headroom_kw: float
    headroom_percent: float
    state: ZoneState
    forecast_peak_kw: float
    ev_load_kw: float
    base_load_kw: float


@dataclass
class ZoneConnection:
    """Connection between two zones."""

    from_zone_id: str
    to_zone_id: str
    transfer_capacity_kw: float
    transfer_efficiency: float
    distance_km: float
    reason: str = ""


@dataclass
class TransferRequest:
    """Request to transfer load between zones."""

    request_id: str
    from_zone_id: str
    to_zone_id: str
    transfer_kw: float
    session_ids: List[str]
    reason: str
    timestamp: datetime
    priority: int = 1  # 1=low, 2=medium, 3=high


@dataclass
class TransferResult:
    """Result of a load transfer."""

    request_id: str
    success: bool
    transferred_kw: float
    actual_efficiency: float
    new_from_zone_load: float
    new_to_zone_load: float
    error: Optional[str] = None


class CrossZoneCoordinator:
    """Production-grade cross-zone coordinator for load balancing."""

    def __init__(
        self,
        max_transfer_distance_km: float = 10.0,
        min_transfer_efficiency: float = 0.85,
        max_concurrent_transfers: int = 5
    ):
        self.max_transfer_distance_km = max_transfer_distance_km
        self.min_transfer_efficiency = min_transfer_efficiency
        self.max_concurrent_transfers = max_concurrent_transfers

        self.logger = logging.getLogger(__name__)

        # Zone connections
        self.connections: Dict[Tuple[str, str], ZoneConnection] = {}

        # Active transfers
        self.active_transfers: Dict[str, TransferRequest] = {}

        # Transfer history
        self.transfer_history: List[TransferResult] = []

        # Zone states cache
        self.zone_states: Dict[str, ZoneLoadInfo] = {}

    def add_connection(self, connection: ZoneConnection) -> None:
        """
        Add a connection between zones.

        Args:
            connection: Zone connection to add
        """
        key = (connection.from_zone_id, connection.to_zone_id)
        self.connections[key] = connection

        # Add reverse connection if not exists
        reverse_key = (connection.to_zone_id, connection.from_zone_id)
        if reverse_key not in self.connections:
            self.connections[reverse_key] = ZoneConnection(
                from_zone_id=connection.to_zone_id,
                to_zone_id=connection.from_zone_id,
                transfer_capacity_kw=connection.transfer_capacity_kw,
                transfer_efficiency=connection.transfer_efficiency,
                distance_km=connection.distance_km,
                reason="Reverse connection"
            )

        self.logger.info(f"Added connection: {connection.from_zone_id} <-> {connection.to_zone_id}")

    def get_zone_connectivity_matrix(self) -> Dict[Tuple[str, str], float]:
        """
        Get zone connectivity matrix.

        Returns:
            Dictionary mapping (from_zone, to_zone) to transfer capacity
        """
        return {
            key: conn.transfer_capacity_kw
            for key, conn in self.connections.items()
        }

    def classify_zone_state(self, load_info: ZoneLoadInfo) -> ZoneState:
        """
        Classify zone state based on load.

        Args:
            load_info: Zone load information

        Returns:
            Zone state classification
        """
        if load_info.headroom_percent < 0:
            return ZoneState.OVERLOADED
        elif load_info.headroom_percent < 0.15:
            return ZoneState.CRITICAL
        elif load_info.headroom_percent < 0.30:
            return ZoneState.CAUTION
        else:
            return ZoneState.SAFE

    def update_zone_states(
        self,
        zone_loads: Dict[str, float],
        zone_capacities: Dict[str, float],
        forecast_peaks: Optional[Dict[str, float]] = None
    ) -> Dict[str, ZoneLoadInfo]:
        """
        Update zone states based on current loads.

        Args:
            zone_loads: Current loads by zone
            zone_capacities: Capacities by zone
            forecast_peaks: Optional forecast peaks

        Returns:
            Dictionary of zone load information
        """
        forecast_peaks = forecast_peaks or {}

        for zone_id, load_kw in zone_loads.items():
            capacity_kw = zone_capacities.get(zone_id, 50000.0)
            headroom_kw = capacity_kw - load_kw
            headroom_percent = headroom_kw / capacity_kw if capacity_kw > 0 else 0

            # Estimate EV load (simplified)
            ev_load_kw = load_kw * 0.3  # Assume 30% is EV load
            base_load_kw = load_kw - ev_load_kw

            load_info = ZoneLoadInfo(
                zone_id=zone_id,
                current_load_kw=load_kw,
                capacity_kw=capacity_kw,
                headroom_kw=headroom_kw,
                headroom_percent=headroom_percent,
                state=self.classify_zone_state(
                    ZoneLoadInfo(
                        zone_id=zone_id,
                        current_load_kw=load_kw,
                        capacity_kw=capacity_kw,
                        headroom_kw=headroom_kw,
                        headroom_percent=headroom_percent,
                        state=ZoneState.SAFE,
                        forecast_peak_kw=forecast_peaks.get(zone_id, load_kw),
                        ev_load_kw=ev_load_kw,
                        base_load_kw=base_load_kw
                    )
                ),
                forecast_peak_kw=forecast_peaks.get(zone_id, load_kw),
                ev_load_kw=ev_load_kw,
                base_load_kw=base_load_kw
            )

            self.zone_states[zone_id] = load_info

        return self.zone_states

    def identify_overloaded_zones(self) -> List[str]:
        """
        Identify zones that need load relief.

        Returns:
            List of overloaded zone IDs
        """
        overloaded = [
            zone_id
            for zone_id, info in self.zone_states.items()
            if info.state in [ZoneState.CRITICAL, ZoneState.OVERLOADED]
        ]

        return overloaded

    def identify_receiving_zones(
        self,
        min_headroom_percent: float = 0.30
    ) -> List[str]:
        """
        Identify zones that can receive additional load.

        Args:
            min_headroom_percent: Minimum headroom percentage

        Returns:
            List of receiving zone IDs
        """
        receiving = [
            zone_id
            for zone_id, info in self.zone_states.items()
            if info.headroom_percent >= min_headroom_percent
        ]

        return receiving

    def find_transfer_opportunities(
        self,
        overloaded_zones: List[str],
        receiving_zones: List[str]
    ) -> List[Tuple[str, str, float]]:
        """
        Find transfer opportunities between zones.

        Args:
            overloaded_zones: List of overloaded zones
            receiving_zones: List of receiving zones

        Returns:
            List of (from_zone, to_zone, transfer_capacity) tuples
        """
        opportunities = []

        for from_zone in overloaded_zones:
            for to_zone in receiving_zones:
                key = (from_zone, to_zone)
                if key in self.connections:
                    conn = self.connections[key]

                    # Check efficiency threshold
                    if conn.transfer_efficiency >= self.min_transfer_efficiency:
                        opportunities.append((from_zone, to_zone, conn.transfer_capacity_kw))

        # Sort by transfer capacity (descending)
        opportunities.sort(key=lambda x: x[2], reverse=True)

        return opportunities

    def calculate_optimal_transfer(
        self,
        from_zone: str,
        to_zone: str,
        available_sessions: List[Dict]
    ) -> float:
        """
        Calculate optimal transfer amount.

        Args:
            from_zone: Source zone
            to_zone: Destination zone
            available_sessions: Available charging sessions

        Returns:
            Optimal transfer amount in kW
        """
        if from_zone not in self.zone_states or to_zone not in self.zone_states:
            return 0.0

        from_info = self.zone_states[from_zone]
        to_info = self.zone_states[to_zone]

        # Get connection capacity
        key = (from_zone, to_zone)
        if key not in self.connections:
            return 0.0

        conn = self.connections[key]

        # Calculate how much to transfer
        # Target: bring from_zone to CAUTION state (30% headroom)
        target_headroom_percent = 0.30
        target_load = from_info.capacity_kw * (1 - target_headroom_percent)
        excess_load = from_info.current_load_kw - target_load

        # Check receiving zone capacity
        receiving_capacity = to_info.headroom_kw

        # Use minimum of excess, receiving capacity, and connection capacity
        transfer_amount = min(
            excess_load,
            receiving_capacity,
            conn.transfer_capacity_kw
        )

        # Ensure positive
        transfer_amount = max(0.0, transfer_amount)

        return transfer_amount

    def create_transfer_request(
        self,
        from_zone: str,
        to_zone: str,
        transfer_kw: float,
        session_ids: List[str],
        reason: str,
        priority: int = 1
    ) -> TransferRequest:
        """
        Create a transfer request.

        Args:
            from_zone: Source zone
            to_zone: Destination zone
            transfer_kw: Transfer amount in kW
            session_ids: Session IDs to transfer
            reason: Reason for transfer
            priority: Transfer priority

        Returns:
            Transfer request
        """
        request_id = f"TR_{datetime.now().strftime('%Y%m%d%H%M%S')}_{from_zone}_{to_zone}"

        request = TransferRequest(
            request_id=request_id,
            from_zone_id=from_zone,
            to_zone_id=to_zone,
            transfer_kw=transfer_kw,
            session_ids=session_ids,
            reason=reason,
            timestamp=datetime.now(),
            priority=priority
        )

        return request

    def execute_transfer(
        self,
        request: TransferRequest
    ) -> TransferResult:
        """
        Execute a transfer request.

        Args:
            request: Transfer request to execute

        Returns:
            Transfer result
        """
        # Check connection exists
        key = (request.from_zone_id, request.to_zone_id)
        if key not in self.connections:
            return TransferResult(
                request_id=request.request_id,
                success=False,
                transferred_kw=0.0,
                actual_efficiency=0.0,
                new_from_zone_load=0.0,
                new_to_zone_load=0.0,
                error="No connection between zones"
            )

        conn = self.connections[key]

        # Check capacity
        if request.transfer_kw > conn.transfer_capacity_kw:
            return TransferResult(
                request_id=request.request_id,
                success=False,
                transferred_kw=0.0,
                actual_efficiency=0.0,
                new_from_zone_load=0.0,
                new_to_zone_load=0.0,
                error=f"Transfer amount exceeds capacity ({conn.transfer_capacity_kw} kW)"
            )

        # Check concurrent transfer limit
        active_count = sum(
            1 for tr in self.active_transfers.values()
            if tr.from_zone_id == request.from_zone_id or tr.to_zone_id == request.to_zone_id
        )
        if active_count >= self.max_concurrent_transfers:
            return TransferResult(
                request_id=request.request_id,
                success=False,
                transferred_kw=0.0,
                actual_efficiency=0.0,
                new_from_zone_load=0.0,
                new_to_zone_load=0.0,
                error="Maximum concurrent transfers exceeded"
            )

        # Execute transfer
        transferred_kw = request.transfer_kw * conn.transfer_efficiency

        # Update zone states
        if request.from_zone_id in self.zone_states:
            from_info = self.zone_states[request.from_zone_id]
            from_info.current_load_kw -= request.transfer_kw
            from_info.headroom_kw += request.transfer_kw
            from_info.headroom_percent = from_info.headroom_kw / from_info.capacity_kw
            from_info.state = self.classify_zone_state(from_info)

        if request.to_zone_id in self.zone_states:
            to_info = self.zone_states[request.to_zone_id]
            to_info.current_load_kw += transferred_kw
            to_info.headroom_kw -= transferred_kw
            to_info.headroom_percent = to_info.headroom_kw / to_info.capacity_kw
            to_info.state = self.classify_zone_state(to_info)

        # Record result
        result = TransferResult(
            request_id=request.request_id,
            success=True,
            transferred_kw=transferred_kw,
            actual_efficiency=conn.transfer_efficiency,
            new_from_zone_load=self.zone_states.get(request.from_zone_id, ZoneLoadInfo(
                request.from_zone_id, 0, 0, 0, 0, ZoneState.SAFE, 0, 0, 0
            )).current_load_kw,
            new_to_zone_load=self.zone_states.get(request.to_zone_id, ZoneLoadInfo(
                request.to_zone_id, 0, 0, 0, 0, ZoneState.SAFE, 0, 0, 0
            )).current_load_kw
        )

        self.transfer_history.append(result)

        self.logger.info(
            f"Transfer executed: {request.from_zone_id} -> {request.to_zone_id}, "
            f"{transferred_kw:.2f} kW (efficiency: {conn.transfer_efficiency:.2%})"
        )

        return result

    def balance_load(
        self,
        zone_loads: Dict[str, float],
        zone_capacities: Dict[str, float],
        forecast_peaks: Optional[Dict[str, float]] = None
    ) -> Tuple[Dict[str, float], List[TransferResult]]:
        """
        Balance load across zones.

        Args:
            zone_loads: Current loads by zone
            zone_capacities: Capacities by zone
            forecast_peaks: Optional forecast peaks

        Returns:
            Tuple of (updated loads, transfer results)
        """
        self.logger.info("Starting cross-zone load balancing...")

        # Update zone states
        self.update_zone_states(zone_loads, zone_capacities, forecast_peaks)

        # Identify overloaded and receiving zones
        overloaded = self.identify_overloaded_zones()
        receiving = self.identify_receiving_zones()

        self.logger.info(f"Overloaded zones: {overloaded}")
        self.logger.info(f"Receiving zones: {receiving}")

        if not overloaded or not receiving:
            self.logger.info("No balancing needed")
            return zone_loads, []

        # Find transfer opportunities
        opportunities = self.find_transfer_opportunities(overloaded, receiving)

        if not opportunities:
            self.logger.info("No transfer opportunities found")
            return zone_loads, []

        # Execute transfers
        results = []
        for from_zone, to_zone, capacity in opportunities[:self.max_concurrent_transfers]:
            # Calculate optimal transfer
            transfer_kw = self.calculate_optimal_transfer(from_zone, to_zone, [])

            if transfer_kw > 0:
                request = self.create_transfer_request(
                    from_zone=from_zone,
                    to_zone=to_zone,
                    transfer_kw=transfer_kw,
                    session_ids=[],
                    reason=f"Load balancing: {from_zone} overloaded",
                    priority=2
                )

                result = self.execute_transfer(request)
                results.append(result)

        # Get updated loads
        updated_loads = {
            zone_id: info.current_load_kw
            for zone_id, info in self.zone_states.items()
        }

        self.logger.info(f"Load balancing complete. {len(results)} transfers executed")

        return updated_loads, results

    def get_transfer_summary(self) -> Dict[str, any]:
        """
        Get summary of transfers.

        Returns:
            Dictionary with transfer summary
        """
        if not self.transfer_history:
            return {
                "total_transfers": 0,
                "total_transferred_kw": 0.0,
                "avg_efficiency": 0.0,
                "success_rate": 0.0
            }

        total_transfers = len(self.transfer_history)
        successful = sum(1 for r in self.transfer_history if r.success)
        total_transferred_kw = sum(r.transferred_kw for r in self.transfer_history)
        avg_efficiency = np.mean([r.actual_efficiency for r in self.transfer_history])

        return {
            "total_transfers": total_transfers,
            "successful_transfers": successful,
            "total_transferred_kw": total_transferred_kw,
            "avg_efficiency": avg_efficiency,
            "success_rate": successful / total_transfers if total_transfers > 0 else 0.0
        }

    def get_zone_summary(self) -> Dict[str, Dict]:
        """
        Get summary of all zones.

        Returns:
            Dictionary mapping zone IDs to zone summaries
        """
        return {
            zone_id: {
                "state": info.state.value,
                "current_load_kw": info.current_load_kw,
                "capacity_kw": info.capacity_kw,
                "headroom_kw": info.headroom_kw,
                "headroom_percent": info.headroom_percent,
                "ev_load_kw": info.ev_load_kw,
                "base_load_kw": info.base_load_kw
            }
            for zone_id, info in self.zone_states.items()
        }


if __name__ == "__main__":
    # Example usage
    coordinator = CrossZoneCoordinator()

    # Add connections
    coordinator.add_connection(ZoneConnection(
        from_zone_id="Z01",
        to_zone_id="Z05",
        transfer_capacity_kw=8500.0,
        transfer_efficiency=0.95,
        distance_km=5.0,
        reason="Primary corridor"
    ))

    coordinator.add_connection(ZoneConnection(
        from_zone_id="Z01",
        to_zone_id="Z06",
        transfer_capacity_kw=5200.0,
        transfer_efficiency=0.92,
        distance_km=8.0,
        reason="Secondary corridor"
    ))

    # Simulate load imbalance
    zone_loads = {
        "Z01": 48000.0,  # Overloaded
        "Z02": 28000.0,
        "Z03": 24500.0,
        "Z04": 19500.0,
        "Z05": 31500.0,
        "Z06": 26600.0
    }

    zone_capacities = {
        "Z01": 50000.0,
        "Z02": 40000.0,
        "Z03": 35000.0,
        "Z04": 30000.0,
        "Z05": 45000.0,
        "Z06": 38000.0
    }

    # Balance load
    updated_loads, results = coordinator.balance_load(zone_loads, zone_capacities)

    print("Load Balancing Results:")
    print(f"  Updated loads: {updated_loads}")
    print(f"  Transfers executed: {len(results)}")

    for result in results:
        print(f"    {result.request_id}: {result.transferred_kw:.2f} kW transferred")

    # Get summary
    summary = coordinator.get_transfer_summary()
    print(f"\nTransfer Summary: {summary}")

    zone_summary = coordinator.get_zone_summary()
    print(f"\nZone Summary:")
    for zone_id, info in zone_summary.items():
        print(f"  {zone_id}: {info['state']} ({info['headroom_percent']:.1%} headroom)")
