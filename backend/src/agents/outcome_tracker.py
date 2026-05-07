"""
Outcome Tracker Module
Records shift outcomes, compliance rates, and feeds back to probability model for continuous learning.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np


class ShiftOutcome(Enum):
    """Possible outcomes of a shift recommendation."""

    APPLIED = "applied"
    PARTIALLY_APPLIED = "partially_applied"
    IGNORED = "ignored"
    FAILED = "failed"
    DEFERRED = "deferred"


@dataclass
class ShiftRecord:
    """Record of a shift recommendation and its outcome."""

    record_id: str
    session_id: str
    user_id: str
    zone_id: str
    archetype_id: str
    recommended_start_hour: int
    actual_start_hour: Optional[int]
    shift_hours: float
    incentive_amount: float
    incentive_type: str
    compliance_probability: float
    outcome: ShiftOutcome
    timestamp: datetime
    satisfaction_score: Optional[int] = None
    metadata: Dict = field(default_factory=dict)


class OutcomeTracker:
    """Production-grade outcome tracker for continuous learning."""

    def __init__(
        self,
        learning_rate: float = 0.1,  # Learning rate for probability updates
        min_samples_for_update: int = 50,  # Minimum samples before updating model
        feedback_window_days: int = 30  # Feedback window for learning
    ):
        self.learning_rate = learning_rate
        self.min_samples_for_update = min_samples_for_update
        self.feedback_window_days = feedback_window_days

        self.logger = logging.getLogger(__name__)

        # Storage
        self.shift_records: List[ShiftRecord] = []
        self.compliance_history: Dict[str, List[float]] = {}  # user_id -> [compliance_probabilities]

        # Statistics
        self.total_shifts = 0
        self.applied_shifts = 0
        self.ignored_shifts = 0
        self.failed_shifts = 0

    def record_shift(
        self,
        session_id: str,
        user_id: str,
        zone_id: str,
        archetype_id: str,
        recommended_start_hour: int,
        actual_start_hour: Optional[int],
        shift_hours: float,
        incentive_amount: float,
        incentive_type: str,
        compliance_probability: float,
        satisfaction_score: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Record the outcome of a shift recommendation.

        Args:
            session_id: Session ID
            user_id: User ID
            zone_id: Zone ID
            archetype_id: Archetype ID
            recommended_start_hour: Recommended start hour
            actual_start_hour: Actual start hour (None if not applied)
            shift_hours: Shift hours (positive if shifted later, negative if earlier)
            incentive_amount: Incentive amount in ₹
            incentive_type: Type of incentive
            compliance_probability: Predicted compliance probability
            satisfaction_score: User satisfaction score (1-5)
            metadata: Additional metadata

        Returns:
            Record ID
        """
        # Determine outcome
        if actual_start_hour is None:
            outcome = ShiftOutcome.IGNORED
        elif actual_start_hour == recommended_start_hour:
            outcome = ShiftOutcome.APPLIED
        elif abs(actual_start_hour - recommended_start_hour) <= 1:
            outcome = ShiftOutcome.PARTIALLY_APPLIED
        else:
            outcome = ShiftOutcome.IGNORED

        # Create record
        record_id = f"R_{session_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        record = ShiftRecord(
            record_id=record_id,
            session_id=session_id,
            user_id=user_id,
            zone_id=zone_id,
            archetype_id=archetype_id,
            recommended_start_hour=recommended_start_hour,
            actual_start_hour=actual_start_hour,
            shift_hours=shift_hours,
            incentive_amount=incentive_amount,
            incentive_type=incentive_type,
            compliance_probability=compliance_probability,
            outcome=outcome,
            satisfaction_score=satisfaction_score,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )

        # Store record
        self.shift_records.append(record)

        # Update statistics
        self.total_shifts += 1
        if outcome == ShiftOutcome.APPLIED:
            self.applied_shifts += 1
        elif outcome == ShiftOutcome.IGNORED:
            self.ignored_shifts += 1
        elif outcome == ShiftOutcome.FAILED:
            self.failed_shifts += 1

        # Update compliance history
        if user_id not in self.compliance_history:
            self.compliance_history[user_id] = []

        # Update compliance probability based on outcome
        if outcome in [ShiftOutcome.APPLIED, ShiftOutcome.PARTIALLY_APPLIED]:
            # Increase compliance probability for successful shifts
            current_prob = self.compliance_history[user_id][-1] if self.compliance_history[user_id] else 0.4
            new_prob = min(0.9, current_prob + self.learning_rate * 0.1)
            self.compliance_history[user_id].append(new_prob)
        else:
            # Decrease compliance probability for ignored shifts
            current_prob = self.compliance_history[user_id][-1] if self.compliance_history[user_id] else 0.4
            new_prob = max(0.1, current_prob - self.learning_rate * 0.05)
            self.compliance_history[user_id].append(new_prob)

        # Keep only last 100 records per user
        if len(self.compliance_history[user_id]) > 100:
            self.compliance_history[user_id] = self.compliance_history[user_id][-100:]

        self.logger.info(f"Recorded shift {record_id} with outcome {outcome.value}")

        return record_id

    def get_user_compliance_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Tuple[datetime, float, ShiftOutcome]]:
        """
        Get compliance history for a user.

        Args:
            user_id: User ID
            limit: Maximum number of records to return

        Returns:
            List of (timestamp, compliance_probability, outcome) tuples
        """
        if user_id not in self.compliance_history:
            return []

        history = self.compliance_history[user_id]

        # Get shift records for this user
        user_records = [
            (r.timestamp, r.compliance_probability, r.outcome)
            for r in self.shift_records
            if r.user_id == user_id
        ]

        # Sort by timestamp (most recent first)
        user_records.sort(key=lambda x: x[0], reverse=True)

        # Return limited records
        return user_records[:limit]

    def get_zone_compliance_stats(
        self,
        zone_id: str,
        hours_back: int = 24
    ) -> Dict[str, any]:
        """
        Get compliance statistics for a zone.

        Args:
            zone_id: Zone ID
            hours_back: Hours to look back

        Returns:
            Dictionary with compliance statistics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        # Get recent records for zone
        zone_records = [
            r for r in self.shift_records
            if r.zone_id == zone_id and r.timestamp >= cutoff_time
        ]

        if not zone_records:
            return {
                "zone_id": zone_id,
                "status": "no_data",
                "total_shifts": 0,
                "applied_shifts": 0,
                "ignored_shifts": 0,
                "failed_shifts": 0,
                "avg_compliance_probability": 0.0
            }

        # Calculate statistics
        total_shifts = len(zone_records)
        applied_shifts = sum(1 for r in zone_records if r.outcome == ShiftOutcome.APPLIED)
        ignored_shifts = sum(1 for r in zone_records if r.outcome == ShiftOutcome.IGNORED)
        failed_shifts = sum(1 for r in zone_records if r.outcome == ShiftOutcome.FAILED)

        # Calculate average compliance probability
        compliance_probs = [r.compliance_probability for r in zone_records]
        avg_compliance = np.mean(compliance_probs) if compliance_probs else 0.0

        # Calculate outcome distribution
        outcome_counts = {}
        for record in zone_records:
            outcome = record.outcome.value
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        # Calculate incentive effectiveness
        incentive_records = [r for r in zone_records if r.incentive_amount > 0]
        if incentive_records:
            applied_with_incentive = sum(
                1 for r in incentive_records
                if r.outcome == ShiftOutcome.APPLIED
            )
            incentive_effectiveness = (
                applied_with_incentive / len(incentive_records)
                if incentive_records else 0
            )
        else:
            incentive_effectiveness = 0.0

        return {
            "zone_id": zone_id,
            "status": "available",
            "total_shifts": total_shifts,
            "applied_shifts": applied_shifts,
            "ignored_shifts": ignored_shifts,
            "failed_shifts": failed_shifts,
            "compliance_rate": avg_compliance,
            "outcome_distribution": outcome_counts,
            "incentive_effectiveness": incentive_effectiveness,
            "time_window_hours": hours_back
        }

    def get_archetype_compliance_stats(
        self,
        archetype_id: str,
        hours_back: int = 24
    ) -> Dict[str, any]:
        """
        Get compliance statistics by archetype.

        Args:
            archetype_id: Archetype ID
            hours_back: Hours to look back

        Returns:
            Dictionary with compliance statistics by archetype
        """
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        # Get recent records for archetype
        archetype_records = [
            r for r in self.shift_records
            if r.archetype_id == archetype_id and r.timestamp >= cutoff_time
        ]

        if not archetype_records:
            return {
                "archetype_id": archetype_id,
                "status": "no_data",
                "total_shifts": 0,
                "applied_shifts": 0,
                "ignored_shifts": 0,
                "failed_shifts": 0,
                "avg_compliance_probability": 0.0
            }

        # Calculate statistics
        total_shifts = len(archetype_records)
        applied_shifts = sum(1 for r in archetype_records if r.outcome == ShiftOutcome.APPLIED)
        ignored_shifts = sum(1 for r in archetype_records if r.outcome == ShiftOutcome.IGNORED)
        failed_shifts = sum(1 for r in archetype_records if r.outcome == ShiftOutcome.FAILED)

        # Calculate average compliance probability
        compliance_probs = [r.compliance_probability for r in archetype_records]
        avg_compliance = np.mean(compliance_probs) if compliance_probs else 0.0

        # Calculate outcome distribution
        outcome_counts = {}
        for record in archetype_records:
            outcome = record.outcome.value
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        # Calculate shift hour distribution
        shift_hours = [r.shift_hours for r in archetype_records if r.shift_hours != 0]
        avg_shift = np.mean(shift_hours) if shift_hours else 0.0

        return {
            "archetype_id": archetype_id,
            "status": "available",
            "total_shifts": total_shifts,
            "applied_shifts": applied_shifts,
            "ignored_shifts": ignored_shifts,
            "failed_shifts": failed_shifts,
            "compliance_rate": avg_compliance,
            "outcome_distribution": outcome_counts,
            "avg_shift_hours": avg_shift,
            "time_window_hours": hours_back
        }

    def get_global_stats(self) -> Dict[str, any]:
        """
        Get global statistics across all shifts.

        Returns:
            Dictionary with global statistics
        """
        if not self.shift_records:
            return {
                "status": "no_data",
                "total_shifts": 0,
                "applied_shifts": 0,
                "ignored_shifts": 0,
                "failed_shifts": 0,
                "avg_compliance_probability": 0.0
            }

        # Calculate global statistics
        total_shifts = len(self.shift_records)
        applied_shifts = sum(1 for r in self.shift_records if r.outcome == ShiftOutcome.APPLIED)
        ignored_shifts = sum(1 for r in self.shift_records if r.outcome == ShiftOutcome.IGNORED)
        failed_shifts = sum(1 for r in self.shift_records if r.outcome == ShiftOutcome.FAILED)

        # Calculate average compliance probability
        compliance_probs = [r.compliance_probability for r in self.shift_records]
        avg_compliance = np.mean(compliance_probs) if compliance_probs else 0.0

        # Calculate outcome distribution
        outcome_counts = {}
        for record in self.shift_records:
            outcome = record.outcome.value
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        # Calculate incentive effectiveness
        incentive_records = [r for r in self.shift_records if r.incentive_amount > 0]
        if incentive_records:
            applied_with_incentive = sum(
                1 for r in incentive_records
                if r.outcome == ShiftOutcome.APPLIED
            )
            incentive_effectiveness = (
                applied_with_incentive / len(incentive_records)
                if incentive_records else 0
            )
        else:
            incentive_effectiveness = 0.0

        # Calculate shift hour distribution
        shift_hours = [r.shift_hours for r in self.shift_records if r.shift_hours != 0]
        avg_shift = np.mean(shift_hours) if shift_hours else 0.0

        # Calculate zone distribution
        zone_counts = {}
        for record in self.shift_records:
            zone_id = record.zone_id
            zone_counts[zone_id] = zone_counts.get(zone_id, 0) + 1

        # Calculate archetype distribution
        archetype_counts = {}
        for record in self.shift_records:
            archetype_id = record.archetype_id
            archetype_counts[archetype_id] = archetype_counts.get(archetype_id, 0) + 1

        return {
            "status": "available",
            "total_shifts": total_shifts,
            "applied_shifts": applied_shifts,
            "ignored_shifts": ignored_shifts,
            "failed_shifts": failed_shifts,
            "compliance_rate": avg_compliance,
            "outcome_distribution": outcome_counts,
            "incentive_effectiveness": incentive_effectiveness,
            "avg_shift_hours": avg_shift,
            "zone_distribution": zone_counts,
            "archetype_distribution": archetype_counts,
            "total_users": len(self.compliance_history)
        }

    def update_compliance_model(
        self,
        user_id: str,
        new_compliance_probability: float
    ) -> bool:
        """
        Update compliance probability for a user.

        Args:
            user_id: User ID
            new_compliance_probability: New compliance probability

        Returns:
            True if updated, False otherwise
        """
        if user_id not in self.compliance_history:
            self.compliance_history[user_id] = [new_compliance_probability]
            return True

        # Update probability
        self.compliance_history[user_id].append(new_compliance_probability)

        # Keep only last 100 records
        if len(self.compliance_history[user_id]) > 100:
            self.compliance_history[user_id] = self.compliance_history[user_id][-100:]

        self.logger.info(f"Updated compliance probability for user {user_id} to {new_compliance_probability:.2f}")

        return True

    def get_compliance_model_update(
        self,
        min_samples: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Get compliance model updates that should be applied.

        Args:
            min_samples: Minimum samples required for update

        Returns:
            Dictionary with users requiring model updates
        """
        min_samples = min_samples or self.min_samples_for_update

        updates = {}

        for user_id, history in self.compliance_history.items():
            if len(history) >= min_samples:
                # Calculate trend
                recent_probs = history[-10:] if len(history) >= 10 else history
                if len(recent_probs) >= 2:
                    first_half = np.mean(recent_probs[:len(recent_probs)//2])
                    second_half = np.mean(recent_probs[len(recent_probs)//2:])

                    if second_half > first_half:
                        trend = "increasing"
                    elif second_half < first_half:
                        trend = "decreasing"
                    else:
                        trend = "stable"

                    avg_prob = np.mean(history)

                    updates[user_id] = {
                        "current_probability": avg_prob,
                        "trend": trend,
                        "sample_count": len(history),
                        "recommended_update": "increase" if trend == "increasing" else "decrease"
                    }

        return updates

    def clear_old_records(self, days_to_keep: int = 90) -> int:
        """
        Clear old shift records.

        Args:
            days_to_keep: Number of days of records to keep

        Returns:
            Number of records cleared
        """
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)

        original_count = len(self.shift_records)
        self.shift_records = [
            r for r in self.shift_records
            if r.timestamp >= cutoff_time
        ]

        cleared_count = original_count - len(self.shift_records)

        self.logger.info(f"Cleared {cleared_count} old shift records")

        return cleared_count

    def export_to_csv(self, output_path: str) -> str:
        """
        Export shift records to CSV file.

        Args:
            output_path: Path to output CSV file

        Returns:
            Path where file was saved
        """
        import os

        # Create directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Convert to DataFrame
        records_data = []
        for record in self.shift_records:
            records_data.append({
                "record_id": record.record_id,
                "session_id": record.session_id,
                "user_id": record.user_id,
                "zone_id": record.zone_id,
                "archetype_id": record.archetype_id,
                "recommended_start_hour": record.recommended_start_hour,
                "actual_start_hour": record.actual_start_hour,
                "shift_hours": record.shift_hours,
                "incentive_amount": record.incentive_amount,
                "incentive_type": record.incentive_type,
                "compliance_probability": record.compliance_probability,
                "outcome": record.outcome.value,
                "satisfaction_score": record.satisfaction_score,
                "timestamp": record.timestamp.isoformat()
            })

        df = pd.DataFrame(records_data)
        df.to_csv(output_path, index=False)

        self.logger.info(f"Exported {len(df)} shift records to {output_path}")

        return output_path

    def import_from_csv(self, input_path: str) -> int:
        """
        Import shift records from CSV file.

        Args:
            input_path: Path to input CSV file

        Returns:
            Number of records imported
        """
        import os

        if not os.path.exists(input_path):
            return 0

        df = pd.read_csv(input_path)

        count = 0
        for _, row in df.iterrows():
            try:
                record = ShiftRecord(
                    record_id=row["record_id"],
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    zone_id=row["zone_id"],
                    archetype_id=row["archetype_id"],
                    recommended_start_hour=int(row["recommended_start_hour"]),
                    actual_start_hour=int(row["actual_start_hour"]) if pd.notna(row["actual_start_hour"]) else None,
                    shift_hours=float(row["shift_hours"]),
                    incentive_amount=float(row["incentive_amount"]),
                    incentive_type=row["incentive_type"],
                    compliance_probability=float(row["compliance_probability"]),
                    satisfaction_score=int(row["satisfaction_score"]) if pd.notna(row["satisfaction_score"]) else None,
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata={}
                )

                self.shift_records.append(record)
                count += 1

                # Update compliance history
                if record.user_id not in self.compliance_history:
                    self.compliance_history[record.user_id] = []
                self.compliance_history[record.user_id].append(record.compliance_probability)

            except Exception as e:
                self.logger.warning(f"Failed to import record {row.get('record_id')}: {e}")

        self.logger.info(f"Imported {count} shift records from {input_path}")

        return count

    def get_shift_summary(
        self,
        zone_id: Optional[str] = None,
        archetype_id: Optional[str] = None,
        hours_back: int = 24
    ) -> Dict[str, any]:
        """
        Get summary of shift outcomes.

        Args:
            zone_id: Optional zone filter
        archetype_id: Optional archetype filter
            hours_back: Hours to look back

        Returns:
            Dictionary with shift summary
        """
        # Filter records
        filtered_records = self.shift_records
        if zone_id:
            filtered_records = [r for r in filtered_records if r.zone_id == zone_id]
        if archetype_id:
            filtered_records = [r for r in filtered_records if r.archetype_id == archetype_id]

        # Filter by time window
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        filtered_records = [r for r in filtered_records if r.timestamp >= cutoff_time]

        if not filtered_records:
            return {
                "status": "no_data",
                "total_shifts": 0,
                "applied_shifts": 0,
                "ignored_shifts": 0,
                "failed_shifts": 0,
                "avg_compliance": 0.0
            }

        # Calculate summary
        total_shifts = len(filtered_records)
        applied_shifts = sum(1 for r in filtered_records if r.outcome == ShiftOutcome.APPLIED)
        ignored_shifts = sum(1 for r in filtered_records if r.outcome == ShiftOutcome.IGNORED)
        failed_shifts = sum(1 for r in filtered_records if r.outcome == ShiftOutcome.FAILED)

        # Calculate average compliance
        compliance_probs = [r.compliance_probability for r in filtered_records]
        avg_compliance = np.mean(compliance_probs) if compliance_probs else 0.0

        # Calculate outcome distribution
        outcome_counts = {}
        for record in filtered_records:
            outcome = record.outcome.value
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        # Calculate incentive effectiveness
        incentive_records = [r for r in filtered_records if r.incentive_amount > 0]
        if incentive_records:
            applied_with_incentive = sum(
                1 for r in incentive_records
                if r.outcome == ShiftOutcome.APPLIED
            )
            incentive_effectiveness = (
                applied_with_incentive / len(incentive_records)
                if incentive_records else 0
            )
        else:
            incentive_effectiveness = 0.0

        return {
            "status": "available",
            "total_shifts": total_shifts,
            "applied_shifts": applied_shifts,
            "ignored_shifts": ignored_shifts,
            "failed_shifts": failed_shifts,
            "compliance_rate": avg_compliance,
            "outcome_distribution": outcome_counts,
            "incentive_effectiveness": incentive_effectiveness,
            "time_window_hours": hours_back,
            "zone_id": zone_id,
            "archetype_id": archetype_id
        }


if __name__ == "__main__":
    # Example usage
    tracker = OutcomeTracker()

    # Record some sample shifts
    tracker.record_shift(
        session_id="S001",
        user_id="U001",
        zone_id="Z01",
        archetype_id="A01",
        recommended_start_hour=18,
        actual_start_hour=20,
        shift_hours=2.0,
        incentive_amount=50.0,
        incentive_type="OFF_PEAK_SHIFT",
        compliance_probability=0.65,
        satisfaction_score=4
    )

    tracker.record_shift(
        session_id="S002",
        user_id="U001",
        zone_id="Z01",
        archetype_id="A01",
        recommended_start_hour=19,
        actual_start_hour=19,
        shift_hours=0.0,
        incentive_amount=0.0,
        incentive_type="NONE",
        compliance_probability=0.5,
        satisfaction_score=3
    )

    tracker.record_shift(
        session_id="S003",
        user_id="U002",
        zone_id="Z02",
        archetype_id="A02",
        recommended_start_hour=14,
        actual_start_hour=16,
        shift_hours=2.0,
        incentive_amount=75.0,
        incentive_type="FLEET_BONUS",
        compliance_probability=0.75,
        satisfaction_score=5
    )

    # Get zone stats
    zone_stats = tracker.get_zone_compliance_stats("Z01", hours_back=24)
    print("Zone Z01 Compliance Stats:")
    print(f"  Total shifts: {zone_stats['total_shifts']}")
    print(f"  Applied shifts: {zone_stats['applied_shifts']}")
    print(f"  Compliance rate: {zone_stats['compliance_rate']:.2%}")
    print(f"  Outcome distribution: {zone_stats['outcome_distribution']}")

    # Get global stats
    global_stats = tracker.get_global_stats()
    print("\nGlobal Stats:")
    print(f"  Total shifts: {global_stats['total_shifts']}")
    print(f"  Applied shifts: {global_stats['applied_shifts']}")
    print(f"  Compliance rate: {global_stats['compliance_rate']:.2%}")
    print(f"  Incentive effectiveness: {global_stats['incentive_effectiveness']:.2%}")
