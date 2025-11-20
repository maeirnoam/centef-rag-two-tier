"""
Comprehensive test suite for format-adaptive synthesizer.
Tests all 10+ output formats with real data to examine response structure and style.
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv

# Add app directories to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "apps" / "agent_api"))

from apps.agent_api.synthesizer_optimized import (
    detect_output_format,
    build_optimized_synthesis_prompt,
    synthesize_answer_optimized
)
from apps.agent_api.retriever_vertex_search import search_chunks, search_summaries

load_dotenv()

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test queries for each format type
FORMAT_TEST_QUERIES = {
    "brief_summary": {
        "query": "Give me a brief summary of FATF recommendations on beneficial ownership",
        "expected_format": "brief_summary",
        "expected_length": "brief",
        "expected_structure": "bullet_points"
    },
    "social_media": {
        "query": "Write a tweet about the importance of AML compliance for financial institutions",
        "expected_format": "social_media",
        "expected_length": "brief",
        "expected_structure": "single_paragraph"
    },
    "blog_post": {
        "query": "Write a blog post explaining the challenges of virtual asset regulation",
        "expected_format": "blog_post",
        "expected_length": "long",
        "expected_structure": "sections"
    },
    "newsletter": {
        "query": "Create a newsletter update on recent FATF guidance for cryptocurrency exchanges",
        "expected_format": "newsletter",
        "expected_length": "medium",
        "expected_structure": "sections"
    },
    "outline": {
        "query": "Create an outline for a presentation on money laundering typologies",
        "expected_format": "outline",
        "expected_length": "medium",
        "expected_structure": "hierarchical"
    },
    "protocol": {
        "query": "What is the protocol for conducting enhanced due diligence on high-risk customers?",
        "expected_format": "protocol",
        "expected_length": "medium",
        "expected_structure": "numbered_steps"
    },
    "report": {
        "query": "Generate a report on sanctions compliance requirements for financial institutions",
        "expected_format": "report",
        "expected_length": "long",
        "expected_structure": "sections"
    },
    "comprehensive_analysis": {
        "query": "Provide a comprehensive analysis of the effectiveness of the risk-based approach to AML",
        "expected_format": "comprehensive_analysis",
        "expected_length": "comprehensive",
        "expected_structure": "sections"
    },
    "factual_answer": {
        "query": "What are the key components of customer due diligence?",
        "expected_format": "factual_answer",
        "expected_length": "medium",
        "expected_structure": "paragraphs"
    },
    "general_answer": {
        "query": "How do financial institutions detect suspicious transactions?",
        "expected_format": "general_answer",
        "expected_length": "medium",
        "expected_structure": "paragraphs"
    }
}


def save_json_output(data: Dict[str, Any], filename: str):
    """Save test results to JSON file."""
    output_dir = Path(__file__).parent / "test_outputs"
    output_dir.mkdir(exist_ok=True)
    
    filepath = output_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved output to: {filepath}")


def save_text_output(content: str, filename: str):
    """Save text output for human review."""
    output_dir = Path(__file__).parent / "test_outputs"
    output_dir.mkdir(exist_ok=True)
    
    filepath = output_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"Saved text output to: {filepath}")


def test_format_detection():
    """Test format detection for all query types."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Format Detection")
    logger.info("="*80)
    
    results = []
    
    for test_name, test_case in FORMAT_TEST_QUERIES.items():
        query = test_case['query']
        logger.info(f"\n--- Testing: {test_name} ---")
        logger.info(f"Query: {query}")
        
        format_info = detect_output_format(query)
        
        result = {
            "test_name": test_name,
            "query": query,
            "detected_format": format_info,
            "expected": {k: v for k, v in test_case.items() if k != 'query'}
        }
        
        # Validate expectations
        validations = []
        if format_info['format_type'] == test_case.get('expected_format'):
            validations.append(f"✓ Format: {format_info['format_type']}")
        else:
            validations.append(f"✗ Format: {format_info['format_type']} (expected {test_case.get('expected_format')})")
        
        if format_info['length'] == test_case.get('expected_length'):
            validations.append(f"✓ Length: {format_info['length']}")
        else:
            validations.append(f"✗ Length: {format_info['length']} (expected {test_case.get('expected_length')})")
        
        if format_info['structure'] == test_case.get('expected_structure'):
            validations.append(f"✓ Structure: {format_info['structure']}")
        else:
            validations.append(f"✗ Structure: {format_info['structure']} (expected {test_case.get('expected_structure')})")
        
        result['validations'] = validations
        
        logger.info(f"Detected format: {format_info['format_type']}")
        logger.info(f"Length: {format_info['length']}, Structure: {format_info['structure']}")
        logger.info(f"Temperature: {format_info['temperature']}, Max tokens: {format_info['max_tokens']}")
        logger.info(f"Style: {format_info['style']}")
        
        for validation in validations:
            logger.info(f"  {validation}")
        
        results.append(result)
    
    save_json_output(results, f"format_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    return results


def test_prompt_building():
    """Test prompt building with format-specific instructions."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Format-Specific Prompt Building")
    logger.info("="*80)
    
    results = []
    
    # Use a sample query and mock search results
    sample_query = "What are FATF recommendations on virtual assets?"
    
    # Mock search results
    mock_summaries = [{
        "title": "FATF Guidance on Virtual Assets",
        "summary_text": "The FATF has issued comprehensive guidance on virtual assets and virtual asset service providers (VASPs)...",
        "author": None,
        "organization": "FATF",
        "date": "2021-10-01",
        "tags": ["virtual_assets", "guidance"]
    }]
    
    mock_chunks = [{
        "title": "FATF Guidance on Virtual Assets",
        "content": "Virtual asset service providers should conduct customer due diligence and implement the travel rule...",
        "page_number": 15,
        "filename": "fatf_va_guidance.pdf"
    }]
    
    for test_name, test_case in list(FORMAT_TEST_QUERIES.items())[:5]:  # Test first 5 formats
        query = test_case['query']
        logger.info(f"\n--- Testing prompt for: {test_name} ---")
        
        format_info = detect_output_format(query)
        
        prompt = build_optimized_synthesis_prompt(
            query=query,
            summary_results=mock_summaries,
            chunk_results=mock_chunks,
            prioritize_citations=True,
            format_info=format_info
        )
        
        result = {
            "test_name": test_name,
            "query": query,
            "format_type": format_info['format_type'],
            "prompt_length": len(prompt),
            "prompt_preview": prompt[:500] + "..." if len(prompt) > 500 else prompt
        }
        
        logger.info(f"Format: {format_info['format_type']}")
        logger.info(f"Prompt length: {len(prompt)} characters")
        logger.info(f"First 200 chars: {prompt[:200]}...")
        
        # Save full prompt to text file
        save_text_output(prompt, f"prompt_{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        results.append(result)
    
    save_json_output(results, f"prompt_building_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    return results


def test_full_synthesis():
    """Test full synthesis pipeline with real search results."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Full Synthesis with Real Search")
    logger.info("="*80)
    
    # Select specific queries to test with real API calls
    test_queries = [
        "brief_summary",
        "blog_post", 
        "protocol",
        "factual_answer"
    ]
    
    results = []
    full_responses = []
    
    for test_name in test_queries:
        if test_name not in FORMAT_TEST_QUERIES:
            continue
            
        test_case = FORMAT_TEST_QUERIES[test_name]
        query = test_case['query']
        
        logger.info(f"\n--- Full synthesis test: {test_name} ---")
        logger.info(f"Query: {query}")
        
        try:
            # Step 1: Search for relevant content
            logger.info("Step 1: Searching for content...")
            summary_results = search_summaries(query, max_results=3)
            chunk_results = search_chunks(query, max_results=5)
            
            logger.info(f"Found {len(summary_results)} summaries, {len(chunk_results)} chunks")
            
            # Step 2: Synthesize answer with format detection
            logger.info("Step 2: Synthesizing answer...")
            synthesis_result = synthesize_answer_optimized(
                query=query,
                summary_results=summary_results,
                chunk_results=chunk_results,
                enable_context_truncation=True,
                enable_adaptive_temperature=True
            )
            
            # Extract key info
            answer = synthesis_result['answer']
            format_info = synthesis_result.get('format_info', {})
            
            result = {
                "test_name": test_name,
                "query": query,
                "format_info": format_info,
                "answer_length": len(answer),
                "answer_words": len(answer.split()),
                "num_summaries_used": synthesis_result.get('num_summaries_used', 0),
                "num_chunks_used": synthesis_result.get('num_chunks_used', 0),
                "citations_count": len(synthesis_result.get('explicit_citations', [])),
                "temperature_used": synthesis_result.get('temperature', 0),
                "model_used": synthesis_result.get('model_used', 'unknown')
            }
            
            # Full response for detailed review
            full_response = {
                "test_name": test_name,
                "query": query,
                "format_type": format_info.get('format_type', 'unknown'),
                "answer": answer,
                "citations": synthesis_result.get('explicit_citations', []),
                "sources": synthesis_result.get('sources', [])
            }
            
            logger.info(f"✓ Synthesis completed")
            logger.info(f"  Format: {format_info.get('format_type', 'unknown')}")
            logger.info(f"  Answer length: {len(answer)} chars, {len(answer.split())} words")
            logger.info(f"  Temperature: {synthesis_result.get('temperature', 0)}")
            logger.info(f"  Citations: {len(synthesis_result.get('explicit_citations', []))}")
            logger.info(f"  Model: {synthesis_result.get('model_used', 'unknown')}")
            
            # Save individual answer to text file for review
            answer_text = f"""
{'='*80}
TEST: {test_name}
QUERY: {query}
FORMAT: {format_info.get('format_type', 'unknown')}
LENGTH: {len(answer)} chars, {len(answer.split())} words
TEMPERATURE: {synthesis_result.get('temperature', 0)}
MAX_TOKENS: {format_info.get('max_tokens', 'unknown')}
{'='*80}

{answer}

{'='*80}
CITATIONS ({len(synthesis_result.get('explicit_citations', []))})
{'='*80}
"""
            for i, citation in enumerate(synthesis_result.get('explicit_citations', []), 1):
                answer_text += f"{i}. {citation}\n"
            
            save_text_output(answer_text, f"answer_{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            
            results.append(result)
            full_responses.append(full_response)
            
        except Exception as e:
            logger.error(f"Error testing {test_name}: {e}", exc_info=True)
            results.append({
                "test_name": test_name,
                "query": query,
                "error": str(e)
            })
    
    save_json_output(results, f"synthesis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    save_json_output(full_responses, f"synthesis_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    return results


def run_all_tests():
    """Run all synthesizer format tests."""
    logger.info("\n" + "="*80)
    logger.info("SYNTHESIZER FORMAT COMPREHENSIVE TEST SUITE")
    logger.info("="*80)
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"Total format types: {len(FORMAT_TEST_QUERIES)}")
    
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "total_formats": len(FORMAT_TEST_QUERIES),
        "tests": {}
    }
    
    try:
        logger.info("\n>>> Running format detection tests...")
        all_results['tests']['format_detection'] = test_format_detection()
    except Exception as e:
        logger.error(f"Format detection test failed: {e}", exc_info=True)
        all_results['tests']['format_detection'] = {"error": str(e)}
    
    try:
        logger.info("\n>>> Running prompt building tests...")
        all_results['tests']['prompt_building'] = test_prompt_building()
    except Exception as e:
        logger.error(f"Prompt building test failed: {e}", exc_info=True)
        all_results['tests']['prompt_building'] = {"error": str(e)}
    
    try:
        logger.info("\n>>> Running full synthesis tests (with real API calls)...")
        all_results['tests']['full_synthesis'] = test_full_synthesis()
    except Exception as e:
        logger.error(f"Full synthesis test failed: {e}", exc_info=True)
        all_results['tests']['full_synthesis'] = {"error": str(e)}
    
    # Save comprehensive report
    save_json_output(all_results, f"synthesizer_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    logger.info("\n" + "="*80)
    logger.info("ALL SYNTHESIZER TESTS COMPLETED")
    logger.info("="*80)
    logger.info(f"Results saved to: test_outputs/")
    logger.info(f"Review individual answers in: test_outputs/answer_*.txt")
    logger.info(f"Review prompts in: test_outputs/prompt_*.txt")


if __name__ == "__main__":
    run_all_tests()
