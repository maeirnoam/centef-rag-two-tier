"""
Configuration for RAG optimization features.
Centralized settings for retriever and synthesizer optimizations.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RetrieverOptimizationConfig:
    """Configuration for retriever optimizations."""
    
    # Query expansion
    enable_query_expansion: bool = True
    query_expansion_model: str = "gemini-2.0-flash-exp"
    
    # Result reranking
    enable_reranking: bool = True
    reranking_model: str = "gemini-2.0-flash-exp"
    rerank_top_k: Optional[int] = None  # None = no limit after reranking
    
    # Deduplication
    enable_deduplication: bool = True
    deduplication_threshold: float = 0.85
    
    # Adaptive result limits
    enable_adaptive_limits: bool = False  # Disabled by default to maintain consistent behavior
    
    # Search parameters
    default_max_chunks: int = 10
    default_max_summaries: int = 5
    
    # Multi-query fusion
    reciprocal_rank_k: int = 60  # Constant for RRF formula
    
    @classmethod
    def from_env(cls) -> 'RetrieverOptimizationConfig':
        """Create configuration from environment variables."""
        return cls(
            enable_query_expansion=os.getenv("RETRIEVER_ENABLE_QUERY_EXPANSION", "true").lower() == "true",
            query_expansion_model=os.getenv("QUERY_EXPANSION_MODEL", "gemini-2.0-flash-exp"),
            enable_reranking=os.getenv("RETRIEVER_ENABLE_RERANKING", "true").lower() == "true",
            reranking_model=os.getenv("RERANKING_MODEL", "gemini-2.0-flash-exp"),
            rerank_top_k=int(os.getenv("RETRIEVER_RERANK_TOP_K")) if os.getenv("RETRIEVER_RERANK_TOP_K") else None,
            enable_deduplication=os.getenv("RETRIEVER_ENABLE_DEDUPLICATION", "true").lower() == "true",
            deduplication_threshold=float(os.getenv("RETRIEVER_DEDUP_THRESHOLD", "0.85")),
            enable_adaptive_limits=os.getenv("RETRIEVER_ENABLE_ADAPTIVE_LIMITS", "false").lower() == "true",
            default_max_chunks=int(os.getenv("RETRIEVER_DEFAULT_MAX_CHUNKS", "10")),
            default_max_summaries=int(os.getenv("RETRIEVER_DEFAULT_MAX_SUMMARIES", "5")),
            reciprocal_rank_k=int(os.getenv("RETRIEVER_RRF_K", "60"))
        )


@dataclass
class SynthesizerOptimizationConfig:
    """Configuration for synthesizer optimizations."""
    
    # Context window management
    enable_context_truncation: bool = True
    max_context_tokens: int = 24000  # Leave room for output
    
    # Temperature
    enable_adaptive_temperature: bool = True
    default_temperature: float = 0.2
    factual_temperature: float = 0.15
    analytical_temperature: float = 0.35
    creative_temperature: float = 0.5
    
    # Output
    max_output_tokens: int = 2048
    
    # Citation quality
    prioritize_citations: bool = True
    min_citations_required: int = 5
    
    # Model selection
    primary_model: str = "gemini-2.0-flash-exp"
    fallback_models: list = None  # Will use default if None
    
    # Token estimation
    chars_per_token: int = 4  # Heuristic for token estimation
    
    @classmethod
    def from_env(cls) -> 'SynthesizerOptimizationConfig':
        """Create configuration from environment variables."""
        return cls(
            enable_context_truncation=os.getenv("SYNTHESIZER_ENABLE_CONTEXT_TRUNCATION", "true").lower() == "true",
            max_context_tokens=int(os.getenv("SYNTHESIZER_MAX_CONTEXT_TOKENS", "24000")),
            enable_adaptive_temperature=os.getenv("SYNTHESIZER_ENABLE_ADAPTIVE_TEMP", "true").lower() == "true",
            default_temperature=float(os.getenv("SYNTHESIZER_DEFAULT_TEMP", "0.2")),
            factual_temperature=float(os.getenv("SYNTHESIZER_FACTUAL_TEMP", "0.15")),
            analytical_temperature=float(os.getenv("SYNTHESIZER_ANALYTICAL_TEMP", "0.35")),
            creative_temperature=float(os.getenv("SYNTHESIZER_CREATIVE_TEMP", "0.5")),
            max_output_tokens=int(os.getenv("SYNTHESIZER_MAX_OUTPUT_TOKENS", "2048")),
            prioritize_citations=os.getenv("SYNTHESIZER_PRIORITIZE_CITATIONS", "true").lower() == "true",
            min_citations_required=int(os.getenv("SYNTHESIZER_MIN_CITATIONS", "5")),
            primary_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
            chars_per_token=int(os.getenv("SYNTHESIZER_CHARS_PER_TOKEN", "4"))
        )


@dataclass
class PerformanceMonitoringConfig:
    """Configuration for performance monitoring and metrics."""
    
    # Latency tracking
    enable_latency_tracking: bool = True
    latency_warning_threshold_ms: float = 5000.0  # Warn if operations take > 5s
    
    # Quality metrics
    enable_quality_metrics: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_token_usage: bool = True
    log_retrieval_stats: bool = True
    
    @classmethod
    def from_env(cls) -> 'PerformanceMonitoringConfig':
        """Create configuration from environment variables."""
        return cls(
            enable_latency_tracking=os.getenv("PERF_ENABLE_LATENCY_TRACKING", "true").lower() == "true",
            latency_warning_threshold_ms=float(os.getenv("PERF_LATENCY_WARNING_MS", "5000.0")),
            enable_quality_metrics=os.getenv("PERF_ENABLE_QUALITY_METRICS", "true").lower() == "true",
            log_level=os.getenv("PERF_LOG_LEVEL", "INFO"),
            log_token_usage=os.getenv("PERF_LOG_TOKEN_USAGE", "true").lower() == "true",
            log_retrieval_stats=os.getenv("PERF_LOG_RETRIEVAL_STATS", "true").lower() == "true"
        )


@dataclass
class RAGOptimizationConfig:
    """Complete RAG optimization configuration."""
    
    retriever: RetrieverOptimizationConfig
    synthesizer: SynthesizerOptimizationConfig
    performance: PerformanceMonitoringConfig
    
    @classmethod
    def from_env(cls) -> 'RAGOptimizationConfig':
        """Create full configuration from environment variables."""
        return cls(
            retriever=RetrieverOptimizationConfig.from_env(),
            synthesizer=SynthesizerOptimizationConfig.from_env(),
            performance=PerformanceMonitoringConfig.from_env()
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "retriever": {
                "query_expansion": self.retriever.enable_query_expansion,
                "reranking": self.retriever.enable_reranking,
                "deduplication": self.retriever.enable_deduplication,
                "adaptive_limits": self.retriever.enable_adaptive_limits,
                "max_chunks": self.retriever.default_max_chunks,
                "max_summaries": self.retriever.default_max_summaries
            },
            "synthesizer": {
                "context_truncation": self.synthesizer.enable_context_truncation,
                "adaptive_temperature": self.synthesizer.enable_adaptive_temperature,
                "max_context_tokens": self.synthesizer.max_context_tokens,
                "max_output_tokens": self.synthesizer.max_output_tokens,
                "prioritize_citations": self.synthesizer.prioritize_citations
            },
            "performance": {
                "latency_tracking": self.performance.enable_latency_tracking,
                "quality_metrics": self.performance.enable_quality_metrics
            }
        }


# Global configuration instance
_config: Optional[RAGOptimizationConfig] = None


def get_config() -> RAGOptimizationConfig:
    """Get or create global configuration instance."""
    global _config
    if _config is None:
        _config = RAGOptimizationConfig.from_env()
    return _config


def reload_config() -> RAGOptimizationConfig:
    """Reload configuration from environment."""
    global _config
    _config = RAGOptimizationConfig.from_env()
    return _config
