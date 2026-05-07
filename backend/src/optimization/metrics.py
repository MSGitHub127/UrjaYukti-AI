"""
Dual Peak Load Metrics
Production-grade implementation of Peak Load Index (PLI) and Peak Load Reduction (PLR) metrics.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


@dataclass
class PeakLoadMetrics:
    """Container for peak load metrics."""

    # Peak Load Index (PLI)
    pli: float  # max_hourly_load / transformer_capacity
    plr: float  # (PLI_unmanaged - PLI_optimized) / PLI_unmanaged

    # Targets
    pli_target: float = 0.85  # 85% capacity target
    plr_target: float = 0.15  # 15% reduction target

    # Additional metrics
    peak_hour: int = 0
    peak_load_kw: float = 0.0
    transformer_capacity_kw: float = 0.0
    unmanaged_peak_load_kw: float = 0.0
    unmanaged_pli: float = 0.0

    # Status
    pli_status: str = "SAFE"  # SAFE, CAUTION, CRITICAL
    plr_achieved: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "pli": self.pli,
            "pli_target": self.pli_target,
            "pli_status": self.pli_status,
            "plr": self.plr,
            "plr_target": self.plr_target,
            "plr_achieved": self.plr_achieved,
            "peak_hour": self.peak_hour,
            "peak_load_kw": self.peak_load_kw,
            "transformer_capacity_kw": self.transformer_capacity_kw,
            "unmanaged_peak_load_kw": self.unmanaged_peak_load_kw,
            "unmanaged_pli": self.unmanaged_pli
        }


class PeakLoadCalculator:
    """Production-grade calculator for dual peak load metrics."""

    def __init__(
        self,
        pli_target: float = 0.85,
        plr_target: float = 0.15,
        caution_threshold: float = 0.70,
        critical_threshold: float = 0.85
    ):
        self.pli_target = pli_target
        self.plr_target = plr_target
        self.caution_threshold = caution_threshold
        self.critical_threshold = critical_threshold

        self.logger = logging.getLogger(__name__)

    def calculate_metrics(
        self,
        hourly_load: pd.DataFrame,
        transformer_capacity_kw: float,
        unmanaged_hourly_load: Optional[pd.DataFrame] = None
    ) -> PeakLoadMetrics:
        """
        Calculate peak load metrics for a zone.

        Args:
            hourly_load: DataFrame with hour and load_kw columns
            transformer_capacity_kw: Transformer capacity in kW
            unmanaged_hourly_load: Optional unmanaged load for PLR calculation

        Returns:
            PeakLoadMetrics object
        """
        # Find peak hour and load
        peak_idx = hourly_load["load_kw"].idxmax()
        peak_hour = hourly_load.loc[peak_idx, "hour"]
        peak_load_kw = hourly_load.loc[peak_idx, "load_kw"]

        # Calculate PLI
        pli = peak_load_kw / transformer_capacity_kw if transformer_capacity_kw > 0 else 0

        # Determine PLI status
        if pli >= self.critical_threshold:
            pli_status = "CRITICAL"
        elif pli >= self.caution_threshold:
            pli_status = "CAUTION"
        else:
            pli_status = "SAFE"

        # Calculate PLR if unmanaged data provided
        plr = 0.0
        unmanaged_peak_load_kw = 0.0
        unmanaged_pli = 0.0
        plr_achieved = False

        if unmanaged_hourly_load is not None:
            unmanaged_peak_idx = unmanaged_hourly_load["load_kw"].idxmax()
            unmanaged_peak_load_kw = unmanaged_hourly_load.loc[unmanaged_peak_idx, "load_kw"]
            unmanaged_pli = unmanaged_peak_load_kw / transformer_capacity_kw if transformer_capacity_kw > 0 else 0

            # Calculate PLR
            if unmanaged_pli > 0:
                plr = (unmanaged_pli - pli) / unmanaged_pli
                plr_achieved = plr >= self.plr_target

        # Create metrics object
        metrics = PeakLoadMetrics(
            pli=pli,
            pli_target=self.pli_target,
            plr=plr,
            plr_target=self.plr_target,
            peak_hour=peak_hour,
            peak_load_kw=peak_load_kw,
            transformer_capacity_kw=transformer_capacity_kw,
            unmanaged_peak_load_kw=unmanaged_peak_load_kw,
            unmanaged_pli=unmanaged_pli,
            pli_status=pli_status,
            plr_achieved=plr_achieved
        )

        return metrics

    def calculate_zone_metrics(
        self,
        zone_data: Dict[str, pd.DataFrame],
        transformer_capacities: Dict[str, float],
        unmanaged_zone_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Dict[str, PeakLoadMetrics]:
        """
        Calculate metrics for multiple zones.

        Args:
            zone_data: Dictionary of zone_id -> hourly load DataFrame
            transformer_capacities: Dictionary of zone_id -> capacity in kW
            unmanaged_zone_data: Optional unmanaged data

        Returns:
            Dictionary of zone_id -> PeakLoadMetrics
        """
        results = {}

        for zone_id, load_df in zone_data.items():
            capacity = transformer_capacities.get(zone_id, 0)
            unmanaged_df = unmanaged_zone_data.get(zone_id) if unmanaged_zone_data else None

            metrics = self.calculate_metrics(load_df, capacity, unmanaged_df)
            results[zone_id] = metrics

        return results

    def calculate_aggregate_metrics(
        self,
        zone_metrics: Dict[str, PeakLoadMetrics]
    ) -> Dict[str, any]:
        """
        Calculate aggregate metrics across all zones.

        Args:
            zone_metrics: Dictionary of zone metrics

        Returns:
            Dictionary with aggregate metrics
        """
        if not zone_metrics:
            return {}

        # Calculate aggregate PLI
        total_peak_load = sum(m.peak_load_kw for m in zone_metrics.values())
        total_capacity = sum(m.transformer_capacity_kw for m in zone_metrics.values())
        aggregate_pli = total_peak_load / total_capacity if total_capacity > 0 else 0

        # Calculate aggregate PLR
        total_unmanaged_peak = sum(m.unmanaged_peak_load_kw for m in zone_metrics.values())
        aggregate_plr = (total_unmanaged_peak - total_peak_load) / total_unmanaged_peak if total_unmanaged_peak > 0 else 0

        # Count zones by status
        status_counts = {
            "SAFE": 0,
            "CAUTION": 0,
            "CRITICAL": 0
        }

        for metrics in zone_metrics.values():
            status_counts[metrics.pli_status] += 1

        # Check if targets achieved
        pli_target_met = aggregate_pli <= self.pli_target
        plr_target_met = aggregate_plr >= self.plr_target

        return {
            "aggregate_pli": aggregate_pli,
            "aggregate_pli_target": self.pli_target,
            "aggregate_pli_target_met": pli_target_met,
            "aggregate_plr": aggregate_plr,
            "aggregate_plr_target": self.plr_target,
            "aggregate_plr_target_met": plr_target_met,
            "total_peak_load_kw": total_peak_load,
            "total_capacity_kw": total_capacity,
            "total_unmanaged_peak_kw": total_unmanaged_peak,
            "zone_status_counts": status_counts,
            "num_zones": len(zone_metrics),
            "num_critical_zones": status_counts["CRITICAL"],
            "num_caution_zones": status_counts["CAUTION"]
        }

    def generate_hourly_profile(
        self,
        load_data: pd.DataFrame,
        capacity_kw: float
    ) -> pd.DataFrame:
        """
        Generate hourly load profile with PLI calculations.

        Args:
            load_data: DataFrame with hour and load_kw columns
            capacity_kw: Transformer capacity in kW

        Returns:
            DataFrame with hourly PLI values
        """
        profile = load_data.copy()

        # Calculate hourly PLI
        profile["pli"] = profile["load_kw"] / capacity_kw

        # Determine hourly status
        profile["status"] = profile["pli"].apply(
            lambda x: "CRITICAL" if x >= self.critical_threshold else
                     "CAUTION" if x >= self.caution_threshold else "SAFE"
        )

        # Calculate headroom
        profile["headroom_kw"] = capacity_kw - profile["load_kw"]
        profile["headroom_percent"] = (profile["headroom_kw"] / capacity_kw * 100)

        return profile

    def compare_scenarios(
        self,
        baseline_metrics: PeakLoadMetrics,
        optimized_metrics: PeakLoadMetrics
    ) -> Dict[str, any]:
        """
        Compare baseline and optimized scenarios.

        Args:
            baseline_metrics: Baseline (unmanaged) metrics
            optimized_metrics: Optimized metrics

        Returns:
            Dictionary with comparison results
        """
        # Calculate improvements
        pli_reduction = baseline_metrics.pli - optimized_metrics.pli
        pli_reduction_percent = (pli_reduction / baseline_metrics.pli * 100) if baseline_metrics.pli > 0 else 0

        load_reduction_kw = baseline_metrics.peak_load_kw - optimized_metrics.peak_load_kw
        load_reduction_percent = (load_reduction_kw / baseline_metrics.peak_load_kw * 100) if baseline_metrics.peak_load_kw > 0 else 0

        # Status change
        status_improved = self._compare_status(baseline_metrics.pli_status, optimized_metrics.pli_status)

        return {
            "baseline_pli": baseline_metrics.pli,
            "optimized_pli": optimized_metrics.pli,
            "pli_reduction": pli_reduction,
            "pli_reduction_percent": pli_reduction_percent,
            "baseline_peak_load_kw": baseline_metrics.peak_load_kw,
            "optimized_peak_load_kw": optimized_metrics.peak_load_kw,
            "load_reduction_kw": load_reduction_kw,
            "load_reduction_percent": load_reduction_percent,
            "baseline_status": baseline_metrics.pli_status,
            "optimized_status": optimized_metrics.pli_status,
            "status_improved": status_improved,
            "plr": optimized_metrics.plr,
            "plr_target_met": optimized_metrics.plr_achieved
        }

    def _compare_status(self, baseline_status: str, optimized_status: str) -> bool:
        """Compare status levels."""
        status_order = ["SAFE", "CAUTION", "CRITICAL"]
        baseline_idx = status_order.index(baseline_status)
        optimized_idx = status_order.index(optimized_status)

        return optimized_idx < baseline_idx

    def validate_constraints(
        self,
        metrics: PeakLoadMetrics,
        n_minus_1_required: bool = True,
        min_headroom_percent: float = 0.30
    ) -> Dict[str, bool]:
        """
        Validate grid constraints.

        Args:
            metrics: Peak load metrics
            n_minus_1_required: Whether N-1 contingency is required
            min_headroom_percent: Minimum headroom percentage

        Returns:
            Dictionary with constraint validation results
        """
        # Calculate headroom
        headroom_percent = 1.0 - metrics.pli

        # Validate constraints
        results = {
            "pli_target_met": metrics.pli <= self.pli_target,
            "headroom_sufficient": headroom_percent >= min_headroom_percent,
            "n_minus_1_compliant": True,  # Simplified for now
            "all_constraints_met": False
        }

        # N-1 contingency check
        if n_minus_1_required:
            # N-1 requires 50% headroom (simplified)
            results["n_minus_1_compliant"] = headroom_percent >= 0.50

        # Overall compliance
        results["all_constraints_met"] = all([
            results["pli_target_met"],
            results["headroom_sufficient"],
            results["n_minus_1_compliant"]
        ])

        return results


if __name__ == "__main__":
    # Example usage
    calculator = PeakLoadCalculator(
        pli_target=0.85,
        plr_target=0.15
    )

    # Create sample hourly load data
    hours = list(range(24))
    base_load = [100.0] * 24

    # Add peak at 7 PM (hour 19)
    base_load[19] = 450.0
    base_load[18] = 400.0
    base_load[20] = 380.0

    hourly_load = pd.DataFrame({
        "hour": hours,
        "load_kw": base_load
    })

    # Create unmanaged load (higher peak)
    unmanaged_load = hourly_load.copy()
    unmanaged_load.loc[19, "load_kw"] = 500.0

    # Calculate metrics
    metrics = calculator.calculate_metrics(
        hourly_load,
        transformer_capacity_kw=500.0,
        unmanaged_hourly_load=unmanaged_load
    )

    print("Peak Load Metrics:")
    print(f"  PLI: {metrics.pli:.2f} (target: {metrics.pli_target})")
    print(f"  PLI Status: {metrics.pli_status}")
    print(f"  PLR: {metrics.plr:.2%} (target: {metrics.plr_target:.0%})")
    print(f"  PLR Achieved: {metrics.plr_achieved}")
    print(f"  Peak Hour: {metrics.peak_hour}:00")
    print(f"  Peak Load: {metrics.peak_load_kw:.2f} kW")
    print(f"  Unmanaged Peak: {metrics.unmanaged_peak_load_kw:.2f} kW")

    # Validate constraints
    constraints = calculator.validate_constraints(metrics)
    print("\nConstraint Validation:")
    for constraint, passed in constraints.items():
        print(f"  {constraint}: {'✓' if passed else '✗'}")
