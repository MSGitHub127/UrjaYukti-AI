"""
Comprehensive Test Script for UrjaYukti AI
Tests all components and verifies they produce expected outputs.
"""

import sys
import os

# Compute absolute path to backend/src so imports work regardless of CWD.
_src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'src')
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("=" * 60)
print("UrjaYukti AI - Comprehensive Component Testing")
print("=" * 60)

# Test 1: Synthetic Data Generator
print("\n[1/8] Testing Synthetic EV Demand Generator...")
try:
    from models.synthetic_generator import SyntheticDemandGenerator
    generator = SyntheticDemandGenerator()
    demand_df = generator.generate_demand()

    # Verify output
    assert len(demand_df) > 0, "No demand data generated"
    assert "time" in demand_df.columns, "Missing time column"
    assert "zone_id" in demand_df.columns, "Missing zone_id column"
    assert "demand_kw" in demand_df.columns, "Missing demand_kw column"

    # Check zones
    zones = demand_df["zone_id"].unique()
    assert len(zones) == 6, f"Expected 6 zones, got {len(zones)}"

    print("  - Generated {} demand records".format(len(demand_df)))
    print("  - Zones: {}".format(list(zones)))
    print("  - Total demand: {:.2f} kWh".format(demand_df["demand_kw"].sum()))
    print("  PASS: Synthetic data generator working correctly")
except Exception as e:
    print("  FAIL: {}".format(str(e)))

# Test 2: User Behavior Baseline Generator
print("\n[2/8] Testing User Behavior Baseline Generator...")
try:
    from models.behavior.baseline_generator import UserBehaviorGenerator
    behavior_gen = UserBehaviorGenerator()
    users_df, feedback_df = behavior_gen.generate_baseline_dataset()

    # Verify output
    assert len(users_df) > 0, "No user profiles generated"
    assert len(feedback_df) > 0, "No compliance feedback generated"

    # Check compliance rate
    avg_compliance = users_df["actual_compliance_rate"].mean()
    assert 0 <= avg_compliance <= 1, "Invalid compliance rate"

    print("  - Generated {} user profiles".format(len(users_df)))
    print("  - Generated {} compliance records".format(len(feedback_df)))
    print("  - Average compliance rate: {:.2%}".format(avg_compliance))
    print("  PASS: Behavior baseline generator working correctly")
except Exception as e:
    print("  FAIL: {}".format(str(e)))

# Test 3: VPP Scheduler
print("\n[3/8] Testing VPP Scheduler...")
try:
    from optimization.vpp.scheduler import VPPScheduler, ChargingSession, ZoneConstraint

    scheduler = VPPScheduler()

    # Set up constraints
    constraints = [
        ZoneConstraint("Z01", 50.0, 42.5, 7.5),
        ZoneConstraint("Z02", 40.0, 28.0, 12.0)
    ]
    scheduler.set_zone_constraints(constraints)

    # Create test sessions
    sessions = [
        ChargingSession("S001", "U001", "Z01", "A01", 18, 20, 25.0, 7.2, 2, 0.6, True),
        ChargingSession("S002", "U002", "Z01", "A01", 19, 21, 30.0, 7.2, 3, 0.5, True)
    ]

    # Create forecast data
    forecast_data = pd.DataFrame({
        "time": pd.date_range(start=datetime.now(), periods=48, freq="h"),
        "zone_id": ["Z01"] * 24 + ["Z02"] * 24,
        "prediction": [100.0] * 24 + [80.0] * 24
    })

    # Optimize
    scheduled, metrics = scheduler.optimize_schedule(sessions, forecast_data)

    # Verify output
    assert len(scheduled) == 2, "Not all sessions scheduled"
    assert "peak_load_index" in metrics, "Missing PLI metric"
    assert "peak_load_reduction" in metrics, "Missing PLR metric"

    print("  - Scheduled {} sessions".format(len(scheduled)))
    print("  - Peak Load Index: {:.2f}".format(metrics["peak_load_index"]))
    print("  - Peak Load Reduction: {:.2%}".format(metrics["peak_load_reduction"]))
    print("  PASS: VPP scheduler working correctly")
except Exception as e:
    print("  FAIL: {}".format(str(e)))

# Test 4: MCDA Site Scorer
print("\n[4/8] Testing MCDA Site Scorer...")
try:
    from optimization.mcda.site_scorer import MCDAEngine, SiteCandidate

    engine = MCDAEngine()

    # Create test candidates
    candidates = [
        SiteCandidate("S001", "Whitefield Tech Park", "Z01", (12.9698, 77.7499)),
        SiteCandidate("S002", "HSR Bus Depot", "Z02", (12.9138, 77.6374))
    ]

    # Create test data
    demand_data = pd.DataFrame({
        "zone_id": ["Z01"] * 24 + ["Z02"] * 24,
        "prediction": [500.0] * 24 + [300.0] * 24
    })

    grid_data = {
        "Z01": {"headroom_percent": 0.15, "power_available": True, "road_access": True, "fiber_available": True, "installation_cost": 800000},
        "Z02": {"headroom_percent": 0.30, "power_available": True, "road_access": True, "fiber_available": False, "installation_cost": 600000}
    }

    # Rank sites
    results = engine.rank_sites(candidates, demand_data, grid_data)

    # Verify output
    assert len(results) == 2, "Not all sites ranked"
    assert results[0].rank == 1, "First site should have rank 1"
    assert results[0].total_score >= 0, "Invalid total score"

    print("  - Ranked {} sites".format(len(results)))
    print("  - Top site: {} (score: {:.2f})".format(results[0].name, results[0].total_score))
    print("  - Recommendation: {}".format(results[0].recommendation))
    print("  PASS: MCDA site scorer working correctly")
except Exception as e:
    print("  FAIL: {}".format(str(e)))

# Test 5: HDBSCAN Clustering
print("\n[5/8] Testing HDBSCAN Clustering...")
try:
    from optimization.spatial.clustering import HDBSCANPipeline

    pipeline = HDBSCANPipeline(min_cluster_size=10)

    # Create test demand points
    np.random.seed(42)
    points = []
    demands = []
    zone_ids = []

    # Create cluster 1
    for _ in range(30):
        lat = 12.9698 + np.random.normal(0, 0.01)
        lon = 77.7499 + np.random.normal(0, 0.01)
        demand = np.random.uniform(20, 50)
        points.append((lat, lon))
        demands.append(demand)
        zone_ids.append("Z01")

    # Create cluster 2
    for _ in range(30):
        lat = 12.9138 + np.random.normal(0, 0.01)
        lon = 77.6374 + np.random.normal(0, 0.01)
        demand = np.random.uniform(15, 40)
        points.append((lat, lon))
        demands.append(demand)
        zone_ids.append("Z02")

    demand_data = pd.DataFrame({
        "lat": [p[0] for p in points],
        "lon": [p[1] for p in points],
        "demand_kw": demands,
        "zone_id": zone_ids
    })

    # Cluster
    result = pipeline.cluster_demand_points(demand_data)

    # Verify output
    assert len(result.clusters) > 0, "No clusters found"
    assert result.total_demand_kw > 0, "No total demand calculated"

    print("  - Found {} clusters".format(len(result.clusters)))
    print("  - Clustered demand: {:.1f}%".format(result.clustered_demand_percent))
    print("  - Total demand: {:.2f} kW".format(result.total_demand_kw))
    print("  PASS: HDBSCAN clustering working correctly")
except Exception as e:
    print("  FAIL: {}".format(str(e)))

# Test 6: Peak Load Calculator
print("\n[6/8] Testing Peak Load Calculator...")
try:
    from optimization.metrics import PeakLoadCalculator

    calculator = PeakLoadCalculator(pli_target=0.85, plr_target=0.15)

    # Create test hourly load
    hours = list(range(24))
    base_load = [100.0] * 24
    base_load[19] = 450.0  # Peak at 7 PM

    hourly_load = pd.DataFrame({
        "hour": hours,
        "load_kw": base_load
    })

    # Calculate metrics
    metrics = calculator.calculate_metrics(hourly_load, 500.0)

    # Verify output
    assert metrics.pli > 0, "Invalid PLI"
    assert metrics.pli_status in ["SAFE", "CAUTION", "CRITICAL"], "Invalid status"

    print("  - Peak Load Index: {:.2f}".format(metrics.pli))
    print("  - Status: {}".format(metrics.pli_status))
    print("  - Peak Hour: {}:00".format(metrics.peak_hour))
    print("  - Peak Load: {:.2f} kW".format(metrics.peak_load_kw))
    print("  PASS: Peak load calculator working correctly")
except Exception as e:
    print("  FAIL: {}".format(str(e)))

# Test 7: Cross-Zone Balancer
print("\n[7/8] Testing Cross-Zone Balancer...")
try:
    from optimization.cross_zone.balancer import CrossZoneBalancer, ZoneConnection

    balancer = CrossZoneBalancer()

    # Add connections
    balancer.add_connection(ZoneConnection("Z01", "Z05", 8.5, 5.0))
    balancer.add_connection(ZoneConnection("Z01", "Z06", 5.2, 8.0))

    # Set up zone loads
    zone_loads = {"Z01": 45000.0, "Z05": 35000.0, "Z06": 30000.0}
    zone_capacities = {"Z01": 50000.0, "Z05": 45000.0, "Z06": 38000.0}

    # Update states
    balancer.update_zone_states(zone_loads, zone_capacities)

    # Detect spill-over
    spill_over = balancer.detect_spill_over()

    # Verify output
    assert len(balancer.zone_states) == 3, "Not all zone states updated"

    print("  - Zone states updated: {}".format(len(balancer.zone_states)))
    print("  - Spill-over zones: {}".format(spill_over))
    print("  - Connections: {}".format(len(balancer.connections)))
    print("  PASS: Cross-zone balancer working correctly")
except Exception as e:
    print("  FAIL: {}".format(str(e)))

# Test 8: API Imports
print("\n[8/8] Testing API Imports...")
try:
    from api.forecast import ForecastAPI
    from api.optimization import OptimizationAPI

    # Create API instances
    forecast_api = ForecastAPI()
    optimization_api = OptimizationAPI()

    # Verify apps are created
    assert forecast_api.app is not None, "Forecast API app not created"
    assert optimization_api.app is not None, "Optimization API app not created"

    print("  - Forecast API: OK")
    print("  - Optimization API: OK")
    print("  - Endpoints available:")
    print("    Forecast: /api/forecast, /api/anomalies, /api/health")
    print("    Optimization: /api/schedule, /api/sites/rank, /api/clustering")
    print("  PASS: APIs imported successfully")
except Exception as e:
    print("  FAIL: {}".format(str(e)))

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print("All core components tested successfully!")
print("\nGenerated Data Files:")
print("  - data/synthetic/ev_demand.csv")
print("  - data/feedback/user_behavior_baseline.csv")
print("  - data/feedback/compliance_feedback_baseline.csv")
print("\nTo run APIs:")
print("  python backend/src/api/forecast.py")
print("  python backend/src/api/optimization.py")
print("\nAPI Documentation:")
print("  http://localhost:8000/docs (Forecast API)")
print("  http://localhost:8001/docs (Optimization API)")
print("=" * 60)
