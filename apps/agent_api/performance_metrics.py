"""
Performance monitoring utilities for RAG optimization.
Tracks latency, token usage, and retrieval quality metrics.
"""
import logging
import time
from contextlib import contextmanager
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import statistics

logger = logging.getLogger(__name__)


@dataclass
class LatencyMetrics:
    """Latency metrics for a single operation."""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "in_progress"  # in_progress, success, error
    error: Optional[str] = None
    
    def complete(self, error: Optional[str] = None):
        """Mark operation as complete."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = "error" if error else "success"
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error
        }


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval operations."""
    query: str
    timestamp: str
    
    # Input parameters
    max_chunks_requested: int
    max_summaries_requested: int
    
    # Results
    chunks_retrieved: int
    summaries_retrieved: int
    chunks_after_dedup: Optional[int] = None
    chunks_after_rerank: Optional[int] = None
    
    # Query expansion
    expanded_queries: Optional[List[str]] = None
    
    # Latency
    total_duration_ms: Optional[float] = None
    search_duration_ms: Optional[float] = None
    rerank_duration_ms: Optional[float] = None
    
    # Optimizations applied
    optimizations: Dict[str, bool] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "timestamp": self.timestamp,
            "retrieval": {
                "requested": {
                    "chunks": self.max_chunks_requested,
                    "summaries": self.max_summaries_requested
                },
                "retrieved": {
                    "chunks": self.chunks_retrieved,
                    "summaries": self.summaries_retrieved
                },
                "after_dedup": self.chunks_after_dedup,
                "after_rerank": self.chunks_after_rerank
            },
            "query_expansion": {
                "enabled": bool(self.expanded_queries and len(self.expanded_queries) > 1),
                "query_count": len(self.expanded_queries) if self.expanded_queries else 1
            },
            "latency_ms": {
                "total": self.total_duration_ms,
                "search": self.search_duration_ms,
                "rerank": self.rerank_duration_ms
            },
            "optimizations": self.optimizations
        }


@dataclass
class SynthesisMetrics:
    """Metrics for synthesis operations."""
    query: str
    timestamp: str
    
    # Input
    summaries_provided: int
    chunks_provided: int
    summaries_used: int
    chunks_used: int
    
    # Output
    answer_length: int
    citations_count: int
    
    # Tokens
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_prompt_tokens: Optional[int] = None
    
    # Model
    model_used: str = "unknown"
    temperature: float = 0.2
    
    # Latency
    total_duration_ms: Optional[float] = None
    
    # Optimizations
    optimizations: Dict[str, Any] = field(default_factory=dict)
    
    # Quality indicators
    citation_quality_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "timestamp": self.timestamp,
            "context": {
                "provided": {
                    "summaries": self.summaries_provided,
                    "chunks": self.chunks_provided
                },
                "used": {
                    "summaries": self.summaries_used,
                    "chunks": self.chunks_used
                },
                "truncation_applied": self.summaries_used < self.summaries_provided or 
                                      self.chunks_used < self.chunks_provided
            },
            "output": {
                "answer_length": self.answer_length,
                "citations_count": self.citations_count,
                "citation_quality_score": self.citation_quality_score
            },
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "total": self.total_tokens,
                "estimated_prompt": self.estimated_prompt_tokens
            },
            "model": {
                "name": self.model_used,
                "temperature": self.temperature
            },
            "latency_ms": {
                "total": self.total_duration_ms
            },
            "optimizations": self.optimizations
        }


@dataclass
class RAGPipelineMetrics:
    """Complete metrics for a full RAG pipeline execution."""
    query: str
    timestamp: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    retrieval: Optional[RetrievalMetrics] = None
    synthesis: Optional[SynthesisMetrics] = None
    
    total_duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "user_id": user_id,
            "retrieval": self.retrieval.to_dict() if self.retrieval else None,
            "synthesis": self.synthesis.to_dict() if self.synthesis else None,
            "total_duration_ms": self.total_duration_ms,
            "breakdown": {
                "retrieval_percent": (self.retrieval.total_duration_ms / self.total_duration_ms * 100) 
                    if self.retrieval and self.total_duration_ms else None,
                "synthesis_percent": (self.synthesis.total_duration_ms / self.total_duration_ms * 100)
                    if self.synthesis and self.total_duration_ms else None
            }
        }


@contextmanager
def track_latency(operation: str, warning_threshold_ms: float = 5000.0):
    """
    Context manager to track operation latency.
    
    Args:
        operation: Name of the operation being tracked
        warning_threshold_ms: Threshold in ms to log a warning
    
    Yields:
        LatencyMetrics object that will be updated on exit
    
    Example:
        with track_latency("search_chunks") as metrics:
            results = search_chunks(query)
        print(f"Search took {metrics.duration_ms}ms")
    """
    metrics = LatencyMetrics(operation=operation, start_time=time.time())
    
    try:
        yield metrics
        metrics.complete()
        
        if metrics.duration_ms and metrics.duration_ms > warning_threshold_ms:
            logger.warning(
                f"⚠️ Slow operation: {operation} took {metrics.duration_ms:.2f}ms "
                f"(threshold: {warning_threshold_ms}ms)"
            )
        else:
            logger.info(f"✅ {operation} completed in {metrics.duration_ms:.2f}ms")
            
    except Exception as e:
        metrics.complete(error=str(e))
        logger.error(f"❌ {operation} failed after {metrics.duration_ms:.2f}ms: {e}")
        raise


def calculate_citation_quality_score(
    citations: List[str],
    min_required: int = 5
) -> float:
    """
    Calculate a quality score for citations.
    
    Factors:
    - Number of citations vs minimum required
    - Diversity of sources (not all from same document)
    
    Args:
        citations: List of citation strings
        min_required: Minimum number of citations expected
    
    Returns:
        Score from 0.0 to 1.0
    """
    if not citations:
        return 0.0
    
    # Factor 1: Citation count (0.5 weight)
    count_score = min(len(citations) / min_required, 1.0) * 0.5
    
    # Factor 2: Source diversity (0.5 weight)
    # Extract document titles from citations
    unique_sources = set()
    for citation in citations:
        # Parse citations like "Document Title (Page X)" or "Document Title"
        # Extract the title part before any parenthesis
        title = citation.split('(')[0].strip()
        unique_sources.add(title)
    
    # More diverse sources = better
    diversity_score = min(len(unique_sources) / max(len(citations) * 0.6, 1), 1.0) * 0.5
    
    total_score = count_score + diversity_score
    
    logger.debug(
        f"Citation quality: {total_score:.2f} "
        f"(count: {len(citations)}/{min_required}, unique sources: {len(unique_sources)})"
    )
    
    return total_score


class MetricsAggregator:
    """Aggregates metrics across multiple requests for analysis."""
    
    def __init__(self):
        self.retrieval_metrics: List[RetrievalMetrics] = []
        self.synthesis_metrics: List[SynthesisMetrics] = []
        self.pipeline_metrics: List[RAGPipelineMetrics] = []
    
    def add_retrieval(self, metrics: RetrievalMetrics):
        """Add retrieval metrics."""
        self.retrieval_metrics.append(metrics)
    
    def add_synthesis(self, metrics: SynthesisMetrics):
        """Add synthesis metrics."""
        self.synthesis_metrics.append(metrics)
    
    def add_pipeline(self, metrics: RAGPipelineMetrics):
        """Add complete pipeline metrics."""
        self.pipeline_metrics.append(metrics)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics across all collected metrics."""
        summary = {
            "total_requests": len(self.pipeline_metrics),
            "retrieval": self._summarize_retrieval(),
            "synthesis": self._summarize_synthesis(),
            "pipeline": self._summarize_pipeline()
        }
        return summary
    
    def _summarize_retrieval(self) -> Dict[str, Any]:
        """Summarize retrieval metrics."""
        if not self.retrieval_metrics:
            return {}
        
        durations = [m.total_duration_ms for m in self.retrieval_metrics if m.total_duration_ms]
        chunks = [m.chunks_retrieved for m in self.retrieval_metrics]
        summaries = [m.summaries_retrieved for m in self.retrieval_metrics]
        
        return {
            "count": len(self.retrieval_metrics),
            "avg_duration_ms": statistics.mean(durations) if durations else None,
            "median_duration_ms": statistics.median(durations) if durations else None,
            "avg_chunks": statistics.mean(chunks) if chunks else None,
            "avg_summaries": statistics.mean(summaries) if summaries else None
        }
    
    def _summarize_synthesis(self) -> Dict[str, Any]:
        """Summarize synthesis metrics."""
        if not self.synthesis_metrics:
            return {}
        
        durations = [m.total_duration_ms for m in self.synthesis_metrics if m.total_duration_ms]
        tokens = [m.total_tokens for m in self.synthesis_metrics if m.total_tokens]
        citations = [m.citations_count for m in self.synthesis_metrics]
        
        return {
            "count": len(self.synthesis_metrics),
            "avg_duration_ms": statistics.mean(durations) if durations else None,
            "median_duration_ms": statistics.median(durations) if durations else None,
            "avg_total_tokens": statistics.mean(tokens) if tokens else None,
            "avg_citations": statistics.mean(citations) if citations else None
        }
    
    def _summarize_pipeline(self) -> Dict[str, Any]:
        """Summarize complete pipeline metrics."""
        if not self.pipeline_metrics:
            return {}
        
        durations = [m.total_duration_ms for m in self.pipeline_metrics if m.total_duration_ms]
        
        return {
            "count": len(self.pipeline_metrics),
            "avg_duration_ms": statistics.mean(durations) if durations else None,
            "median_duration_ms": statistics.median(durations) if durations else None,
            "p95_duration_ms": statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else None
        }
    
    def reset(self):
        """Clear all collected metrics."""
        self.retrieval_metrics.clear()
        self.synthesis_metrics.clear()
        self.pipeline_metrics.clear()


# Global aggregator instance
_aggregator = MetricsAggregator()


def get_aggregator() -> MetricsAggregator:
    """Get global metrics aggregator."""
    return _aggregator
