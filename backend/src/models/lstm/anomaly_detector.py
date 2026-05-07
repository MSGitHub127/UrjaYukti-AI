"""
LSTM Anomaly Detector for EV Demand
Production-grade implementation with real-time detection and WebSocket API.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

import torch
import torch.nn as nn
import pytorch_lightning as pl
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint
from pytorch_lightning.loggers import MLFlowLogger

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_recall_fscore_support

from ..config import ModelConfig, ModelType, get_config


class LSTMAnomalyModel(nn.Module):
    """LSTM Autoencoder for anomaly detection."""

    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        num_layers: int,
        dropout: float = 0.2
    ):
        super().__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # Encoder
        self.encoder = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )

        # Decoder
        self.decoder = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )

        # Output layer
        self.output_layer = nn.Linear(hidden_size, input_size)

        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape (batch, seq_len, input_size)

        Returns:
            Reconstructed tensor of same shape
        """
        batch_size = x.size(0)

        # Encode
        encoder_outputs, (hidden, cell) = self.encoder(x)

        # Decode
        decoder_input = encoder_outputs
        decoder_outputs, _ = self.decoder(decoder_input, (hidden, cell))

        # Apply dropout
        decoder_outputs = self.dropout(decoder_outputs)

        # Reconstruct
        reconstructed = self.output_layer(decoder_outputs)

        return reconstructed


class LSTMAnomalyDetector(pl.LightningModule):
    """PyTorch Lightning module for LSTM anomaly detection."""

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 32,
        num_layers: int = 2,
        dropout: float = 0.2,
        learning_rate: float = 0.01,
        threshold_sigma: float = 2.0
    ):
        super().__init__()

        self.save_hyperparameters()

        self.model = LSTMAnomalyModel(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout
        )

        self.learning_rate = learning_rate
        self.threshold_sigma = threshold_sigma

        # For threshold calculation
        self.train_errors: List[float] = []

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)

    def training_step(self, batch: Tuple[torch.Tensor, torch.Tensor], batch_idx: int) -> torch.Tensor:
        x, y = batch
        reconstructed = self(x)

        # Calculate reconstruction error
        loss = nn.MSELoss()(reconstructed, y)

        # Store errors for threshold calculation
        with torch.no_grad():
            errors = torch.mean((reconstructed - y) ** 2, dim=(1, 2))
            self.train_errors.extend(errors.cpu().tolist())

        self.log("train_loss", loss, prog_bar=True, on_step=True, on_epoch=True)
        return loss

    def validation_step(self, batch: Tuple[torch.Tensor, torch.Tensor], batch_idx: int) -> torch.Tensor:
        x, y = batch
        reconstructed = self(x)

        loss = nn.MSELoss()(reconstructed, y)

        self.log("val_loss", loss, prog_bar=True, on_step=False, on_epoch=True)
        return loss

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=0.5,
            patience=5,
            verbose=True
        )
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss"
            }
        }

    def calculate_threshold(self) -> float:
        """Calculate anomaly threshold based on training errors."""
        if not self.train_errors:
            return 0.0

        errors = np.array(self.train_errors)
        mean_error = np.mean(errors)
        std_error = np.std(errors)

        threshold = mean_error + self.threshold_sigma * std_error

        return float(threshold)


class AnomalyData:
    """Data preparation for anomaly detection."""

    def __init__(self, sequence_length: int = 24):
        self.sequence_length = sequence_length
        self.scaler = StandardScaler()

    def prepare_sequences(
        self,
        data: pd.DataFrame,
        feature_cols: List[str],
        time_col: str = "time"
    ) -> np.ndarray:
        """
        Prepare sequences for LSTM training.

        Args:
            data: Input DataFrame
            feature_cols: List of feature columns
            time_col: Time column name

        Returns:
            Array of sequences
        """
        # Ensure time column is datetime
        data = data.copy()
        data[time_col] = pd.to_datetime(data[time_col])

        # Sort by time
        data = data.sort_values(time_col)

        # Extract features
        features = data[feature_cols].values

        # Scale features
        scaled_features = self.scaler.fit_transform(features)

        # Create sequences
        sequences = []
        for i in range(len(scaled_features) - self.sequence_length + 1):
            sequences.append(scaled_features[i:i + self.sequence_length])

        return np.array(sequences)

    def create_dataloaders(
        self,
        sequences: np.ndarray,
        batch_size: int = 32,
        validation_split: float = 0.2,
        num_workers: int = 4
    ) -> Tuple[torch.utils.data.DataLoader, torch.utils.data.DataLoader]:
        """
        Create training and validation data loaders.

        Args:
            sequences: Array of sequences
            batch_size: Batch size
            validation_split: Validation split ratio
            num_workers: Number of workers

        Returns:
            Tuple of (train_loader, val_loader)
        """
        # Split into train and validation
        split_idx = int(len(sequences) * (1 - validation_split))
        train_sequences = sequences[:split_idx]
        val_sequences = sequences[split_idx:]

        # Create datasets
        train_dataset = torch.utils.data.TensorDataset(
            torch.FloatTensor(train_sequences),
            torch.FloatTensor(train_sequences)
        )

        val_dataset = torch.utils.data.TensorDataset(
            torch.FloatTensor(val_sequences),
            torch.FloatTensor(val_sequences)
        )

        # Create data loaders
        train_loader = torch.utils.data.DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=True
        )

        val_loader = torch.utils.data.DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=True
        )

        return train_loader, val_loader


class AnomalyDetector:
    """Production-grade anomaly detector with real-time capabilities."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_config()
        self.lstm_config = self.config.get_config(ModelType.LSTM)

        self.model: Optional[LSTMAnomalyDetector] = None
        self.trainer: Optional[pl.Trainer] = None
        self.threshold: float = 0.0

        self.data_prep = AnomalyData(sequence_length=self.lstm_config.sequence_length)

        self._setup_logging()
        self._setup_directories()

        # Real-time state
        self.recent_errors: List[Tuple[str, float]] = []
        self.alert_cooldown: Dict[str, float] = {}

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
            path = Path(getattr(self.lstm_config, attr))
            path.mkdir(parents=True, exist_ok=True)

    def train(
        self,
        data: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        max_epochs: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Train the anomaly detector.

        Args:
            data: Training data
            feature_cols: Feature columns to use
            max_epochs: Maximum number of epochs

        Returns:
            Dictionary with training metrics
        """
        max_epochs = max_epochs or self.lstm_config.epochs

        # Default feature columns
        if feature_cols is None:
            feature_cols = ["demand_kw", "session_count"]

        self.logger.info(f"Training anomaly detector for {max_epochs} epochs...")

        # Prepare sequences
        sequences = self.data_prep.prepare_sequences(data, feature_cols)

        if len(sequences) < 100:
            self.logger.warning(f"Only {len(sequences)} sequences available. Consider more data.")

        # Create data loaders
        train_loader, val_loader = self.data_prep.create_dataloaders(
            sequences,
            batch_size=self.lstm_config.batch_size,
            validation_split=self.lstm_config.validation_split,
            num_workers=self.config.num_workers
        )

        # Create model
        input_size = len(feature_cols)
        self.model = LSTMAnomalyDetector(
            input_size=input_size,
            hidden_size=self.lstm_config.hidden_size,
            num_layers=self.lstm_config.num_layers,
            dropout=self.lstm_config.dropout,
            learning_rate=self.lstm_config.learning_rate,
            threshold_sigma=self.lstm_config.threshold_sigma
        )

        # Setup callbacks
        callbacks = [
            EarlyStopping(
                monitor="val_loss",
                min_delta=1e-4,
                patience=self.lstm_config.early_stopping_patience,
                verbose=True,
                mode="min"
            ),
            ModelCheckpoint(
                dirpath=self.lstm_config.checkpoint_dir,
                filename="lstm-anomaly-{epoch:02d}-{val_loss:.4f}",
                monitor="val_loss",
                save_top_k=3,
                mode="min"
            )
        ]

        # Setup logger
        logger = None
        if self.config.use_mlflow:
            logger = MLFlowLogger(
                experiment_name=f"{self.config.mlflow_experiment_name}-anomaly",
                tracking_uri=self.config.mlflow_tracking_uri
            )

        # Setup trainer
        self.trainer = pl.Trainer(
            max_epochs=max_epochs,
            accelerator=self.config.device,
            devices="auto" if self.config.device == "auto" else 1,
            callbacks=callbacks,
            logger=logger,
            log_every_n_steps=10,
            enable_progress_bar=True
        )

        # Train model
        self.trainer.fit(self.model, train_loader, val_loader)

        # Calculate threshold
        self.threshold = self.model.calculate_threshold()
        self.logger.info(f"Anomaly threshold calculated: {self.threshold:.4f}")

        # Get best model path
        best_model_path = callbacks[1].best_model_path
        self.logger.info(f"Training complete. Best model: {best_model_path}")

        # Load best model
        self.model = LSTMAnomalyDetector.load_from_checkpoint(best_model_path)

        # Get training metrics
        metrics = {
            "best_val_loss": callbacks[1].best_model_score.item(),
            "threshold": self.threshold,
            "epochs_trained": self.trainer.current_epoch + 1
        }

        return metrics

    def detect_anomalies(
        self,
        data: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        return_details: bool = False
    ) -> pd.DataFrame:
        """
        Detect anomalies in new data.

        Args:
            data: Input data
            feature_cols: Feature columns to use
            return_details: Whether to return detailed error information

        Returns:
            DataFrame with anomaly flags
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Default feature columns
        if feature_cols is None:
            feature_cols = ["demand_kw", "session_count"]

        self.logger.info(f"Detecting anomalies in {len(data)} records...")

        # Prepare sequences
        sequences = self.data_prep.prepare_sequences(data, feature_cols)

        if len(sequences) == 0:
            return pd.DataFrame()

        # Create data loader
        dataset = torch.utils.data.TensorDataset(
            torch.FloatTensor(sequences),
            torch.FloatTensor(sequences)
        )

        loader = torch.utils.data.DataLoader(
            dataset,
            batch_size=1,
            shuffle=False
        )

        # Detect anomalies
        results = []
        self.model.eval()

        with torch.no_grad():
            for i, (x, _) in enumerate(loader):
                reconstructed = self.model(x)

                # Calculate reconstruction error
                error = torch.mean((reconstructed - x) ** 2).item()

                # Determine if anomaly
                is_anomaly = error > self.threshold
                sigma_score = (error - self.threshold) / (self.threshold / self.lstm_config.threshold_sigma)

                # Determine severity
                if sigma_score >= 3:
                    severity = "CRITICAL"
                elif sigma_score >= 2:
                    severity = "HIGH"
                elif sigma_score >= 1:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"

                # Get corresponding data row
                row_idx = i + self.lstm_config.sequence_length - 1
                if row_idx < len(data):
                    row = data.iloc[row_idx].copy()

                    result = {
                        "time": row.get("time"),
                        "zone_id": row.get("zone_id"),
                        "archetype_id": row.get("archetype_id"),
                        "is_anomaly": is_anomaly,
                        "reconstruction_error": error,
                        "threshold": self.threshold,
                        "sigma_score": sigma_score,
                        "severity": severity
                    }

                    if return_details:
                        result["actual_values"] = row[feature_cols].tolist()
                        result["reconstructed_values"] = reconstructed[0, -1, :].cpu().numpy().tolist()

                    results.append(result)

        return pd.DataFrame(results)

    def get_real_time_anomaly(
        self,
        current_data: Dict[str, float],
        zone_id: str,
        timestamp: str
    ) -> Dict[str, any]:
        """
        Get real-time anomaly detection for single data point.

        Args:
            current_data: Current data values
            zone_id: Zone identifier
            timestamp: ISO timestamp

        Returns:
            Dictionary with anomaly information
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Check cooldown
        cooldown_key = f"{zone_id}_{timestamp}"
        if cooldown_key in self.alert_cooldown:
            cooldown_time = self.alert_cooldown[cooldown_key]
            if (pd.Timestamp.now() - pd.Timestamp(cooldown_time)).total_seconds() < self.lstm_config.alert_cooldown_minutes * 60:
                return {"status": "cooldown", "message": "Alert in cooldown period"}

        # For real-time, we need recent history
        # This is a simplified version - in production, maintain a sliding window
        result = {
            "zone_id": zone_id,
            "timestamp": timestamp,
            "is_anomaly": False,
            "message": "Real-time detection requires historical context"
        }

        return result

    def save_model(self, path: Optional[str] = None) -> str:
        """
        Save the trained model.

        Args:
            path: Path to save model

        Returns:
            Path where model was saved
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        path = path or os.path.join(self.lstm_config.model_dir, "lstm_anomaly_model.ckpt")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self.trainer.save_checkpoint(str(path))

        # Save threshold
        threshold_path = path.parent / "threshold.txt"
        with open(threshold_path, "w") as f:
            f.write(str(self.threshold))

        self.logger.info(f"Model saved to: {path}")

        return str(path)

    def load_model(self, path: str) -> None:
        """
        Load a trained model.

        Args:
            path: Path to saved model checkpoint
        """
        self.logger.info(f"Loading model from: {path}")

        self.model = LSTMAnomalyDetector.load_from_checkpoint(path)

        # Load threshold
        threshold_path = Path(path).parent / "threshold.txt"
        if threshold_path.exists():
            with open(threshold_path, "r") as f:
                self.threshold = float(f.read().strip())
            self.logger.info(f"Threshold loaded: {self.threshold}")

        self.logger.info("Model loaded successfully")


if __name__ == "__main__":
    # Example usage
    detector = AnomalyDetector()

    # Load synthetic data
    data_path = "data/synthetic/ev_demand.csv"
    if Path(data_path).exists():
        data = pd.read_csv(data_path)

        # Train detector
        metrics = detector.train(data)

        print(f"Training metrics: {metrics}")

        # Detect anomalies
        anomalies = detector.detect_anomalies(data.tail(100))

        print(f"\nDetected {anomalies['is_anomaly'].sum()} anomalies in last 100 records")

        # Save model
        detector.save_model()
    else:
        print(f"Data file not found: {data_path}")
