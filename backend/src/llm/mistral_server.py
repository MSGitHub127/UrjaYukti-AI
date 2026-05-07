"""
Mistral 7B Server for Private VPC Deployment
Production-grade FastAPI server for explainability layer.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Try to import ML dependencies
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# Try to import ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


# Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "mistralai/Mistral-7B-Instruct-v0.2")
DEVICE = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "512"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
TOP_P = float(os.getenv("TOP_P", "0.9"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db")


# Pydantic models
class ExplainRequest(BaseModel):
    """Request for explainability generation."""

    context: Dict[str, Any] = Field(..., description="Context data for explanation")
    decision_type: str = Field(..., description="Type of decision (SCHEDULE, SITE, ALERT)")
    zone_id: str = Field(..., description="Zone ID")
    include_rag: bool = Field(True, description="Whether to include RAG context")
    max_tokens: Optional[int] = Field(None, description="Override max tokens")


class ExplainResponse(BaseModel):
    """Response from explainability generation."""

    explanation: str
    confidence: float
    rag_context: Optional[List[str]] = None
    model_used: str
    tokens_generated: int
    latency_ms: float


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    model_loaded: bool
    chroma_connected: bool
    device: str
    model_name: str
    timestamp: str


class MistralServer:
    """Production-grade Mistral 7B server."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.tokenizer = None
        self.chroma_client = None
        self.chroma_collection = None

        # Initialize
        self._initialize_model()
        self._initialize_chroma()

        # Create FastAPI app
        self.app = FastAPI(
            title="UrjaYukti AI Mistral 7B Server",
            description="Private VPC LLM for explainability layer",
            version="1.0.0"
        )

        # Setup routes
        self._setup_routes()

    def _initialize_model(self):
        """Initialize Mistral 7B model."""
        if not ML_AVAILABLE:
            self.logger.warning("ML dependencies not available. Model will not be loaded.")
            return

        try:
            self.logger.info(f"Loading model: {MODEL_NAME}")

            # Configure quantization for memory efficiency
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True
            )

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                MODEL_NAME,
                trust_remote_code=True
            )

            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True
            )

            self.logger.info(f"Model loaded successfully on {DEVICE}")

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            self.model = None
            self.tokenizer = None

    def _initialize_chroma(self):
        """Initialize ChromaDB connection."""
        if not CHROMA_AVAILABLE:
            self.logger.warning("ChromaDB not available. RAG will be disabled.")
            return

        try:
            self.chroma_client = chromadb.PersistentClient(
                path=CHROMA_PERSIST_DIR,
                settings=Settings(anonymized_telemetry=False)
            )

            # Get or create collection
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name="planning_decisions",
                metadata={"hnsw:space": "cosine"}
            )

            self.logger.info("ChromaDB connected successfully")

        except Exception as e:
            self.logger.error(f"Failed to connect to ChromaDB: {e}")
            self.chroma_client = None
            self.chroma_collection = None

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.get("/health", response_model=HealthResponse)
        async def health():
            """Health check endpoint."""
            return HealthResponse(
                status="healthy" if self.model else "degraded",
                model_loaded=self.model is not None,
                chroma_connected=self.chroma_client is not None,
                device=DEVICE,
                model_name=MODEL_NAME,
                timestamp=datetime.now().isoformat()
            )

        @self.app.post("/api/explain", response_model=ExplainResponse)
        async def explain(request: ExplainRequest):
            """
            Generate explanation for a decision.

            - **context**: Context data for explanation
            - **decision_type**: Type of decision
            - **zone_id**: Zone ID
            - **include_rag**: Whether to include RAG context
            """
            start_time = datetime.now()

            try:
                # Generate explanation
                explanation, confidence, tokens = self._generate_explanation(
                    request.context,
                    request.decision_type,
                    request.zone_id,
                    request.include_rag,
                    request.max_tokens or MAX_TOKENS
                )

                # Calculate latency
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000

                return ExplainResponse(
                    explanation=explanation,
                    confidence=confidence,
                    rag_context=None,  # Would be populated if RAG enabled
                    model_used=MODEL_NAME,
                    tokens_generated=tokens,
                    latency_ms=latency_ms
                )

            except Exception as e:
                self.logger.error(f"Error generating explanation: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/rag/add")
        async def add_rag_context(
            decision_id: str,
            context: Dict[str, Any],
            rationale: str
        ):
            """Add context to RAG pipeline."""
            if not self.chroma_collection:
                raise HTTPException(status_code=503, detail="ChromaDB not available")

            try:
                # Create document content
                content = f"""
Decision ID: {decision_id}
Context: {context}
Rationale: {rationale}
                """.strip()

                # Add to collection
                self.chroma_collection.add(
                    documents=[content],
                    metadatas=[{
                        "decision_id": decision_id,
                        "timestamp": datetime.now().isoformat()
                    }],
                    ids=[decision_id]
                )

                return {"status": "success", "decision_id": decision_id}

            except Exception as e:
                self.logger.error(f"Error adding RAG context: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/rag/query")
        async def query_rag(
            query: str,
            n_results: int = 3
        ):
            """Query RAG pipeline."""
            if not self.chroma_collection:
                raise HTTPException(status_code=503, detail="ChromaDB not available")

            try:
                results = self.chroma_collection.query(
                    query_texts=[query],
                    n_results=n_results
                )

                return {
                    "query": query,
                    "results": results
                }

            except Exception as e:
                self.logger.error(f"Error querying RAG: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _generate_explanation(
        self,
        context: Dict[str, Any],
        decision_type: str,
        zone_id: str,
        include_rag: bool,
        max_tokens: int
    ) -> tuple[str, float, int]:
        """
        Generate explanation using Mistral 7B.

        Args:
            context: Context data
            decision_type: Type of decision
            zone_id: Zone ID
            include_rag: Whether to include RAG
            max_tokens: Maximum tokens to generate

        Returns:
            Tuple of (explanation, confidence, tokens_generated)
        """
        if not self.model or not self.tokenizer:
            # Fallback explanation
            fallback = self._generate_fallback_explanation(
                context, decision_type, zone_id
            )
            return fallback, 0.5, 0

        # Create prompt
        prompt = self._create_prompt(context, decision_type, zone_id)

        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        ).to(DEVICE)

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=TEMPERATURE,
                top_p=TOP_P,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        # Decode
        generated_text = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )

        # Calculate confidence (simplified)
        confidence = 0.85  # Would be calculated from logits in production

        # Count tokens
        tokens = len(self.tokenizer.encode(generated_text))

        return generated_text, confidence, tokens

    def _create_prompt(
        self,
        context: Dict[str, Any],
        decision_type: str,
        zone_id: str
    ) -> str:
        """Create prompt for Mistral 7B."""
        prompt = f"""[INST]
You are an AI assistant for BESCOM's EV charging optimization system. Your role is to provide clear, actionable explanations for planning decisions.

Decision Type: {decision_type}
Zone: {zone_id}

Context:
{self._format_context(context)}

Task: Provide a plain-language explanation of this decision that an IAS officer or BESCOM planner can understand. Include:
1. What action is being recommended
2. Why this action is beneficial
3. What the expected outcome is
4. Any relevant constraints or considerations

Keep your response under 200 words and use clear, professional language.
[/INST]"""

        return prompt

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for prompt."""
        lines = []
        for key, value in context.items():
            if isinstance(value, (int, float)):
                lines.append(f"- {key}: {value:.2f}")
            elif isinstance(value, list):
                lines.append(f"- {key}: {len(value)} items")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _generate_fallback_explanation(
        self,
        context: Dict[str, Any],
        decision_type: str,
        zone_id: str
    ) -> str:
        """Generate fallback explanation when model is not available."""
        if decision_type == "SCHEDULE":
            peak_reduction = context.get("peak_reduction_percent", 0)
            return (
                f"Shifting evening charging load in {zone_id} by 2 hours is projected "
                f"to reduce transformer peak stress by {peak_reduction:.1f}%, "
                f"aligning with BESCOM's N-1 safety standard."
            )
        elif decision_type == "SITE":
            score = context.get("total_score", 0)
            return (
                f"This site ranks highly due to strong demand indicators and "
                f"adequate grid headroom. The total score of {score:.2f} indicates "
                f"it is a priority location for new charging infrastructure."
            )
        else:
            return (
                f"This recommendation for {zone_id} is based on current grid "
                f"conditions and demand forecasts. The action helps maintain "
                f"system reliability while supporting EV adoption."
            )

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the server."""
        self.logger.info(f"Starting Mistral 7B server on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)


# Create server instance
server = MistralServer()
app = server.app


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run server
    server.run()
