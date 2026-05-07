"""
MCDA (Multi-Criteria Decision Analysis) Site Scoring Engine
Production-grade implementation for charging station site ranking with 6-dimension weighted scoring.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon


class ScoringDimension(Enum):
    """Scoring dimensions for site evaluation."""

    DEMAND = "demand"
    GROWTH = "growth"
    ACCESSIBILITY = "accessibility"
    INFRASTRUCTURE = "infrastructure"
    GRID_CAPACITY = "grid_capacity"
    COST = "cost"


@dataclass
class ScoringWeights:
    """Weights for each scoring dimension."""

    demand: float = 0.30
    growth: float = 0.20
    accessibility: float = 0.15
    infrastructure: float = 0.15
    grid_capacity: float = 0.10
    cost: float = 0.10

    def normalize(self) -> "ScoringWeights":
        """Normalize weights to sum to 1.0."""
        total = sum([
            self.demand, self.growth, self.accessibility,
            self.infrastructure, self.grid_capacity, self.cost
        ])

        return ScoringWeights(
            demand=self.demand / total,
            growth=self.growth / total,
            accessibility=self.accessibility / total,
            infrastructure=self.infrastructure / total,
            grid_capacity=self.grid_capacity / total,
            cost=self.cost / total
        )

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "demand": self.demand,
            "growth": self.growth,
            "accessibility": self.accessibility,
            "infrastructure": self.infrastructure,
            "grid_capacity": self.grid_capacity,
            "cost": self.cost
        }

    @classmethod
    def from_dict(cls, weights: Dict[str, float]) -> "ScoringWeights":
        """Create from dictionary."""
        return cls(
            demand=weights.get("demand", 0.30),
            growth=weights.get("growth", 0.20),
            accessibility=weights.get("accessibility", 0.15),
            infrastructure=weights.get("infrastructure", 0.15),
            grid_capacity=weights.get("grid_capacity", 0.10),
            cost=weights.get("cost", 0.10)
        )


@dataclass
class SiteCandidate:
    """Represents a potential charging station site."""

    site_id: str
    name: str
    zone_id: str
    location: Tuple[float, float]  # (lat, lon)
    demand_score: float = 0.0
    growth_score: float = 0.0
    accessibility_score: float = 0.0
    infrastructure_score: float = 0.0
    grid_capacity_score: float = 0.0
    cost_score: float = 0.0
    total_score: float = 0.0
    red_flags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class SiteRankingResult:
    """Result of site ranking."""

    rank: int
    site_id: str
    name: str
    zone_id: str
    total_score: float
    dimension_scores: Dict[str, float]
    red_flags: List[str]
    recommendation: str
    payback_years: Optional[float] = None
    utilization_rate: Optional[float] = None


class MCDAEngine:
    """Production-grade MCDA engine for charging station site ranking."""

    def __init__(self, default_weights: Optional[ScoringWeights] = None):
        self.weights = (default_weights or ScoringWeights()).normalize()

        self.logger = logging.getLogger(__name__)

        # Scoring parameters
        self.demand_threshold = 0.7  # Minimum demand score
        self.grid_headroom_threshold = 0.2  # Minimum grid headroom (20%)
        self.max_red_flags = 3  # Maximum red flags for recommendation

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """
        Update scoring weights.

        Args:
            new_weights: Dictionary of dimension weights
        """
        self.weights = ScoringWeights.from_dict(new_weights).normalize()
        self.logger.info(f"Updated weights: {self.weights.to_dict()}")

    def get_weights(self) -> Dict[str, float]:
        """Get current weights."""
        return self.weights.to_dict()

    def score_site(
        self,
        site: SiteCandidate,
        demand_data: pd.DataFrame,
        grid_data: Dict[str, any],
        poi_data: Optional[pd.DataFrame] = None
    ) -> SiteCandidate:
        """
        Score a single site candidate.

        Args:
            site: Site candidate to score
            demand_data: Demand forecast data
            grid_data: Grid capacity data
            poi_data: Points of interest data

        Returns:
            Scored site candidate
        """
        # Score each dimension
        site.demand_score = self._score_demand(site, demand_data)
        site.growth_score = self._score_growth(site, demand_data)
        site.accessibility_score = self._score_accessibility(site, poi_data)
        site.infrastructure_score = self._score_infrastructure(site, grid_data)
        site.grid_capacity_score = self._score_grid_capacity(site, grid_data)
        site.cost_score = self._score_cost(site, grid_data)

        # Calculate total score
        site.total_score = self._calculate_total_score(site)

        # Identify red flags
        site.red_flags = self._identify_red_flags(site)

        return site

    def _score_demand(self, site: SiteCandidate, demand_data: pd.DataFrame) -> float:
        """Score demand dimension."""
        if demand_data.empty:
            return 0.5  # Default score

        # Get demand for zone
        zone_demand = demand_data[demand_data["zone_id"] == site.zone_id]

        if zone_demand.empty:
            return 0.5

        # Calculate average demand
        avg_demand = zone_demand["prediction"].mean()

        # Normalize to 0-1 scale (assuming max demand of 1000 kW)
        normalized = min(1.0, avg_demand / 1000.0)

        return normalized

    def _score_growth(self, site: SiteCandidate, demand_data: pd.DataFrame) -> float:
        """Score growth dimension."""
        if demand_data.empty:
            return 0.5

        # Get demand for zone
        zone_demand = demand_data[demand_data["zone_id"] == site.zone_id]

        if zone_demand.empty or len(zone_demand) < 24:
            return 0.5

        # Calculate growth rate (compare first 12 hours to last 12 hours)
        first_half = zone_demand.iloc[:12]["prediction"].mean()
        second_half = zone_demand.iloc[12:]["prediction"].mean()

        if first_half == 0:
            return 0.5

        growth_rate = (second_half - first_half) / first_half

        # Normalize to 0-1 scale (assuming growth rate of -0.5 to 1.0)
        normalized = (growth_rate + 0.5) / 1.5
        normalized = max(0.0, min(1.0, normalized))

        return normalized

    def _score_accessibility(self, site: SiteCandidate, poi_data: Optional[pd.DataFrame]) -> float:
        """Score accessibility dimension."""
        if poi_data is None or poi_data.empty:
            return 0.5

        # Count nearby POIs within 1km
        site_point = Point(site.location[1], site.location[0])

        nearby_pois = 0
        for _, poi in poi_data.iterrows():
            if "geometry" in poi and poi["geometry"]:
                try:
                    poi_point = poi["geometry"]
                    distance = site_point.distance(poi_point) * 111  # Approximate km

                    if distance <= 1.0:  # Within 1km
                        nearby_pois += 1
                except:
                    continue

        # Normalize to 0-1 scale (assuming 10+ POIs is excellent)
        normalized = min(1.0, nearby_pois / 10.0)

        return normalized

    def _score_infrastructure(self, site: SiteCandidate, grid_data: Dict[str, any]) -> float:
        """Score infrastructure dimension."""
        # Check for existing infrastructure
        has_power = grid_data.get("power_available", True)
        has_road_access = grid_data.get("road_access", True)
        has_fiber = grid_data.get("fiber_available", False)

        score = 0.0
        if has_power:
            score += 0.4
        if has_road_access:
            score += 0.4
        if has_fiber:
            score += 0.2

        return score

    def _score_grid_capacity(self, site: SiteCandidate, grid_data: Dict[str, any]) -> float:
        """Score grid capacity dimension."""
        # Get transformer headroom
        headroom_percent = grid_data.get("headroom_percent", 0.0)

        # Normalize to 0-1 scale
        normalized = min(1.0, headroom_percent / 0.5)  # 50% headroom = 1.0

        return normalized

    def _score_cost(self, site: SiteCandidate, grid_data: Dict[str, any]) -> float:
        """Score cost dimension (lower cost = higher score)."""
        # Get installation cost
        installation_cost = grid_data.get("installation_cost", 1000000)  # Default ₹10L

        # Normalize to 0-1 scale (assuming max cost of ₹50L)
        normalized = 1.0 - min(1.0, installation_cost / 5000000.0)

        return normalized

    def _calculate_total_score(self, site: SiteCandidate) -> float:
        """Calculate total weighted score."""
        total = (
            site.demand_score * self.weights.demand +
            site.growth_score * self.weights.growth +
            site.accessibility_score * self.weights.accessibility +
            site.infrastructure_score * self.weights.infrastructure +
            site.grid_capacity_score * self.weights.grid_capacity +
            site.cost_score * self.weights.cost
        )

        return total

    def _identify_red_flags(self, site: SiteCandidate) -> List[str]:
        """Identify red flags for the site."""
        red_flags = []

        # Low demand
        if site.demand_score < self.demand_threshold:
            red_flags.append("Low demand")

        # Insufficient grid capacity
        if site.grid_capacity_score < self.grid_headroom_threshold:
            red_flags.append("Insufficient grid headroom")

        # High cost
        if site.cost_score < 0.3:
            red_flags.append("High installation cost")

        # Poor accessibility
        if site.accessibility_score < 0.3:
            red_flags.append("Poor accessibility")

        return red_flags

    def rank_sites(
        self,
        candidates: List[SiteCandidate],
        demand_data: pd.DataFrame,
        grid_data: Dict[str, any],
        poi_data: Optional[pd.DataFrame] = None
    ) -> List[SiteRankingResult]:
        """
        Rank multiple site candidates.

        Args:
            candidates: List of site candidates
            demand_data: Demand forecast data
            grid_data: Grid capacity data
            poi_data: Points of interest data

        Returns:
            List of ranked site results
        """
        self.logger.info(f"Ranking {len(candidates)} site candidates...")

        # Score all sites
        scored_sites = []
        for candidate in candidates:
            scored = self.score_site(candidate, demand_data, grid_data, poi_data)
            scored_sites.append(scored)

        # Sort by total score
        scored_sites.sort(key=lambda s: s.total_score, reverse=True)

        # Create ranking results
        results = []
        for rank, site in enumerate(scored_sites, start=1):
            # Determine recommendation
            recommendation = self._get_recommendation(site)

            result = SiteRankingResult(
                rank=rank,
                site_id=site.site_id,
                name=site.name,
                zone_id=site.zone_id,
                total_score=site.total_score,
                dimension_scores={
                    "demand": site.demand_score,
                    "growth": site.growth_score,
                    "accessibility": site.accessibility_score,
                    "infrastructure": site.infrastructure_score,
                    "grid_capacity": site.grid_capacity_score,
                    "cost": site.cost_score
                },
                red_flags=site.red_flags,
                recommendation=recommendation
            )

            results.append(result)

        self.logger.info(f"Ranking complete. Top site: {results[0].name} (score: {results[0].total_score:.2f})")

        return results

    def _get_recommendation(self, site: SiteCandidate) -> str:
        """Get recommendation for a site."""
        if len(site.red_flags) > self.max_red_flags:
            return "NOT_RECOMMENDED"
        elif site.total_score >= 0.8:
            return "HIGH_PRIORITY"
        elif site.total_score >= 0.6:
            return "RECOMMENDED"
        elif site.total_score >= 0.4:
            return "CONSIDER"
        else:
            return "LOW_PRIORITY"

    def calculate_roi(
        self,
        site: SiteCandidate,
        demand_data: pd.DataFrame,
        grid_data: Dict[str, any]
    ) -> Dict[str, float]:
        """
        Calculate ROI metrics for a site.

        Args:
            site: Site candidate
            demand_data: Demand forecast data
            grid_data: Grid capacity data

        Returns:
            Dictionary with ROI metrics
        """
        # Get installation cost
        capex = grid_data.get("installation_cost", 1000000)  # ₹10L default

        # Get annual demand
        zone_demand = demand_data[demand_data["zone_id"] == site.zone_id]
        annual_demand_kwh = zone_demand["prediction"].sum() * 365 if not zone_demand.empty else 0

        # Revenue calculation
        revenue_per_kwh = 4.0  # ₹4/kWh profit margin
        annual_revenue = annual_demand_kwh * revenue_per_kwh

        # OPEX (5% of CAPEX annually)
        opex = capex * 0.05

        # Annual profit
        annual_profit = annual_revenue - opex

        # Payback period
        payback_years = capex / annual_profit if annual_profit > 0 else float('inf')

        # Utilization rate
        charger_capacity_kw = 50.0  # 50kW charger
        annual_capacity_kwh = charger_capacity_kw * 24 * 365
        utilization_rate = annual_demand_kwh / annual_capacity_kwh if annual_capacity_kwh > 0 else 0

        # NPV (10% discount rate, 10 years)
        discount_rate = 0.10
        npv = sum(
            annual_profit / ((1 + discount_rate) ** year)
            for year in range(1, 11)
        ) - capex

        return {
            "capex": capex,
            "annual_revenue": annual_revenue,
            "annual_opex": opex,
            "annual_profit": annual_profit,
            "payback_years": payback_years,
            "utilization_rate": utilization_rate,
            "npv": npv
        }


if __name__ == "__main__":
    # Example usage
    engine = MCDAEngine()

    # Create sample candidates
    candidates = [
        SiteCandidate(
            site_id="S001",
            name="Whitefield Tech Park",
            zone_id="Z01",
            location=(12.9698, 77.7499)
        ),
        SiteCandidate(
            site_id="S002",
            name="HSR Bus Depot",
            zone_id="Z02",
            location=(12.9138, 77.6374)
        )
    ]

    # Create sample data
    demand_data = pd.DataFrame({
        "zone_id": ["Z01"] * 24 + ["Z02"] * 24,
        "prediction": [500.0] * 24 + [300.0] * 24
    })

    grid_data = {
        "Z01": {
            "headroom_percent": 0.15,
            "power_available": True,
            "road_access": True,
            "fiber_available": True,
            "installation_cost": 800000
        },
        "Z02": {
            "headroom_percent": 0.30,
            "power_available": True,
            "road_access": True,
            "fiber_available": False,
            "installation_cost": 600000
        }
    }

    # Rank sites
    results = engine.rank_sites(candidates, demand_data, grid_data)

    print("Site Ranking Results:")
    for result in results:
        print(f"\nRank {result.rank}: {result.name}")
        print(f"  Total Score: {result.total_score:.2f}")
        print(f"  Recommendation: {result.recommendation}")
        print(f"  Red Flags: {result.red_flags}")
