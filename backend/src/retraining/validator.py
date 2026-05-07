"""
Model Validation Module
Production-grade implementation for model validation before deployment.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    mean_absolute_percentage_error,
    r2_score
)


class ValidationStatus(Enum):
    """Status of model validation."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    PENDING = "pending"


@dataclass
class ValidationMetric:
    """Single validation metric."""

    name: str
    value: float
    threshold: float
    passed: bool
    direction: str = "le"  # "le" for less-than-or-equal, "ge" for greater-than-or-equal


@dataclass
class ValidationResult:
    """Result of model validation."""

    model_name: str
    model_version: str
    zone_id: str
    status: ValidationStatus
    timestamp: datetime
    metrics: List[ValidationMetric]
    overall_score: float
    recommendation: str
    metadata: Dict = field(default_factory=dict)


class ModelValidator:
    """Production-grade model validator."""

    def __init__(
        self,
        mape_threshold: float = 0.12,  # 12% MAPE threshold
        mae_threshold: float = 50.0,  # 50 kW MAE threshold
        rmse_threshold: float = 75.0,  # 75 kW RMSE threshold
        r2_threshold: float = 0.85  # 0.85 R2 threshold
    ):
        self.mape_threshold = mape_threshold
        self.mae_threshold = mae_threshold
        self.rmse_threshold = rmse_threshold
        self.r2_threshold = r2_threshold

        self.logger = logging.getLogger(__name__)

        # Validation history
        self.validation_history: List[ValidationResult] = []

    def validate_model(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str = "TFT",
        model_version: str = "1.0.0",
        zone_id: str = "ALL"
    ) -> ValidationResult:
        """
        Validate model predictions.

        Args:
            y_true: True values
            y_pred: Predicted values
            model_name: Name of the model
            model_version: Version of the model
            zone_id: Zone ID

        Returns:
            Validation result
        """
        self.logger.info(f"Validating model {model_name} v{model_version} for zone {zone_id}")

        # Calculate metrics
        mae = mean_absolute_error(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        mape = mean_absolute_percentage_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)

        # Create metric objects
        metrics = [
            ValidationMetric(
                name="MAE",
                value=mae,
                threshold=self.mae_threshold,
                passed=mae <= self.mae_threshold,
                direction="le"
            ),
            ValidationMetric(
                name="RMSE",
                value=rmse,
                threshold=self.rmse_threshold,
                passed=rmse <= self.rmse_threshold,
                direction="le"
            ),
            ValidationMetric(
                name="MAPE",
                value=mape,
                threshold=self.mape_threshold,
                passed=mape <= self.mape_threshold,
                direction="le"
            ),
            ValidationMetric(
                name="R2",
                value=r2,
                threshold=self.r2_threshold,
                passed=r2 >= self.r2_threshold,
                direction="ge"
            )
        ]

        # Calculate overall score
        passed_count = sum(1 for m in metrics if m.passed)
        overall_score = passed_count / len(metrics)

        # Determine status
        if overall_score == 1.0:
            status = ValidationStatus.PASSED
        elif overall_score >= 0.75:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAILED

        # Generate recommendation
        recommendation = self._generate_recommendation(status, metrics)

        # Create result
        result = ValidationResult(
            model_name=model_name,
            model_version=model_version,
            zone_id=zone_id,
            status=status,
            timestamp=datetime.now(),
            metrics=metrics,
            overall_score=overall_score,
            recommendation=recommendation,
            metadata={
                "sample_count": len(y_true),
                "mean_true": float(np.mean(y_true)),
                "mean_pred": float(np.mean(y_pred)),
                "std_true": float(np.std(y_true)),
                "std_pred": float(np.std(y_pred))
            }
        )

        # Store in history
        self.validation_history.append(result)

        self.logger.info(
            f"Validation complete: {status.value} (score: {overall_score:.2f})"
        )

        return result

    def _generate_recommendation(
        self,
        status: ValidationStatus,
        metrics: List[ValidationMetric]
    ) -> str:
        """Generate recommendation based on validation status."""
        if status == ValidationStatus.PASSED:
            return "Model passed all validation criteria. Ready for deployment."

        if status == ValidationStatus.WARNING:
            failed_metrics = [m.name for m in metrics if not m.passed]
            return (
                f"Model passed most criteria but failed on: {', '.join(failed_metrics)}. "
                "Review before deployment."
            )

        if status == ValidationStatus.FAILED:
            failed_metrics = [m.name for m in metrics if not m.passed]
            return (
                f"Model failed validation on: {', '.join(failed_metrics)}. "
                "Retraining required before deployment."
            )

        return "Validation pending."

    def compare_models(
        self,
        results: List[ValidationResult]
    ) -> Dict[str, any]:
        """
        Compare multiple model validation results.

        Args:
            results: List of validation results

        Returns:
            Dictionary with comparison results
        """
        if not results:
            return {"error": "No results to compare"}

        # Sort by overall score
        sorted_results = sorted(results, key=lambda x: x.overall_score, reverse=True)

        # Get best model
        best = sorted_results[0]

        # Create comparison table
        comparison = {
            "best_model": {
                "name": best.model_name,
                "version": best.model_version,
                "zone_id": best.zone_id,
                "overall_score": best.overall_score,
                "status": best.status.value
            },
            "rankings": [
                {
                    "rank": i + 1,
                    "name": r.model_name,
                    "version": r.model_version,
                    "overall_score": r.overall_score,
                    "status": r.status.value
                }
                for i, r in enumerate(sorted_results)
            ],
            "metric_comparison": {}
        }

        # Compare metrics across models
        metric_names = [m.name for m in results[0].metrics]
        for metric_name in metric_names:
            comparison["metric_comparison"][metric_name] = [
                {
                    "model": r.model_name,
                    "value": next(m.value for m in r.metrics if m.name == metric_name),
                    "passed": next(m.passed for m in r.metrics if m.name == metric_name)
                }
                for r in results
            ]

        return comparison

    def get_validation_summary(self) -> Dict[str, any]:
        """
        Get summary of validation history.

        Returns:
            Dictionary with validation summary
        """
        if not self.validation_history:
            return {
                "total_validations": 0,
                "passed_count": 0,
                "failed_count": 0,
                "warning_count": 0,
                "avg_overall_score": 0.0
            }

        total = len(self.validation_history)
        passed = sum(1 for v in self.validation_history if v.status == ValidationStatus.PASSED)
        failed = sum(1 for v in self.validation_history if v.status == ValidationStatus.FAILED)
        warning = sum(1 for v in self.validation_history if v.status == ValidationStatus.WARNING)

        avg_score = np.mean([v.overall_score for v in self.validation_history])

        return {
            "total_validations": total,
            "passed_count": passed,
            "failed_count": failed,
            "warning_count": warning,
            "pass_rate": passed / total if total > 0 else 0,
            "avg_overall_score": avg_score
        }

    def get_model_performance_trend(
        self,
        model_name: str,
        zone_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get performance trend for a model over time.

        Args:
            model_name: Name of the model
            zone_id: Optional zone filter

        Returns:
            List of performance data points
        """
        trend = []

        for result in self.validation_history:
            if result.model_name == model_name:
                if zone_id is None or result.zone_id == zone_id:
                    trend.append({
                        "timestamp": result.timestamp.isoformat(),
                        "overall_score": result.overall_score,
                        "status": result.status.value,
                        "metrics": {
                            m.name: m.value for m in result.metrics
                        }
                    })

        # Sort by timestamp
        trend.sort(key=lambda x: x["timestamp"])

        return trend


if __name__ == "__main__":
    # Example usage
    validator = ModelValidator()

    # Create sample predictions
    np.random.seed(42)
    n_samples = 100
    y_true = np.random.normal(100, 20, n_samples)
    y_pred_good = y_true + np.random.normal(0, 5, n_samples)  # Good predictions
    y_pred_bad = y_true + np.random.normal(0, 30, n_samples)  # Bad predictions

    # Validate good model
    result_good = validator.validate_model(
        y_true, y_pred_good,
        model_name="TFT",
        model_version="1.0.0",
        zone_id="Z01"
    )

    print("Good Model Validation:")
    print(f"  Status: {result_good.status.value}")
    print(f"  Overall Score: {result_good.overall_score:.2f}")
    print(f"  Recommendation: {result_good.recommendation}")

    # Validate bad model
    result_bad = validator.validate_model(
        y_true, y_pred_bad,
        model_name="TFT",
        model_version="0.9.0",
        zone_id="Z01"
    )

    print("\nBad Model Validation:")
    print(f"  Status: {result_bad.status.value}")
    print(f"  Overall Score: {result_bad.overall_score:.2f}")
    print(f"  Recommendation: {result_bad.recommendation}")

    # Compare models
    comparison = validator.compare_models([result_good, result_bad])
    print(f"\nModel Comparison: {comparison}")

    # Get summary
    summary = validator.get_validation_summary()
    print(f"\nValidation Summary: {summary}")
