"""
Retraining Pipeline Module
Production-grade implementation for human-in-the-loop model retraining.
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import pandas as pd
import numpy as np

from .detector import DriftDetector, RetrainingTrigger, DriftSeverity


class RetrainingStatus(Enum):
    """Status of retraining process."""

    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RetrainingJob:
    """Retraining job configuration."""

    job_id: str
    model_name: str
    zone_id: str
    trigger: RetrainingTrigger
    status: RetrainingStatus
    created_at: datetime
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics: Dict = field(default_factory=dict)
    error: Optional[str] = None
    new_model_path: Optional[str] = None


class RetrainingPipeline:
    """Production-grade retraining pipeline with human-in-the-loop."""

    def __init__(
        self,
        drift_detector: DriftDetector,
        model_dir: str = "data/models",
        auto_approve_threshold: int = 1,  # Only auto-approve priority 1 (low)
        require_validation: bool = True
    ):
        self.drift_detector = drift_detector
        self.model_dir = Path(model_dir)
        self.auto_approve_threshold = auto_approve_threshold
        self.require_validation = require_validation

        self.logger = logging.getLogger(__name__)

        # Retraining jobs
        self.jobs: Dict[str, RetrainingJob] = {}

        # Approval queue
        self.approval_queue: List[str] = []

        # Training callbacks
        self.training_callbacks: List[Callable] = []

        # Create directories
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def check_and_create_triggers(self) -> List[RetrainingTrigger]:
        """
        Check for drift and create retraining triggers if needed.

        Returns:
            List of new triggers created
        """
        # Get pending triggers from drift detector
        triggers = self.drift_detector.get_retraining_triggers(min_priority=2)

        new_triggers = []
        for trigger in triggers:
            # Check if job already exists for this trigger
            existing = any(
                job.trigger.trigger_id == trigger.trigger_id
                for job in self.jobs.values()
            )

            if not existing:
                # Create retraining job
                job_id = f"JOB_{datetime.now().strftime('%Y%m%d%H%M%S')}_{trigger.model_name}"

                job = RetrainingJob(
                    job_id=job_id,
                    model_name=trigger.model_name,
                    zone_id=trigger.zone_id,
                    trigger=trigger,
                    status=RetrainingStatus.PENDING,
                    created_at=datetime.now()
                )

                self.jobs[job_id] = job

                # Add to approval queue if needed
                if trigger.priority > self.auto_approve_threshold:
                    self.approval_queue.append(job_id)

                new_triggers.append(trigger)

        return new_triggers

    def approve_job(
        self,
        job_id: str,
        approved_by: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Approve a retraining job.

        Args:
            job_id: Job ID to approve
            approved_by: Person approving
            notes: Optional approval notes

        Returns:
            True if approved, False otherwise
        """
        if job_id not in self.jobs:
            self.logger.error(f"Job {job_id} not found")
            return False

        job = self.jobs[job_id]

        if job.status != RetrainingStatus.PENDING:
            self.logger.warning(f"Job {job_id} is not pending (status: {job.status})")
            return False

        # Update job
        job.status = RetrainingStatus.APPROVED
        job.approved_by = approved_by
        job.approved_at = datetime.now()

        if notes:
            job.metadata = job.metadata or {}
            job.metadata["approval_notes"] = notes

        # Remove from approval queue
        if job_id in self.approval_queue:
            self.approval_queue.remove(job_id)

        self.logger.info(f"Job {job_id} approved by {approved_by}")

        return True

    def reject_job(
        self,
        job_id: str,
        rejected_by: str,
        reason: str
    ) -> bool:
        """
        Reject a retraining job.

        Args:
            job_id: Job ID to reject
            rejected_by: Person rejecting
            reason: Reason for rejection

        Returns:
            True if rejected, False otherwise
        """
        if job_id not in self.jobs:
            self.logger.error(f"Job {job_id} not found")
            return False

        job = self.jobs[job_id]

        if job.status != RetrainingStatus.PENDING:
            self.logger.warning(f"Job {job_id} is not pending (status: {job.status})")
            return False

        # Update job
        job.status = RetrainingStatus.CANCELLED
        job.error = f"Rejected by {rejected_by}: {reason}"

        # Remove from approval queue
        if job_id in self.approval_queue:
            self.approval_queue.remove(job_id)

        self.logger.info(f"Job {job_id} rejected by {rejected_by}: {reason}")

        return True

    def start_job(self, job_id: str) -> bool:
        """
        Start a retraining job.

        Args:
            job_id: Job ID to start

        Returns:
            True if started, False otherwise
        """
        if job_id not in self.jobs:
            self.logger.error(f"Job {job_id} not found")
            return False

        job = self.jobs[job_id]

        if job.status != RetrainingStatus.APPROVED:
            self.logger.warning(f"Job {job_id} is not approved (status: {job.status})")
            return False

        # Update job
        job.status = RetrainingStatus.IN_PROGRESS
        job.started_at = datetime.now()

        self.logger.info(f"Job {job_id} started")

        # In production, this would trigger actual training
        # For now, we simulate completion
        self._simulate_training(job)

        return True

    def _simulate_training(self, job: RetrainingJob) -> None:
        """Simulate training process (placeholder for actual training)."""
        # Simulate training time
        import time
        time.sleep(1)

        # Update job with simulated results
        job.status = RetrainingStatus.COMPLETED
        job.completed_at = datetime.now()
        job.metrics = {
            "train_loss": 0.0234,
            "val_loss": 0.0289,
            "epochs": 10,
            "training_time_seconds": 60.0
        }
        job.new_model_path = str(self.model_dir / f"{job.model_name}_{job.job_id}.pt")

        self.logger.info(f"Job {job.job_id} completed")

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Get status of a retraining job.

        Args:
            job_id: Job ID

        Returns:
            Dictionary with job status
        """
        if job_id not in self.jobs:
            return None

        job = self.jobs[job_id]

        return {
            "job_id": job.job_id,
            "model_name": job.model_name,
            "zone_id": job.zone_id,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "approved_by": job.approved_by,
            "approved_at": job.approved_at.isoformat() if job.approved_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "metrics": job.metrics,
            "error": job.error,
            "new_model_path": job.new_model_path,
            "trigger": {
                "trigger_id": job.trigger.trigger_id,
                "trigger_type": job.trigger.trigger_type,
                "severity": job.trigger.severity.value,
                "reason": job.trigger.reason
            }
        }

    def get_approval_queue(self) -> List[Dict]:
        """
        Get jobs awaiting approval.

        Returns:
            List of jobs awaiting approval
        """
        queue = []
        for job_id in self.approval_queue:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                queue.append({
                    "job_id": job.job_id,
                    "model_name": job.model_name,
                    "zone_id": job.zone_id,
                    "priority": job.trigger.priority,
                    "severity": job.trigger.severity.value,
                    "reason": job.trigger.reason,
                    "created_at": job.created_at.isoformat()
                })

        # Sort by priority (descending)
        queue.sort(key=lambda x: x["priority"], reverse=True)

        return queue

    def get_pipeline_summary(self) -> Dict[str, any]:
        """
        Get summary of retraining pipeline.

        Returns:
            Dictionary with pipeline summary
        """
        total_jobs = len(self.jobs)
        status_counts = {}
        for job in self.jobs.values():
            status = job.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_jobs": total_jobs,
            "status_distribution": status_counts,
            "approval_queue_size": len(self.approval_queue),
            "auto_approve_threshold": self.auto_approve_threshold,
            "require_validation": self.require_validation
        }

    def export_job_report(self, job_id: str, output_path: str) -> bool:
        """
        Export job report to JSON file.

        Args:
            job_id: Job ID
            output_path: Output file path

        Returns:
            True if exported, False otherwise
        """
        status = self.get_job_status(job_id)
        if not status:
            return False

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(status, f, indent=2, default=str)

        self.logger.info(f"Job report exported to {output_path}")

        return True


if __name__ == "__main__":
    # Example usage
    from backend.src.retraining.detector import DriftDetector

    # Create drift detector
    detector = DriftDetector()

    # Create sample reference data
    np.random.seed(42)
    reference_data = pd.DataFrame({
        "hour": np.arange(24),
        "demand_kw": 100 + 50 * np.sin(np.arange(24) * 2 * np.pi / 24) + np.random.normal(0, 10, 24),
        "prediction": 100 + 50 * np.sin(np.arange(24) * 2 * np.pi / 24)
    })

    detector.set_reference_data(
        reference_data,
        target_col="demand_kw",
        prediction_col="prediction"
    )

    # Create current data with drift
    current_data = pd.DataFrame({
        "hour": np.arange(24),
        "demand_kw": 150 + 50 * np.sin(np.arange(24) * 2 * np.pi / 24) + np.random.normal(0, 10, 24),
        "prediction": 100 + 50 * np.sin(np.arange(24) * 2 * np.pi / 24)
    })

    # Detect drift
    detector.detect_drift(current_data, model_name="TFT", zone_id="Z01")

    # Create retraining pipeline
    pipeline = RetrainingPipeline(detector)

    # Check for triggers
    triggers = pipeline.check_and_create_triggers()
    print(f"Created {len(triggers)} retraining triggers")

    # Get approval queue
    queue = pipeline.get_approval_queue()
    print(f"\nApproval Queue ({len(queue)} jobs):")
    for job in queue:
        print(f"  {job['job_id']}: {job['severity']} - {job['reason']}")

    # Approve a job
    if queue:
        job_id = queue[0]["job_id"]
        pipeline.approve_job(job_id, approved_by="admin", notes="Approved for testing")

        # Start the job
        pipeline.start_job(job_id)

        # Get job status
        status = pipeline.get_job_status(job_id)
        print(f"\nJob Status: {status}")

    # Get pipeline summary
    summary = pipeline.get_pipeline_summary()
    print(f"\nPipeline Summary: {summary}")
