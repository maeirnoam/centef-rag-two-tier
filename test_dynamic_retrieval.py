"""
Comprehensive test suite for dynamic retrieval strategies.
Tests query analysis, adaptive limits, metadata filtering, and search strategies.
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

# Add app directories to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "apps" / "agent_api"))

from apps.agent_api.retriever_optimized import (
    analyze_query_characteristics,
    adaptive_result_limits,
    build_metadata_filter,
    select_search_strategy,
    search_two_tier_optimized
)

load_dotenv()

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test queries covering different types and scenarios
TEST_QUERIES = {
    "factual_simple": {
        "query": "What is a PEP?",
        "expected_type": "factual",
        "expected_complexity": "simple",
        "expected_expansion": False
    },
    "factual_moderate": {
        "query": "What are the key requirements for customer due diligence?",
        "expected_type": "factual",
        "expected_complexity": "moderate"
    },
    "procedural": {
        "query": "How to file a suspicious activity report?",
        "expected_type": "procedural",
        "expected_complexity": "moderate",
        "expected_chunks_priority": True
    },
    "comparative": {
        "query": "Compare risk-based approach vs rules-based approach to AML",
        "expected_type": "comparative",
        "expected_complexity": "moderate",
        "expected_expansion": True
    },
    "analytical_complex": {
        "query": "Provide a comprehensive analysis of FATF effectiveness on terrorism financing",
        "expected_type": "analytical",
        "expected_complexity": "complex",
        "expected_expansion": True,
        "expected_org_filter": "FATF",
        "expected_topic_filter": "terrorism_financing"
    },
    "exploratory": {
        "query": "Tell me about trade-based money laundering",
        "expected_type": "exploratory",
        "expected_topic_filter": "trade_based_money_laundering"
    },
    "org_filter_fatf": {
        "query": "FATF recommendations on virtual assets",
        "expected_org_filter": "FATF",
        "expected_topic_filter": "virtual_assets"
    },
    "org_filter_worldbank": {
        "query": "World Bank report on AML effectiveness",
        "expected_org_filter": "World Bank"
    },
    "topic_crypto": {
        "query": "Cryptocurrency money laundering regulations",
        "expected_topic_filter": "virtual_assets"
    },
    "topic_sanctions": {
        "query": "Sanctions screening procedures for wire transfers",
        "expected_topic_filter": "sanctions"
    },
    "topic_beneficial_ownership": {
        "query": "Ultimate beneficial owner identification requirements",
        "expected_topic_filter": "beneficial_ownership"
    },
    "topic_peps": {
        "query": "PEP screening and enhanced due diligence",
        "expected_topic_filter": "peps"
    },
    "multi_filter": {
        "query": "IMF assessment of cryptocurrency AML compliance",
        "expected_org_filter": "IMF",
        "expected_topic_filter": "virtual_assets"
    },
    "complex_multi_filter": {
        "query": "FATF guidance on beneficial ownership for virtual asset service providers",
        "expected_org_filter": "FATF",
        "expected_topic_filter": "beneficial_ownership"  # First match wins
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


def test_query_analysis():
    """Test query characteristic analysis."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Query Characteristic Analysis")
    logger.info("="*80)
    
    results = []
    
    for test_name, test_case in TEST_QUERIES.items():
        query = test_case['query']
        logger.info(f"\n--- Testing: {test_name} ---")
        logger.info(f"Query: {query}")
        
        characteristics = analyze_query_characteristics(query)
        
        result = {
            "test_name": test_name,
            "query": query,
            "characteristics": characteristics,
            "expected": {k: v for k, v in test_case.items() if k != 'query'}
        }
        
        # Validate expectations
        validations = []
        if 'expected_type' in test_case:
            match = characteristics['query_type'] == test_case['expected_type']
            validations.append(f"Type: {characteristics['query_type']} {'✓' if match else '✗ expected ' + test_case['expected_type']}")
        
        if 'expected_complexity' in test_case:
            match = characteristics['complexity'] == test_case['expected_complexity']
            validations.append(f"Complexity: {characteristics['complexity']} {'✓' if match else '✗ expected ' + test_case['expected_complexity']}")
        
        if 'expected_org_filter' in test_case:
            orgs = [v for f, v in characteristics['filter_hints'] if f == 'organization']
            match = test_case['expected_org_filter'] in orgs
            validations.append(f"Org filter: {orgs} {'✓' if match else '✗ expected ' + test_case['expected_org_filter']}")
        
        if 'expected_topic_filter' in test_case:
            topics = [v for f, v in characteristics['filter_hints'] if f == 'topic']
            match = test_case['expected_topic_filter'] in topics
            validations.append(f"Topic filter: {topics} {'✓' if match else '✗ expected ' + test_case['expected_topic_filter']}")
        
        result['validations'] = validations
        
        logger.info(f"Type: {characteristics['query_type']}")
        logger.info(f"Complexity: {characteristics['complexity']}")
        logger.info(f"Scope: {characteristics['scope']}")
        logger.info(f"Needs chunks: {characteristics['needs_chunks']}, summaries: {characteristics['needs_summaries']}")
        logger.info(f"Filter hints: {characteristics['filter_hints']}")
        
        for validation in validations:
            logger.info(f"  {validation}")
        
        results.append(result)
    
    save_json_output(results, f"query_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    return results


def test_adaptive_limits():
    """Test adaptive result limit calculation."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Adaptive Result Limits")
    logger.info("="*80)
    
    results = []
    
    for test_name, test_case in TEST_QUERIES.items():
        query = test_case['query']
        logger.info(f"\n--- Testing: {test_name} ---")
        logger.info(f"Query: {query}")
        
        characteristics = analyze_query_characteristics(query)
        chunks, summaries = adaptive_result_limits(query, characteristics)
        
        result = {
            "test_name": test_name,
            "query": query,
            "query_type": characteristics['query_type'],
            "complexity": characteristics['complexity'],
            "scope": characteristics['scope'],
            "adaptive_limits": {
                "chunks": chunks,
                "summaries": summaries
            }
        }
        
        logger.info(f"Type: {characteristics['query_type']}, Complexity: {characteristics['complexity']}, Scope: {characteristics['scope']}")
        logger.info(f"Adaptive limits → Chunks: {chunks}, Summaries: {summaries}")
        
        results.append(result)
    
    save_json_output(results, f"adaptive_limits_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    return results


def test_metadata_filters():
    """Test metadata filter building with OR and AND logic."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Metadata Filter Building")
    logger.info("="*80)
    
    results = []
    
    for test_name, test_case in TEST_QUERIES.items():
        query = test_case['query']
        logger.info(f"\n--- Testing: {test_name} ---")
        logger.info(f"Query: {query}")
        
        characteristics = analyze_query_characteristics(query)
        
        # Test both OR and AND logic
        filter_or = build_metadata_filter(query, characteristics, filter_logic="OR")
        filter_and = build_metadata_filter(query, characteristics, filter_logic="AND")
        
        result = {
            "test_name": test_name,
            "query": query,
            "filter_hints": characteristics['filter_hints'],
            "filters": {
                "OR": filter_or,
                "AND": filter_and
            }
        }
        
        logger.info(f"Filter hints: {characteristics['filter_hints']}")
        logger.info(f"OR filter:  {filter_or or 'None'}")
        logger.info(f"AND filter: {filter_and or 'None'}")
        
        results.append(result)
    
    save_json_output(results, f"metadata_filters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    return results


def test_search_strategies():
    """Test search strategy selection."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Search Strategy Selection")
    logger.info("="*80)
    
    results = []
    
    for test_name, test_case in TEST_QUERIES.items():
        query = test_case['query']
        logger.info(f"\n--- Testing: {test_name} ---")
        logger.info(f"Query: {query}")
        
        characteristics = analyze_query_characteristics(query)
        strategy = select_search_strategy(query, characteristics)
        
        result = {
            "test_name": test_name,
            "query": query,
            "query_type": characteristics['query_type'],
            "complexity": characteristics['complexity'],
            "strategy": strategy
        }
        
        logger.info(f"Type: {characteristics['query_type']}, Complexity: {characteristics['complexity']}")
        logger.info(f"Strategy: {strategy}")
        
        # Validate expectations
        if 'expected_expansion' in test_case:
            match = strategy['enable_query_expansion'] == test_case['expected_expansion']
            logger.info(f"  Query expansion: {strategy['enable_query_expansion']} {'✓' if match else '✗ expected ' + str(test_case['expected_expansion'])}")
        
        results.append(result)
    
    save_json_output(results, f"search_strategies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    return results


def test_full_retrieval_sample():
    """Test full retrieval pipeline on a few sample queries."""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Full Retrieval Pipeline (Sample)")
    logger.info("="*80)
    
    # Select a few representative queries for full testing
    sample_queries = [
        "factual_simple",
        "analytical_complex",
        "org_filter_fatf",
        "multi_filter"
    ]
    
    results = []
    
    for test_name in sample_queries:
        if test_name not in TEST_QUERIES:
            continue
            
        test_case = TEST_QUERIES[test_name]
        query = test_case['query']
        
        logger.info(f"\n--- Testing Full Pipeline: {test_name} ---")
        logger.info(f"Query: {query}")
        
        try:
            # Test with OR logic
            logger.info("\n>>> Testing with OR filter logic")
            result_or = search_two_tier_optimized(
                query=query,
                use_adaptive_strategy=True,
                filter_logic="OR"
            )
            
            # Test with AND logic
            logger.info("\n>>> Testing with AND filter logic")
            result_and = search_two_tier_optimized(
                query=query,
                use_adaptive_strategy=True,
                filter_logic="AND"
            )
            
            # Prepare result summary (without full chunk/summary content)
            result_summary = {
                "test_name": test_name,
                "query": query,
                "OR_logic": {
                    "total_chunks": result_or['total_chunks'],
                    "total_summaries": result_or['total_summaries'],
                    "query_characteristics": result_or.get('query_characteristics'),
                    "optimizations_applied": result_or['optimizations_applied'],
                    "chunk_sources": [
                        {
                            "source_id": c.get('source_id'),
                            "title": c.get('title'),
                            "score": c.get('score'),
                            "page": c.get('page_number')
                        }
                        for c in result_or['chunks'][:5]  # First 5 only
                    ],
                    "summary_sources": [
                        {
                            "source_id": s.get('source_id'),
                            "title": s.get('title'),
                            "organization": s.get('organization'),
                            "tags": s.get('tags'),
                            "score": s.get('score')
                        }
                        for s in result_or['summaries'][:5]  # First 5 only
                    ]
                },
                "AND_logic": {
                    "total_chunks": result_and['total_chunks'],
                    "total_summaries": result_and['total_summaries'],
                    "optimizations_applied": result_and['optimizations_applied'],
                    "chunk_sources": [
                        {
                            "source_id": c.get('source_id'),
                            "title": c.get('title'),
                            "score": c.get('score'),
                            "page": c.get('page_number')
                        }
                        for c in result_and['chunks'][:5]
                    ],
                    "summary_sources": [
                        {
                            "source_id": s.get('source_id'),
                            "title": s.get('title'),
                            "organization": s.get('organization'),
                            "tags": s.get('tags'),
                            "score": s.get('score')
                        }
                        for s in result_and['summaries'][:5]
                    ]
                }
            }
            
            logger.info(f"\nOR Logic Results:")
            logger.info(f"  Chunks: {result_or['total_chunks']}, Summaries: {result_or['total_summaries']}")
            logger.info(f"  Filter: {result_or['optimizations_applied'].get('filter_expression')}")
            
            logger.info(f"\nAND Logic Results:")
            logger.info(f"  Chunks: {result_and['total_chunks']}, Summaries: {result_and['total_summaries']}")
            logger.info(f"  Filter: {result_and['optimizations_applied'].get('filter_expression')}")
            
            results.append(result_summary)
            
        except Exception as e:
            logger.error(f"Error testing {test_name}: {e}", exc_info=True)
            results.append({
                "test_name": test_name,
                "query": query,
                "error": str(e)
            })
    
    save_json_output(results, f"full_retrieval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    return results


def run_all_tests():
    """Run all test suites."""
    logger.info("\n" + "="*80)
    logger.info("DYNAMIC RETRIEVAL COMPREHENSIVE TEST SUITE")
    logger.info("="*80)
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"Total test queries: {len(TEST_QUERIES)}")
    
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(TEST_QUERIES),
        "tests": {}
    }
    
    try:
        all_results['tests']['query_analysis'] = test_query_analysis()
    except Exception as e:
        logger.error(f"Query analysis test failed: {e}", exc_info=True)
        all_results['tests']['query_analysis'] = {"error": str(e)}
    
    try:
        all_results['tests']['adaptive_limits'] = test_adaptive_limits()
    except Exception as e:
        logger.error(f"Adaptive limits test failed: {e}", exc_info=True)
        all_results['tests']['adaptive_limits'] = {"error": str(e)}
    
    try:
        all_results['tests']['metadata_filters'] = test_metadata_filters()
    except Exception as e:
        logger.error(f"Metadata filters test failed: {e}", exc_info=True)
        all_results['tests']['metadata_filters'] = {"error": str(e)}
    
    try:
        all_results['tests']['search_strategies'] = test_search_strategies()
    except Exception as e:
        logger.error(f"Search strategies test failed: {e}", exc_info=True)
        all_results['tests']['search_strategies'] = {"error": str(e)}
    
    try:
        all_results['tests']['full_retrieval'] = test_full_retrieval_sample()
    except Exception as e:
        logger.error(f"Full retrieval test failed: {e}", exc_info=True)
        all_results['tests']['full_retrieval'] = {"error": str(e)}
    
    # Save comprehensive report
    save_json_output(all_results, f"comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    logger.info("\n" + "="*80)
    logger.info("ALL TESTS COMPLETED")
    logger.info("="*80)
    logger.info(f"Results saved to: test_outputs/")


if __name__ == "__main__":
    run_all_tests()
