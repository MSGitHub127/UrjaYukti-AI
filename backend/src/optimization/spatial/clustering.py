"""
HDBSCAN Clustering Pipeline for EV Demand Hotspots
Production-grade implementation with demand surface, constraint masking, and cluster priority scoring.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon
from hdbscan import HDBSCAN
from sklearn.preprocessing import StandardScaler
from scipy.interpolate import griddata
from scipy.spatial import ConvexHull


@dataclass
class DemandCluster:
    """Represents a demand cluster."""

    cluster_id: str
    zone_id: str
    center_lat: float
    center_lon: float
    demand_kw: float
    area_km2: float
    demand_density_kw_per_km2: float
    priority_score: float
    points: List[Tuple[float, float]]
    geometry: Optional[Polygon] = None
    red_flags: List[str] = None

    def __post_init__(self):
        if self.red_flags is None:
            self.red_flags = []


@dataclass
class ClusteringResult:
    """Result of demand clustering."""

    clusters: List[DemandCluster]
    noise_points: List[Tuple[float, float]]
    total_demand_kw: float
    clustered_demand_percent: float


class HDBSCANPipeline:
    """Production-grade HDBSCAN clustering pipeline for EV demand hotspots."""

    def __init__(
        self,
        min_cluster_size: int = 10,
        min_samples: int = 5,
        cluster_selection_epsilon: float = 0.01,
        metric: str = "haversine"
    ):
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.cluster_selection_epsilon = cluster_selection_epsilon
        self.metric = metric

        self.logger = logging.getLogger(__name__)

        # Clustering model
        self.clusterer: Optional[HDBSCAN] = None

        # Scaler
        self.scaler = StandardScaler()

    def create_demand_surface(
        self,
        demand_data: pd.DataFrame,
        grid_resolution_km: float = 0.1
    ) -> np.ndarray:
        """
        Create a demand surface from point data.

        Args:
            demand_data: DataFrame with lat, lon, demand columns
            grid_resolution_km: Grid resolution in km

        Returns:
            2D array of demand values
        """
        self.logger.info("Creating demand surface...")

        # Extract points and values
        points = demand_data[["lon", "lat"]].values
        values = demand_data["demand_kw"].values

        # Create grid
        lon_min, lon_max = points[:, 0].min(), points[:, 0].max()
        lat_min, lat_max = points[:, 1].min(), points[:, 1].max()

        # Convert km to degrees (approximate)
        grid_resolution_deg = grid_resolution_km / 111

        lon_grid = np.arange(lon_min, lon_max + grid_resolution_deg, grid_resolution_deg)
        lat_grid = np.arange(lat_min, lat_max + grid_resolution_deg, grid_resolution_deg)

        lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
        grid_points = np.column_stack([lon_mesh.ravel(), lat_mesh.ravel()])

        # Interpolate demand values
        try:
            grid_values = griddata(
                points,
                values,
                grid_points,
                method="linear",
                fill_value=0
            )
        except:
            # Fallback to nearest neighbor
            grid_values = griddata(
                points,
                values,
                grid_points,
                method="nearest",
                fill_value=0
            )

        # Reshape to 2D array
        demand_surface = grid_values.reshape(len(lat_grid), len(lon_grid))

        self.logger.info(f"Demand surface created: {demand_surface.shape}")

        return demand_surface

    def apply_constraint_mask(
        self,
        demand_surface: np.ndarray,
        zone_polygons: Dict[str, Polygon],
        grid_bounds: Tuple[float, float, float, float]
    ) -> np.ndarray:
        """
        Apply zone constraint mask to demand surface.

        Args:
            demand_surface: 2D demand array
            zone_polygons: Dictionary of zone polygons
            grid_bounds: (lon_min, lon_max, lat_min, lat_max)

        Returns:
            Masked demand surface
        """
        self.logger.info("Applying constraint mask...")

        masked_surface = demand_surface.copy()

        lon_min, lon_max, lat_min, lat_max = grid_bounds
        ny, nx = demand_surface.shape

        lon_step = (lon_max - lon_min) / nx
        lat_step = (lat_max - lat_min) / ny

        # Create mask for each zone
        for zone_id, polygon in zone_polygons.items():
            for i in range(ny):
                for j in range(nx):
                    lon = lon_min + j * lon_step
                    lat = lat_max - i * lat_step  # Lat decreases as we go down

                    point = Point(lon, lat)

                    # Check if point is in zone polygon
                    if not polygon.contains(point):
                        masked_surface[i, j] = 0

        self.logger.info("Constraint mask applied")

        return masked_surface

    def cluster_demand_points(
        self,
        demand_data: pd.DataFrame,
        zone_id: Optional[str] = None
    ) -> ClusteringResult:
        """
        Cluster demand points using HDBSCAN.

        Args:
            demand_data: DataFrame with lat, lon, demand columns
            zone_id: Optional zone ID filter

        Returns:
            Clustering result
        """
        self.logger.info(f"Clustering demand points ({len(demand_data)} points)...")

        # Filter by zone if specified
        if zone_id:
            demand_data = demand_data[demand_data["zone_id"] == zone_id]

        if len(demand_data) < self.min_cluster_size:
            self.logger.warning(f"Insufficient points for clustering: {len(demand_data)}")
            return ClusteringResult([], [], 0, 0)

        # Extract coordinates
        coords = demand_data[["lat", "lon"]].values
        demands = demand_data["demand_kw"].values

        # Convert to radians for haversine metric
        if self.metric == "haversine":
            coords = np.radians(coords)

        # Fit HDBSCAN
        self.clusterer = HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            cluster_selection_epsilon=self.cluster_selection_epsilon,
            metric=self.metric,
            alpha=1.0
        )

        labels = self.clusterer.fit_predict(coords)

        # Process clusters
        clusters = []
        noise_points = []
        total_demand = 0
        clustered_demand = 0

        unique_labels = set(labels)
        unique_labels.discard(-1)  # Remove noise label

        for label in unique_labels:
            # Get points in this cluster
            mask = labels == label
            cluster_coords = coords[mask]
            cluster_demands = demands[mask]

            # Convert back from radians if needed
            if self.metric == "haversine":
                cluster_coords = np.degrees(cluster_coords)

            # Calculate cluster properties
            center_lat = cluster_coords[:, 0].mean()
            center_lon = cluster_coords[:, 1].mean()
            total_demand_kw = cluster_demands.sum()

            # Calculate area using convex hull
            points = cluster_coords.tolist()
            try:
                hull = ConvexHull(points)
                area_km2 = hull.volume * (111 ** 2)  # Approximate conversion
            except:
                area_km2 = 0.1  # Default area

            # Calculate demand density
            demand_density = total_demand_kw / area_km2 if area_km2 > 0 else 0

            # Calculate priority score
            priority_score = self._calculate_priority_score(
                total_demand_kw,
                demand_density,
                len(points)
            )

            # Create cluster geometry
            geometry = self._create_cluster_geometry(points)

            # Identify red flags
            red_flags = self._identify_cluster_red_flags(
                total_demand_kw,
                demand_density,
                area_km2
            )

            cluster = DemandCluster(
                cluster_id=f"C{label:03d}",
                zone_id=zone_id or "UNKNOWN",
                center_lat=center_lat,
                center_lon=center_lon,
                demand_kw=total_demand_kw,
                area_km2=area_km2,
                demand_density_kw_per_km2=demand_density,
                priority_score=priority_score,
                points=points,
                geometry=geometry,
                red_flags=red_flags
            )

            clusters.append(cluster)
            clustered_demand += total_demand_kw

        # Collect noise points
        noise_mask = labels == -1
        if self.metric == "haversine":
            noise_coords = np.degrees(coords[noise_mask])
        else:
            noise_coords = coords[noise_mask]

        noise_points = [(lat, lon) for lat, lon in noise_coords]

        total_demand = demands.sum()
        clustered_percent = (clustered_demand / total_demand * 100) if total_demand > 0 else 0

        result = ClusteringResult(
            clusters=clusters,
            noise_points=noise_points,
            total_demand_kw=total_demand,
            clustered_demand_percent=clustered_percent
        )

        self.logger.info(
            f"Clustering complete: {len(clusters)} clusters, "
            f"{clustered_percent:.1f}% demand clustered"
        )

        return result

    def _calculate_priority_score(
        self,
        total_demand: float,
        demand_density: float,
        num_points: int
    ) -> float:
        """Calculate priority score for a cluster."""
        # Normalize each component
        demand_score = min(1.0, total_demand / 500.0)  # 500 kW = 1.0
        density_score = min(1.0, demand_density / 100.0)  # 100 kW/km² = 1.0
        size_score = min(1.0, num_points / 50.0)  # 50 points = 1.0

        # Weighted combination
        priority = (
            demand_score * 0.5 +
            density_score * 0.3 +
            size_score * 0.2
        )

        return priority

    def _create_cluster_geometry(self, points: List[Tuple[float, float]]) -> Optional[Polygon]:
        """Create geometry for a cluster."""
        if len(points) < 3:
            return None

        try:
            # Create convex hull
            hull = ConvexHull(points)
            hull_points = [points[i] for i in hull.vertices]

            # Create polygon (lon, lat order)
            polygon = Polygon([(lon, lat) for lat, lon in hull_points])

            return polygon
        except:
            return None

    def _identify_cluster_red_flags(
        self,
        total_demand: float,
        demand_density: float,
        area_km2: float
    ) -> List[str]:
        """Identify red flags for a cluster."""
        red_flags = []

        if total_demand < 50:
            red_flags.append("Low total demand")

        if demand_density < 10:
            red_flags.append("Low demand density")

        if area_km2 > 10:
            red_flags.append("Large dispersed area")

        return red_flags

    def rank_clusters(
        self,
        result: ClusteringResult,
        max_clusters: int = 10
    ) -> List[DemandCluster]:
        """
        Rank clusters by priority score.

        Args:
            result: Clustering result
            max_clusters: Maximum number of clusters to return

        Returns:
            List of ranked clusters
        """
        # Sort by priority score
        ranked = sorted(result.clusters, key=lambda c: c.priority_score, reverse=True)

        return ranked[:max_clusters]

    def get_cluster_summary(self, result: ClusteringResult) -> Dict:
        """Get summary statistics for clustering result."""
        if not result.clusters:
            return {
                "status": "no_clusters",
                "total_points": 0,
                "noise_points": len(result.noise_points)
            }

        return {
            "status": "success",
            "num_clusters": len(result.clusters),
            "total_demand_kw": result.total_demand_kw,
            "clustered_demand_percent": result.clustered_demand_percent,
            "noise_points": len(result.noise_points),
            "top_clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "zone_id": c.zone_id,
                    "demand_kw": c.demand_kw,
                    "priority_score": c.priority_score,
                    "red_flags": c.red_flags
                }
                for c in result.clusters[:5]
            ]
        }


if __name__ == "__main__":
    # Example usage
    pipeline = HDBSCANPipeline(
        min_cluster_size=10,
        min_samples=5,
        metric="haversine"
    )

    # Create sample demand data
    np.random.seed(42)
    n_points = 100

    # Create two clusters
    cluster1_center = (12.9698, 77.7499)  # Whitefield
    cluster2_center = (12.9138, 77.6374)  # HSR Layout

    points = []
    demands = []
    zone_ids = []

    for _ in range(n_points // 2):
        # Cluster 1
        lat = cluster1_center[0] + np.random.normal(0, 0.01)
        lon = cluster1_center[1] + np.random.normal(0, 0.01)
        demand = np.random.uniform(20, 50)
        points.append((lat, lon))
        demands.append(demand)
        zone_ids.append("Z01")

    for _ in range(n_points // 2):
        # Cluster 2
        lat = cluster2_center[0] + np.random.normal(0, 0.01)
        lon = cluster2_center[1] + np.random.normal(0, 0.01)
        demand = np.random.uniform(15, 40)
        points.append((lat, lon))
        demands.append(demand)
        zone_ids.append("Z02")

    # Add some noise
    for _ in range(10):
        lat = np.random.uniform(12.8, 13.0)
        lon = np.random.uniform(77.5, 77.8)
        demand = np.random.uniform(5, 15)
        points.append((lat, lon))
        demands.append(demand)
        zone_ids.append("Z01")

    demand_data = pd.DataFrame({
        "lat": [p[0] for p in points],
        "lon": [p[1] for p in points],
        "demand_kw": demands,
        "zone_id": zone_ids
    })

    # Cluster demand points
    result = pipeline.cluster_demand_points(demand_data)

    print(f"Clustering result: {len(result.clusters)} clusters")
    print(f"Total demand: {result.total_demand_kw:.2f} kW")
    print(f"Clustered demand: {result.clustered_demand_percent:.1f}%")

    # Rank clusters
    ranked = pipeline.rank_clusters(result)

    print("\nTop clusters:")
    for i, cluster in enumerate(ranked, 1):
        print(f"  {i}. {cluster.cluster_id}: {cluster.demand_kw:.2f} kW (priority: {cluster.priority_score:.2f})")
