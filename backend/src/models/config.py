"""
Configuration management for UrjaYukti AI models.
Loads configuration from YAML files with validation and defaults.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ModelType(Enum):
    TFT = "tft"
    LSTM = "lstm"
    BEHAVIOR = "behavior"
    ARIMA = "arima"


@dataclass
class TFTConfig:
    """Configuration for Temporal Fusion Transformer."""

    # Model architecture
    hidden_size: int = 64
    num_attention_heads: int = 4
    dropout: float = 0.1
    hidden_continuous_size: int = 8

    # Training parameters
    batch_size: int = 64
    learning_rate: float = 0.001
    epochs: int = 100
    early_stopping_patience: int = 10
    gradient_clip_val: float = 0.01

    # Forecasting parameters
    horizon_hours: int = 72
    input_window_hours: int = 168  # 7 days
    prediction_interval_length: int = 1  # hours

    # Data parameters
    max_encoder_length: int = 168
    min_encoder_length: int = 24
    max_prediction_length: int = 72

    # Validation
    validation_split: float = 0.2
    test_split: float = 0.1

    # Paths
    model_dir: str = "data/models/tft"
    checkpoint_dir: str = "data/models/tft/checkpoints"
    log_dir: str = "logs/tft"

    # Zones
    zones: list = field(default_factory=lambda: ["Z01", "Z02", "Z03", "Z04", "Z05", "Z06"])

    # Archetypes
    archetypes: list = field(default_factory=lambda: ["A01", "A02", "A03"])

    # Confidence intervals
    confidence_levels: list = field(default_factory=lambda: [0.80, 0.95])

    # Target MAPE
    target_mape: float = 0.12  # 12%


@dataclass
class LSTMConfig:
    """Configuration for LSTM Anomaly Detector."""

    # Model architecture
    sequence_length: int = 24  # hours
    hidden_size: int = 32
    num_layers: int = 2
    dropout: float = 0.2

    # Training parameters
    batch_size: int = 32
    learning_rate: float = 0.01
    epochs: int = 50
    early_stopping_patience: int = 5

    # Anomaly detection
    threshold_sigma: float = 2.0  # 2-sigma threshold
    anomaly_window_hours: int = 1

    # Paths
    model_dir: str = "data/models/lstm"
    checkpoint_dir: str = "data/models/lstm/checkpoints"
    log_dir: str = "logs/lstm"

    # Real-time parameters
    update_interval_minutes: int = 15
    alert_cooldown_minutes: int = 30


@dataclass
class BehaviorConfig:
    """Configuration for User Behavior Model."""

    # Model parameters
    compliance_window_days: int = 30
    min_compliance_samples: int = 100
    feature_window_days: int = 7

    # Incentive parameters
    incentive_sensitivity: float = 0.5  # ₹/kWh impact factor
    time_preference_weight: float = 0.3
    baseline_compliance_rate: float = 0.4

    # Training parameters
    batch_size: int = 128
    learning_rate: float = 0.001
    epochs: int = 30
    validation_split: float = 0.2

    # Paths
    model_dir: str = "data/models/behavior"
    checkpoint_dir: str = "data/models/behavior/checkpoints"
    log_dir: str = "logs/behavior"

    # Compliance probability
    max_probability: float = 0.8
    min_probability: float = 0.1


@dataclass
class ARIMAConfig:
    """Configuration for ARIMA baseline model."""

    # ARIMA parameters
    p: int = 5  # Auto-regressive order
    d: int = 1  # Differencing order
    q: int = 0  # Moving average order

    # Seasonal parameters
    seasonal_p: int = 1
    seasonal_d: int = 1
    seasonal_q: int = 1
    seasonal_period: int = 24  # Daily seasonality

    # Forecasting parameters
    horizon_hours: int = 72
    confidence_level: float = 0.95

    # Paths
    model_dir: str = "data/models/arima"
    log_dir: str = "logs/arima"

    # Expected baseline MAPE
    baseline_mape: float = 0.22  # 22%


@dataclass
class ModelConfig:
    """Main configuration container for all models."""

    tft: TFTConfig = field(default_factory=TFTConfig)
    lstm: LSTMConfig = field(default_factory=LSTMConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    arima: ARIMAConfig = field(default_factory=ARIMAConfig)

    # General settings
    random_seed: int = 42
    device: str = "auto"  # auto, cpu, cuda
    num_workers: int = 4
    pin_memory: bool = True

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # MLflow tracking
    use_mlflow: bool = True
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment_name: str = "urjayukti-ai"

    # Additional config sections (drift, cross_zone, roi)
    drift: Dict[str, Any] = field(default_factory=dict)
    cross_zone: Dict[str, Any] = field(default_factory=dict)
    roi: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, config_path: str) -> "ModelConfig":
        """Load configuration from YAML file."""
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            config_dict = yaml.safe_load(f)

        return cls._from_dict(config_dict)

    @classmethod
    def _from_dict(cls, config_dict: Dict[str, Any]) -> "ModelConfig":
        """Create configuration from dictionary."""
        tft_config = TFTConfig(**config_dict.get("tft", {}))
        lstm_config = LSTMConfig(**config_dict.get("lstm", {}))
        behavior_config = BehaviorConfig(**config_dict.get("behavior", {}))
        arima_config = ARIMAConfig(**config_dict.get("arima", {}))

        general_config = {
            k: v for k, v in config_dict.items()
            if k not in ["tft", "lstm", "behavior", "arima"]
        }

        return cls(
            tft=tft_config,
            lstm=lstm_config,
            behavior=behavior_config,
            arima=arima_config,
            **general_config
        )

    def to_yaml(self, output_path: str) -> None:
        """Save configuration to YAML file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = {
            "tft": self.tft.__dict__,
            "lstm": self.lstm.__dict__,
            "behavior": self.behavior.__dict__,
            "arima": self.arima.__dict__,
            "random_seed": self.random_seed,
            "device": self.device,
            "num_workers": self.num_workers,
            "pin_memory": self.pin_memory,
            "log_level": self.log_level,
            "log_format": self.log_format,
            "use_mlflow": self.use_mlflow,
            "mlflow_tracking_uri": self.mlflow_tracking_uri,
            "mlflow_experiment_name": self.mlflow_experiment_name
        }

        with open(output_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False)

    def get_config(self, model_type: ModelType) -> Any:
        """Get configuration for specific model type."""
        config_map = {
            ModelType.TFT: self.tft,
            ModelType.LSTM: self.lstm,
            ModelType.BEHAVIOR: self.behavior,
            ModelType.ARIMA: self.arima
        }
        return config_map.get(model_type)

    def create_directories(self) -> None:
        """Create all necessary directories."""
        for config in [self.tft, self.lstm, self.behavior, self.arima]:
            for attr in ["model_dir", "checkpoint_dir", "log_dir"]:
                if hasattr(config, attr):
                    path = Path(getattr(config, attr))
                    path.mkdir(parents=True, exist_ok=True)


# Global configuration instance
_config: Optional[ModelConfig] = None


def get_config(config_path: Optional[str] = None) -> ModelConfig:
    """Get global configuration instance."""
    global _config

    if _config is None:
        if config_path is None:
            # Try to find config file
            config_path = os.environ.get(
                "URJAYUKTI_CONFIG",
                "config/model_config.yaml"
            )

        if Path(config_path).exists():
            _config = ModelConfig.from_yaml(config_path)
        else:
            # Use default configuration
            _config = ModelConfig()
            _config.create_directories()

    return _config


def set_config(config: ModelConfig) -> None:
    """Set global configuration instance."""
    global _config
    _config = config
