"""
Grid State Monitor
Production-grade implementation for real-time feeder load monitoring with zone classification.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np


class ZoneStatus(Enum):
    """Zone status classification."""

    SAFE = "SAFE"
    CAUTION = "CAUTION"
    CRITICAL = "CRITICAL"


@dataclass
class FeederLoad:
    """Represents load data for a feeder."""

    feeder_id: str
    zone_id: str
    timestamp: datetime
    total_load_kw: float
    ev_load_kw: float
    non_ev_load_kw: float
    headroom_percent: float
    capacity_kw: float
    status: ZoneStatus


@dataclass
class ZoneLoadState:
    """Represents the current load state of a zone."""

    zone_id: str
    timestamp: datetime
    total_load_kw: float
    ev_load_kw: float
    non_ev_load_kw: float
    capacity_kw: float
    headroom_percent: float
    status: ZoneStatus
    feeder_count: int
    critical_feeders: List[str]
    caution_feeders: List[str]
    safe_feeders: List[str]


class GridStateMonitor:
    """Production-grade grid state monitor for real-time monitoring."""

    def __init__(
        self,
        safe_threshold: float = 0.70,  # 70% load = SAFE
        caution_threshold: float = 0.85,  # 85% load = CAUTION
        critical_threshold: float = 0.95  # 95% load = CRITICAL
    ):
        self.safe_threshold = safe_threshold
        self.caution_threshold = caution_threshold
        self.critical_threshold = critical_threshold

        self.logger = logging.getLogger(__name__)

        # Current state
        self.zone_states: Dict[str, ZoneLoadState] = {}
        self.feeder_loads: List[FeederLoad] = []

        # Historical data
        self.historical_loads: Dict[str, List[float]] = {}

        # Alert thresholds
        self.alert_cooldown_minutes = 30
        self.last_alerts: Dict[str, datetime] = {}

    def update_feeder_load(
        self,
        feeder_id: str,
        zone_id: str,
        total_load_kw: float,
        ev_load_kw: float,
        capacity_kw: float,
        timestamp: Optional[datetime] = None
    ) -> ZoneStatus:
        """
        Update load data for a feeder and determine zone status.

        Args:
            feeder_id: Feeder ID
            zone_id: Zone ID
            total_load_kw: Total load in kW
            ev_load_kw: EV load in kW
            capacity_kw: Feeder capacity in kW
            timestamp: Timestamp of the reading

        Returns:
            Zone status
        """
        timestamp = timestamp or datetime.now()

        # Calculate headroom
        headroom_percent = ((capacity_kw - total_load_kw) / capacity_kw) * 100 if capacity_kw > 0 else 0

        # Determine status
        load_percent = total_load_kw / capacity_kw if capacity_kw > 0 else 0

        if load_percent >= self.critical_threshold:
            status = ZoneStatus.CRITICAL
        elif load_percent >= self.caution_threshold:
            status = ZoneStatus.CAUTION
        else:
            status = ZoneStatus.SAFE

        # Store feeder load
        feeder_load = FeederLoad(
            feeder_id=feeder_id,
            zone_id=zone_id,
            timestamp=timestamp,
            total_load_kw=total_load_kw,
            ev_load_kw=ev_load_kw,
            non_ev_load_kw=total_load_kw - ev_load_kw,
            headroom_percent=headroom_percent,
            capacity_kw=capacity_kw,
            status=status
        )

        self.feeder_loads.append(feeder_load)

        # Update zone state
        self._update_zone_state(zone_id, timestamp)

        return status

    def _update_zone_state(self, zone_id: str, timestamp: datetime):
        """Update zone state based on feeder data."""
        # Get all feeders for this zone
        zone_feeders = [f for f in self.feeder_loads if f.zone_id == zone_id]

        if not zone_feeders:
            return

        # Calculate aggregate zone metrics
        total_load = sum(f.total_load_kw for f in zone_feeders)
        ev_load = sum(f.ev_load_kw for f in zone_feeders)
        capacity = sum(f.capacity_kw for f in zone_feeders)

        # Calculate zone status based on worst feeder
        zone_status = ZoneStatus.SAFE
        for feeder in zone_feeders:
            if feeder.status == ZoneStatus.CRITICAL:
                zone_status = ZoneStatus.CRITICAL
                break
            elif feeder.status == ZoneStatus.CAUTION and zone_status != ZoneStatus.CRITICAL:
                zone_status = ZoneStatus.CAUTION

        # Count feeders by status
        critical_feeders = [f.feeder_id for f in zone_feeders if f.status == ZoneStatus.CRITICAL]
        caution_feeders = [f.feeder_id for f in zone_feeders if f.status == ZoneStatus.CAUTION]
        safe_feeders = [f.feeder_id for f in zone_feeders if f.status == ZoneStatus.SAFE]

        # Store zone state
        self.zone_states[zone_id] = ZoneLoadState(
            zone_id=zone_id,
            timestamp=timestamp,
            total_load_kw=total_load,
            ev_load_kw=ev_load,
            non_ev_load_kw=total_load - ev_load,
            capacity_kw=capacity,
            headroom_percent=((capacity - total_load) / capacity * 100) if capacity > 0 else 0,
            status=zone_status,
            feeder_count=len(zone_feeders),
            critical_feeders=critical_feeders,
            caution_feeders=caution_feeders,
            safe_feeders=safe_feeders
        )

        # Store historical data
        if zone_id not in self.historical_loads:
            self.historical_loads[zone_id] = []

        self.historical_loads[zone_id].append(total_load)

        # Keep only last 1000 data points
        if len(self.historical_loads[zone_id]) > 1000:
            self.historical_loads[zone_id] = self.historical_loads[zone_id][-1000:]

    def get_zone_status(self, zone_id: str) -> Optional[ZoneLoadState]:
        """
        Get current status for a zone.

        Args:
            zone_id: Zone ID

        Returns:
            Zone load state or None if zone not found
        """
        return self.zone_states.get(zone_id)

    def get_all_zone_statuses(self) -> Dict[str, ZoneLoadState]:
        """
        Get current status for all zones.

        Returns:
            Dictionary of zone_id -> ZoneLoadState
        """
        return self.zone_states.copy()

    def get_critical_zones(self) -> List[str]:
        """
        Get list of zones in CRITICAL status.

        Returns:
            List of zone IDs
        """
        return [
            zone_id for zone_id, state in self.zone_states.items()
            if state.status == ZoneStatus.CRITICAL
        ]

    def get_caution_zones(self) -> List[str]:
        """
        Get list of zones in CAUTION status.

        Returns:
            List of zone IDs
        """
        return [
            zone_id for zone_id, state in self.zone_states.items()
            if state.status == ZoneStatus.CAUTION
        ]

    def get_safe_zones(self) -> List[str]:
        """
        Get list of zones in SAFE status.

        Returns:
            List of zone IDs
        """
        return [
            zone_id for zone_id, state in self.zone_states.items()
            if state.status == ZoneStatus.SAFE
        ]

    def check_alert_conditions(
        self,
        zone_id: str,
        feeder_id: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        Check if alert conditions are met for a zone or feeder.

        Args:
            zone_id: Zone ID to check
            feeder_id: Optional feeder ID to check

        Returns:
            List of alerts
        """
        alerts = []

        # Check zone-level alerts
        zone_state = self.get_zone_status(zone_id)
        if zone_state:
            # Check for critical status
            if zone_state.status == ZoneStatus.CRITICAL:
                alerts.append({
                    "type": "ZONE_CRITICAL",
                    "severity": "CRITICAL",
                    "zone_id": zone_id,
                    "feeder_id": None,
                    "message": f"Zone {zone_id} in CRITICAL status. Load: {zone_state.total_load_kw:.2f} kW, Headroom: {zone_state.headroom_percent:.1f}%",
                    "timestamp": zone_state.timestamp.isoformat(),
                    "recommendation": "Immediate intervention required"
                })

            # Check for caution status
            elif zone_state.status == ZoneStatus.CAUTION:
                alerts.append({
                    "type": "ZONE_CAUTION",
                    "severity": "HIGH",
                    "zone_id": zone_id,
                    "feeder_id": None,
                    "message": f"Zone {zone_id} in CAUTION status. Load: {zone_state.total_load_kw:.2f} kW, Headroom: {zone_state.headroom_percent:.1f}%",
                    "timestamp": zone_state.timestamp.isoformat(),
                    "recommendation": "Monitor closely, consider load shifting"
                })

            # Check for high EV load percentage
            if zone_state.ev_load_kw > 0:
                ev_percentage = (zone_state.ev_load_kw / zone_state.total_load_kw * 100) if zone_state.total_load_kw > 0 else 0
                if ev_percentage > 50:
                    alerts.append({
                        "type": "HIGH_EV_LOAD",
                        "severity": "MEDIUM",
                        "zone_id": zone_id,
                        "feeder_id": None,
                        "message": f"High EV load: {ev_percentage:.1f}% of total load",
                        "timestamp": zone_state.timestamp.isoformat(),
                        "recommendation": "Consider shifting EV charging to off-peak hours"
                    })

        # Check feeder-level alerts if specified
        if feeder_id:
            feeder_loads = [f for f in self.feeder_loads if f.feeder_id == feeder_id]
            if feeder_loads:
                feeder = feeder_loads[0]

                # Check for critical feeder
                if feeder.status == ZoneStatus.CRITICAL:
                    alerts.append({
                        "type": "FEEDER_CRITICAL",
                        "severity": "CRITICAL",
                        "zone_id": zone_id,
                        "feeder_id": feeder_id,
                        "message": f"Feeder {feeder_id} in CRITICAL status. Load: {feeder.total_load_kw:.2f} kW",
                        "timestamp": feeder.timestamp.isoformat(),
                        "recommendation": "Immediate intervention required"
                    })

                # Check for high EV load on feeder
                if feeder.ev_load_kw > 0:
                    ev_percentage = (feeder.ev_load_kw / feeder.total_load_kw * 100) if feeder.total_load_kw > 0 else 0
                    if ev_percentage > 60:
                        alerts.append({
                            "type": "FEEDER_HIGH_EV",
                            "severity": "MEDIUM",
                            "zone_id": zone_id,
                            "feeder_id": feeder_id,
                            "message": f"High EV load on feeder: {ev_percentage:.1f}%",
                            "timestamp": feeder.timestamp.isoformat(),
                            "recommendation": "Consider shifting EV charging on this feeder"
                        })

        # Check cooldown for alerts
        current_time = datetime.now()
        filtered_alerts = []

        for alert in alerts:
            alert_key = f"{alert['type']}_{alert['zone_id']}_{alert.get('feeder_id', 'all')}"
            last_alert_time = self.last_alerts.get(alert_key)

            if last_alert_time is None:
                filtered_alerts.append(alert)
                self.last_alerts[alert_key] = current_time
            else:
                time_since_last = (current_time - last_alert_time).total_seconds() / 60
                if time_since_last >= self.alert_cooldown_minutes:
                    filtered_alerts.append(alert)
                    self.last_alerts[alert_key] = current_time

        return filtered_alerts

    def get_load_trend(
        self,
        zone_id: str,
        hours_back: int = 24
    ) -> Dict[str, any]:
        """
        Get load trend for a zone over time.

        Args:
            zone_id: Zone ID
            hours_back: Number of hours to look back

        Returns:
            Dictionary with trend information
        """
        if zone_id not in self.historical_loads:
            return {"status": "no_data"}

        historical = self.historical_loads[zone_id]

        if len(historical) < 2:
            return {"status": "insufficient_data"}

        # Calculate trend
        recent_loads = historical[-hours_back:]
        if len(recent_loads) < 2:
            recent_loads = historical

        # Calculate simple trend (positive/negative)
        if len(recent_loads) >= 2:
            first_half = np.mean(recent_loads[:len(recent_loads)//2])
            second_half = np.mean(recents[len(recent_loads)//2:])

            if second_half > first_half:
                trend = "increasing"
                trend_percent = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
            elif second_half < first_half:
                trend = "decreasing"
                trend_percent = ((first_half - second_half) / first_half * 100) if first_half > 0 else 0
            else:
                trend = "stable"
                trend_percent = 0.0
        else:
            trend = "stable"
            trend_percent = 0.0

        # Calculate volatility (standard deviation)
        if len(recent_loads) > 1:
            volatility = np.std(recent_loads)
            avg_load = np.mean(recent_loads)
            volatility_percent = (volatility / avg_load * 100) if avg_load > 0 else 0
        else:
            volatility = 0.0
            volatility_percent = 0.0

        return {
            "status": "available",
            "zone_id": zone_id,
            "hours_back": hours_back,
            "current_load": historical[-1] if historical else 0,
            "avg_load": np.mean(historical) if historical else 0,
            "max_load": max(historical) if historical else 0,
            "min_load": min(historical) if historical else 0,
            "trend": trend,
            "trend_percent": trend_percent,
            "volatility_percent": volatility_percent,
            "data_points": len(historical)
        }

    def get_zone_summary(self) -> Dict[str, any]:
        """
        Get summary of all zones.

        Returns:
            Dictionary with zone summary information
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_zones": len(self.zone_states),
            "zones": {}
        }

        for zone_id, state in self.zone_states.items():
            summary["zones"][zone_id] = {
                "status": state.status.value,
                "total_load_kw": state.total_load_kw,
                "ev_load_kw": state.ev_load_kw,
                "headroom_percent": state.headroom_percent,
                "capacity_kw": state.capacity_kw,
                "feeder_count": state.feeder_count,
                "critical_feeders_count": len(state.critical_feeders),
                "caution_feeders_count": len(state.caution_feeders),
                "safe_feeders_count": len(state.safe_feeders)
            }

        # Add alert counts
        summary["alert_counts"] = {
            "critical": len(self.get_critical_zones()),
            "caution": len(self.get_caution_zones()),
            "safe": len(self.get_safe_zones())
        }

        return summary

    def clear_old_data(self, hours_to_keep: int = 168) -> int:
        """
        Clear old data to prevent memory issues.

        Args:
            hours_to_keep: Number of hours of data to keep

        Returns:
            Number of records cleared
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)

        # Clear old feeder loads
        original_count = len(self.feeder_loads)
        self.feeder_loads = [
            f for f in self.feeder_loads
            if f.timestamp >= cutoff_time
        ]
        cleared_count = original_count - len(self.feeder_loads)

        # Clear old historical data
        for zone_id in list(self.historical_loads.keys()):
            if zone_id not in self.zone_states:
                # Zone no longer monitored, clear all data
                del self.historical_loads[zone_id]
            else:
                # Keep only recent data
                if zone_id in self.historical_loads:
                    cutoff_time = datetime.now() - timedelta(hours=hours_to_keep)
                    self.historical_loads[zone_id] = [
                        load for load in self.historical_loads[zone_id]
                        if load.get("timestamp") and
                        datetime.fromisoformat(load["timestamp"]) >= cutoff_time
                    ]

        self.logger.info(f"Cleared {cleared_count} old records, keeping {len(self.feeder_loads)} feeder loads")

        return cleared_count


if __name__ == "__main__":
    # Example usage
    monitor = GridStateMonitor()

    # Simulate some feeder updates
    print("Simulating grid state updates...")

    # Zone 1 - Whitefield (gradually increasing load)
    for hour in range(18, 22):
        base_load = 100 + (hour - 18) * 50
        ev_load = 50 + (hour - 18) * 30
        status = monitor.update_feeder_load(
            feeder_id="F01-Z01",
            zone_id="Z01",
            total_load_kw=base_load + ev_load,
            ev_load_kw=ev_load,
            capacity_kw=500.0
        )
        print(f"  Hour {hour}:00 - Zone Z01 status: {status.value}")

    # Zone 2 - HSR Layout (stable load)
    for hour in range(18, 22):
        base_load = 80
        ev_load = 20
        status = monitor.update_feeder_load(
            feeder_id="F01-Z02",
            zone_id="Z02",
            total_load_kw=base_load + ev_load,
            ev_load_kw=ev_load,
            capacity_kw=400.0
        )
        print(f"  Hour {hour}:00 - Zone Z02 status: {status.value}")

    # Get summary
    summary = monitor.get_zone_summary()
    print(f"\nZone Summary:")
    for zone_id, zone_info in summary["zones"].items():
        print(f"  {zone_id}: {zone_info['status']} - {zone_info['total_load_kw']:.2f} kW ({zone_info['headroom_percent']:.1f}% headroom)")

    # Get alerts
    print(f"\nAlert Counts:")
    for alert_type, count in summary["alert_counts"].items():
        print(f"  {alert_type}: {count}")

    # Get load trend for Zone 1
    trend = monitor.get_load_trend("Z01", hours_back=4)
    print(f"\nZone Z01 Load Trend (last 4 hours):")
    print(f"  Current: {trend['current_load']:.2f} kW")
    print(f"  Average: {trend['avg_load']:.2f} kW")
    print(f"  Trend: {trend['trend']} ({trend['trend_percent']:.1f}%)")
    print(f"  Volatility: {trend['volatility_percent']:.1f}%")
