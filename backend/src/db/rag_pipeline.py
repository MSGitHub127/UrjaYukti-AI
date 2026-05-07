"""
ChromaDB RAG Pipeline for Explainability
Production-grade implementation for storing and retrieving past planning decisions for explainability.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import hashlib

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    from sentence_transformers import SentenceTransformer
    CHROMADB_AVAILABLE = True
except ImportError as e:
    CHROMADB_AVAILABLE = False
    import sys
    print(f"ChromaDB import failed: {e}", file=sys.stderr)


@dataclass
class PlanningDecision:
    """Represents a past planning decision for RAG."""

    decision_id: str
    timestamp: datetime
    zone_id: str
    decision_type: str  # SCHEDULE, SITE, ALERT, etc.
    context: Dict[str, any]
    rationale: str
    outcome: str
    metrics: Dict[str, float]
    tags: List[str] = field(default_factory=list)


class ChromaRAGPipeline:
    """Production-grade RAG pipeline for explainability."""

    def __init__(
        self,
        collection_name: str = "planning_decisions",
        persist_directory: str = "data/chroma_db",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model

        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.client = None
        self.collection = None
        self.embedding_function = None

        # Initialize
        self._initialize()

    def _initialize(self):
        """Initialize ChromaDB and embedding model."""
        if not CHROMADB_AVAILABLE:
            self.logger.warning("ChromaDB not available. RAG pipeline will be disabled.")
            return

        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            # Initialize embedding function
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model
            )

            self.logger.info(f"ChromaDB RAG pipeline initialized: {self.collection_name}")

        except Exception as e:
            self.logger.error(f"Error initializing ChromaDB: {e}")
            self.client = None
            self.collection = None

    def add_decision(
        self,
        decision: PlanningDecision
    ) -> str:
        """
        Add a planning decision to the RAG pipeline.

        Args:
            decision: Planning decision to add

        Returns:
            Document ID
        """
        if not self.collection:
            self.logger.warning("ChromaDB not available. Decision not stored.")
            return ""

        try:
            # Create document content
            content = self._create_document_content(decision)

            # Create metadata
            metadata = {
                "zone_id": decision.zone_id,
                "decision_type": decision.decision_type,
                "timestamp": decision.timestamp.isoformat(),
                "tags": ",".join(decision.tags)
            }

            # Add to collection
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[decision.decision_id]
            )

            self.logger.info(f"Added decision {decision.decision_id} to RAG pipeline")

            return decision.decision_id

        except Exception as e:
            self.logger.error(f"Error adding decision to RAG: {e}")
            return ""

    def _create_document_content(self, decision: PlanningDecision) -> str:
        """Create document content from planning decision."""
        content = f"""
Decision ID: {decision.decision_id}
Timestamp: {decision.timestamp.isoformat()}
Zone: {decision.zone_id}
Type: {decision.decision_type}

Context:
{json.dumps(decision.context, indent=2)}

Rationale:
{decision.rationale}

Outcome:
{decision.outcome}

Metrics:
{json.dumps(decision.metrics, indent=2)}

Tags:
{", ".join(decision.tags)}
        """.strip()

        return content

    def query_decisions(
        self,
        query: str,
        zone_id: Optional[str] = None,
        decision_type: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, any]]:
        """
        Query past planning decisions.

        Args:
            query: Query text
            zone_id: Optional zone filter
            decision_type: Optional decision type filter
            n_results: Number of results to return

        Returns:
            List of matching decisions
        """
        if not self.collection:
            self.logger.warning("ChromaDB not available. Cannot query.")
            return []

        try:
            # Create query filter
            where = {}
            if zone_id:
                where["zone_id"] = zone_id
            if decision_type:
                where["decision_type"] = decision_type

            # Query collection
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["metadatas", "documents", "distances"]
            )

            # Format results
            formatted_results = []
            for i in range(len(results["ids"])):
                result = {
                    "id": results["ids"][i],
                    "document": results["documents"][i],
                    "metadata": results["metadatas"][i],
                    "distance": results["distances"][i]
                }
                formatted_results.append(result)

            self.logger.info(f"Found {len(formatted_results)} matching decisions")

            return formatted_results

        except Exception as e:
            self.logger.error(f"Error querying RAG pipeline: {e}")
            return []

    def get_similar_decisions(
        self,
        decision: PlanningDecision,
        n_similar: int = 3
    ) -> List[Dict[str, any]]:
        """
        Get similar past decisions for a given decision.

        Args:
            decision: Current planning decision
            n_similar: Number of similar decisions to return

        Returns:
            List of similar decisions
        """
        if not self.collection:
            return []

        try:
            # Create query from decision context
            query = f"{decision.decision_type} {decision.zone_id} {decision.rationale}"

            # Query for similar decisions
            similar = self.query_decisions(
                query=query,
                zone_id=decision.zone_id,
                decision_type=decision.decision_type,
                n_results=n_similar
            )

            return similar

        except Exception as e:
            self.logger.error(f"Error getting similar decisions: {e}")
            return []

    def get_decision_context(
        self,
        zone_id: str,
        decision_type: str,
        time_window_hours: int = 24
    ) -> Dict[str, any]:
        """
        Get context for a decision type in a zone.

        Args:
            zone_id: Zone ID
            decision_type: Decision type
            time_window_hours: Time window in hours

        Returns:
            Dictionary with context information
        """
        if not self.collection:
            return {"status": "unavailable", "decisions": []}

        try:
            # Query recent decisions
            query = f"{decision_type} {zone_id}"
            results = self.query_decisions(
                query=query,
                zone_id=zone_id,
                decision_type=decision_type,
                n_results=10
            )

            # Filter by time window
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            recent_results = [
                r for r in results
                if datetime.fromisoformat(r["metadata"]["timestamp"]) >= cutoff_time
            ]

            # Extract context
            context = {
                "status": "available",
                "zone_id": zone_id,
                "decision_type": decision_type,
                "time_window_hours": time_window_hours,
                "total_decisions": len(results),
                "recent_decisions": len(recent_results),
                "decisions": recent_results
            }

            # Calculate statistics
            if recent_results:
                outcomes = [r["document"].split("Outcome:")[1].strip() for r in recent_results if "Outcome:" in r["document"]]
                context["outcome_distribution"] = {
                    outcome: outcomes.count(outcome) for outcome in set(outcomes)
                }

            return context

        except Exception as e:
            self.logger.error(f"Error getting decision context: {e}")
            return {"status": "error", "error": str(e)}

    def generate_explanation(
        self,
        current_decision: PlanningDecision,
        include_similar: bool = True
    ) -> str:
        """
        Generate explanation for a decision using RAG.

        Args:
            current_decision: Current planning decision
            include_similar: Whether to include similar past decisions

        Returns:
            Explanation text
        """
        if not self.collection:
            return "RAG pipeline not available. Cannot generate explanation."

        try:
            explanation_parts = []

            # Get similar decisions
            if include_similar:
                similar = self.get_similar_decisions(current_decision, n_similar=3)

                if similar:
                    explanation_parts.append("Similar past decisions:")
                    for i, sim in enumerate(similar, 1):
                        explanation_parts.append(f"  {i}. {sim['metadata']['timestamp']} - {sim['document'][:100]}...")

            # Get context
            context = self.get_decision_context(
                current_decision.zone_id,
                current_decision.decision_type
            )

            if context["status"] == "available":
                explanation_parts.append(f"\nContext: {context['total_decisions']} similar decisions in last {context['time_window_hours']} hours.")

            # Generate explanation
            explanation = "\n".join(explanation_parts)

            return explanation

        except Exception as e:
            self.logger.error(f"Error generating explanation: {e}")
            return f"Error generating explanation: {e}"

    def delete_decision(self, decision_id: str) -> bool:
        """
        Delete a decision from the RAG pipeline.

        Args:
            decision_id: Decision ID to delete

        Returns:
            True if deleted, False otherwise
        """
        if not self.collection:
            return False

        try:
            self.collection.delete(ids=[decision_id])
            self.logger.info(f"Deleted decision {decision_id} from RAG pipeline")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting decision: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, any]:
        """
        Get statistics about the RAG collection.

        Returns:
            Dictionary with collection statistics
        """
        if not self.collection:
            return {"status": "unavailable"}

        try:
            count = self.collection.count()

            # Get data from ChromaDB dictionary
            collection_data = self.collection.get()
            metadatas = collection_data.get("metadatas") or []

            # Get distributions
            decision_types = {}
            zones = {}

            for metadata in metadatas:
                if metadata:
                    dtype = metadata.get("decision_type", "unknown")
                    decision_types[dtype] = decision_types.get(dtype, 0) + 1

                    zid = metadata.get("zone_id", "unknown")
                    zones[zid] = zones.get(zid, 0) + 1

            return {
                "status": "available",
                "collection_name": self.collection_name,
                "total_decisions": count,
                "decision_types": decision_types,
                "zones": zones,
                "persist_directory": self.persist_directory
            }

        except Exception as e:
            self.logger.error(f"Error getting collection stats: {e}")
            return {"status": "error", "error": str(e)}

    def clear_old_decisions(self, days_to_keep: int = 90) -> int:
        """
        Clear decisions older than specified days.

        Args:
            days_to_keep: Number of days to keep

        Returns:
            Number of decisions deleted
        """
        if not self.collection:
            return 0

        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)

            # Get all documents
            collection_data = self.collection.get()
            metadatas = collection_data.get("metadatas") or []
            ids = collection_data.get("ids") or []

            # Find old documents
            old_ids = []
            for i, metadata in enumerate(metadatas):
                if metadata:
                    timestamp_str = metadata.get("timestamp")
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                            if timestamp < cutoff_time:
                                old_ids.append(ids[i])
                        except Exception:
                            pass

            # Delete old documents
            if old_ids:
                self.collection.delete(ids=old_ids)
                self.logger.info(f"Deleted {len(old_ids)} old decisions")

            return len(old_ids)

        except Exception as e:
            self.logger.error(f"Error clearing old decisions: {e}")
            return 0


if __name__ == "__main__":
    # Example usage
    rag = ChromaRAGPipeline()

    if CHROMADB_AVAILABLE:
        # Add a sample decision
        sample_decision = PlanningDecision(
            decision_id="D001",
            timestamp=datetime.now(),
            zone_id="Z01",
            decision_type="SCHEDULE",
            context={
                "peak_load_kw": 450.0,
                "headroom_percent": 15.0,
                "sessions_count": 2
            },
            rationale="Shifting Whitefield load reduces transformer peak stress by 18%, aligning with BESCOM N-1 standard.",
            outcome="APPROVED",
            metrics={
                "peak_reduction_percent": 18.0,
                "compliance_probability": 0.65
            },
            tags=["peak_reduction", "whitefield", "approved"]
        )

        doc_id = rag.add_decision(sample_decision)
        print(f"Added decision with ID: {doc_id}")

        # Query decisions
        results = rag.query_decisions(
            query="peak load reduction whitefield",
            zone_id="Z01",
            n_results=3
        )

        print(f"\nFound {len(results)} matching decisions:")
        for result in results:
            print(f"  - {result['id']}: {result['document'][:80]}...")

        # Get stats
        stats = rag.get_collection_stats()
        print(f"\nCollection stats: {stats}")
    else:
        print("ChromaDB not available. Install with: pip install chromadb sentence-transformers")
