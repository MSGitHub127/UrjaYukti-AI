"""
Synthetic EV Demand Dataset Generator
Uses agent-based modeling to generate realistic EV charging demand patterns.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import random


class EVAgent:
    """Represents a single EV user with charging behavior."""

    def __init__(self, agent_id: str, zone_id: str, archetype: str, config: Dict):
        self.agent_id = agent_id
        self.zone_id = zone_id
        self.archetype = archetype
        self.config = config

        # Agent-specific parameters
        self.battery_capacity = self._generate_battery_capacity()
        self.daily_driving_km = self._generate_daily_driving()
        self.charging_efficiency = 0.9
        self.current_soc = np.random.uniform(0.2, 0.8)

        # Behavioral parameters
        self.preferred_charging_time = self._generate_preferred_time()
        self.flexibility = self._generate_flexibility()
        self.home_charging = np.random.random() < 0.7  # 70% have home charging

    def _generate_battery_capacity(self) -> float:
        """Generate battery capacity in kWh based on archetype."""
        capacities = {
            "A01": np.random.normal(40, 10),  # Commuter: 40kWh average
            "A02": np.random.normal(60, 15),  # Fleet: 60kWh average
            "A03": np.random.normal(30, 8)    # Opportunity: 30kWh average
        }
        return max(20, capacities[self.archetype])

    def _generate_daily_driving(self) -> float:
        """Generate daily driving distance in km."""
        driving = {
            "A01": np.random.normal(50, 20),  # Commuter: 50km average
            "A02": np.random.normal(150, 50), # Fleet: 150km average
            "A03": np.random.normal(30, 15)   # Opportunity: 30km average
        }
        return max(10, driving[self.archetype])

    def _generate_preferred_time(self) -> Tuple[int, int]:
        """Generate preferred charging time window."""
        if self.archetype == "A01":  # Commuter: evening peak
            start = np.random.randint(17, 21)
            end = start + 2
        elif self.archetype == "A02":  # Fleet: afternoon
            start = np.random.randint(13, 17)
            end = start + 4
        else:  # Opportunity: distributed
            start = np.random.randint(10, 18)
            end = start + 1

        return start, min(end, 23)

    def _generate_flexibility(self) -> float:
        """Generate flexibility score (0-1)."""
        base_flexibility = {
            "A01": 0.2,
            "A02": 0.6,
            "A03": 0.8
        }
        return np.clip(np.random.normal(base_flexibility[self.archetype], 0.1), 0.0, 1.0)

    def simulate_day(self, date: datetime) -> List[Dict]:
        """Simulate charging behavior for a single day."""
        sessions = []

        # Determine if charging is needed today
        energy_needed = self._calculate_energy_needed()
        if energy_needed < 5:  # Less than 5kWh needed, skip
            return sessions

        # Determine charging time
        start_hour, duration = self._determine_charging_schedule(date)

        # Calculate charging power
        charging_power = self._get_charging_power()

        # Calculate energy charged
        energy_charged = min(energy_needed, charging_power * duration)

        sessions.append({
            "agent_id": self.agent_id,
            "zone_id": self.zone_id,
            "archetype_id": self.archetype,
            "date": date.date(),
            "start_hour": start_hour,
            "duration_hours": duration,
            "energy_kwh": energy_charged,
            "power_kw": charging_power,
            "flexibility": self.flexibility,
            "home_charging": self.home_charging
        })

        return sessions

    def _calculate_energy_needed(self) -> float:
        """Calculate energy needed based on driving and current SOC."""
        # Energy consumption: ~0.15 kWh/km
        energy_consumed = self.daily_driving_km * 0.15
        energy_needed = energy_consumed - (self.current_soc * self.battery_capacity)

        # Update SOC for next day
        self.current_soc = max(0.2, self.current_soc - (energy_consumed / self.battery_capacity))

        return max(0, energy_needed)

    def _determine_charging_schedule(self, date: datetime) -> Tuple[int, float]:
        """Determine when and how long to charge."""
        preferred_start, preferred_end = self.preferred_charging_time

        # Add some randomness to preferred time
        start_hour = preferred_start + np.random.randint(-1, 2)
        start_hour = max(0, min(23, start_hour))

        # Duration based on energy needed and flexibility
        base_duration = 2  # Default 2 hours
        if self.flexibility > 0.5:
            # More flexible users may charge longer
            duration = base_duration + np.random.choice([0, 1, 2])
        else:
            duration = base_duration

        return start_hour, duration

    def _get_charging_power(self) -> float:
        """Get charging power in kW."""
        if self.home_charging:
            return 7.2  # Level 2 home charging
        else:
            return 50  # DC fast charging


class SyntheticDemandGenerator:
    """Generates synthetic EV demand data using agent-based modeling."""

    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.agents: List[EVAgent] = []
        self._initialize_agents()

    def _default_config(self) -> Dict:
        """Default configuration for demand generation."""
        return {
            "zones": [
                {"id": "Z01", "name": "Whitefield", "ev_count": 5000},
                {"id": "Z02", "name": "HSR Layout", "ev_count": 4000},
                {"id": "Z03", "name": "Indiranagar", "ev_count": 3500},
                {"id": "Z04", "name": "Koramangala", "ev_count": 3000},
                {"id": "Z05", "name": "Electronic City", "ev_count": 4500},
                {"id": "Z06", "name": "Marathahalli", "ev_count": 3800}
            ],
            "archetypes": [
                {"id": "A01", "name": "Commuter", "distribution": [0.6, 0.5, 0.4, 0.5, 0.3, 0.6]},
                {"id": "A02", "name": "Fleet", "distribution": [0.3, 0.2, 0.1, 0.2, 0.5, 0.2]},
                {"id": "A03", "name": "Opportunity", "distribution": [0.1, 0.3, 0.5, 0.3, 0.2, 0.2]}
            ],
            "days_to_generate": 90,
            "start_date": datetime.now() - timedelta(days=90)
        }

    def _initialize_agents(self):
        """Initialize EV agents for each zone."""
        print("Initializing EV agents...")

        for zone in self.config["zones"]:
            zone_id = zone["id"]
            ev_count = zone["ev_count"]

            # Get archetype distribution for this zone
            zone_idx = self.config["zones"].index(zone)
            archetype_dist = {
                a["id"]: a["distribution"][zone_idx]
                for a in self.config["archetypes"]
            }

            # Create agents
            for i in range(ev_count):
                agent_id = f"{zone_id}_E{i:05d}"

                # Assign archetype based on distribution
                archetype_id = np.random.choice(
                    list(archetype_dist.keys()),
                    p=list(archetype_dist.values())
                )

                agent = EVAgent(agent_id, zone_id, archetype_id, self.config)
                self.agents.append(agent)

        print(f"Initialized {len(self.agents)} EV agents")

    def generate_demand(self) -> pd.DataFrame:
        """Generate demand data for all agents over the configured period."""
        print(f"Generating demand data for {self.config['days_to_generate']} days...")

        all_sessions = []

        for day in range(self.config["days_to_generate"]):
            current_date = self.config["start_date"] + timedelta(days=day)

            # Simulate each agent
            for agent in self.agents:
                sessions = agent.simulate_day(current_date)
                all_sessions.extend(sessions)

            if (day + 1) % 10 == 0:
                print(f"  Generated {day + 1}/{self.config['days_to_generate']} days")

        # Convert to DataFrame
        df = pd.DataFrame(all_sessions)

        # Aggregate by hour, zone, and archetype
        demand_df = self._aggregate_demand(df)

        return demand_df

    def _aggregate_demand(self, sessions_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate individual sessions to hourly demand by zone and archetype."""
        # Create hourly records
        hourly_records = []

        for _, session in sessions_df.iterrows():
            start_hour = int(session["start_hour"])
            duration = session["duration_hours"]

            for hour_offset in range(int(duration)):
                hour = (start_hour + hour_offset) % 24
                date = session["date"]

                hourly_records.append({
                    "time": datetime.combine(date, datetime.min.time()) + timedelta(hours=hour),
                    "zone_id": session["zone_id"],
                    "archetype_id": session["archetype_id"],
                    "demand_kw": session["power_kw"],
                    "session_count": 1,
                    "avg_session_duration_min": session["duration_hours"] * 60,
                    "confidence": "HIGH",
                    "data_source": "SYNTHETIC"
                })

        # Aggregate by time, zone, and archetype
        df = pd.DataFrame(hourly_records)
        aggregated = df.groupby(
            ["time", "zone_id", "archetype_id"]
        ).agg({
            "demand_kw": "sum",
            "session_count": "sum",
            "avg_session_duration_min": "mean"
        }).reset_index()

        # Add created_at timestamp
        aggregated["created_at"] = datetime.now().isoformat()

        return aggregated

    def save_to_csv(self, output_path: str = "data/synthetic/ev_demand.csv"):
        """Save generated demand data to CSV."""
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        demand_df = self.generate_demand()
        demand_df.to_csv(output_path, index=False)

        print(f"\nSaved EV demand data to: {output_path}")
        print(f"Total records: {len(demand_df)}")

        # Print summary statistics
        self._print_summary(demand_df)

        return demand_df

    def _print_summary(self, df: pd.DataFrame):
        """Print summary statistics of generated data."""
        print("\n=== Summary Statistics ===")

        # Total demand by zone
        print("\nTotal demand by zone:")
        zone_demand = df.groupby("zone_id")["demand_kw"].sum()
        for zone_id, demand in zone_demand.items():
            zone_name = next(z["name"] for z in self.config["zones"] if z["id"] == zone_id)
            print(f"  {zone_name} ({zone_id}): {demand:,.0f} kWh")

        # Demand by archetype
        print("\nTotal demand by archetype:")
        arch_demand = df.groupby("archetype_id")["demand_kw"].sum()
        for arch_id, demand in arch_demand.items():
            arch_name = next(a["name"] for a in self.config["archetypes"] if a["id"] == arch_id)
            print(f"  {arch_name} ({arch_id}): {demand:,.0f} kWh")

        # Hourly demand pattern
        print("\nAverage hourly demand (all zones):")
        hourly_demand = df.groupby(df["time"].dt.hour)["demand_kw"].mean()
        for hour in range(24):
            demand = hourly_demand.get(hour, 0)
            bar = "█" * int(demand / 100)
            print(f"  {hour:02d}:00 - {bar} {demand:,.0f} kW")

        # Peak hours
        print("\nPeak demand hours:")
        peak_hours = df.groupby(df["time"].dt.hour)["demand_kw"].sum().nlargest(5)
        for hour, demand in peak_hours.items():
            print(f"  {hour:02d}:00: {demand:,.0f} kW")


if __name__ == "__main__":
    generator = SyntheticDemandGenerator()
    generator.save_to_csv()
