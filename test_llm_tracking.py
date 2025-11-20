#!/usr/bin/env python3
"""
End-to-end test of LLM tracking system.

This script:
1. Takes an existing PDF from the root folder
2. Processes it through the ingestion pipeline (chunks + summary)
3. Performs a chat query against it
4. Shows all tracked LLM calls

Usage:
    python test_llm_tracking.py
"""

import os
import sys
import json
import time
import uuid
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from shared.llm_tracker import get_tracker
from shared.llm_usage_analyzer import LLMUsageAnalyzer, print_usage_stats


def process_pdf_file():
    """Process the test PDF through chunking and summarization."""
    print("\n" + "="*70)
    print("STEP 1: Process PDF File")
    print("="*70)

    pdf_path = Path("20202001_ctf_final_web_copy_2.pdf")
    if not pdf_path.exists():
        print(f"✗ PDF not found: {pdf_path}")
        return None, None

    print(f"✓ Found PDF: {pdf_path}")
    print(f"  Size: {pdf_path.stat().st_size:,} bytes")

    # Generate a test source_id
    source_id = f"test_llm_tracking_{uuid.uuid4().hex[:8]}"
    print(f"  Source ID: {source_id}")

    # Process PDF to chunks
    print("\nProcessing PDF to chunks...")
    from tools.processing.process_pdf import extract_pdf_text_by_page
    from shared.schemas import ChunkMetadata, ChunkAnchor, Chunk

    try:
        pages = extract_pdf_text_by_page(str(pdf_path))
        print(f"✓ Extracted {len(pages)} pages from PDF")

        # Create chunks from pages
        test_chunks = []
        for i, (page_num, text) in enumerate(pages[:5]):  # Use first 5 pages for speed
            metadata = ChunkMetadata(
                id=f"{source_id}_page_{page_num}",
                source_id=source_id,
                filename=pdf_path.name,
                title="Test Document - LLM Tracking",
                mimetype="application/pdf"
            )

            anchor = ChunkAnchor(page=page_num)

            chunk = Chunk(
                metadata=metadata,
                anchor=anchor,
                content=text,
                chunk_index=i
            )
            test_chunks.append(chunk)

        print(f"✓ Created {len(test_chunks)} chunks for summarization")

        # Call summarization (this will trigger tracking)
        print("\nCalling Gemini API for summarization...")
        print("(This will be TRACKED in the master log)")

        from tools.processing.summarize_chunks import summarize_with_gemini

        summary_result = summarize_with_gemini(
            chunks=test_chunks,
            description="Test document for demonstrating LLM tracking system",
            source_id=source_id
        )

        print("\n✓ Summarization completed!")
        print(f"  Summary: {summary_result['summary_text'][:150]}...")
        if summary_result.get('author'):
            print(f"  Author: {summary_result['author']}")
        if summary_result.get('tags'):
            print(f"  Tags: {', '.join(summary_result['tags'][:5])}")

        return source_id, summary_result

    except Exception as e:
        print(f"\n✗ PDF processing failed: {e}")
        import traceback
        traceback.print_exc()
        return source_id, None


def simulate_chat_query(source_id, summary_result):
    """Simulate a chat query."""
    print("\n" + "="*70)
    print("STEP 2: Simulate Chat Query")
    print("="*70)

    if not summary_result:
        print("✗ No summary available, skipping chat query")
        return None

    print("\nSimulating chat query: 'What is this document about?'")
    print("Calling Gemini API for answer synthesis...")
    print("(This will be TRACKED in the master log)")

    from apps.agent_api.synthesizer import synthesize_answer

    # Create mock search results
    summary_results = [{
        'summary_text': summary_result['summary_text'],
        'source_id': source_id,
        'title': 'Test Document - LLM Tracking',
        'tags': summary_result.get('tags', [])
    }]

    chunk_results = [{
        'content': summary_result['summary_text'][:500],  # Use part of summary as chunk
        'page_number': 1,
        'source_id': source_id,
        'filename': '20202001_ctf_final_web_copy_2.pdf'
    }]

    try:
        answer = synthesize_answer(
            query="What is this document about?",
            summary_results=summary_results,
            chunk_results=chunk_results,
            temperature=0.3,
            user_id="test_user_123",
            session_id="test_session_456"
        )

        print("\n✓ Chat answer generated!")
        print(f"  Answer: {answer['answer'][:200]}...")
        print(f"  Model used: {answer.get('model_used', 'N/A')}")
        if answer.get('input_tokens'):
            print(f"  Input tokens: {answer['input_tokens']:,}")
        if answer.get('output_tokens'):
            print(f"  Output tokens: {answer['output_tokens']:,}")
        if answer.get('total_tokens'):
            print(f"  Total tokens: {answer['total_tokens']:,}")

        return answer

    except Exception as e:
        print(f"\n✗ Chat query failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_tracking_results(source_id):
    """Analyze the tracking results."""
    print("\n" + "="*70)
    print("STEP 3: Analyze Tracking Results")
    print("="*70)

    # Give it a moment for logs to be written
    time.sleep(0.5)

    analyzer = LLMUsageAnalyzer()

    # Check if log file exists
    if not analyzer.log_file.exists():
        print(f"\n✗ Log file not found: {analyzer.log_file}")
        print("  The tracking directory may not have been created.")
        print(f"  Expected location: {analyzer.log_file.parent}")
        return

    print(f"\n✓ Log file found: {analyzer.log_file}")
    print(f"  Size: {analyzer.log_file.stat().st_size:,} bytes")

    # Read recent records
    print("\n" + "-"*70)
    print("Recent LLM API Calls (last 5):")
    print("-"*70)

    try:
        with open(analyzer.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-5:] if len(lines) >= 5 else lines

            if not recent_lines:
                print("  No tracking records found")
                return

            for i, line in enumerate(recent_lines, 1):
                try:
                    record = json.loads(line)
                    print(f"\n{i}. {record['operation'].upper()} - {record['model']}")
                    print(f"   Timestamp: {record['timestamp']}")
                    print(f"   Function:  {record['source_function']}")
                    print(f"   Status:    {record['status']}")
                    print(f"   Tokens:    {record.get('input_tokens', 0):,} in, "
                          f"{record.get('output_tokens', 0):,} out, "
                          f"{record.get('total_tokens', 0):,} total")
                    print(f"   Latency:   {record.get('latency_ms', 0):.2f} ms")

                    if record.get('user_id'):
                        print(f"   User:      {record['user_id']}")
                    if record.get('session_id'):
                        print(f"   Session:   {record['session_id']}")
                    if record.get('source_id'):
                        print(f"   Source:    {record['source_id']}")
                    if record.get('error_message'):
                        print(f"   Error:     {record['error_message'][:100]}")

                except json.JSONDecodeError:
                    print(f"{i}. [Invalid JSON]")

    except Exception as e:
        print(f"\n✗ Error reading log file: {e}")
        return

    # Get statistics for test source
    print("\n" + "-"*70)
    print("Source Processing Statistics:")
    print("-"*70)

    source_stats = analyzer.get_source_usage(source_id)
    if source_stats.total_calls > 0:
        print_usage_stats(source_stats, f"Source: {source_id}")
    else:
        print("No calls found for test source")

    # Get statistics for test user
    print("\n" + "-"*70)
    print("User Statistics:")
    print("-"*70)

    user_stats = analyzer.get_user_usage("test_user_123")
    if user_stats.total_calls > 0:
        print_usage_stats(user_stats, "User: test_user_123")
    else:
        print("No calls found for test user")

    # Get statistics for test session
    print("\n" + "-"*70)
    print("Session Statistics:")
    print("-"*70)

    session_stats = analyzer.get_session_usage("test_session_456")
    if session_stats.total_calls > 0:
        print_usage_stats(session_stats, "Session: test_session_456")
    else:
        print("No calls found for test session")


def main():
    """Run the end-to-end test."""
    print("\n" + "="*70)
    print(" "*15 + "LLM TRACKING SYSTEM TEST")
    print(" "*10 + "End-to-End PDF Processing with Tracking")
    print("="*70)

    # Check environment
    print("\nEnvironment:")
    print(f"  Tracking Dir:  {os.getenv('LLM_TRACKING_DIR', './logs/llm_tracking')}")
    print(f"  Tracking File: {os.getenv('LLM_TRACKING_FILE', 'master_llm_calls.jsonl')}")

    # Step 1: Process PDF
    source_id, summary_result = process_pdf_file()

    if not source_id:
        print("\n✗ Test failed - could not process PDF")
        return

    # Step 2: Chat query
    if summary_result:
        answer = simulate_chat_query(source_id, summary_result)
    else:
        print("\nSkipping chat query due to summarization failure")

    # Step 3: Analyze results
    analyze_tracking_results(source_id)

    # Final summary
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print("\nWhat was tested:")
    print("  ✓ PDF chunking")
    print("  ✓ Summarization with Gemini (TRACKED)")
    print("  ✓ Chat query with Gemini (TRACKED)")
    print("  ✓ Usage analysis and reporting")
    print("\nTracking data saved to:")
    analyzer = LLMUsageAnalyzer()
    print(f"  {analyzer.log_file}")
    print("\nNext steps:")
    print("  - View the log file to see raw JSON records")
    print("  - Run: python analyze_llm_usage.py --summary")
    print("  - Run: python analyze_llm_usage.py --user test_user_123")
    print(f"  - Run: python analyze_llm_usage.py --source {source_id}")
    print("\n")


if __name__ == "__main__":
    main()
