"""
Local API Integration Test (No Authentication)

Tests the optimization integration by directly importing and calling functions.
This avoids authentication requirements and allows quick validation of the integration.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add apps directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the integrated modules
from apps.agent_api.retriever_optimized import (
    analyze_query_characteristics,
    adaptive_result_limits,
    build_metadata_filter,
    select_search_strategy
)
from apps.agent_api.synthesizer_optimized import detect_output_format

# Test queries
TEST_QUERIES = [
    {
        "name": "brief_factual",
        "query": "What is CENTEF?",
        "expected_format": "brief_summary"
    },
    {
        "name": "tweet_request",
        "query": "Write a tweet about Pope Francis's latest encyclical",
        "expected_format": "social_media"
    },
    {
        "name": "blog_post",
        "query": "Write a blog post about Catholic social teaching",
        "expected_format": "blog_post"
    },
    {
        "name": "protocol_request",
        "query": "Create a step-by-step protocol for implementing parish programs",
        "expected_format": "protocol"
    },
    {
        "name": "comprehensive",
        "query": "Provide a comprehensive analysis of Catholic social teaching across papal encyclicals",
        "expected_format": "comprehensive_analysis"
    },
    {
        "name": "social_justice_org_filter",
        "query": "What does the Vatican say about social justice?",
        "metadata_filters": {
            "organization": ["Vatican", "Catholic Church"]
        }
    },
    {
        "name": "labor_rights_query",
        "query": "Explain Catholic teaching on labor rights and unions",
        "expected_topics": ["labor rights", "social justice"]
    }
]


class LocalIntegrationTester:
    """Test the optimization integration locally without API calls."""
    
    def __init__(self):
        self.output_dir = Path("test_outputs/local_integration")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
    
    def test_query_analysis(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test query analysis functionality."""
        print(f"\n{'='*80}")
        print(f"TEST: {test_case['name']}")
        print(f"{'='*80}")
        print(f"Query: {test_case['query']}")
        
        result = {
            "test_name": test_case['name'],
            "query": test_case['query'],
            "validations": []
        }
        
        try:
            # 1. Analyze query characteristics
            print("\n1. Query Analysis:")
            query_analysis = analyze_query_characteristics(test_case['query'])
            result['query_analysis'] = query_analysis
            
            print(f"   Type: {query_analysis['query_type']}")
            print(f"   Complexity: {query_analysis['complexity']}")
            print(f"   Scope: {query_analysis['scope']}")
            print(f"   Needs chunks: {query_analysis.get('needs_chunks', True)}")
            print(f"   Needs summaries: {query_analysis.get('needs_summaries', True)}")
            print(f"   Filter hints: {query_analysis.get('filter_hints', [])}")
            
            # Validate expected topics if provided
            if 'expected_topics' in test_case:
                found_topics = any(
                    any(topic.lower() in hint[1].lower() if isinstance(hint, tuple) else False
                        for hint in query_analysis.get('filter_hints', []))
                    for topic in test_case['expected_topics']
                )
                validation = {
                    "check": "topic_detection",
                    "expected": test_case['expected_topics'],
                    "actual": query_analysis.get('filter_hints', []),
                    "passed": found_topics
                }
                result['validations'].append(validation)
                print(f"   ✓ Topic detection: {'PASS' if found_topics else 'FAIL'}")
            
            # 2. Adaptive result limits
            print("\n2. Adaptive Result Limits:")
            max_chunks, max_summaries = adaptive_result_limits(
                test_case['query'],
                query_analysis
            )
            result['adaptive_limits'] = {
                'max_chunks': max_chunks,
                'max_summaries': max_summaries
            }
            
            print(f"   Max chunks: {max_chunks}")
            print(f"   Max summaries: {max_summaries}")
            
            # 3. Format detection
            print("\n3. Format Detection:")
            format_info = detect_output_format(test_case['query'])
            result['format_detection'] = format_info
            
            print(f"   Format type: {format_info['format_type']}")
            print(f"   Expected length: {format_info['length']}")
            print(f"   Structure: {format_info['structure']}")
            print(f"   Temperature: {format_info['temperature']}")
            print(f"   Max tokens: {format_info['max_tokens']}")
            print(f"   Style: {format_info['style']}")
            
            # Validate expected format if provided
            if 'expected_format' in test_case:
                format_match = format_info['format_type'] == test_case['expected_format']
                validation = {
                    "check": "format_detection",
                    "expected": test_case['expected_format'],
                    "actual": format_info['format_type'],
                    "passed": format_match
                }
                result['validations'].append(validation)
                print(f"   ✓ Format detection: {'PASS' if format_match else 'FAIL'}")
            
            # 4. Metadata filter building
            if 'metadata_filters' in test_case:
                print("\n4. Metadata Filter Building:")
                
                # Test OR logic
                filter_or = build_metadata_filter(
                    test_case['query'],
                    query_analysis,
                    filter_logic="OR"
                )
                result['metadata_filter_or'] = filter_or
                
                print(f"   OR filter: {filter_or}")
                
                # Test AND logic
                filter_and = build_metadata_filter(
                    test_case['query'],
                    query_analysis,
                    filter_logic="AND"
                )
                result['metadata_filter_and'] = filter_and
                
                print(f"   AND filter: {filter_and}")
            
            # 5. Search strategy selection
            print("\n5. Search Strategy Selection:")
            strategy = select_search_strategy(
                test_case['query'],
                query_analysis
            )
            result['search_strategy'] = strategy
            
            print(f"   Query expansion: {strategy.get('enable_query_expansion', False)}")
            print(f"   Reranking: {strategy.get('enable_reranking', False)}")
            print(f"   Deduplication: {strategy.get('enable_deduplication', False)}")
            
            result['success'] = True
            print(f"\n✓ TEST PASSED")
            
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            print(f"\n✗ TEST FAILED: {str(e)}")
        
        return result
    
    def run_all_tests(self):
        """Run all test cases."""
        print(f"\n{'#'*80}")
        print(f"# LOCAL INTEGRATION TEST SUITE")
        print(f"# Testing optimization modules integration")
        print(f"# Total tests: {len(TEST_QUERIES)}")
        print(f"{'#'*80}")
        
        for test_case in TEST_QUERIES:
            result = self.test_query_analysis(test_case)
            self.results.append(result)
            
            # Save individual result
            result_file = self.output_dir / f"{test_case['name']}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\nSaved result to: {result_file}")
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate summary report."""
        print(f"\n{'#'*80}")
        print(f"# TEST SUMMARY")
        print(f"{'#'*80}")
        
        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r.get('success'))
        failed = total_tests - successful
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(successful/total_tests*100):.1f}%")
        
        # Validation summary
        all_validations = []
        for result in self.results:
            all_validations.extend(result.get('validations', []))
        
        if all_validations:
            passed_validations = sum(1 for v in all_validations if v['passed'])
            total_validations = len(all_validations)
            
            print(f"\nValidations:")
            print(f"Total: {total_validations}")
            print(f"Passed: {passed_validations}")
            print(f"Failed: {total_validations - passed_validations}")
            print(f"Success Rate: {(passed_validations/total_validations*100):.1f}%")
        
        # Format detection summary
        format_types = {}
        for result in self.results:
            if result.get('format_detection'):
                fmt = result['format_detection']['format_type']
                format_types[fmt] = format_types.get(fmt, 0) + 1
        
        print(f"\nFormat Types Detected:")
        for fmt, count in format_types.items():
            print(f"  {fmt}: {count}")
        
        # Query types summary
        query_types = {}
        for result in self.results:
            if result.get('query_analysis'):
                qtype = result['query_analysis']['query_type']
                query_types[qtype] = query_types.get(qtype, 0) + 1
        
        print(f"\nQuery Types:")
        for qtype, count in query_types.items():
            print(f"  {qtype}: {count}")
        
        # Save summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "successful": successful,
            "failed": failed,
            "success_rate": successful/total_tests*100,
            "validations": {
                "total": len(all_validations),
                "passed": sum(1 for v in all_validations if v['passed']),
                "failed": sum(1 for v in all_validations if not v['passed'])
            },
            "format_types": format_types,
            "query_types": query_types,
            "results": self.results
        }
        
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved summary to: {summary_file}")
        print(f"\n{'#'*80}")


def main():
    """Main test execution."""
    print("Local Integration Test Suite")
    print("=" * 80)
    print("Testing optimization integration without API calls")
    
    tester = LocalIntegrationTester()
    tester.run_all_tests()
    
    print("\n✓ All tests completed!")
    print(f"Results saved to: {tester.output_dir}")


if __name__ == "__main__":
    main()
