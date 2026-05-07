"""
Temporal Fusion Transformer (TFT) Model for EV Demand Forecasting
Production-grade implementation using PyTorch Forecasting.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

import torch
import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint
from pytorch_lightning.loggers import MLFlowLogger

from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
from pytorch_forecasting.metrics import QuantileLoss, SMAPE

from .config import ModelConfig, ModelType, get_config


class TFTForecaster:
    """Production-grade TFT forecaster for EV demand prediction."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_config()
        self.tft_config = self.config.get_config(ModelType.TFT)

        self.model: Optional[TemporalFusionTransformer] = None
        self.dataset: Optional[TimeSeriesDataSet] = None
        self.trainer: Optional[pl.Trainer] = None

        self._setup_logging()
        self._setup_directories()

    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=self.config.log_level,
            format=self.config.log_format
        )
        self.logger = logging.getLogger(__name__)

    def _setup_directories(self):
        """Create necessary directories."""
        for attr in ["model_dir", "checkpoint_dir", "log_dir"]:
            path = Path(getattr(self.tft_config, attr))
            path.mkdir(parents=True, exist_ok=True)

    def prepare_data(
        self,
        data: pd.DataFrame,
        time_col: str = "time",
        target_col: str = "demand_kw",
        group_cols: List[str] = ["zone_id", "archetype_id"]
    ) -> TimeSeriesDataSet:
        """
        Prepare data for TFT training.

        Args:
            data: Input DataFrame with time series data
            time_col: Name of time column
            target_col: Name of target column
            group_cols: List of grouping columns

        Returns:
            TimeSeriesDataSet ready for training
        """
        self.logger.info("Preparing data for TFT training...")

        # Ensure time column is datetime
        data[time_col] = pd.to_datetime(data[time_col])

        # Add time features
        data = self._add_time_features(data, time_col)

        # Create TimeSeriesDataSet
        max_encoder_length = self.tft_config.max_encoder_length
        max_prediction_length = self.tft_config.max_prediction_length

        training_cutoff = data[time_col].max() - pd.Timedelta(
            days=max_prediction_length // 24
        )

        self.dataset = TimeSeriesDataSet(
            data,
            time_idx="time_idx",
            target=target_col,
            categorical_encodings={
                "zone_id": len(self.tft_config.zones),
                "archetype_id": len(self.tft_config.archetypes)
            },
            group_ids=group_cols,
            min_encoder_length=self.tft_config.min_encoder_length,
            max_encoder_length=max_encoder_length,
            min_prediction_length=1,
            max_prediction_length=max_prediction_length,
            static_categoricals=group_cols,
            time_varying_known_reals=[
                "time_idx",
                "hour",
                "day_of_week",
                "day_of_month",
                "is_weekend",
                "is_peak_hour"
            ],
            time_varying_unknown_reals=[target_col],
            target_normalizer=None,  # Let TFT handle normalization
            add_relative_time_idx=True,
            add_target_scales=True,
            add_encoder_length=True,
            allow_missing_timesteps=True
        )

        self.logger.info(f"Dataset created with {len(self.dataset)} samples")
        return self.dataset

    def _add_time_features(self, data: pd.DataFrame, time_col: str) -> pd.DataFrame:
        """Add time-based features to the data."""
        data = data.copy()

        # Add time index (integer representation)
        data["time_idx"] = (
            data[time_col] - data[time_col].min()
        ).dt.total_seconds() // 3600  # Convert to hours

        # Add hour of day
        data["hour"] = data[time_col].dt.hour

        # Add day of week
        data["day_of_week"] = data[time_col].dt.dayofweek

        # Add day of month
        data["day_of_month"] = data[time_col].dt.day

        # Add weekend indicator
        data["is_weekend"] = (data["day_of_week"] >= 5).astype(int)

        # Add peak hour indicator (7-10 AM, 6-9 PM)
        data["is_peak_hour"] = (
            ((data["hour"] >= 7) & (data["hour"] <= 10)) |
            ((data["hour"] >= 18) & (data["hour"] <= 21))
        ).astype(int)

        return data

    def create_data_loaders(
        self,
        batch_size: Optional[int] = None,
        validation_split: Optional[float] = None
    ) -> Tuple[torch.utils.data.DataLoader, torch.utils.data.DataLoader]:
        """
        Create training and validation data loaders.

        Args:
            batch_size: Batch size for training
            validation_split: Fraction of data for validation

        Returns:
            Tuple of (train_loader, val_loader)
        """
        if self.dataset is None:
            raise ValueError("Dataset not prepared. Call prepare_data() first.")

        batch_size = batch_size or self.tft_config.batch_size
        validation_split = validation_split or self.tft_config.validation_split

        # Create train/validation split
        train_dataset, val_dataset = self.dataset.split(
            split=validation_split,
            shuffle=True
        )

        # Create data loaders
        train_loader = train_dataset.to_dataloader(
            train=True,
            batch_size=batch_size,
            num_workers=self.config.num_workers,
            pin_memory=self.config.pin_memory
        )

        val_loader = val_dataset.to_dataloader(
            train=False,
            batch_size=batch_size * 2,  # Larger batch for validation
            num_workers=self.config.num_workers,
            pin_memory=self.config.pin_memory
        )

        self.logger.info(f"Created data loaders: train={len(train_loader)}, val={len(val_loader)}")

        return train_loader, val_loader

    def build_model(self) -> TemporalFusionTransformer:
        """
        Build the TFT model.

        Returns:
            Configured TemporalFusionTransformer model
        """
        if self.dataset is None:
            raise ValueError("Dataset not prepared. Call prepare_data() first.")

        self.logger.info("Building TFT model...")

        # Calculate output size (quantiles)
        quantiles = [0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98]
        output_size = len(quantiles)

        self.model = TemporalFusionTransformer.from_dataset(
            self.dataset,
            learning_rate=self.tft_config.learning_rate,
            hidden_size=self.tft_config.hidden_size,
            attention_head_size=self.tft_config.hidden_size,
            dropout=self.tft_config.dropout,
            hidden_continuous_size=self.tft_config.hidden_continuous_size,
            output_size=output_size,
            loss=QuantileLoss(quantiles=quantiles),
            log_interval=10,
            reduce_on_plateau_patience=4,
            log_val_interval=1,
            log_gradient_norm=True,
            log_target_scale_normalization=True,
            log_prediction_interval=True,
            log_evaluation_metrics=True,
            optimizer="Adam",
            optimizer_params={"weight_decay": 1e-2},
            lr_scheduler="ReduceLROnPlateau",
            lr_scheduler_params={
                "factor": 0.5,
                "patience": 5,
                "verbose": True
            }
        )

        self.logger.info(f"TFT model built with {sum(p.numel() for p in self.model.parameters())} parameters")

        return self.model

    def train(
        self,
        train_loader: torch.utils.data.DataLoader,
        val_loader: torch.utils.data.DataLoader,
        max_epochs: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Train the TFT model.

        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            max_epochs: Maximum number of epochs

        Returns:
            Dictionary with training metrics
        """
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")

        max_epochs = max_epochs or self.tft_config.epochs

        self.logger.info(f"Starting TFT training for {max_epochs} epochs...")

        # Setup callbacks
        callbacks = [
            EarlyStopping(
                monitor="val_loss",
                min_delta=1e-4,
                patience=self.tft_config.early_stopping_patience,
                verbose=True,
                mode="min"
            ),
            ModelCheckpoint(
                dirpath=self.tft_config.checkpoint_dir,
                filename="tft-best-{epoch:02d}-{val_loss:.2f}",
                monitor="val_loss",
                save_top_k=3,
                mode="min"
            )
        ]

        # Setup logger
        logger = None
        if self.config.use_mlflow:
            logger = MLFlowLogger(
                experiment_name=self.config.mlflow_experiment_name,
                tracking_uri=self.config.mlflow_tracking_uri
            )

        # Setup trainer
        self.trainer = pl.Trainer(
            max_epochs=max_epochs,
            accelerator=self.config.device,
            devices="auto" if self.config.device == "auto" else 1,
            callbacks=callbacks,
            logger=logger,
            gradient_clip_val=self.tft_config.gradient_clip_val,
            log_every_n_steps=10,
            enable_progress_bar=True,
            enable_model_summary=True
        )

        # Train model
        self.trainer.fit(
            self.model,
            train_dataloaders=train_loader,
            val_dataloaders=val_loader
        )

        # Get best model path
        best_model_path = callbacks[1].best_model_path
        self.logger.info(f"Training complete. Best model: {best_model_path}")

        # Load best model
        self.model = TemporalFusionTransformer.load_from_checkpoint(best_model_path)

        # Get training metrics
        metrics = {
            "best_val_loss": callbacks[1].best_model_score.item(),
            "epochs_trained": self.trainer.current_epoch + 1
        }

        return metrics

    def predict(
        self,
        data: pd.DataFrame,
        horizon_hours: Optional[int] = None,
        return_raw: bool = False
    ) -> pd.DataFrame:
        """
        Generate predictions using the trained model.

        Args:
            data: Input data for prediction
            horizon_hours: Forecast horizon in hours
            return_raw: Whether to return raw predictions

        Returns:
            DataFrame with predictions and confidence intervals
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        horizon_hours = horizon_hours or self.tft_config.horizon_hours

        self.logger.info(f"Generating predictions for {horizon_hours} hours...")

        # Prepare prediction data
        pred_data = self._add_time_features(data.copy(), "time")

        # Create prediction dataset
        pred_dataset = TimeSeriesDataSet.from_dataset(
            self.dataset,
            pred_data,
            min_prediction_length=1,
            max_prediction_length=horizon_hours
        )

        # Create data loader
        pred_loader = pred_dataset.to_dataloader(
            train=False,
            batch_size=1,
            num_workers=0
        )

        # Generate predictions
        raw_predictions, x = self.model.predict(
            pred_loader,
            mode="raw",
            return_x=True,
            n_samples=100  # Monte Carlo samples for uncertainty
        )

        # Process predictions
        predictions = self._process_predictions(raw_predictions, x, data)

        if return_raw:
            return predictions, raw_predictions

        return predictions

    def _process_predictions(
        self,
        raw_predictions: torch.Tensor,
        x: Dict[str, torch.Tensor],
        original_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Process raw predictions into DataFrame format."""
        # Extract predictions
        predictions = raw_predictions["prediction"].detach().cpu().numpy()

        # Extract decoder time indices
        decoder_time_idx = x["decoder_time_idx"].detach().cpu().numpy()

        # Extract group IDs
        if "decoder_cat" in x:
            zone_ids = x["decoder_cat"][:, :, 0].detach().cpu().numpy()
            archetype_ids = x["decoder_cat"][:, :, 1].detach().cpu().numpy()
        else:
            # Fallback to encoder categories
            zone_ids = x["encoder_cat"][:, -1:, 0].detach().cpu().numpy()
            archetype_ids = x["encoder_cat"][:, -1:, 1].detach().cpu().numpy()

        # Create result DataFrame
        results = []

        for i in range(predictions.shape[0]):
            zone_id = self.tft_config.zones[int(zone_ids[i, 0])]
            archetype_id = self.tft_config.archetypes[int(archetype_ids[i, 0])]

            for j in range(predictions.shape[1]):
                time_idx = decoder_time_idx[i, j]
                time = original_data["time"].min() + pd.Timedelta(hours=int(time_idx))

                # Extract quantiles
                quantiles = [0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98]
                pred_values = predictions[i, j, :]

                results.append({
                    "time": time,
                    "zone_id": zone_id,
                    "archetype_id": archetype_id,
                    "prediction": pred_values[3],  # Median (0.5 quantile)
                    "p02": pred_values[0],
                    "p10": pred_values[1],
                    "p25": pred_values[2],
                    "p75": pred_values[4],
                    "p90": pred_values[5],
                    "p98": pred_values[6],
                    "confidence_80_lower": pred_values[1],
                    "confidence_80_upper": pred_values[5],
                    "confidence_95_lower": pred_values[0],
                    "confidence_95_upper": pred_values[6]
                })

        return pd.DataFrame(results)

    def evaluate(
        self,
        test_loader: torch.utils.data.DataLoader
    ) -> Dict[str, float]:
        """
        Evaluate the model on test data.

        Args:
            test_loader: Test data loader

        Returns:
            Dictionary with evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        self.logger.info("Evaluating model on test data...")

        # Generate predictions
        raw_predictions, x = self.model.predict(
            test_loader,
            mode="raw",
            return_x=True
        )

        # Calculate metrics
        metrics = {}

        # SMAPE
        actuals = x["decoder_target"].detach().cpu().numpy()
        predictions = raw_predictions["prediction"][:, :, 3].detach().cpu().numpy()  # Median

        smape = self._calculate_smape(actuals, predictions)
        metrics["smape"] = smape

        # MAPE
        mape = self._calculate_mape(actuals, predictions)
        metrics["mape"] = mape

        # RMSE
        rmse = self._calculate_rmse(actuals, predictions)
        metrics["rmse"] = rmse

        self.logger.info(f"Evaluation metrics: {metrics}")

        return metrics

    def _calculate_smape(self, actuals: np.ndarray, predictions: np.ndarray) -> float:
        """Calculate Symmetric Mean Absolute Percentage Error."""
        mask = actuals != 0
        return np.mean(
            2 * np.abs(predictions[mask] - actuals[mask]) /
            (np.abs(actuals[mask]) + np.abs(predictions[mask]))
        ) * 100

    def _calculate_mape(self, actuals: np.ndarray, predictions: np.ndarray) -> float:
        """Calculate Mean Absolute Percentage Error."""
        mask = actuals != 0
        return np.mean(
            np.abs((actuals[mask] - predictions[mask]) / actuals[mask])
        ) * 100

    def _calculate_rmse(self, actuals: np.ndarray, predictions: np.ndarray) -> float:
        """Calculate Root Mean Square Error."""
        return np.sqrt(np.mean((actuals - predictions) ** 2))

    def save_model(self, path: Optional[str] = None) -> str:
        """
        Save the trained model.

        Args:
            path: Path to save model (default: model_dir/tft_model.ckpt)

        Returns:
            Path where model was saved
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        path = path or os.path.join(self.tft_config.model_dir, "tft_model.ckpt")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self.trainer.save_checkpoint(str(path))

        self.logger.info(f"Model saved to: {path}")

        return str(path)

    def load_model(self, path: str) -> None:
        """
        Load a trained model.

        Args:
            path: Path to saved model checkpoint
        """
        self.logger.info(f"Loading model from: {path}")

        self.model = TemporalFusionTransformer.load_from_checkpoint(path)

        self.logger.info("Model loaded successfully")


if __name__ == "__main__":
    # Example usage
    forecaster = TFTForecaster()

    # Load synthetic data
    data_path = "data/synthetic/ev_demand.csv"
    if Path(data_path).exists():
        data = pd.read_csv(data_path)

        # Prepare data
        dataset = forecaster.prepare_data(data)

        # Create data loaders
        train_loader, val_loader = forecaster.create_data_loaders()

        # Build model
        forecaster.build_model()

        # Train model
        metrics = forecaster.train(train_loader, val_loader)

        print(f"Training metrics: {metrics}")

        # Save model
        forecaster.save_model()
    else:
        print(f"Data file not found: {data_path}")
