"""
User Behavior Baseline Dataset
Generates synthetic user behavior data with compliance patterns and incentive responses.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import random


class UserBehaviorGenerator:
    """Generates synthetic user behavior data for EV charging compliance modeling."""

    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.zones = self.config["zones"]
        self.archetypes = self.config["archetypes"]

    def _default_config(self) -> Dict:
        """Default configuration for behavior generation."""
        return {
            "zones": [
                {"id": "Z01", "name": "Whitefield"},
                {"id": "Z02", "name": "HSR Layout"},
                {"id": "Z03", "name": "Indiranagar"},
                {"id": "Z04", "name": "Koramangala"},
                {"id": "Z05", "name": "Electronic City"},
                {"id": "Z06", "name": "Marathahalli"}
            ],
            "archetypes": [
                {"id": "A01", "name": "Commuter", "flexibility": 0.2},
                {"id": "A02", "name": "Fleet", "flexibility": 0.6},
                {"id": "A03", "name": "Opportunity", "flexibility": 0.8}
            ],
            "user_counts": {
                "Z01": 500,
                "Z02": 400,
                "Z03": 350,
                "Z04": 300,
                "Z05": 450,
                "Z06": 380
            },
            "baseline_compliance": 0.4,  # 40% baseline compliance
            "incentive_sensitivity": 0.3,  # Each ₹/kWh adds 30% probability
            "days_to_generate": 90
        }

    def generate_users(self) -> pd.DataFrame:
        """Generate synthetic user profiles."""
        users = []

        for zone in self.zones:
            zone_id = zone["id"]
            user_count = self.config["user_counts"][zone_id]

            for i in range(user_count):
                user_id = f"{zone_id}_U{i:04d}"

                # Assign archetype based on zone characteristics
                archetype = self._assign_archetype(zone_id)

                # Generate preferred charging time
                preferred_start, preferred_end = self._generate_preferred_time(archetype)

                # Generate flexibility and incentive sensitivity
                flexibility = self._generate_flexibility(archetype)
                incentive_sensitivity = np.random.beta(2, 5)  # Most users have low sensitivity

                users.append({
                    "user_id": user_id,
                    "zone_id": zone_id,
                    "archetype_id": archetype["id"],
                    "preferred_start_hour": preferred_start,
                    "preferred_end_hour": preferred_end,
                    "flexibility_score": flexibility,
                    "incentive_sensitivity": incentive_sensitivity,
                    "compliance_rate": self.config["baseline_compliance"],
                    "total_sessions": 0,
                    "shifted_sessions": 0,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                })

        return pd.DataFrame(users)

    def _assign_archetype(self, zone_id: str) -> Dict:
        """Assign archetype based on zone characteristics."""
        # Zone-specific archetype distributions
        distributions = {
            "Z01": {"A01": 0.6, "A02": 0.3, "A03": 0.1},  # Whitefield: mostly commuters
            "Z02": {"A01": 0.5, "A02": 0.2, "A03": 0.3},  # HSR: mixed
            "Z03": {"A01": 0.4, "A02": 0.1, "A03": 0.5},  # Indiranagar: more opportunity
            "Z04": {"A01": 0.5, "A02": 0.2, "A03": 0.3},  # Koramangala: mixed
            "Z05": {"A01": 0.3, "A02": 0.5, "A03": 0.2},  # Electronic City: fleet-heavy
            "Z06": {"A01": 0.6, "A02": 0.2, "A03": 0.2}   # Marathahalli: commuters
        }

        dist = distributions.get(zone_id, {"A01": 0.5, "A02": 0.3, "A03": 0.2})
        archetype_id = np.random.choice(
            list(dist.keys()),
            p=list(dist.values())
        )

        return next(a for a in self.archetypes if a["id"] == archetype_id)

    def _generate_preferred_time(self, archetype: Dict) -> Tuple[int, int]:
        """Generate preferred charging time based on archetype."""
        if archetype["id"] == "A01":  # Commuter: evening peak
            start = np.random.randint(17, 21)  # 5-8 PM
            end = start + 2
        elif archetype["id"] == "A02":  # Fleet: afternoon
            start = np.random.randint(13, 17)  # 1-5 PM
            end = start + 4
        else:  # Opportunity: distributed
            start = np.random.randint(10, 18)  # 10 AM - 6 PM
            end = start + 1

        return start, min(end, 23)

    def _generate_flexibility(self, archetype: Dict) -> float:
        """Generate flexibility score based on archetype."""
        base_flexibility = archetype["flexibility"]
        # Add some randomness
        return np.clip(np.random.normal(base_flexibility, 0.1), 0.0, 1.0)

    def generate_compliance_feedback(
        self,
        users_df: pd.DataFrame,
        start_date: datetime,
        days: int = 90
    ) -> pd.DataFrame:
        """Generate compliance feedback data."""
        feedback = []

        for day in range(days):
            current_date = start_date + timedelta(days=day)

            # Each user has 0-3 charging sessions per day
            for _, user in users_df.iterrows():
                sessions = np.random.poisson(0.5)  # Average 0.5 sessions per day

                for _ in range(sessions):
                    # Generate recommended shift
                    recommended_shift = self._generate_recommended_shift(user)

                    # Determine if user complies
                    complies = self._determine_compliance(user, recommended_shift)

                    # Calculate shift hours
                    shift_hours = recommended_shift if complies else 0

                    # Calculate incentive
                    incentive_amount = self._calculate_incentive(shift_hours, user)

                    # Generate satisfaction score
                    satisfaction = self._generate_satisfaction(complies, shift_hours, user)

                    feedback.append({
                        "time": current_date.isoformat(),
                        "user_id": user["user_id"],
                        "zone_id": user["zone_id"],
                        "recommended_start_time": (current_date + timedelta(hours=int(user["preferred_start_hour"]))).isoformat(),
                        "actual_start_time": (current_date + timedelta(hours=int(user["preferred_start_hour"]) + int(shift_hours))).isoformat() if complies else None,
                        "shifted": complies,
                        "shift_hours": float(shift_hours),
                        "incentive_amount": float(incentive_amount),
                        "incentive_type": "OFF_PEAK_SHIFT" if shift_hours > 0 else None,
                        "satisfaction_score": int(satisfaction),
                        "created_at": current_date.isoformat()
                    })

        return pd.DataFrame(feedback)

    def _generate_recommended_shift(self, user: pd.Series) -> float:
        """Generate recommended shift hours for a user."""
        # Recommend shift based on flexibility and incentive
        if user["flexibility_score"] < 0.3:
            return 0  # Low flexibility users get no recommendation

        # Recommend 2-4 hour shift for flexible users
        return np.random.choice([0, 2, 3, 4], p=[0.3, 0.3, 0.25, 0.15])

    def _determine_compliance(self, user: pd.Series, recommended_shift: float) -> bool:
        """Determine if user complies with recommended shift."""
        if recommended_shift == 0:
            return False

        # Calculate compliance probability
        base_prob = user["compliance_rate"]
        flexibility_boost = user["flexibility_score"] * 0.3
        incentive_boost = self.config["incentive_sensitivity"] * recommended_shift

        total_prob = base_prob + flexibility_boost + incentive_boost
        total_prob = min(total_prob, 0.8)  # Cap at 80%

        return np.random.random() < total_prob

    def _calculate_incentive(self, shift_hours: float, user: pd.Series) -> float:
        """Calculate incentive amount for compliance."""
        if shift_hours == 0:
            return 0.0

        # ₹2 per kWh shifted, assuming 25 kWh per session
        return 2.0 * 25 * (shift_hours / 2)  # Proportional to shift

    def _generate_satisfaction(self, complies: bool, shift_hours: float, user: pd.Series) -> int:
        """Generate satisfaction score (1-5)."""
        if not complies:
            # Non-compliant users are less satisfied
            return np.random.randint(1, 4)

        # Compliant users are more satisfied
        base_score = np.random.randint(3, 6)

        # Adjust based on shift hours (too much shift = less satisfied)
        if shift_hours > 3:
            base_score -= 1

        return max(1, min(5, base_score))

    def generate_baseline_dataset(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Generate complete baseline dataset."""
        print("Generating user profiles...")
        users_df = self.generate_users()

        print(f"Generated {len(users_df)} user profiles")

        print("Generating compliance feedback...")
        start_date = datetime.now() - timedelta(days=self.config["days_to_generate"])
        feedback_df = self.generate_compliance_feedback(
            users_df,
            start_date,
            self.config["days_to_generate"]
        )

        print(f"Generated {len(feedback_df)} compliance records")

        # Update user compliance rates based on feedback
        user_compliance = feedback_df.groupby("user_id")["shifted"].mean().reset_index()
        user_compliance.columns = ["user_id", "actual_compliance_rate"]

        users_df = users_df.merge(
            user_compliance,
            on="user_id",
            how="left"
        )
        users_df["actual_compliance_rate"] = users_df["actual_compliance_rate"].fillna(
            self.config["baseline_compliance"]
        )

        return users_df, feedback_df

    def save_to_csv(self, output_dir: str = "data/feedback"):
        """Save generated datasets to CSV files."""
        import os
        os.makedirs(output_dir, exist_ok=True)

        users_df, feedback_df = self.generate_baseline_dataset()

        users_path = f"{output_dir}/user_behavior_baseline.csv"
        feedback_path = f"{output_dir}/compliance_feedback_baseline.csv"

        users_df.to_csv(users_path, index=False)
        feedback_df.to_csv(feedback_path, index=False)

        print(f"\nSaved user behavior baseline to: {users_path}")
        print(f"Saved compliance feedback baseline to: {feedback_path}")

        # Print summary statistics
        print("\n=== Summary Statistics ===")
        print(f"Total users: {len(users_df)}")
        print(f"Total compliance records: {len(feedback_df)}")
        print(f"Average compliance rate: {users_df['actual_compliance_rate'].mean():.2%}")
        print(f"Compliance rate by archetype:")
        for archetype in self.archetypes:
            arch_users = users_df[users_df["archetype_id"] == archetype["id"]]
            if len(arch_users) > 0:
                print(f"  {archetype['name']}: {arch_users['actual_compliance_rate'].mean():.2%}")


if __name__ == "__main__":
    generator = UserBehaviorGenerator()
    generator.save_to_csv()
