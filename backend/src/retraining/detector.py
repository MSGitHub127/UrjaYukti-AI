"""
Evidently AI Drift Detection Module
Production-grade implementation for model drift detection and retraining triggers.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

try:
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset, RegressionPreset
    from evidently.ui.workspace import Workspace
    from evidently.pipeline.column_mapping import ColumnMapping
    EVIDENTLY_AVAILABLE = True
except ImportError:
    EVIDENTLY_AVAILABLE = False


class DriftSeverity(Enum):
    """Severity levels for drift detection."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftResult:
    """Result of drift detection."""

    timestamp: datetime
    model_name: str
    zone_id: str
    drift_detected: bool
    severity: DriftSeverity
    drift_score: float
    p_value: float
    features_drifted: List[str]
    recommendation: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class RetrainingTrigger:
    """Trigger for model retraining."""

    trigger_id: str
    model_name: str
    zone_id: str
    trigger_type: str  # DRIFT, PERFORMANCE, SCHEDULED
    severity: DriftSeverity
    reason: str
    timestamp: datetime
    priority: int  # 1=low, 2=medium, 3=high
    auto_retrain: bool = False


class DriftDetector:
    """Production-grade drift detector using Evidently AI."""

    def __init__(
        self,
        drift_threshold: float = 0.5,
        p_value_threshold: float = 0.05,
        min_samples: int = 100,
        window_size_days: int = 7
    ):
        self.drift_threshold = drift_threshold
        self.p_value_threshold = p_value_threshold
        self.min_samples = min_samples
        self.window_size_days = window_size_days

        self.logger = logging.getLogger(__name__)

        # Reference data (baseline)
        self.reference_data: Optional[pd.DataFrame] = None
        self.reference_timestamp: Optional[datetime] = None

        # Drift history
        self.drift_history: List[DriftResult] = []

        # Retraining triggers
        self.retraining_triggers: List[RetrainingTrigger] = []

        # Column mapping (only if Evidently available)
        self.column_mapping = ColumnMapping() if EVIDENTLY_AVAILABLE else None

    def set_reference_data(
        self,
        data: pd.DataFrame,
        target_col: str = "prediction",
        prediction_col: str = "forecast",
        numerical_features: Optional[List[str]] = None,
        categorical_features: Optional[List[str]] = None
    ) -> None:
        """
        Set reference (baseline) data for drift detection.

        Args:
            data: Reference dataset
            target_col: Target column name
            prediction_col: Prediction column name
            numerical_features: List of numerical feature columns
            categorical_features: List of categorical feature columns
        """
        if len(data) < self.min_samples:
            raise ValueError(f"Reference data must have at least {self.min_samples} samples")

        self.reference_data = data.copy()
        self.reference_timestamp = datetime.now()

        # Setup column mapping (only if Evidently available)
        if self.column_mapping is not None:
            self.column_mapping.target = target_col
            self.column_mapping.prediction = prediction_col

            if numerical_features:
                self.column_mapping.numerical_features = numerical_features
            if categorical_features:
                self.column_mapping.categorical_features = categorical_features

        self.logger.info(f"Reference data set with {len(data)} samples")

    def detect_drift(
        self,
        current_data: pd.DataFrame,
        model_name: str = "TFT",
        zone_id: str = "ALL"
    ) -> DriftResult:
        """
        Detect drift in current data compared to reference.

        Args:
            current_data: Current dataset to check
            model_name: Name of the model
            zone_id: Zone ID

        Returns:
            Drift detection result
        """
        if self.reference_data is None:
            raise ValueError("Reference data not set. Call set_reference_data() first.")

        if len(current_data) < self.min_samples:
            self.logger.warning(f"Current data has only {len(current_data)} samples")
            return DriftResult(
                timestamp=datetime.now(),
                model_name=model_name,
                zone_id=zone_id,
                drift_detected=False,
                severity=DriftSeverity.NONE,
                drift_score=0.0,
                p_value=1.0,
                features_drifted=[],
                recommendation="Insufficient data for drift detection",
                metadata={"sample_count": len(current_data)}
            )

        if not EVIDENTLY_AVAILABLE:
            # Fallback to simple statistical test
            return self._simple_drift_detection(current_data, model_name, zone_id)

        # Use Evidently AI for drift detection
        try:
            # Create drift report
            drift_report = Report(
                metrics=[DataDriftPreset()],
                timestamp=datetime.now()
            )

            # Run report
            drift_report.run(
                reference_data=self.reference_data,
                current_data=current_data,
                column_mapping=self.column_mapping
            )

            # Extract results
            results = drift_report.as_dict()

            # Get drift score
            drift_score = self._extract_drift_score(results)

            # Get p-value
            p_value = self._extract_p_value(results)

            # Get drifted features
            features_drifted = self._extract_drifted_features(results)

            # Determine severity
            severity = self._determine_severity(drift_score, p_value)

            # Generate recommendation
            recommendation = self._generate_recommendation(severity, features_drifted)

            # Create result
            result = DriftResult(
                timestamp=datetime.now(),
                model_name=model_name,
                zone_id=zone_id,
                drift_detected=severity != DriftSeverity.NONE,
                severity=severity,
                drift_score=drift_score,
                p_value=p_value,
                features_drifted=features_drifted,
                recommendation=recommendation,
                metadata={
                    "sample_count": len(current_data),
                    "reference_sample_count": len(self.reference_data)
                }
            )

            # Store in history
            self.drift_history.append(result)

            # Check if retraining trigger needed
            if severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
                self._create_retraining_trigger(result)

            self.logger.info(
                f"Drift detection complete: {severity.value} (score: {drift_score:.3f})"
            )

            return result

        except Exception as e:
            self.logger.error(f"Error in drift detection: {e}")
            # Fallback to simple detection
            return self._simple_drift_detection(current_data, model_name, zone_id)

    def _simple_drift_detection(
        self,
        current_data: pd.DataFrame,
        model_name: str,
        zone_id: str
    ) -> DriftResult:
        """Simple statistical drift detection as fallback."""
        # Get common columns
        common_cols = set(self.reference_data.columns) & set(current_data.columns)
        numerical_cols = [
            col for col in common_cols
            if pd.api.types.is_numeric_dtype(self.reference_data[col])
        ]

        features_drifted = []
        total_drift = 0.0

        for col in numerical_cols:
            ref_mean = self.reference_data[col].mean()
            ref_std = self.reference_data[col].std()
            curr_mean = current_data[col].mean()

            if ref_std > 0:
                z_score = abs(curr_mean - ref_mean) / ref_std
                if z_score > 2.0:  # 2 sigma threshold
                    features_drifted.append(col)
                    total_drift += z_score

        # Calculate average drift score
        drift_score = total_drift / len(numerical_cols) if numerical_cols else 0.0
        drift_score = min(1.0, drift_score / 5.0)  # Normalize to 0-1

        # Determine severity
        if drift_score > 0.8:
            severity = DriftSeverity.CRITICAL
        elif drift_score > 0.6:
            severity = DriftSeverity.HIGH
        elif drift_score > 0.4:
            severity = DriftSeverity.MEDIUM
        elif drift_score > 0.2:
            severity = DriftSeverity.LOW
        else:
            severity = DriftSeverity.NONE

        result = DriftResult(
            timestamp=datetime.now(),
            model_name=model_name,
            zone_id=zone_id,
            drift_detected=severity != DriftSeverity.NONE,
            severity=severity,
            drift_score=drift_score,
            p_value=1.0 - drift_score,  # Approximate
            features_drifted=features_drifted,
            recommendation=self._generate_recommendation(severity, features_drifted),
            metadata={"method": "simple_statistical"}
        )

        self.drift_history.append(result)

        if severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
            self._create_retraining_trigger(result)

        return result

    def _extract_drift_score(self, results: Dict) -> float:
        """Extract drift score from Evidently results."""
        try:
            metrics = results.get("metrics", [])
            for metric in metrics:
                if "dataset_drift" in metric:
                    return metric["dataset_drift"].get("drift_score", 0.0)
        except:
            pass
        return 0.0

    def _extract_p_value(self, results: Dict) -> float:
        """Extract p-value from Evidently results."""
        try:
            metrics = results.get("metrics", [])
            for metric in metrics:
                if "dataset_drift" in metric:
                    return metric["dataset_drift"].get("p_value", 1.0)
        except:
            pass
        return 1.0

    def _extract_drifted_features(self, results: Dict) -> List[str]:
        """Extract list of drifted features from Evidently results."""
        try:
            metrics = results.get("metrics", [])
            for metric in metrics:
                if "column_drift" in metric:
                    drifted = [
                        col for col, stats in metric["column_drift"].items()
                        if stats.get("drift_detected", False)
                    ]
                    return drifted
        except:
            pass
        return []

    def _determine_severity(self, drift_score: float, p_value: float) -> DriftSeverity:
        """Determine drift severity."""
        if drift_score > 0.8 or p_value < 0.01:
            return DriftSeverity.CRITICAL
        elif drift_score > 0.6 or p_value < 0.05:
            return DriftSeverity.HIGH
        elif drift_score > 0.4:
            return DriftSeverity.MEDIUM
        elif drift_score > 0.2:
            return DriftSeverity.LOW
        else:
            return DriftSeverity.NONE

    def _generate_recommendation(
        self,
        severity: DriftSeverity,
        features_drifted: List[str]
    ) -> str:
        """Generate recommendation based on drift severity."""
        if severity == DriftSeverity.NONE:
            return "No significant drift detected. Continue monitoring."

        if severity == DriftSeverity.LOW:
            return "Minor drift detected. Monitor closely, consider data refresh."

        if severity == DriftSeverity.MEDIUM:
            return "Moderate drift detected. Review data quality, consider retraining soon."

        if severity == DriftSeverity.HIGH:
            return f"Significant drift detected in features: {', '.join(features_drifted)}. Retraining recommended."

        if severity == DriftSeverity.CRITICAL:
            return f"Critical drift detected in features: {', '.join(features_drifted)}. Immediate retraining required."

        return "Unknown severity."

    def _create_retraining_trigger(self, drift_result: DriftResult) -> None:
        """Create a retraining trigger based on drift result."""
        trigger_id = f"RT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{drift_result.model_name}"

        priority = 3 if drift_result.severity == DriftSeverity.CRITICAL else 2

        trigger = RetrainingTrigger(
            trigger_id=trigger_id,
            model_name=drift_result.model_name,
            zone_id=drift_result.zone_id,
            trigger_type="DRIFT",
            severity=drift_result.severity,
            reason=drift_result.recommendation,
            timestamp=datetime.now(),
            priority=priority,
            auto_retrain=False  # Human-in-the-loop required
        )

        self.retraining_triggers.append(trigger)

        self.logger.warning(f"Retraining trigger created: {trigger_id}")

    def get_retraining_triggers(
        self,
        min_priority: int = 2,
        hours_back: int = 24
    ) -> List[RetrainingTrigger]:
        """
        Get pending retraining triggers.

        Args:
            min_priority: Minimum priority to include
            hours_back: Hours to look back

        Returns:
            List of retraining triggers
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        triggers = [
            t for t in self.retraining_triggers
            if t.priority >= min_priority and t.timestamp >= cutoff_time
        ]

        # Sort by priority (descending) and timestamp (ascending)
        triggers.sort(key=lambda x: (-x.priority, x.timestamp))

        return triggers

    def clear_old_triggers(self, days_to_keep: int = 30) -> int:
        """
        Clear old retraining triggers.

        Args:
            days_to_keep: Number of days to keep

        Returns:
            Number of triggers cleared
        """
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)

        original_count = len(self.retraining_triggers)
        self.retraining_triggers = [
            t for t in self.retraining_triggers
            if t.timestamp >= cutoff_time
        ]

        cleared_count = original_count - len(self.retraining_triggers)

        self.logger.info(f"Cleared {cleared_count} old triggers")

        return cleared_count

    def get_drift_summary(self) -> Dict[str, any]:
        """
        Get summary of drift detection history.

        Returns:
            Dictionary with drift summary
        """
        if not self.drift_history:
            return {
                "total_detections": 0,
                "drift_detected_count": 0,
                "severity_distribution": {},
                "avg_drift_score": 0.0
            }

        total = len(self.drift_history)
        drift_detected = sum(1 for d in self.drift_history if d.drift_detected)

        # Severity distribution
        severity_dist = {}
        for d in self.drift_history:
            severity = d.severity.value
            severity_dist[severity] = severity_dist.get(severity, 0) + 1

        # Average drift score
        avg_drift_score = np.mean([d.drift_score for d in self.drift_history])

        return {
            "total_detections": total,
            "drift_detected_count": drift_detected,
            "drift_rate": drift_detected / total if total > 0 else 0,
            "severity_distribution": severity_dist,
            "avg_drift_score": avg_drift_score,
            "reference_data_timestamp": self.reference_timestamp.isoformat() if self.reference_timestamp else None
        }


if __name__ == "__main__":
    # Example usage
    detector = DriftDetector()

    # Create sample reference data
    np.random.seed(42)
    reference_data = pd.DataFrame({
        "hour": np.arange(24),
        "demand_kw": 100 + 50 * np.sin(np.arange(24) * 2 * np.pi / 24) + np.random.normal(0, 10, 24),
        "temperature": 25 + 5 * np.sin(np.arange(24) * 2 * np.pi / 24),
        "prediction": 100 + 50 * np.sin(np.arange(24) * 2 * np.pi / 24)
    })

    # Set reference data
    detector.set_reference_data(
        reference_data,
        target_col="demand_kw",
        prediction_col="prediction",
        numerical_features=["hour", "demand_kw", "temperature", "prediction"]
    )

    # Create current data with drift
    current_data = pd.DataFrame({
        "hour": np.arange(24),
        "demand_kw": 150 + 50 * np.sin(np.arange(24) * 2 * np.pi / 24) + np.random.normal(0, 10, 24),  # Drifted
        "temperature": 25 + 5 * np.sin(np.arange(24) * 2 * np.pi / 24),
        "prediction": 100 + 50 * np.sin(np.arange(24) * 2 * np.pi / 24)
    })

    # Detect drift
    result = detector.detect_drift(current_data, model_name="TFT", zone_id="Z01")

    print("Drift Detection Result:")
    print(f"  Drift Detected: {result.drift_detected}")
    print(f"  Severity: {result.severity.value}")
    print(f"  Drift Score: {result.drift_score:.3f}")
    print(f"  P-Value: {result.p_value:.3f}")
    print(f"  Features Drifted: {result.features_drifted}")
    print(f"  Recommendation: {result.recommendation}")

    # Get summary
    summary = detector.get_drift_summary()
    print(f"\nDrift Summary: {summary}")

    # Get triggers
    triggers = detector.get_retraining_triggers()
    print(f"\nRetraining Triggers: {len(triggers)}")
    for trigger in triggers:
        print(f"  {trigger.trigger_id}: {trigger.severity.value} - {trigger.reason}")
