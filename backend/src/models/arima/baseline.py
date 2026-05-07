"""
ARIMA Baseline Model for EV Demand Forecasting
Production-grade implementation for comparison with TFT model.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import seasonal_decompose
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error

from ..config import ModelConfig, ModelType, get_config

# Suppress statsmodels warnings
warnings.filterwarnings("ignore")


class ARIMABaseline:
    """Production-grade ARIMA baseline model for EV demand forecasting."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_config()
        self.arima_config = self.config.get_config(ModelType.ARIMA)

        self.logger = logging.getLogger(__name__)

        # Model parameters
        self.p = self.arima_config.p
        self.d = self.arima_config.d
        self.q = self.arima_config.q

        self.seasonal_p = self.arima_config.seasonal_p
        self.seasonal_d = self.arima_config.seasonal_d
        self.seasonal_q = self.arima_config.seasonal_q
        self.seasonal_period = self.arima_config.seasonal_period

        # Trained models (one per zone/archetype combination)
        self.models: Dict[str, ARIMA] = {}

        # Model metadata
        self.model_metadata: Dict[str, Dict] = {}

    def prepare_data(
        self,
        data: pd.DataFrame,
        time_col: str = "time",
        target_col: str = "demand_kw",
        group_cols: List[str] = ["zone_id", "archetype_id"]
    ) -> Dict[str, pd.DataFrame]:
        """
        Prepare data for ARIMA modeling.

        Args:
            data: Input DataFrame
            time_col: Time column name
            target_col: Target column name
            group_cols: Grouping columns

        Returns:
            Dictionary of DataFrames keyed by group
        """
        self.logger.info("Preparing data for ARIMA modeling...")

        # Ensure time column is datetime
        data = data.copy()
        data[time_col] = pd.to_datetime(data[time_col])

        # Sort by time
        data = data.sort_values(time_col)

        # Group by zone and archetype
        grouped_data = {}

        for group_keys, group_df in data.groupby(group_cols):
            group_key = "_".join(group_keys)
            grouped_data[group_key] = group_df.set_index(time_col)[target_col].asfreq('H')

        self.logger.info(f"Prepared {len(grouped_data)} time series for modeling")

        return grouped_data

    def fit_model(
        self,
        series: pd.Series,
        group_key: str,
        use_seasonal: bool = True
    ) -> ARIMA:
        """
        Fit ARIMA/SARIMA model to a time series.

        Args:
            series: Time series data
            group_key: Group identifier
            use_seasonal: Whether to use seasonal ARIMA

        Returns:
            Fitted ARIMA model
        """
        self.logger.info(f"Fitting ARIMA model for {group_key}...")

        try:
            if use_seasonal:
                # Use SARIMA for seasonal patterns
                model = SARIMAX(
                    series,
                    order=(self.p, self.d, self.q),
                    seasonal_order=(self.seasonal_p, self.seasonal_d, self.seasonal_q, self.seasonal_period),
                    enforce_stationarity=False,
                    enforce_invertibility=False
                )
            else:
                # Use non-seasonal ARIMA
                model = ARIMA(
                    series,
                    order=(self.p, self.d, self.q)
                )

            fitted_model = model.fit(disp=False)

            # Store model metadata
            self.model_metadata[group_key] = {
                "use_seasonal": use_seasonal,
                "aic": fitted_model.aic,
                "bic": fitted_model.bic,
                "params": fitted_model.params.to_dict(),
                "fitted_at": pd.Timestamp.now().isoformat()
            }

            self.logger.info(f"ARIMA model fitted for {group_key} (AIC: {fitted_model.aic:.2f})")

            return fitted_model

        except Exception as e:
            self.logger.error(f"Error fitting ARIMA model for {group_key}: {e}")
            raise

    def train(
        self,
        data: pd.DataFrame,
        use_seasonal: bool = True
    ) -> Dict[str, float]:
        """
        Train ARIMA models on all time series.

        Args:
            data: Input DataFrame
            use_seasonal: Whether to use seasonal ARIMA

        Returns:
            Dictionary with training metrics
        """
        self.logger.info("Training ARIMA baseline models...")

        # Prepare data
        grouped_data = self.prepare_data(data)

        # Fit model for each group
        for group_key, series in grouped_data.items():
            try:
                model = self.fit_model(series, group_key, use_seasonal)
                self.models[group_key] = model
            except Exception as e:
                self.logger.warning(f"Failed to fit model for {group_key}: {e}")

        # Calculate overall metrics
        metrics = {
            "models_trained": len(self.models),
            "total_groups": len(grouped_data),
            "success_rate": len(self.models) / len(grouped_data) if grouped_data else 0
        }

        # Calculate average AIC
        if self.model_metadata:
            avg_aic = np.mean([m["aic"] for m in self.model_metadata.values()])
            metrics["average_aic"] = avg_aic

        self.logger.info(f"ARIMA training complete: {metrics}")

        return metrics

    def predict(
        self,
        group_key: str,
        steps: int = 72,
        return_conf_int: bool = True,
        alpha: float = 0.05
    ) -> pd.DataFrame:
        """
        Generate predictions for a specific group.

        Args:
            group_key: Group identifier
            steps: Number of steps to forecast
            return_conf_int: Whether to return confidence intervals
            alpha: Significance level for confidence intervals

        Returns:
            DataFrame with predictions
        """
        if group_key not in self.models:
            raise ValueError(f"No model found for group: {group_key}")

        model = self.models[group_key]

        # Generate forecast
        forecast = model.get_forecast(
            steps=steps,
            alpha=alpha if return_conf_int else None
        )

        # Create result DataFrame
        result = pd.DataFrame({
            "prediction": forecast.predicted_mean
        })

        # Add confidence intervals if requested
        if return_conf_int:
            conf_int = forecast.conf_int()
            result["confidence_lower"] = conf_int.iloc[:, 0]
            result["confidence_upper"] = conf_int.iloc[:, 1]

        # Add time index
        last_time = model.data.orig_end
        result["time"] = pd.date_range(
            start=last_time + pd.Timedelta(hours=1),
            periods=steps,
            freq="H"
        )
        result = result.set_index("time")

        return result

    def predict_all(
        self,
        steps: int = 72,
        return_conf_int: bool = True,
        alpha: float = 0.05
    ) -> pd.DataFrame:
        """
        Generate predictions for all groups.

        Args:
            steps: Number of steps to forecast
            return_conf_int: Whether to return confidence intervals
            alpha: Significance level for confidence intervals

        Returns:
            DataFrame with predictions for all groups
        """
        self.logger.info(f"Generating {steps}-hour forecasts for all groups...")

        all_predictions = []

        for group_key in self.models.keys():
            try:
                # Parse group key
                parts = group_key.split("_")
                zone_id = parts[0]
                archetype_id = parts[1] if len(parts) > 1 else None

                # Generate predictions
                forecast = self.predict(group_key, steps, return_conf_int, alpha)
                forecast = forecast.reset_index()

                # Add group identifiers
                forecast["zone_id"] = zone_id
                forecast["archetype_id"] = archetype_id

                all_predictions.append(forecast)

            except Exception as e:
                self.logger.warning(f"Failed to generate forecast for {group_key}: {e}")

        if not all_predictions:
            return pd.DataFrame()

        # Combine all predictions
        result = pd.concat(all_predictions, ignore_index=True)

        # Rename columns for consistency
        if return_conf_int:
            result = result.rename(columns={
                "confidence_lower": "confidence_95_lower",
                "confidence_upper": "confidence_95_upper"
            })

            # Add 80% confidence intervals (approximate)
            result["confidence_80_lower"] = result["confidence_95_lower"] * 0.9
            result["confidence_80_upper"] = result["confidence_95_upper"] * 1.1

        self.logger.info(f"Generated {len(result)} forecast records")

        return result

    def evaluate(
        self,
        test_data: pd.DataFrame,
        steps: int = 24
    ) -> Dict[str, float]:
        """
        Evaluate ARIMA model on test data.

        Args:
            test_data: Test data DataFrame
            steps: Number of steps to evaluate

        Returns:
            Dictionary with evaluation metrics
        """
        self.logger.info("Evaluating ARIMA model on test data...")

        # Prepare test data
        grouped_test = self.prepare_data(test_data)

        metrics = {
            "mape": [],
            "rmse": [],
            "mae": []
        }

        for group_key, test_series in grouped_test.items():
            if group_key not in self.models:
                continue

            try:
                # Generate predictions
                forecast = self.predict(group_key, steps=min(steps, len(test_series)))

                # Align with test data
                test_values = test_series.iloc[:len(forecast)]
                pred_values = forecast["prediction"].values

                # Calculate metrics
                mape = mean_absolute_percentage_error(test_values, pred_values)
                rmse = np.sqrt(mean_squared_error(test_values, pred_values))
                mae = np.mean(np.abs(test_values - pred_values))

                metrics["mape"].append(mape)
                metrics["rmse"].append(rmse)
                metrics["mae"].append(mae)

            except Exception as e:
                self.logger.warning(f"Failed to evaluate {group_key}: {e}")

        # Calculate average metrics
        result = {}
        for metric_name, values in metrics.items():
            if values:
                result[f"avg_{metric_name}"] = np.mean(values)
                result[f"std_{metric_name}"] = np.std(values)

        self.logger.info(f"ARIMA evaluation metrics: {result}")

        return result

    def save_models(self, path: Optional[str] = None) -> str:
        """
        Save trained models to disk.

        Args:
            path: Directory to save models

        Returns:
            Path where models were saved
        """
        import pickle

        path = path or self.arima_config.model_dir
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save models
        model_path = path / "arima_models.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(self.models, f)

        # Save metadata
        metadata_path = path / "arima_metadata.json"
        import json
        with open(metadata_path, "w") as f:
            json.dump(self.model_metadata, f, indent=2, default=str)

        self.logger.info(f"ARIMA models saved to: {path}")

        return str(path)

    def load_models(self, path: Optional[str] = None) -> None:
        """
        Load trained models from disk.

        Args:
            path: Directory to load models from
        """
        import pickle
        import json

        path = path or self.arima_config.model_dir
        path = Path(path)

        # Load models
        model_path = path / "arima_models.pkl"
        if model_path.exists():
            with open(model_path, "rb") as f:
                self.models = pickle.load(f)
            self.logger.info(f"Loaded {len(self.models)} ARIMA models")

        # Load metadata
        metadata_path = path / "arima_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                self.model_metadata = json.load(f)
            self.logger.info("Loaded ARIMA model metadata")


if __name__ == "__main__":
    # Example usage
    baseline = ARIMABaseline()

    # Load synthetic data
    data_path = "data/synthetic/ev_demand.csv"
    if Path(data_path).exists():
        data = pd.read_csv(data_path)

        # Train model
        metrics = baseline.train(data)

        print(f"Training metrics: {metrics}")

        # Generate predictions
        predictions = baseline.predict_all(steps=72)

        print(f"\nGenerated {len(predictions)} forecast records")
        print(predictions.head())

        # Save models
        baseline.save_models()
    else:
        print(f"Data file not found: {data_path}")
