"""
OSM Data Ingestion for Bengaluru
Ingests OpenStreetMap road network, POI data, and zone polygons using NetworkX.
"""

import osmnx as ox
import geopandas as gpd
import pandas as pd
import networkx as nx
from typing import Dict, List, Tuple, Optional
import numpy as np
from shapely.geometry import Point, Polygon, MultiPolygon
import json


class OSMDataIngestor:
    """Ingests and processes OSM data for Bengaluru zones."""

    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.road_network: Optional[nx.Graph] = None
        self.zone_polygons: Dict[str, Polygon] = {}
        self.pois: Dict[str, gpd.GeoDataFrame] = {}

    def _default_config(self) -> Dict:
        """Default configuration for OSM data ingestion."""
        return {
            "city": "Bengaluru, Karnataka, India",
            "zones": [
                {
                    "id": "Z01",
                    "name": "Whitefield",
                    "query": "Whitefield, Bengaluru",
                    "center": (12.9698, 77.7499),
                    "radius_km": 5
                },
                {
                    "id": "Z02",
                    "name": "HSR Layout",
                    "query": "HSR Layout, Bengaluru",
                    "center": (12.9138, 77.6374),
                    "radius_km": 3
                },
                {
                    "id": "Z03",
                    "name": "Indiranagar",
                    "query": "Indiranagar, Bengaluru",
                    "center": (12.9740, 77.6408),
                    "radius_km": 3
                },
                {
                    "id": "Z04",
                    "name": "Koramangala",
                    "query": "Koramangala, Bengaluru",
                    "center": (12.9352, 77.6245),
                    "radius_km": 4
                },
                {
                    "id": "Z05",
                    "name": "Electronic City",
                    "query": "Electronic City, Bengaluru",
                    "center": (12.8356, 77.6666),
                    "radius_km": 6
                },
                {
                    "id": "Z06",
                    "name": "Marathahalli",
                    "query": "Marathahalli, Bengaluru",
                    "center": (12.9556, 77.7008),
                    "radius_km": 4
                }
            ],
            "poi_categories": [
                "parking",
                "fuel",
                "charging_station",
                "commercial",
                "office",
                "residential"
            ],
            "network_type": "drive"
        }

    def ingest_road_network(self) -> nx.Graph:
        """Ingest road network for Bengaluru."""
        print("Ingesting road network for Bengaluru...")

        try:
            # Download road network
            self.road_network = ox.graph_from_place(
                self.config["city"],
                network_type=self.config["network_type"]
            )

            print(f"Downloaded road network with {self.road_network.number_of_nodes()} nodes "
                  f"and {self.road_network.number_of_edges()} edges")

            return self.road_network

        except Exception as e:
            print(f"Error ingesting road network: {e}")
            # Fallback: create a synthetic network
            return self._create_synthetic_network()

    def _create_synthetic_network(self) -> nx.Graph:
        """Create a synthetic road network as fallback."""
        print("Creating synthetic road network as fallback...")

        G = nx.Graph()

        # Create nodes for each zone center
        for zone in self.config["zones"]:
            zone_id = zone["id"]
            center = zone["center"]
            G.add_node(f"{zone_id}_center", pos=center, type="zone_center")

        # Create grid of nodes within each zone
        for zone in self.config["zones"]:
            zone_id = zone["id"]
            center = zone["center"]
            radius = zone["radius_km"]

            # Create a 5x5 grid within the zone
            for i in range(5):
                for j in range(5):
                    lat = center[0] + (i - 2) * (radius / 111)  # Approximate km to degrees
                    lon = center[1] + (j - 2) * (radius / (111 * np.cos(np.radians(center[0]))))

                    node_id = f"{zone_id}_n{i}_{j}"
                    G.add_node(node_id, pos=(lat, lon), type="road_node")

                    # Connect to nearby nodes
                    if i > 0:
                        G.add_edge(node_id, f"{zone_id}_n{i-1}_{j}", weight=1.0)
                    if j > 0:
                        G.add_edge(node_id, f"{zone_id}_n{i}_{j-1}", weight=1.0)

        print(f"Created synthetic network with {G.number_of_nodes()} nodes "
              f"and {G.number_of_edges()} edges")

        return G

    def ingest_zone_polygons(self) -> Dict[str, Polygon]:
        """Ingest zone polygons from OSM."""
        print("Ingesting zone polygons...")

        for zone in self.config["zones"]:
            zone_id = zone["id"]
            query = zone["query"]

            try:
                # Get polygon from OSM
                gdf = ox.geocode_to_gdf(query)
                if not gdf.empty:
                    geometry = gdf.geometry.iloc[0]
                    if isinstance(geometry, MultiPolygon):
                        # Use the largest polygon
                        geometry = max(geometry.geoms, key=lambda p: p.area)
                    self.zone_polygons[zone_id] = geometry
                    print(f"  {zone['name']}: Polygon ingested")
                else:
                    # Fallback: create circular buffer
                    self.zone_polygons[zone_id] = self._create_circular_buffer(zone)
                    print(f"  {zone['name']}: Using circular buffer fallback")

            except Exception as e:
                print(f"  {zone['name']}: Error - {e}, using circular buffer")
                self.zone_polygons[zone_id] = self._create_circular_buffer(zone)

        return self.zone_polygons

    def _create_circular_buffer(self, zone: Dict) -> Polygon:
        """Create a circular buffer around zone center."""
        center = zone["center"]
        radius_km = zone["radius_km"]

        # Convert km to degrees (approximate)
        radius_deg = radius_km / 111

        # Create circle points
        points = []
        for angle in np.linspace(0, 2 * np.pi, 32):
            lat = center[0] + radius_deg * np.cos(angle)
            lon = center[1] + radius_deg * np.sin(angle) / np.cos(np.radians(center[0]))
            points.append((lon, lat))

        return Polygon(points)

    def ingest_pois(self) -> Dict[str, gpd.GeoDataFrame]:
        """Ingest Points of Interest for each zone."""
        print("Ingesting Points of Interest...")

        for zone in self.config["zones"]:
            zone_id = zone["id"]
            center = zone["center"]
            radius = zone["radius_km"]

            try:
                # Get POIs within zone
                tags = {}
                for category in self.config["poi_categories"]:
                    tags[category] = True

                gdf = ox.features_from_point(
                    center,
                    tags=tags,
                    dist=radius * 1000  # Convert to meters
                )

                if not gdf.empty:
                    self.pois[zone_id] = gdf
                    print(f"  {zone['name']}: {len(gdf)} POIs ingested")
                else:
                    # Fallback: create synthetic POIs
                    self.pois[zone_id] = self._create_synthetic_pois(zone)
                    print(f"  {zone['name']}: Using synthetic POIs")

            except Exception as e:
                print(f"  {zone['name']}: Error - {e}, using synthetic POIs")
                self.pois[zone_id] = self._create_synthetic_pois(zone)

        return self.pois

    def _create_synthetic_pois(self, zone: Dict) -> gpd.GeoDataFrame:
        """Create synthetic POIs as fallback."""
        center = zone["center"]
        radius = zone["radius_km"]

        pois = []
        num_pois = np.random.randint(20, 50)

        for _ in range(num_pois):
            # Random position within zone
            angle = np.random.uniform(0, 2 * np.pi)
            dist = np.random.uniform(0, radius) * 1000  # meters

            lat = center[0] + (dist / 111000) * np.cos(angle)
            lon = center[1] + (dist / (111000 * np.cos(np.radians(center[0])))) * np.sin(angle)

            category = np.random.choice(self.config["poi_categories"])

            pois.append({
                "geometry": Point(lon, lat),
                "category": category,
                "name": f"Synthetic {category}",
                "zone_id": zone["id"]
            })

        return gpd.GeoDataFrame(pois, crs="EPSG:4326")

    def calculate_zone_connectivity(self) -> List[Dict]:
        """Calculate connectivity between zones based on road network."""
        print("Calculating zone connectivity...")

        connectivity = []

        for i, zone1 in enumerate(self.config["zones"]):
            for zone2 in self.config["zones"][i+1:]:
                center1 = zone1["center"]
                center2 = zone2["center"]

                # Calculate distance
                distance_km = self._haversine_distance(center1, center2)

                # Only connect zones within 15km
                if distance_km <= 15:
                    # Estimate transfer capacity based on distance
                    transfer_capacity = max(3, 10 - distance_km * 0.5)

                    connectivity.append({
                        "from_zone_id": zone1["id"],
                        "from_zone_name": zone1["name"],
                        "to_zone_id": zone2["id"],
                        "to_zone_name": zone2["name"],
                        "distance_km": round(distance_km, 2),
                        "transfer_capacity_mw": round(transfer_capacity, 2),
                        "transfer_efficiency": 0.90
                    })

        print(f"Found {len(connectivity)} zone connections")
        return connectivity

    def _haversine_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculate distance between two coordinates using Haversine formula."""
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        R = 6371  # Earth's radius in km

        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)

        a = (np.sin(dlat/2)**2 +
             np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) *
             np.sin(dlon/2)**2)

        c = 2 * np.arcsin(np.sqrt(a))
        distance = R * c

        return distance

    def save_to_files(self, output_dir: str = "data/osm"):
        """Save all ingested data to files."""
        import os
        os.makedirs(output_dir, exist_ok=True)

        # Save road network
        if self.road_network is not None:
            road_path = f"{output_dir}/road_network.graphml"
            ox.save_graphml(self.road_network, road_path)
            print(f"Saved road network to: {road_path}")

        # Save zone polygons
        polygons_path = f"{output_dir}/zone_polygons.geojson"
        features = []
        for zone_id, polygon in self.zone_polygons.items():
            zone_name = next(z["name"] for z in self.config["zones"] if z["id"] == zone_id)
            features.append({
                "type": "Feature",
                "properties": {
                    "zone_id": zone_id,
                    "zone_name": zone_name
                },
                "geometry": polygon.__geo_interface__
            })

        with open(polygons_path, 'w') as f:
            json.dump({"type": "FeatureCollection", "features": features}, f)
        print(f"Saved zone polygons to: {polygons_path}")

        # Save POIs
        for zone_id, gdf in self.pois.items():
            poi_path = f"{output_dir}/pois_{zone_id}.geojson"
            gdf.to_file(poi_path, driver="GeoJSON")
            print(f"Saved POIs for {zone_id} to: {poi_path}")

        # Save connectivity
        connectivity = self.calculate_zone_connectivity()
        connectivity_path = f"{output_dir}/zone_connectivity.json"
        with open(connectivity_path, 'w') as f:
            json.dump(connectivity, f, indent=2)
        print(f"Saved zone connectivity to: {connectivity_path}")

        print(f"\nAll OSM data saved to: {output_dir}")


if __name__ == "__main__":
    ingestor = OSMDataIngestor()

    # Ingest all data
    ingestor.ingest_road_network()
    ingestor.ingest_zone_polygons()
    ingestor.ingest_pois()

    # Save to files
    ingestor.save_to_files()
