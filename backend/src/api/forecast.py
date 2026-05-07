"""
Forecast API
Production-grade FastAPI endpoints for EV demand forecasting.
"""

import logging
import sys
import os

# Ensure the `src` directory is on sys.path so sibling packages
# (models, db, etc.) are importable when this file is executed
# directly (e.g. `python backend/src/api/forecast.py`).
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Create a simple config class for fallback
class SimpleConfig:
    def __init__(self):
        self.log_level = "INFO"
        self.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.device = "auto"
        self.num_workers = 4
        self.pin_memory = True

try:
    from models.config import ModelConfig, get_config
    from models.tft.forecaster import TFTForecaster
    from models.lstm.anomaly_detector import AnomalyDetector
    from models.multi_resolution import MultiResolutionPredictor
    from db.confidence_scorer import DataConfidenceScorer, DataSource, ConfidenceLevel
except ImportError:
    # Fallback for direct execution
    ModelConfig = None
    def get_config(config_path=None):
        return None
    TFTForecaster = None
    AnomalyDetector = None
    MultiResolutionPredictor = None
    DataConfidenceScorer = None
    DataSource = None
    ConfidenceLevel = None


# Pydantic models for API requests/responses
class ForecastRequest(BaseModel):
    """Request model for forecast generation."""

    zone_id: Optional[str] = Field(None, description="Zone ID (optional, forecasts all zones if not provided)")
    archetype_id: Optional[str] = Field(None, description="Archetype ID (optional)")
    horizon_hours: int = Field(72, ge=1, le=168, description="Forecast horizon in hours (1-168)")
    start_time: Optional[str] = Field(None, description="Start time in ISO format (default: now)")
    resolution: str = Field("zone", description="Resolution: zone, sub_zone, or all")

    class Config:
        json_schema_extra = {
            "example": {
                "zone_id": "Z01",
                "horizon_hours": 72,
                "resolution": "zone"
            }
        }


class ForecastResponse(BaseModel):
    """Response model for forecast data."""

    time: str
    zone_id: str
    archetype_id: Optional[str] = None
    cell_id: Optional[str] = None
    feeder_id: Optional[str] = None
    prediction: float
    confidence_80_lower: float
    confidence_80_upper: float
    confidence_95_lower: float
    confidence_95_upper: float
    confidence: str = "HIGH"


class AnomalyAlert(BaseModel):
    """Model for anomaly alerts."""

    time: str
    zone_id: str
    severity: str
    reconstruction_error: float
    threshold: float
    sigma_score: float
    message: str


class ForecastAPI:
    """Production-grade Forecast API."""

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or get_config() or SimpleConfig()

        self.app = FastAPI(
            title="UrjaYukti AI Forecast API",
            description="EV Demand Forecasting and Anomaly Detection API",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )

        self.logger = logging.getLogger(__name__)

        # Initialize models
        self.forecaster: Optional[TFTForecaster] = None
        self.anomaly_detector: Optional[AnomalyDetector] = None
        self.multi_resolution_predictor: Optional[MultiResolutionPredictor] = None
        self.confidence_scorer = DataConfidenceScorer() if DataConfidenceScorer else None

        # Setup routes
        self._setup_routes()

        # Load models if available
        self._load_models()

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint with API information."""
            return {
                "name": "UrjaYukti AI Forecast API",
                "version": "1.0.0",
                "status": "operational" if self.forecaster else "initializing",
                "endpoints": {
                    "forecast": "/api/forecast",
                    "anomalies": "/api/anomalies",
                    "health": "/api/health",
                    "confidence": "/api/confidence"
                }
            }

        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "forecaster_loaded": self.forecaster is not None,
                "anomaly_detector_loaded": self.anomaly_detector is not None,
                "multi_resolution_loaded": self.multi_resolution_predictor is not None,
                "timestamp": datetime.now().isoformat()
            }

        @self.app.get("/api/confidence")
        async def get_confidence():
            """Get overall data confidence status."""
            return self.confidence_scorer.get_overall_confidence()

        @self.app.post("/api/forecast", response_model=List[ForecastResponse])
        async def generate_forecast(request: ForecastRequest):
            """
            Generate EV demand forecast.

            - **zone_id**: Optional zone ID (forecasts all zones if not provided)
            - **archetype_id**: Optional archetype ID
            - **horizon_hours**: Forecast horizon in hours (1-168)
            - **start_time**: Optional start time in ISO format
            - **resolution**: Resolution level (zone, sub_zone, or all)
            """
            if self.forecaster is None:
                raise HTTPException(
                    status_code=503,
                    detail="Forecaster not initialized. Please wait for model loading."
                )

            try:
                # Parse start time
                start_time = datetime.fromisoformat(request.start_time) if request.start_time else datetime.now()

                # Load recent data for prediction
                data = self._load_recent_data(
                    zone_id=request.zone_id,
                    archetype_id=request.archetype_id,
                    hours_back=168  # 7 days
                )

                if data.empty:
                    raise HTTPException(
                        status_code=404,
                        detail="No data available for the specified parameters"
                    )

                # Generate predictions based on resolution
                if request.resolution == "zone":
                    predictions = self.forecaster.predict(data, horizon_hours=request.horizon_hours)
                elif request.resolution == "sub_zone":
                    if self.multi_resolution_predictor is None:
                        raise HTTPException(
                            status_code=503,
                            detail="Multi-resolution predictor not initialized"
                        )
                    zone_preds = self.forecaster.predict(data, horizon_hours=request.horizon_hours)
                    predictions = self.multi_resolution_predictor.predict_sub_zone_level(
                        zone_preds,
                        request.zone_id or data["zone_id"].iloc[0],
                        request.horizon_hours
                    )
                elif request.resolution == "all":
                    if self.multi_resolution_predictor is None:
                        raise HTTPException(
                            status_code=503,
                            detail="Multi-resolution predictor not initialized"
                        )
                    predictions = self.multi_resolution_predictor.predict_all_resolutions(
                        data,
                        request.horizon_hours
                    )
                    # Flatten all resolutions
                    all_preds = []
                    for res, df in predictions.items():
                        if not df.empty:
                            all_preds.append(df)
                    predictions = pd.concat(all_preds, ignore_index=True)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid resolution: {request.resolution}. Must be 'zone', 'sub_zone', or 'all'"
                    )

                # Filter by zone if specified
                if request.zone_id:
                    predictions = predictions[predictions["zone_id"] == request.zone_id]

                # Filter by archetype if specified
                if request.archetype_id:
                    predictions = predictions[predictions["archetype_id"] == request.archetype_id]

                # Convert to response format
                response = []
                for _, row in predictions.iterrows():
                    response.append(ForecastResponse(
                        time=row["time"].isoformat() if hasattr(row["time"], "isoformat") else str(row["time"]),
                        zone_id=row["zone_id"],
                        archetype_id=row.get("archetype_id"),
                        cell_id=row.get("cell_id"),
                        feeder_id=row.get("feeder_id"),
                        prediction=float(row["prediction"]),
                        confidence_80_lower=float(row["confidence_80_lower"]),
                        confidence_80_upper=float(row["confidence_80_upper"]),
                        confidence_95_lower=float(row["confidence_95_lower"]),
                        confidence_95_upper=float(row["confidence_95_upper"]),
                        confidence="HIGH"  # Default confidence
                    ))

                return response

            except Exception as e:
                self.logger.error(f"Error generating forecast: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/anomalies", response_model=List[AnomalyAlert])
        async def get_anomalies(
            zone_id: Optional[str] = Query(None, description="Zone ID filter"),
            hours_back: int = Query(24, ge=1, le=168, description="Hours to look back"),
            min_severity: str = Query("MEDIUM", description="Minimum severity: LOW, MEDIUM, HIGH, CRITICAL")
        ):
            """
            Get recent anomaly alerts.

            - **zone_id**: Optional zone ID filter
            - **hours_back**: Hours to look back (1-168)
            - **min_severity**: Minimum severity level
            """
            if self.anomaly_detector is None:
                raise HTTPException(
                    status_code=503,
                    detail="Anomaly detector not initialized"
                )

            try:
                # Load recent data
                data = self._load_recent_data(zone_id=zone_id, hours_back=hours_back)

                if data.empty:
                    return []

                # Detect anomalies
                anomalies = self.anomaly_detector.detect_anomalies(data, return_details=True)

                # Filter by severity
                severity_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
                min_sev_level = severity_order.get(min_severity, 0)
                anomalies = anomalies[
                    anomalies["severity"].apply(lambda x: severity_order.get(x, 0) >= min_sev_level)
                ]

                # Convert to response format
                response = []
                for _, row in anomalies.iterrows():
                    if row["is_anomaly"]:
                        response.append(AnomalyAlert(
                            time=row["time"].isoformat() if hasattr(row["time"], "isoformat") else str(row["time"]),
                            zone_id=row["zone_id"],
                            severity=row["severity"],
                            reconstruction_error=float(row["reconstruction_error"]),
                            threshold=float(row["threshold"]),
                            sigma_score=float(row["sigma_score"]),
                            message=f"Anomaly detected with {row['sigma_score']:.2f}σ deviation"
                        ))

                return response

            except Exception as e:
                self.logger.error(f"Error getting anomalies: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/forecast/stats")
        async def get_forecast_stats(
            zone_id: Optional[str] = Query(None, description="Zone ID filter")
        ):
            """Get forecast statistics and accuracy metrics."""
            if self.forecaster is None:
                raise HTTPException(
                    status_code=503,
                    detail="Forecaster not initialized"
                )

            try:
                # Load recent data
                data = self._load_recent_data(zone_id=zone_id, hours_back=168)

                if data.empty:
                    return {"status": "no_data"}

                # Generate predictions
                predictions = self.forecaster.predict(data, horizon_hours=24)

                # Calculate statistics
                stats = {
                    "zone_id": zone_id,
                    "forecast_horizon_hours": 24,
                    "prediction_count": len(predictions),
                    "total_predicted_demand_kw": predictions["prediction"].sum(),
                    "average_demand_kw": predictions["prediction"].mean(),
                    "peak_demand_kw": predictions["prediction"].max(),
                    "peak_time": predictions.loc[predictions["prediction"].idxmax(), "time"].isoformat()
                    if not predictions.empty else None,
                    "confidence": "HIGH"
                }

                return stats

            except Exception as e:
                self.logger.error(f"Error getting forecast stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _load_recent_data(
        self,
        zone_id: Optional[str] = None,
        archetype_id: Optional[str] = None,
        hours_back: int = 168
    ) -> pd.DataFrame:
        """Load recent data for prediction."""
        # In production, this would load from database
        # For now, load from synthetic data file
        data_path = Path("data/synthetic/ev_demand.csv")

        if not data_path.exists():
            return pd.DataFrame()

        data = pd.read_csv(data_path)
        data["time"] = pd.to_datetime(data["time"])

        # Filter by time
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        data = data[data["time"] >= cutoff_time]

        # Filter by zone
        if zone_id:
            data = data[data["zone_id"] == zone_id]

        # Filter by archetype
        if archetype_id:
            data = data[data["archetype_id"] == archetype_id]

        return data

    def _load_models(self):
        """Load trained models if available."""
        model_dir = Path("data/models")

        # Load TFT forecaster
        tft_path = model_dir / "tft" / "tft_model.ckpt"
        if tft_path.exists():
            try:
                self.forecaster = TFTForecaster(self.config)
                self.forecaster.load_model(str(tft_path))
                self.logger.info("TFT forecaster loaded successfully")
            except Exception as e:
                self.logger.error(f"Error loading TFT forecaster: {e}")

        # Load anomaly detector
        lstm_path = model_dir / "lstm" / "lstm_anomaly_model.ckpt"
        if lstm_path.exists():
            try:
                self.anomaly_detector = AnomalyDetector(self.config)
                self.anomaly_detector.load_model(str(lstm_path))
                self.logger.info("LSTM anomaly detector loaded successfully")
            except Exception as e:
                self.logger.error(f"Error loading LSTM anomaly detector: {e}")

        # Initialize multi-resolution predictor
        if self.forecaster:
            self.multi_resolution_predictor = MultiResolutionPredictor(self.forecaster, self.config)

            # Load zone polygons if available
            polygons_path = Path("data/osm/zone_polygons.geojson")
            if polygons_path.exists():
                self.multi_resolution_predictor.load_zone_polygons(str(polygons_path))

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the API server."""
        self.logger.info(f"Starting Forecast API on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create and run API
    api = ForecastAPI()
    api.run()
