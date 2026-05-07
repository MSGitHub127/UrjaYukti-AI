"""
User Behavior Adoption Model
Production-grade implementation for predicting EV charging compliance behavior.
"""

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

from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_score, roc_auc_score

from ..config import ModelConfig, ModelType, get_config


class BehaviorModel(nn.Module):
    """Neural network for predicting user compliance behavior."""

    def __init__(
        self,
        input_size: int,
        hidden_sizes: List[int] = [64, 32],
        dropout: float = 0.3,
        output_size: int = 1
    ):
        super().__init__()

        self.input_size = input_size
        self.hidden_sizes = hidden_sizes
        self.dropout = dropout

        # Build layers
        layers = []
        prev_size = input_size

        for hidden_size in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.BatchNorm1d(hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_size = hidden_size

        # Output layer
        layers.append(nn.Linear(prev_size, output_size))
        layers.append(nn.Sigmoid())

        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass."""
        return self.network(x)


class BehaviorLightningModule(pl.LightningModule):
    """PyTorch Lightning module for behavior prediction."""

    def __init__(
        self,
        input_size: int,
        hidden_sizes: List[int] = [64, 32],
        dropout: float = 0.3,
        learning_rate: float = 0.001,
        class_weight: Optional[float] = None
    ):
        super().__init__()

        self.save_hyperparameters()

        self.model = BehaviorModel(
            input_size=input_size,
            hidden_sizes=hidden_sizes,
            dropout=dropout
        )

        self.learning_rate = learning_rate
        self.class_weight = class_weight

        # Loss function
        if class_weight is not None:
            pos_weight = torch.tensor([class_weight])
            self.criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        else:
            self.criterion = nn.BCELoss()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)

    def training_step(self, batch: Tuple[torch.Tensor, torch.Tensor], batch_idx: int) -> torch.Tensor:
        x, y = batch
        y_hat = self(x)

        loss = self.criterion(y_hat.squeeze(), y.float())

        self.log("train_loss", loss, prog_bar=True, on_step=True, on_epoch=True)
        return loss

    def validation_step(self, batch: Tuple[torch.Tensor, torch.Tensor], batch_idx: int) -> torch.Tensor:
        x, y = batch
        y_hat = self(x)

        loss = self.criterion(y_hat.squeeze(), y.float())

        # Calculate accuracy
        predictions = (y_hat.squeeze() > 0.5).float()
        accuracy = (predictions == y).float().mean()

        self.log("val_loss", loss, prog_bar=True, on_step=False, on_epoch=True)
        self.log("val_accuracy", accuracy, prog_bar=True, on_step=False, on_epoch=True)

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


class BehaviorPredictor:
    """Production-grade behavior adoption predictor."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_config()
        self.behavior_config = self.config.get_config(ModelType.BEHAVIOR)

        self.model: Optional[BehaviorLightningModule] = None
        self.trainer: Optional[pl.Trainer] = None

        # Feature encoders and scalers
        self.scaler = StandardScaler()
        self.zone_encoder = LabelEncoder()
        self.archetype_encoder = LabelEncoder()

        # Feature columns
        self.feature_columns = [
            "preferred_start_hour",
            "preferred_end_hour",
            "flexibility_score",
            "incentive_sensitivity",
            "incentive_amount",
            "shift_hours",
            "hour_of_day",
            "day_of_week",
            "is_weekend",
            "is_peak_hour"
        ]

        self.logger = logging.getLogger(__name__)

        self._setup_directories()

    def _setup_directories(self):
        """Create necessary directories."""
        for attr in ["model_dir", "checkpoint_dir", "log_dir"]:
            path = Path(getattr(self.behavior_config, attr))
            path.mkdir(parents=True, exist_ok=True)

    def prepare_features(
        self,
        data: pd.DataFrame,
        fit_encoders: bool = True
    ) -> pd.DataFrame:
        """
        Prepare features for behavior prediction.

        Args:
            data: Input DataFrame
            fit_encoders: Whether to fit encoders (True for training, False for inference)

        Returns:
            DataFrame with prepared features
        """
        data = data.copy()

        # Encode categorical variables
        if fit_encoders:
            if "zone_id" in data.columns:
                data["zone_encoded"] = self.zone_encoder.fit_transform(data["zone_id"])
            if "archetype_id" in data.columns:
                data["archetype_encoded"] = self.archetype_encoder.fit_transform(data["archetype_id"])
        else:
            if "zone_id" in data.columns:
                # Handle unseen zones
                known_zones = set(self.zone_encoder.classes_)
                data["zone_encoded"] = data["zone_id"].apply(
                    lambda x: self.zone_encoder.transform([x])[0] if x in known_zones else -1
                )
            if "archetype_id" in data.columns:
                known_archetypes = set(self.archetype_encoder.classes_)
                data["archetype_encoded"] = data["archetype_id"].apply(
                    lambda x: self.archetype_encoder.transform([x])[0] if x in known_archetypes else -1
                )

        # Add time-based features
        if "time" in data.columns:
            data["time"] = pd.to_datetime(data["time"])
            data["hour_of_day"] = data["time"].dt.hour
            data["day_of_week"] = data["time"].dt.dayofweek
            data["is_weekend"] = (data["day_of_week"] >= 5).astype(int)

            # Peak hour indicator
            data["is_peak_hour"] = (
                ((data["hour_of_day"] >= 7) & (data["hour_of_day"] <= 10)) |
                ((data["hour_of_day"] >= 18) & (data["hour_of_day"] <= 21))
            ).astype(int)

        # Ensure all feature columns exist
        for col in self.feature_columns:
            if col not in data.columns:
                data[col] = 0  # Default value

        # Add encoded columns to features
        if "zone_encoded" in data.columns:
            self.feature_columns.append("zone_encoded")
        if "archetype_encoded" in data.columns:
            self.feature_columns.append("archetype_encoded")

        return data

    def create_dataloaders(
        self,
        data: pd.DataFrame,
        target_col: str = "shifted",
        batch_size: Optional[int] = None,
        validation_split: Optional[float] = None
    ) -> Tuple[torch.utils.data.DataLoader, torch.utils.data.DataLoader]:
        """
        Create training and validation data loaders.

        Args:
            data: Input DataFrame
            target_col: Target column name
            batch_size: Batch size
            validation_split: Validation split ratio

        Returns:
            Tuple of (train_loader, val_loader)
        """
        batch_size = batch_size or self.behavior_config.batch_size
        validation_split = validation_split or self.behavior_config.validation_split

        # Prepare features
        data = self.prepare_features(data, fit_encoders=True)

        # Extract features and target
        features = data[self.feature_columns].values
        target = data[target_col].values

        # Scale features
        features = self.scaler.fit_transform(features)

        # Split into train and validation
        X_train, X_val, y_train, y_val = train_test_split(
            features,
            target,
            test_size=validation_split,
            random_state=self.config.random_seed,
            stratify=target
        )

        # Create datasets
        train_dataset = torch.utils.data.TensorDataset(
            torch.FloatTensor(X_train),
            torch.FloatTensor(y_train)
        )

        val_dataset = torch.utils.data.TensorDataset(
            torch.FloatTensor(X_val),
            torch.FloatTensor(y_val)
        )

        # Create data loaders
        train_loader = torch.utils.data.DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=self.config.num_workers,
            pin_memory=self.config.pin_memory
        )

        val_loader = torch.utils.data.DataLoader(
            val_dataset,
            batch_size=batch_size * 2,
            shuffle=False,
            num_workers=self.config.num_workers,
            pin_memory=self.config.pin_memory
        )

        return train_loader, val_loader

    def train(
        self,
        data: pd.DataFrame,
        target_col: str = "shifted",
        max_epochs: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Train the behavior prediction model.

        Args:
            data: Training data
            target_col: Target column name
            max_epochs: Maximum number of epochs

        Returns:
            Dictionary with training metrics
        """
        max_epochs = max_epochs or self.behavior_config.epochs

        self.logger.info(f"Training behavior model for {max_epochs} epochs...")

        # Create data loaders
        train_loader, val_loader = self.create_dataloaders(data, target_col)

        # Calculate class weight for imbalanced data
        target_values = data[target_col].values
        class_weight = None
        if np.mean(target_values) < 0.3:  # If less than 30% positive samples
            class_weight = (1 - np.mean(target_values)) / np.mean(target_values)
            self.logger.info(f"Using class weight: {class_weight:.2f}")

        # Create model
        input_size = len(self.feature_columns)
        self.model = BehaviorLightningModule(
            input_size=input_size,
            hidden_sizes=[64, 32],
            dropout=0.3,
            learning_rate=self.behavior_config.learning_rate,
            class_weight=class_weight
        )

        # Setup callbacks
        callbacks = [
            EarlyStopping(
                monitor="val_loss",
                min_delta=1e-4,
                patience=self.behavior_config.early_stopping_patience,
                verbose=True,
                mode="min"
            ),
            ModelCheckpoint(
                dirpath=self.behavior_config.checkpoint_dir,
                filename="behavior-model-{epoch:02d}-{val_loss:.4f}",
                monitor="val_loss",
                save_top_k=3,
                mode="min"
            )
        ]

        # Setup logger
        logger = None
        if self.config.use_mlflow:
            logger = MLFlowLogger(
                experiment_name=f"{self.config.mlflow_experiment_name}-behavior",
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

        # Get best model path
        best_model_path = callbacks[1].best_model_path
        self.logger.info(f"Training complete. Best model: {best_model_path}")

        # Load best model
        self.model = BehaviorLightningModule.load_from_checkpoint(best_model_path)

        # Get training metrics
        metrics = {
            "best_val_loss": callbacks[1].best_model_score.item(),
            "epochs_trained": self.trainer.current_epoch + 1,
            "class_weight": class_weight
        }

        return metrics

    def predict(
        self,
        data: pd.DataFrame,
        return_probability: bool = True
    ) -> pd.DataFrame:
        """
        Predict compliance behavior.

        Args:
            data: Input data
            return_probability: Whether to return probability scores

        Returns:
            DataFrame with predictions
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        self.logger.info(f"Generating predictions for {len(data)} records...")

        # Prepare features
        data = self.prepare_features(data, fit_encoders=False)

        # Extract features
        features = data[self.feature_columns].values

        # Scale features
        features = self.scaler.transform(features)

        # Create data loader
        dataset = torch.utils.data.TensorDataset(torch.FloatTensor(features))
        loader = torch.utils.data.DataLoader(
            dataset,
            batch_size=1,
            shuffle=False
        )

        # Generate predictions
        predictions = []
        self.model.eval()

        with torch.no_grad():
            for x, in loader:
                prob = self.model(x).squeeze().item()
                predictions.append(prob)

        # Add predictions to data
        result = data.copy()
        result["compliance_probability"] = predictions

        if return_probability:
            result["predicted_compliance"] = (result["compliance_probability"] > 0.5).astype(int)

        return result

    def calculate_compliance_probability(
        self,
        user_data: Dict[str, any],
        incentive_amount: float = 0.0,
        shift_hours: float = 0.0
    ) -> Dict[str, float]:
        """
        Calculate compliance probability for a specific user scenario.

        Args:
            user_data: User profile data
            incentive_amount: Incentive amount in ₹
            shift_hours: Recommended shift hours

        Returns:
            Dictionary with compliance probability and factors
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Create input DataFrame
        input_data = pd.DataFrame([{
            **user_data,
            "incentive_amount": incentive_amount,
            "shift_hours": shift_hours,
            "time": pd.Timestamp.now()
        }])

        # Generate prediction
        predictions = self.predict(input_data)

        # Extract probability
        probability = predictions["compliance_probability"].iloc[0]

        # Calculate factors
        factors = {
            "base_probability": self.behavior_config.baseline_compliance_rate,
            "flexibility_boost": user_data.get("flexibility_score", 0.5) * 0.3,
            "incentive_boost": incentive_amount * self.behavior_config.incentive_sensitivity * 0.01,
            "shift_penalty": max(0, shift_hours - 2) * 0.1  # Penalty for shifts > 2 hours
        }

        # Calculate total probability
        total_probability = min(
            self.behavior_config.max_probability,
            max(
                self.behavior_config.min_probability,
                sum(factors.values())
            )
        )

        return {
            "compliance_probability": probability,
            "model_prediction": probability,
            "rule_based_estimate": total_probability,
            "factors": factors,
            "recommendation": "HIGH" if probability > 0.7 else "MEDIUM" if probability > 0.4 else "LOW"
        }

    def evaluate(
        self,
        test_data: pd.DataFrame,
        target_col: str = "shifted"
    ) -> Dict[str, float]:
        """
        Evaluate the model on test data.

        Args:
            test_data: Test data
            target_col: Target column name

        Returns:
            Dictionary with evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        self.logger.info("Evaluating behavior model...")

        # Generate predictions
        predictions = self.predict(test_data)

        # Calculate metrics
        y_true = test_data[target_col].values
        y_pred = predictions["predicted_compliance"].values
        y_prob = predictions["compliance_probability"].values

        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_score(y_true, y_pred, average='binary', zero_division=0)

        try:
            auc = roc_auc_score(y_true, y_prob)
        except:
            auc = 0.0

        metrics = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "auc_roc": auc
        }

        self.logger.info(f"Evaluation metrics: {metrics}")

        return metrics

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

        path = path or os.path.join(self.behavior_config.model_dir, "behavior_model.ckpt")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        self.trainer.save_checkpoint(str(path))

        # Save encoders and scaler
        import pickle
        artifacts = {
            "scaler": self.scaler,
            "zone_encoder": self.zone_encoder,
            "archetype_encoder": self.archetype_encoder,
            "feature_columns": self.feature_columns
        }

        artifacts_path = path.parent / "behavior_artifacts.pkl"
        with open(artifacts_path, "wb") as f:
            pickle.dump(artifacts, f)

        self.logger.info(f"Model saved to: {path}")

        return str(path)

    def load_model(self, path: str) -> None:
        """
        Load a trained model.

        Args:
            path: Path to saved model checkpoint
        """
        import pickle

        self.logger.info(f"Loading model from: {path}")

        self.model = BehaviorLightningModule.load_from_checkpoint(path)

        # Load encoders and scaler
        artifacts_path = Path(path).parent / "behavior_artifacts.pkl"
        if artifacts_path.exists():
            with open(artifacts_path, "rb") as f:
                artifacts = pickle.load(f)

            self.scaler = artifacts["scaler"]
            self.zone_encoder = artifacts["zone_encoder"]
            self.archetype_encoder = artifacts["archetype_encoder"]
            self.feature_columns = artifacts["feature_columns"]

        self.logger.info("Model loaded successfully")


if __name__ == "__main__":
    # Example usage
    predictor = BehaviorPredictor()

    # Load user behavior data
    data_path = "data/feedback/user_behavior_baseline.csv"
    if Path(data_path).exists():
        data = pd.read_csv(data_path)

        # Train model
        metrics = predictor.train(data)

        print(f"Training metrics: {metrics}")

        # Save model
        predictor.save_model()
    else:
        print(f"Data file not found: {data_path}")
