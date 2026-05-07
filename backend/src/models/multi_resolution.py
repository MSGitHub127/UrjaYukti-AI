"""
Multi-Resolution Prediction System
Provides predictions at zone-level, sub-zone (50-100m grid), and feeder-level resolutions.
"""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
from scipy.interpolate import griddata

from ..config import ModelConfig, get_config
from .tft.forecaster import TFTForecaster


class MultiResolutionPredictor:
    """Multi-resolution prediction system for EV demand."""

    def __init__(
        self,
        forecaster: TFTForecaster,
        config: Optional[ModelConfig] = None
    ):
        self.forecaster = forecaster
        self.config = config or get_config()

        self.logger = logging.getLogger(__name__)

        # Resolution levels
        self.resolutions = {
            "zone": {"grid_size_m": None, "description": "Zone-level aggregation"},
            "sub_zone": {"grid_size_m": 100, "description": "100m grid cells"},
            "feeder": {"grid_size_m": None, "description": "Feeder-level aggregation"}
        }

        # Spatial data
        self.zone_polygons: Dict[str, Polygon] = {}
        self.feeder_geometries: Dict[str, gpd.GeoDataFrame] = {}
        self.grid_cells: Dict[str, List[Dict]] = {}

    def load_zone_polygons(self, polygons_path: str) -> None:
        """
        Load zone polygons from GeoJSON file.

        Args:
            polygons_path: Path to zone polygons GeoJSON file
        """
        import json

        self.logger.info(f"Loading zone polygons from: {polygons_path}")

        with open(polygons_path, "r") as f:
            geojson = json.load(f)

        for feature in geojson["features"]:
            zone_id = feature["properties"]["zone_id"]
            geometry = feature["geometry"]

            if geometry["type"] == "Polygon":
                coords = geometry["coordinates"][0]
                self.zone_polygons[zone_id] = Polygon(coords)
            elif geometry["type"] == "MultiPolygon":
                # Use the largest polygon
                polygons = [Polygon(coords[0]) for coords in geometry["coordinates"]]
                self.zone_polygons[zone_id] = max(polygons, key=lambda p: p.area)

        self.logger.info(f"Loaded {len(self.zone_polygons)} zone polygons")

    def load_feeder_geometries(self, feeders_path: str) -> None:
        """
        Load feeder geometries from GeoJSON file.

        Args:
            feeders_path: Path to feeder geometries GeoJSON file
        """
        self.logger.info(f"Loading feeder geometries from: {feeders_path}")

        gdf = gpd.read_file(feeders_path)

        for feeder_id in gdf["feeder_id"].unique():
            feeder_gdf = gdf[gdf["feeder_id"] == feeder_id]
            self.feeder_geometries[feeder_id] = feeder_gdf

        self.logger.info(f"Loaded {len(self.feeder_geometries)} feeder geometries")

    def create_sub_zone_grid(
        self,
        zone_id: str,
        grid_size_m: int = 100
    ) -> List[Dict]:
        """
        Create a grid of sub-zones within a zone.

        Args:
            zone_id: Zone identifier
            grid_size_m: Grid cell size in meters

        Returns:
            List of grid cell dictionaries
        """
        if zone_id not in self.zone_polygons:
            self.logger.warning(f"Zone {zone_id} not found in polygons")
            return []

        polygon = self.zone_polygons[zone_id]
        bounds = polygon.bounds  # (minx, miny, maxx, maxy)

        # Convert meters to degrees (approximate)
        # 1 degree ≈ 111 km at equator
        grid_size_deg = grid_size_m / 111000

        grid_cells = []

        # Create grid
        x_coords = np.arange(bounds[0], bounds[2], grid_size_deg)
        y_coords = np.arange(bounds[1], bounds[3], grid_size_deg)

        cell_id = 0
        for i, x in enumerate(x_coords):
            for j, y in enumerate(y_coords):
                # Create cell polygon
                cell_polygon = Polygon([
                    (x, y),
                    (x + grid_size_deg, y),
                    (x + grid_size_deg, y + grid_size_deg),
                    (x, y + grid_size_deg)
                ])

                # Check if cell intersects with zone polygon
                if polygon.intersects(cell_polygon):
                    # Get intersection
                    intersection = polygon.intersection(cell_polygon)

                    # Calculate center point
                    centroid = intersection.centroid

                    grid_cells.append({
                        "cell_id": f"{zone_id}_C{cell_id:04d}",
                        "zone_id": zone_id,
                        "geometry": intersection,
                        "center_lat": centroid.y,
                        "center_lon": centroid.x,
                        "area_m2": intersection.area * (111000 ** 2),  # Approximate area in m²
                        "grid_row": i,
                        "grid_col": j
                    })

                    cell_id += 1

        self.grid_cells[zone_id] = grid_cells

        self.logger.info(f"Created {len(grid_cells)} grid cells for zone {zone_id}")

        return grid_cells

    def predict_zone_level(
        self,
        data: pd.DataFrame,
        horizon_hours: int = 72
    ) -> pd.DataFrame:
        """
        Generate zone-level predictions.

        Args:
            data: Input data
            horizon_hours: Forecast horizon in hours

        Returns:
            DataFrame with zone-level predictions
        """
        self.logger.info(f"Generating zone-level predictions for {horizon_hours} hours...")

        # Use TFT forecaster for predictions
        predictions = self.forecaster.predict(data, horizon_hours=horizon_hours)

        # Aggregate by zone
        zone_predictions = predictions.groupby(
            ["time", "zone_id"]
        ).agg({
            "prediction": "sum",
            "p02": "sum",
            "p10": "sum",
            "p25": "sum",
            "p75": "sum",
            "p90": "sum",
            "p98": "sum"
        }).reset_index()

        # Recalculate confidence intervals
        zone_predictions["confidence_80_lower"] = zone_predictions["p10"]
        zone_predictions["confidence_80_upper"] = zone_predictions["p90"]
        zone_predictions["confidence_95_lower"] = zone_predictions["p02"]
        zone_predictions["confidence_95_upper"] = zone_predictions["p98"]

        return zone_predictions

    def predict_sub_zone_level(
        self,
        zone_predictions: pd.DataFrame,
        zone_id: str,
        horizon_hours: int = 72
    ) -> pd.DataFrame:
        """
        Generate sub-zone (grid cell) level predictions using spatial interpolation.

        Args:
            zone_predictions: Zone-level predictions
            zone_id: Zone identifier
            horizon_hours: int = 72

        Returns:
            DataFrame with sub-zone level predictions
        """
        self.logger.info(f"Generating sub-zone predictions for zone {zone_id}...")

        if zone_id not in self.grid_cells:
            self.logger.warning(f"Grid cells not created for zone {zone_id}")
            return pd.DataFrame()

        grid_cells = self.grid_cells[zone_id]

        # Get zone predictions for this zone
        zone_data = zone_predictions[zone_predictions["zone_id"] == zone_id].copy()

        if zone_data.empty:
            self.logger.warning(f"No predictions found for zone {zone_id}")
            return pd.DataFrame()

        # Distribute zone-level predictions to grid cells
        # Use area-weighted distribution
        total_area = sum(cell["area_m2"] for cell in grid_cells)

        sub_zone_predictions = []

        for _, row in zone_data.iterrows():
            time = row["time"]
            zone_prediction = row["prediction"]

            for cell in grid_cells:
                # Calculate cell's share based on area
                area_weight = cell["area_m2"] / total_area

                # Add some spatial variation based on distance from center
                # This is a simplified approach - in production, use more sophisticated methods
                center_distance = np.sqrt(
                    (cell["center_lat"] - 12.9716) ** 2 +  # Approximate Bengaluru center
                    (cell["center_lon"] - 77.5946) ** 2
                )
                spatial_weight = 1.0 - (center_distance * 0.1)  # Decay with distance
                spatial_weight = max(0.5, min(1.5, spatial_weight))

                # Calculate cell prediction
                cell_prediction = zone_prediction * area_weight * spatial_weight

                sub_zone_predictions.append({
                    "time": time,
                    "zone_id": zone_id,
                    "cell_id": cell["cell_id"],
                    "center_lat": cell["center_lat"],
                    "center_lon": cell["center_lon"],
                    "prediction": cell_prediction,
                    "confidence_80_lower": cell_prediction * 0.8,
                    "confidence_80_upper": cell_prediction * 1.2,
                    "confidence_95_lower": cell_prediction * 0.6,
                    "confidence_95_upper": cell_prediction * 1.4
                })

        return pd.DataFrame(sub_zone_predictions)

    def predict_feeder_level(
        self,
        zone_predictions: pd.DataFrame,
        feeder_zone_mapping: Dict[str, str],
        horizon_hours: int = 72
    ) -> pd.DataFrame:
        """
        Generate feeder-level predictions.

        Args:
            zone_predictions: Zone-level predictions
            feeder_zone_mapping: Mapping of feeder_id to zone_id
            horizon_hours: Forecast horizon in hours

        Returns:
            DataFrame with feeder-level predictions
        """
        self.logger.info("Generating feeder-level predictions...")

        feeder_predictions = []

        for feeder_id, zone_id in feeder_zone_mapping.items():
            # Get zone predictions for this zone
            zone_data = zone_predictions[zone_predictions["zone_id"] == zone_id].copy()

            if zone_data.empty:
                continue

            # Distribute zone prediction to feeders
            # In production, this would use actual feeder load distribution
            num_feeders_in_zone = sum(
                1 for fid, zid in feeder_zone_mapping.items() if zid == zone_id
            )

            for _, row in zone_data.iterrows():
                feeder_predictions.append({
                    "time": row["time"],
                    "zone_id": zone_id,
                    "feeder_id": feeder_id,
                    "prediction": row["prediction"] / num_feeders_in_zone,
                    "confidence_80_lower": row["confidence_80_lower"] / num_feeders_in_zone,
                    "confidence_80_upper": row["confidence_80_upper"] / num_feeders_in_zone,
                    "confidence_95_lower": row["confidence_95_lower"] / num_feeders_in_zone,
                    "confidence_95_upper": row["confidence_95_upper"] / num_feeders_in_zone
                })

        return pd.DataFrame(feeder_predictions)

    def predict_all_resolutions(
        self,
        data: pd.DataFrame,
        horizon_hours: int = 72,
        feeder_zone_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Generate predictions at all resolution levels.

        Args:
            data: Input data
            horizon_hours: Forecast horizon in hours
            feeder_zone_mapping: Mapping of feeder_id to zone_id

        Returns:
            Dictionary with predictions at each resolution
        """
        self.logger.info(f"Generating multi-resolution predictions for {horizon_hours} hours...")

        results = {}

        # Zone-level predictions
        results["zone"] = self.predict_zone_level(data, horizon_hours)

        # Sub-zone predictions for each zone
        results["sub_zone"] = pd.DataFrame()
        for zone_id in results["zone"]["zone_id"].unique():
            if zone_id in self.grid_cells:
                zone_sub_zone = self.predict_sub_zone_level(
                    results["zone"],
                    zone_id,
                    horizon_hours
                )
                results["sub_zone"] = pd.concat([results["sub_zone"], zone_sub_zone], ignore_index=True)

        # Feeder-level predictions
        if feeder_zone_mapping:
            results["feeder"] = self.predict_feeder_level(
                results["zone"],
                feeder_zone_mapping,
                horizon_hours
            )
        else:
            results["feeder"] = pd.DataFrame()

        self.logger.info(
            f"Generated predictions: "
            f"zone={len(results['zone'])}, "
            f"sub_zone={len(results['sub_zone'])}, "
            f"feeder={len(results['feeder'])}"
        )

        return results

    def get_resolution_summary(
        self,
        predictions: Dict[str, pd.DataFrame]
    ) -> Dict[str, Dict]:
        """
        Get summary statistics for each resolution level.

        Args:
            predictions: Dictionary of predictions by resolution

        Returns:
            Dictionary with summary statistics
        """
        summary = {}

        for resolution, df in predictions.items():
            if df.empty:
                summary[resolution] = {"status": "no_data"}
                continue

            summary[resolution] = {
                "status": "available",
                "record_count": len(df),
                "time_range": {
                    "start": df["time"].min(),
                    "end": df["time"].max()
                },
                "prediction_stats": {
                    "mean": df["prediction"].mean(),
                    "std": df["prediction"].std(),
                    "min": df["prediction"].min(),
                    "max": df["prediction"].max()
                }
            }

            if resolution == "zone":
                summary[resolution]["zones"] = df["zone_id"].unique().tolist()
            elif resolution == "sub_zone":
                summary[resolution]["cells"] = df["cell_id"].nunique()
            elif resolution == "feeder":
                summary[resolution]["feeders"] = df["feeder_id"].nunique()

        return summary


if __name__ == "__main__":
    # Example usage
    from .tft.forecaster import TFTForecaster

    # Initialize forecaster
    forecaster = TFTForecaster()

    # Initialize multi-resolution predictor
    predictor = MultiResolutionPredictor(forecaster)

    # Load zone polygons
    predictor.load_zone_polygons("data/osm/zone_polygons.geojson")

    # Create grid cells for each zone
    for zone_id in predictor.zone_polygons.keys():
        predictor.create_sub_zone_grid(zone_id, grid_size_m=100)

    # Load data
    data_path = "data/synthetic/ev_demand.csv"
    if Path(data_path).exists():
        data = pd.read_csv(data_path)

        # Generate predictions at all resolutions
        predictions = predictor.predict_all_resolutions(data, horizon_hours=72)

        # Get summary
        summary = predictor.get_resolution_summary(predictions)

        print("Multi-resolution prediction summary:")
        for resolution, stats in summary.items():
            print(f"  {resolution}: {stats}")
    else:
        print(f"Data file not found: {data_path}")
