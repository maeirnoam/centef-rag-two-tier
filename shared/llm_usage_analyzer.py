"""
LLM Usage Analysis Utilities for CENTEF RAG Pipeline.

This module provides utilities to analyze LLM usage from the master tracking log,
calculate token usage by user, session, and source, and generate reports.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UsageStats:
    """Statistics for LLM usage."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    total_cost_estimate: float = 0.0

    # Breakdown by model
    by_model: Dict[str, Dict[str, int]] = None

    # Breakdown by operation
    by_operation: Dict[str, Dict[str, int]] = None

    def __post_init__(self):
        if self.by_model is None:
            self.by_model = {}
        if self.by_operation is None:
            self.by_operation = {}


class LLMUsageAnalyzer:
    """
    Analyzer for LLM usage from tracking logs.

    Usage:
        analyzer = LLMUsageAnalyzer()

        # Get user usage
        user_stats = analyzer.get_user_usage("user123")

        # Get session usage
        session_stats = analyzer.get_session_usage("session456")

        # Get source processing usage
        source_stats = analyzer.get_source_usage("source789")

        # Get time-based reports
        daily_stats = analyzer.get_usage_by_time_period(days=7)
    """

    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize the usage analyzer.

        Args:
            log_file: Optional path to the tracking log file
        """
        from shared.llm_tracker import MASTER_LOG_DIR, MASTER_LOG_FILE

        self.log_dir = Path(MASTER_LOG_DIR)
        self.log_file = Path(log_file) if log_file else self.log_dir / MASTER_LOG_FILE

        if not self.log_file.exists():
            logger.warning(f"Log file not found: {self.log_file}")

    def _read_records(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        api_provider: Optional[str] = None,
        operation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Read and filter records from the log file.

        Args:
            user_id: Filter by user ID
            session_id: Filter by session ID
            source_id: Filter by source ID
            start_date: Filter records after this date
            end_date: Filter records before this date
            status: Filter by status (success, error, etc.)
            api_provider: Filter by API provider
            operation: Filter by operation type

        Returns:
            List of matching records
        """
        if not self.log_file.exists():
            return []

        records = []

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        record = json.loads(line)

                        # Apply filters
                        if user_id and record.get('user_id') != user_id:
                            continue
                        if session_id and record.get('session_id') != session_id:
                            continue
                        if source_id and record.get('source_id') != source_id:
                            continue
                        if status and record.get('status') != status:
                            continue
                        if api_provider and record.get('api_provider') != api_provider:
                            continue
                        if operation and record.get('operation') != operation:
                            continue

                        # Date filtering
                        if start_date or end_date:
                            timestamp = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                            if start_date and timestamp < start_date:
                                continue
                            if end_date and timestamp > end_date:
                                continue

                        records.append(record)

                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse log line: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error reading log file: {e}", exc_info=True)

        return records

    def _calculate_stats(self, records: List[Dict[str, Any]]) -> UsageStats:
        """
        Calculate usage statistics from records.

        Args:
            records: List of tracking records

        Returns:
            UsageStats object with calculated statistics
        """
        stats = UsageStats()
        stats.by_model = defaultdict(lambda: {
            'calls': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0
        })
        stats.by_operation = defaultdict(lambda: {
            'calls': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0
        })

        total_latency = 0.0

        for record in records:
            stats.total_calls += 1

            if record.get('status') == 'success':
                stats.successful_calls += 1
            elif record.get('status') == 'error':
                stats.failed_calls += 1

            input_tokens = record.get('input_tokens', 0)
            output_tokens = record.get('output_tokens', 0)
            total_tokens = record.get('total_tokens', input_tokens + output_tokens)

            stats.total_input_tokens += input_tokens
            stats.total_output_tokens += output_tokens
            stats.total_tokens += total_tokens

            latency = record.get('latency_ms', 0.0)
            total_latency += latency

            cost = record.get('cost_estimate', 0.0)
            stats.total_cost_estimate += cost

            # By model
            model = record.get('model', 'unknown')
            stats.by_model[model]['calls'] += 1
            stats.by_model[model]['input_tokens'] += input_tokens
            stats.by_model[model]['output_tokens'] += output_tokens
            stats.by_model[model]['total_tokens'] += total_tokens

            # By operation
            operation = record.get('operation', 'unknown')
            stats.by_operation[operation]['calls'] += 1
            stats.by_operation[operation]['input_tokens'] += input_tokens
            stats.by_operation[operation]['output_tokens'] += output_tokens
            stats.by_operation[operation]['total_tokens'] += total_tokens

        # Calculate average latency
        if stats.total_calls > 0:
            stats.avg_latency_ms = total_latency / stats.total_calls

        # Convert defaultdicts to regular dicts
        stats.by_model = dict(stats.by_model)
        stats.by_operation = dict(stats.by_operation)

        return stats

    def get_user_usage(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UsageStats:
        """
        Get LLM usage statistics for a specific user.

        Args:
            user_id: User ID to analyze
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            UsageStats for the user
        """
        records = self._read_records(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        return self._calculate_stats(records)

    def get_session_usage(
        self,
        session_id: str
    ) -> UsageStats:
        """
        Get LLM usage statistics for a specific chat session.

        Args:
            session_id: Session ID to analyze

        Returns:
            UsageStats for the session
        """
        records = self._read_records(session_id=session_id)
        return self._calculate_stats(records)

    def get_source_usage(
        self,
        source_id: str
    ) -> UsageStats:
        """
        Get LLM usage statistics for processing a specific source/document.

        Args:
            source_id: Source ID to analyze

        Returns:
            UsageStats for the source processing
        """
        records = self._read_records(source_id=source_id)
        return self._calculate_stats(records)

    def get_usage_by_time_period(
        self,
        days: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UsageStats:
        """
        Get LLM usage statistics for a time period.

        Args:
            days: Number of days to look back (from now)
            start_date: Specific start date (overrides days)
            end_date: Specific end date (defaults to now)

        Returns:
            UsageStats for the time period
        """
        if start_date is None and days is not None:
            start_date = datetime.utcnow() - timedelta(days=days)

        if end_date is None:
            end_date = datetime.utcnow()

        records = self._read_records(
            start_date=start_date,
            end_date=end_date
        )
        return self._calculate_stats(records)

    def get_all_user_ids(self) -> List[str]:
        """
        Get list of all user IDs that have LLM usage.

        Returns:
            List of unique user IDs
        """
        records = self._read_records()
        user_ids = set()

        for record in records:
            user_id = record.get('user_id')
            if user_id:
                user_ids.add(user_id)

        return sorted(list(user_ids))

    def get_all_session_ids(self, user_id: Optional[str] = None) -> List[str]:
        """
        Get list of all session IDs.

        Args:
            user_id: Optional filter by user ID

        Returns:
            List of unique session IDs
        """
        records = self._read_records(user_id=user_id)
        session_ids = set()

        for record in records:
            session_id = record.get('session_id')
            if session_id:
                session_ids.add(session_id)

        return sorted(list(session_ids))

    def get_all_source_ids(self) -> List[str]:
        """
        Get list of all source IDs that have been processed.

        Returns:
            List of unique source IDs
        """
        records = self._read_records()
        source_ids = set()

        for record in records:
            source_id = record.get('source_id')
            if source_id:
                source_ids.add(source_id)

        return sorted(list(source_ids))

    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive usage summary across all dimensions.

        Returns:
            Dict with overall statistics and breakdowns
        """
        all_records = self._read_records()
        overall_stats = self._calculate_stats(all_records)

        # Get counts
        user_count = len(self.get_all_user_ids())
        session_count = len(self.get_all_session_ids())
        source_count = len(self.get_all_source_ids())

        # Get breakdown by provider
        by_provider = defaultdict(lambda: {'calls': 0, 'tokens': 0})
        for record in all_records:
            provider = record.get('api_provider', 'unknown')
            by_provider[provider]['calls'] += 1
            by_provider[provider]['tokens'] += record.get('total_tokens', 0)

        return {
            'overall_stats': {
                'total_calls': overall_stats.total_calls,
                'successful_calls': overall_stats.successful_calls,
                'failed_calls': overall_stats.failed_calls,
                'total_input_tokens': overall_stats.total_input_tokens,
                'total_output_tokens': overall_stats.total_output_tokens,
                'total_tokens': overall_stats.total_tokens,
                'avg_latency_ms': overall_stats.avg_latency_ms,
                'total_cost_estimate': overall_stats.total_cost_estimate
            },
            'unique_counts': {
                'users': user_count,
                'sessions': session_count,
                'sources': source_count
            },
            'by_provider': dict(by_provider),
            'by_model': overall_stats.by_model,
            'by_operation': overall_stats.by_operation
        }

    def export_user_report(
        self,
        user_id: str,
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate detailed usage report for a user.

        Args:
            user_id: User ID to report on
            output_file: Optional file to write JSON report

        Returns:
            Dict with detailed user report
        """
        # Overall user stats
        user_stats = self.get_user_usage(user_id)

        # Get all sessions for this user
        session_ids = self.get_all_session_ids(user_id)

        # Stats by session
        sessions_breakdown = {}
        for session_id in session_ids:
            sessions_breakdown[session_id] = self.get_session_usage(session_id)

        # Last 30 days
        last_30_days = self.get_user_usage(
            user_id,
            start_date=datetime.utcnow() - timedelta(days=30)
        )

        report = {
            'user_id': user_id,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'overall_stats': {
                'total_calls': user_stats.total_calls,
                'successful_calls': user_stats.successful_calls,
                'failed_calls': user_stats.failed_calls,
                'total_input_tokens': user_stats.total_input_tokens,
                'total_output_tokens': user_stats.total_output_tokens,
                'total_tokens': user_stats.total_tokens,
                'avg_latency_ms': user_stats.avg_latency_ms,
                'total_cost_estimate': user_stats.total_cost_estimate,
                'by_model': user_stats.by_model,
                'by_operation': user_stats.by_operation
            },
            'last_30_days': {
                'total_calls': last_30_days.total_calls,
                'total_tokens': last_30_days.total_tokens,
                'total_cost_estimate': last_30_days.total_cost_estimate
            },
            'total_sessions': len(session_ids),
            'sessions': {
                sid: {
                    'total_calls': stats.total_calls,
                    'total_tokens': stats.total_tokens,
                    'total_cost_estimate': stats.total_cost_estimate
                }
                for sid, stats in sessions_breakdown.items()
            }
        }

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"User report exported to: {output_file}")

        return report


def print_usage_stats(stats: UsageStats, title: str = "Usage Statistics"):
    """
    Pretty print usage statistics.

    Args:
        stats: UsageStats to print
        title: Title for the report
    """
    print(f"\n{'='*60}")
    print(f"{title:^60}")
    print(f"{'='*60}\n")

    print(f"Total Calls:        {stats.total_calls:,}")
    print(f"  ✓ Successful:     {stats.successful_calls:,}")
    print(f"  ✗ Failed:         {stats.failed_calls:,}")
    print()
    print(f"Token Usage:")
    print(f"  Input Tokens:     {stats.total_input_tokens:,}")
    print(f"  Output Tokens:    {stats.total_output_tokens:,}")
    print(f"  Total Tokens:     {stats.total_tokens:,}")
    print()
    print(f"Avg Latency:        {stats.avg_latency_ms:.2f} ms")
    print(f"Est. Total Cost:    ${stats.total_cost_estimate:.4f}")

    if stats.by_model:
        print(f"\nBy Model:")
        for model, model_stats in sorted(stats.by_model.items(),
                                         key=lambda x: x[1]['total_tokens'],
                                         reverse=True):
            print(f"  {model}:")
            print(f"    Calls: {model_stats['calls']:,}")
            print(f"    Tokens: {model_stats['total_tokens']:,}")

    if stats.by_operation:
        print(f"\nBy Operation:")
        for operation, op_stats in sorted(stats.by_operation.items(),
                                          key=lambda x: x[1]['total_tokens'],
                                          reverse=True):
            print(f"  {operation}:")
            print(f"    Calls: {op_stats['calls']:,}")
            print(f"    Tokens: {op_stats['total_tokens']:,}")

    print(f"\n{'='*60}\n")
