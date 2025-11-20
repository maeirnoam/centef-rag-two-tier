#!/usr/bin/env python3
"""
Example script to analyze LLM usage from tracking logs.

Usage:
    # Get overall usage summary
    python analyze_llm_usage.py --summary

    # Get user usage
    python analyze_llm_usage.py --user USER_ID

    # Get session usage
    python analyze_llm_usage.py --session SESSION_ID

    # Get source processing usage
    python analyze_llm_usage.py --source SOURCE_ID

    # Get usage for last N days
    python analyze_llm_usage.py --days 7

    # Export user report
    python analyze_llm_usage.py --user USER_ID --export report.json

    # List all users with LLM usage
    python analyze_llm_usage.py --list-users

    # List all sessions for a user
    python analyze_llm_usage.py --list-sessions --user USER_ID
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from shared.llm_usage_analyzer import LLMUsageAnalyzer, print_usage_stats


def main():
    parser = argparse.ArgumentParser(
        description="Analyze LLM usage from tracking logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Action arguments
    parser.add_argument("--summary", action="store_true",
                        help="Show overall usage summary")
    parser.add_argument("--user", type=str,
                        help="Analyze usage for specific user")
    parser.add_argument("--session", type=str,
                        help="Analyze usage for specific session")
    parser.add_argument("--source", type=str,
                        help="Analyze usage for specific source processing")
    parser.add_argument("--days", type=int,
                        help="Analyze usage for last N days")

    # List arguments
    parser.add_argument("--list-users", action="store_true",
                        help="List all users with LLM usage")
    parser.add_argument("--list-sessions", action="store_true",
                        help="List all sessions (optionally filtered by user)")
    parser.add_argument("--list-sources", action="store_true",
                        help="List all sources that have been processed")

    # Export arguments
    parser.add_argument("--export", type=str,
                        help="Export report to JSON file")

    # Log file argument
    parser.add_argument("--log-file", type=str,
                        help="Custom path to tracking log file")

    args = parser.parse_args()

    # Initialize analyzer
    analyzer = LLMUsageAnalyzer(log_file=args.log_file)

    # Handle list commands
    if args.list_users:
        print("\n=== All Users with LLM Usage ===\n")
        users = analyzer.get_all_user_ids()
        if users:
            for user in users:
                print(f"  - {user}")
        else:
            print("  No users found")
        print()
        return

    if args.list_sessions:
        print("\n=== All Sessions ===\n")
        sessions = analyzer.get_all_session_ids(user_id=args.user)
        if sessions:
            for session in sessions:
                print(f"  - {session}")
        else:
            print("  No sessions found")
        print()
        return

    if args.list_sources:
        print("\n=== All Processed Sources ===\n")
        sources = analyzer.get_all_source_ids()
        if sources:
            for source in sources:
                print(f"  - {source}")
        else:
            print("  No sources found")
        print()
        return

    # Handle analysis commands
    if args.summary:
        print("\n" + "="*70)
        print(" "*20 + "OVERALL USAGE SUMMARY")
        print("="*70)

        summary = analyzer.get_usage_summary()

        print(f"\nOverall Statistics:")
        print(f"  Total Calls:        {summary['overall_stats']['total_calls']:,}")
        print(f"  Successful Calls:   {summary['overall_stats']['successful_calls']:,}")
        print(f"  Failed Calls:       {summary['overall_stats']['failed_calls']:,}")
        print(f"\nToken Usage:")
        print(f"  Input Tokens:       {summary['overall_stats']['total_input_tokens']:,}")
        print(f"  Output Tokens:      {summary['overall_stats']['total_output_tokens']:,}")
        print(f"  Total Tokens:       {summary['overall_stats']['total_tokens']:,}")
        print(f"\nPerformance:")
        print(f"  Avg Latency:        {summary['overall_stats']['avg_latency_ms']:.2f} ms")
        print(f"  Est. Total Cost:    ${summary['overall_stats']['total_cost_estimate']:.4f}")

        print(f"\nUnique Counts:")
        print(f"  Users:              {summary['unique_counts']['users']:,}")
        print(f"  Sessions:           {summary['unique_counts']['sessions']:,}")
        print(f"  Sources:            {summary['unique_counts']['sources']:,}")

        print(f"\nBy Provider:")
        for provider, stats in summary['by_provider'].items():
            print(f"  {provider}:")
            print(f"    Calls:  {stats['calls']:,}")
            print(f"    Tokens: {stats['tokens']:,}")

        print(f"\nTop Models by Token Usage:")
        models_sorted = sorted(
            summary['by_model'].items(),
            key=lambda x: x[1]['total_tokens'],
            reverse=True
        )[:5]
        for model, stats in models_sorted:
            print(f"  {model}:")
            print(f"    Calls:  {stats['calls']:,}")
            print(f"    Tokens: {stats['total_tokens']:,}")

        print(f"\nTop Operations by Token Usage:")
        ops_sorted = sorted(
            summary['by_operation'].items(),
            key=lambda x: x[1]['total_tokens'],
            reverse=True
        )[:5]
        for op, stats in ops_sorted:
            print(f"  {op}:")
            print(f"    Calls:  {stats['calls']:,}")
            print(f"    Tokens: {stats['total_tokens']:,}")

        print("\n" + "="*70 + "\n")
        return

    if args.user:
        if args.export:
            report = analyzer.export_user_report(args.user, output_file=args.export)
            print(f"\n✓ User report exported to: {args.export}\n")
        else:
            stats = analyzer.get_user_usage(args.user)
            print_usage_stats(stats, f"Usage Statistics for User: {args.user}")
        return

    if args.session:
        stats = analyzer.get_session_usage(args.session)
        print_usage_stats(stats, f"Usage Statistics for Session: {args.session}")
        return

    if args.source:
        stats = analyzer.get_source_usage(args.source)
        print_usage_stats(stats, f"Usage Statistics for Source: {args.source}")
        return

    if args.days:
        stats = analyzer.get_usage_by_time_period(days=args.days)
        print_usage_stats(stats, f"Usage Statistics for Last {args.days} Days")
        return

    # If no arguments, show help
    parser.print_help()


if __name__ == "__main__":
    main()
