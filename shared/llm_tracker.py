"""
Centralized LLM Call Tracking System for CENTEF RAG Pipeline.

This module provides comprehensive tracking of all LLM and AI API calls across the pipeline,
logging to a master JSONL file for usage analysis, billing, and monitoring.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Literal
from contextlib import contextmanager
from threading import Lock
from dataclasses import dataclass, asdict
import time

# Setup logging
logger = logging.getLogger(__name__)

# File lock for thread-safe JSONL writing
_file_lock = Lock()

# Master log file path
MASTER_LOG_DIR = os.getenv("LLM_TRACKING_DIR", "./logs/llm_tracking")
MASTER_LOG_FILE = os.getenv("LLM_TRACKING_FILE", "master_llm_calls.jsonl")


@dataclass
class LLMCallRecord:
    """
    Comprehensive record of an LLM or AI API call.

    Fields:
        id: Unique identifier for this call
        timestamp: ISO 8601 timestamp of the call
        source_function: Name of the function/module that made the call
        api_provider: Provider (gemini, google_speech, google_translate, google_vision, vertex_search)
        api_type: Type of API (generative, speech_to_text, translation, ocr, search, embedding)
        model: Specific model used (e.g., gemini-2.0-flash-exp, gemini-1.5-pro)
        operation: Specific operation (e.g., chat_answer, summarization, transcription)

        # Token/Usage tracking
        input_tokens: Number of input tokens (or equivalent units)
        output_tokens: Number of output tokens (or equivalent units)
        total_tokens: Total tokens used

        # Performance tracking
        latency_ms: Latency in milliseconds
        status: Call status (success, error, timeout)
        error_message: Error details if applicable

        # Context tracking
        user_id: User ID if applicable
        session_id: Chat session ID if applicable
        source_id: Document/source ID being processed

        # Additional metadata
        temperature: Temperature parameter if applicable
        max_tokens: Max output tokens if applicable
        additional_params: Any other relevant parameters as JSON
        cost_estimate: Estimated cost in USD (optional)
    """
    id: str
    timestamp: str
    source_function: str
    api_provider: str
    api_type: str
    model: str
    operation: str

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    latency_ms: float = 0.0
    status: str = "success"
    error_message: Optional[str] = None

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source_id: Optional[str] = None

    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    additional_params: Optional[Dict[str, Any]] = None
    cost_estimate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


class LLMTracker:
    """
    Centralized tracker for all LLM and AI API calls.

    Usage:
        # Basic usage
        tracker = LLMTracker()

        # Track a call
        with tracker.track_call(
            source_function="synthesize_answer",
            api_provider="gemini",
            api_type="generative",
            model="gemini-2.0-flash-exp",
            operation="chat_answer",
            user_id="user123",
            session_id="session456"
        ) as call:
            # Make your LLM call
            response = model.generate_content(prompt)

            # Update token counts
            call.update_tokens(
                input_tokens=response.usage_metadata.prompt_token_count,
                output_tokens=response.usage_metadata.candidates_token_count
            )
    """

    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize the LLM tracker.

        Args:
            log_file: Optional custom log file path. Defaults to MASTER_LOG_FILE.
        """
        self.log_dir = Path(MASTER_LOG_DIR)
        self.log_file = Path(log_file) if log_file else self.log_dir / MASTER_LOG_FILE

        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"LLM Tracker initialized. Logging to: {self.log_file}")

    def _write_record(self, record: LLMCallRecord) -> None:
        """
        Write a record to the JSONL file (thread-safe).

        Args:
            record: LLMCallRecord to write
        """
        try:
            with _file_lock:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    json.dump(record.to_dict(), f, ensure_ascii=False)
                    f.write('\n')
        except Exception as e:
            logger.error(f"Failed to write LLM tracking record: {e}", exc_info=True)

    @contextmanager
    def track_call(
        self,
        source_function: str,
        api_provider: str,
        api_type: str,
        model: str,
        operation: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracking an LLM call.

        Usage:
            with tracker.track_call(...) as call:
                # Make API call
                response = api_call()
                # Update tokens
                call.update_tokens(input_tokens=100, output_tokens=200)

        Args:
            source_function: Name of calling function
            api_provider: API provider name
            api_type: Type of API call
            model: Model identifier
            operation: Specific operation being performed
            user_id: Optional user ID
            session_id: Optional session ID
            source_id: Optional source/document ID
            temperature: Optional temperature parameter
            max_tokens: Optional max tokens parameter
            additional_params: Optional dict of additional parameters

        Yields:
            CallTracker: Object for updating call details during execution
        """
        call_id = str(uuid.uuid4())
        start_time = time.time()

        record = LLMCallRecord(
            id=call_id,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            source_function=source_function,
            api_provider=api_provider,
            api_type=api_type,
            model=model,
            operation=operation,
            user_id=user_id,
            session_id=session_id,
            source_id=source_id,
            temperature=temperature,
            max_tokens=max_tokens,
            additional_params=additional_params,
            status="in_progress"
        )

        # Create call tracker helper
        call_tracker = CallTracker(record)

        try:
            yield call_tracker
            record.status = "success"
        except Exception as e:
            record.status = "error"
            record.error_message = str(e)
            logger.error(f"LLM call failed: {e}", exc_info=True)
            raise
        finally:
            # Calculate latency
            end_time = time.time()
            record.latency_ms = (end_time - start_time) * 1000

            # Write the record
            self._write_record(record)

            logger.debug(
                f"LLM call tracked: {operation} via {api_provider}/{model} "
                f"({record.total_tokens} tokens, {record.latency_ms:.2f}ms)"
            )

    def log_call(
        self,
        source_function: str,
        api_provider: str,
        api_type: str,
        model: str,
        operation: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
        status: str = "success",
        error_message: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        additional_params: Optional[Dict[str, Any]] = None,
        cost_estimate: Optional[float] = None
    ) -> str:
        """
        Directly log an LLM call (without context manager).

        Use this when you can't use the context manager pattern.

        Args:
            source_function: Name of calling function
            api_provider: API provider name
            api_type: Type of API call
            model: Model identifier
            operation: Specific operation being performed
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency_ms: Latency in milliseconds
            status: Call status
            error_message: Error message if failed
            user_id: Optional user ID
            session_id: Optional session ID
            source_id: Optional source/document ID
            temperature: Optional temperature parameter
            max_tokens: Optional max tokens parameter
            additional_params: Optional dict of additional parameters
            cost_estimate: Optional cost estimate

        Returns:
            str: Call ID
        """
        call_id = str(uuid.uuid4())

        record = LLMCallRecord(
            id=call_id,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            source_function=source_function,
            api_provider=api_provider,
            api_type=api_type,
            model=model,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            user_id=user_id,
            session_id=session_id,
            source_id=source_id,
            temperature=temperature,
            max_tokens=max_tokens,
            additional_params=additional_params,
            cost_estimate=cost_estimate
        )

        self._write_record(record)

        logger.debug(
            f"LLM call logged: {operation} via {api_provider}/{model} "
            f"({record.total_tokens} tokens, {latency_ms:.2f}ms)"
        )

        return call_id


class CallTracker:
    """Helper class for updating call details within context manager."""

    def __init__(self, record: LLMCallRecord):
        self.record = record

    def update_tokens(self, input_tokens: int = 0, output_tokens: int = 0, total_tokens: Optional[int] = None):
        """Update token counts for this call."""
        self.record.input_tokens = input_tokens
        self.record.output_tokens = output_tokens
        self.record.total_tokens = total_tokens if total_tokens is not None else (input_tokens + output_tokens)

    def set_error(self, error_message: str):
        """Set error status for this call."""
        self.record.status = "error"
        self.record.error_message = error_message

    def set_cost_estimate(self, cost: float):
        """Set cost estimate for this call."""
        self.record.cost_estimate = cost


# Global singleton instance
_global_tracker: Optional[LLMTracker] = None


def get_tracker() -> LLMTracker:
    """
    Get the global LLM tracker instance (singleton pattern).

    Returns:
        LLMTracker: Global tracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = LLMTracker()
    return _global_tracker


# Convenience function for direct usage
def track_llm_call(
    source_function: str,
    api_provider: str,
    api_type: str,
    model: str,
    operation: str,
    **kwargs
):
    """
    Convenience function to track an LLM call using the global tracker.

    Usage:
        with track_llm_call(
            source_function="synthesize_answer",
            api_provider="gemini",
            api_type="generative",
            model="gemini-2.0-flash-exp",
            operation="chat_answer",
            user_id="user123"
        ) as call:
            response = model.generate_content(prompt)
            call.update_tokens(input_tokens=100, output_tokens=200)
    """
    return get_tracker().track_call(
        source_function=source_function,
        api_provider=api_provider,
        api_type=api_type,
        model=model,
        operation=operation,
        **kwargs
    )
