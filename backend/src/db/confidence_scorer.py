"""
Data Confidence Scoring System
Provides HIGH/MEDIUM/LOW confidence ratings for data sources with fallback strategies.
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import numpy as np


class ConfidenceLevel(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DataSource(Enum):
    SYNTHETIC = "SYNTHETIC"
    BESCOM_API = "BESCOM_API"
    OSM = "OSM"
    USER_FEEDBACK = "USER_FEEDBACK"
    HISTORICAL = "HISTORICAL"


class DataConfidenceScorer:
    """Scores data quality and provides confidence levels with fallback strategies."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.quality_metrics: Dict[str, Dict[str, Any]] = {}

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for confidence scoring."""
        return {
            "thresholds": {
                "high": {
                    "completeness": 0.95,
                    "freshness_hours": 24,
                    "anomaly_rate": 0.02
                },
                "medium": {
                    "completeness": 0.80,
                    "freshness_hours": 72,
                    "anomaly_rate": 0.05
                }
            },
            "source_weights": {
                DataSource.BESCOM_API: 1.0,
                DataSource.USER_FEEDBACK: 0.9,
                DataSource.HISTORICAL: 0.8,
                DataSource.OSM: 0.7,
                DataSource.SYNTHETIC: 0.5
            }
        }

    def score_data(
        self,
        data: Any,
        source: DataSource,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Score data quality and return confidence level.

        Args:
            data: The data to score
            source: The data source
            metadata: Additional metadata about the data

        Returns:
            Dictionary with confidence level and metrics
        """
        metrics = self._calculate_metrics(data, source, metadata or {})
        confidence = self._determine_confidence(metrics, source)

        # Store quality metrics for this source
        source_key = source.value
        self.quality_metrics[source_key] = {
            **metrics,
            "confidence": confidence.value,
            "last_updated": datetime.now().isoformat()
        }

        return {
            "confidence": confidence.value,
            "metrics": metrics,
            "fallback_strategy": self._get_fallback_strategy(confidence, source)
        }

    def _calculate_metrics(
        self,
        data: Any,
        source: DataSource,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate quality metrics for the data."""
        metrics = {
            "completeness": 0.0,
            "freshness_hours": 0.0,
            "anomaly_rate": 0.0,
            "record_count": 0,
            "missing_percent": 0.0
        }

        if hasattr(data, '__len__'):
            metrics["record_count"] = len(data)

        # Calculate completeness
        if "completeness" in metadata:
            metrics["completeness"] = metadata["completeness"]
        elif hasattr(data, 'shape'):
            # For numpy arrays or pandas DataFrames
            if len(data.shape) == 2:
                total = data.shape[0] * data.shape[1]
                missing = np.isnan(data).sum() if hasattr(data, '__array__') else 0
                metrics["completeness"] = 1.0 - (missing / total) if total > 0 else 0.0
                metrics["missing_percent"] = (missing / total) * 100 if total > 0 else 0.0

        # Calculate freshness
        if "timestamp" in metadata:
            timestamp = metadata["timestamp"]
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            metrics["freshness_hours"] = (datetime.now() - timestamp).total_seconds() / 3600

        # Calculate anomaly rate
        if "anomaly_rate" in metadata:
            metrics["anomaly_rate"] = metadata["anomaly_rate"]

        return metrics

    def _determine_confidence(
        self,
        metrics: Dict[str, Any],
        source: DataSource
    ) -> ConfidenceLevel:
        """Determine confidence level based on metrics."""
        thresholds = self.config["thresholds"]
        source_weight = self.config["source_weights"].get(source, 0.5)

        # Adjust thresholds based on source weight
        high_threshold = thresholds["high"]["completeness"] * source_weight
        medium_threshold = thresholds["medium"]["completeness"] * source_weight

        if metrics["completeness"] >= high_threshold:
            if metrics["freshness_hours"] <= thresholds["high"]["freshness_hours"]:
                if metrics["anomaly_rate"] <= thresholds["high"]["anomaly_rate"]:
                    return ConfidenceLevel.HIGH

        if metrics["completeness"] >= medium_threshold:
            if metrics["freshness_hours"] <= thresholds["medium"]["freshness_hours"]:
                if metrics["anomaly_rate"] <= thresholds["medium"]["anomaly_rate"]:
                    return ConfidenceLevel.MEDIUM

        return ConfidenceLevel.LOW

    def _get_fallback_strategy(
        self,
        confidence: ConfidenceLevel,
        source: DataSource
    ) -> str:
        """Get fallback strategy based on confidence level."""
        strategies = {
            ConfidenceLevel.HIGH: "Use data directly",
            ConfidenceLevel.MEDIUM: "Use with warning, validate against historical",
            ConfidenceLevel.LOW: "Use synthetic data as primary, this as reference"
        }

        # Source-specific fallbacks
        if source == DataSource.BESCOM_API and confidence == ConfidenceLevel.LOW:
            return "CRITICAL: Switch to synthetic data immediately, alert operators"

        if source == DataSource.SYNTHETIC:
            return "Synthetic data - always validate with real data when available"

        return strategies[confidence]

    def get_source_quality(self, source: DataSource) -> Dict[str, Any]:
        """Get current quality metrics for a data source."""
        source_key = source.value
        if source_key not in self.quality_metrics:
            return {
                "confidence": "UNKNOWN",
                "message": "No quality data available for this source"
            }
        return self.quality_metrics[source_key]

    def get_overall_confidence(self) -> Dict[str, Any]:
        """Get overall system confidence across all data sources."""
        if not self.quality_metrics:
            return {
                "overall": "UNKNOWN",
                "message": "No data sources scored yet"
            }

        confidence_counts = {
            ConfidenceLevel.HIGH.value: 0,
            ConfidenceLevel.MEDIUM.value: 0,
            ConfidenceLevel.LOW.value: 0
        }

        for metrics in self.quality_metrics.values():
            conf = metrics.get("confidence", "UNKNOWN")
            if conf in confidence_counts:
                confidence_counts[conf] += 1

        total = sum(confidence_counts.values())

        # Determine overall confidence
        if confidence_counts[ConfidenceLevel.HIGH.value] / total >= 0.7:
            overall = ConfidenceLevel.HIGH.value
        elif confidence_counts[ConfidenceLevel.MEDIUM.value] / total >= 0.5:
            overall = ConfidenceLevel.MEDIUM.value
        else:
            overall = ConfidenceLevel.LOW.value

        return {
            "overall": overall,
            "counts": confidence_counts,
            "total_sources": total,
            "recommendation": self._get_overall_recommendation(overall)
        }

    def _get_overall_recommendation(self, overall: str) -> str:
        """Get recommendation based on overall confidence."""
        recommendations = {
            "HIGH": "System operating with high confidence. Proceed with normal operations.",
            "MEDIUM": "System operating with medium confidence. Monitor closely and validate outputs.",
            "LOW": "System operating with low confidence. Use synthetic data and investigate data quality issues.",
            "UNKNOWN": "No confidence data available. Initialize data scoring before proceeding."
        }
        return recommendations.get(overall, "Unknown confidence level.")


# Singleton instance
_scorer: Optional[DataConfidenceScorer] = None


def get_confidence_scorer() -> DataConfidenceScorer:
    """Get the singleton confidence scorer instance."""
    global _scorer
    if _scorer is None:
        _scorer = DataConfidenceScorer()
    return _scorer
