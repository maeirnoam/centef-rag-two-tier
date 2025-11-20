"""
End-to-End API Integration Test for Optimized RAG System

Tests the /chat endpoint with various optimization configurations.
"""

import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Configuration
API_BASE_URL = "http://localhost:8000"  # Adjust for your deployment
TEST_TOKEN = "test-token-placeholder"  # Replace with actual token or generate one

# Test queries covering different scenarios
TEST_QUERIES = [
    {
        "name": "brief_query",
        "query": "What is CENTEF?",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_query_expansion": False,
            "enable_reranking": True,
            "enable_deduplication": True,
            "filter_logic": "OR"
        }
    },
    {
        "name": "tweet_request",
        "query": "Write a tweet about Pope Francis's latest encyclical on social justice",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_query_expansion": True,
            "enable_reranking": True,
            "enable_deduplication": True,
            "filter_logic": "OR",
            "metadata_filters": {
                "organization": ["Vatican", "Catholic Church"]
            }
        }
    },
    {
        "name": "blog_post_request",
        "query": "Write a blog post about Catholic social teaching and economic justice",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_query_expansion": True,
            "enable_reranking": True,
            "enable_deduplication": True,
            "filter_logic": "OR"
        }
    },
    {
        "name": "protocol_request",
        "query": "Create a step-by-step protocol for implementing Catholic social teaching in a parish",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_query_expansion": False,
            "enable_reranking": True,
            "enable_deduplication": True,
            "filter_logic": "AND"
        }
    },
    {
        "name": "comprehensive_analysis",
        "query": "Provide a comprehensive analysis of the relationship between Catholic social teaching, labor rights, and economic policy across different papal encyclicals",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_query_expansion": True,
            "enable_reranking": True,
            "enable_deduplication": True,
            "filter_logic": "OR"
        }
    },
    {
        "name": "organization_filter_or",
        "query": "What are the main teachings about social justice?",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_query_expansion": False,
            "enable_reranking": True,
            "enable_deduplication": True,
            "filter_logic": "OR",
            "metadata_filters": {
                "organization": ["Vatican", "US Conference of Catholic Bishops"]
            }
        }
    },
    {
        "name": "organization_filter_and",
        "query": "What are the main teachings about social justice?",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_query_expansion": False,
            "enable_reranking": True,
            "enable_deduplication": True,
            "filter_logic": "AND",
            "metadata_filters": {
                "organization": ["Vatican"],
                "tags": ["social justice"]
            }
        }
    },
    {
        "name": "standard_non_optimized",
        "query": "What is the Catholic Church's position on labor unions?",
        "config": {
            "use_optimizations": False,
            "max_chunks": 8,
            "max_summaries": 3,
            "temperature": 0.2
        }
    },
    {
        "name": "comparison_optimized_vs_standard",
        "query": "Explain the concept of the common good in Catholic social teaching",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_query_expansion": True,
            "enable_reranking": True,
            "enable_deduplication": True,
            "filter_logic": "OR"
        }
    }
]


class APIIntegrationTester:
    """Test harness for end-to-end API integration testing."""
    
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.auth_token = auth_token
        self.output_dir = Path("test_outputs/api_integration")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
        
    def test_chat_endpoint(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test the /chat endpoint with a specific configuration.
        
        Args:
            test_case: Test case with name, query, and config
            
        Returns:
            Test result with response and metadata
        """
        print(f"\n{'='*80}")
        print(f"TEST: {test_case['name']}")
        print(f"{'='*80}")
        print(f"Query: {test_case['query']}")
        print(f"Config: {json.dumps(test_case['config'], indent=2)}")
        
        # Prepare request
        request_data = {
            "query": test_case['query'],
            **test_case['config']
        }
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        # Make API call
        try:
            start_time = datetime.now()
            response = requests.post(
                f"{self.base_url}/chat",
                json=request_data,
                headers=headers,
                timeout=120
            )
            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds()
            
            # Parse response
            if response.status_code == 200:
                response_data = response.json()
                
                # Extract key metrics
                result = {
                    "test_name": test_case['name'],
                    "query": test_case['query'],
                    "config": test_case['config'],
                    "success": True,
                    "latency_seconds": latency,
                    "status_code": response.status_code,
                    "message_id": response_data.get('message_id'),
                    "session_id": response_data.get('session_id'),
                    "answer_length": len(response_data.get('answer', '')),
                    "num_sources": len(response_data.get('sources', [])),
                    "num_citations": len(response_data.get('explicit_citations', [])),
                    "model_used": response_data.get('model_used'),
                    "optimization_metadata": response_data.get('optimization_metadata'),
                    "answer_preview": response_data.get('answer', '')[:200] + "...",
                    "full_response": response_data
                }
                
                # Print summary
                print(f"\n✓ SUCCESS")
                print(f"Latency: {latency:.2f}s")
                print(f"Answer length: {result['answer_length']} chars")
                print(f"Sources: {result['num_sources']}")
                print(f"Citations: {result['num_citations']}")
                print(f"Model: {result['model_used']}")
                
                if result['optimization_metadata']:
                    print(f"\nOptimization Metadata:")
                    print(json.dumps(result['optimization_metadata'], indent=2))
                
                print(f"\nAnswer Preview:")
                print(result['answer_preview'])
                
                return result
                
            else:
                # Error response
                result = {
                    "test_name": test_case['name'],
                    "query": test_case['query'],
                    "config": test_case['config'],
                    "success": False,
                    "latency_seconds": latency,
                    "status_code": response.status_code,
                    "error": response.text
                }
                
                print(f"\n✗ FAILED")
                print(f"Status code: {response.status_code}")
                print(f"Error: {response.text}")
                
                return result
                
        except Exception as e:
            result = {
                "test_name": test_case['name'],
                "query": test_case['query'],
                "config": test_case['config'],
                "success": False,
                "error": str(e)
            }
            
            print(f"\n✗ EXCEPTION")
            print(f"Error: {str(e)}")
            
            return result
    
    def run_all_tests(self):
        """Run all test cases and save results."""
        print(f"\n{'#'*80}")
        print(f"# API INTEGRATION TEST SUITE")
        print(f"# Testing endpoint: {self.base_url}/chat")
        print(f"# Total tests: {len(TEST_QUERIES)}")
        print(f"{'#'*80}")
        
        for test_case in TEST_QUERIES:
            result = self.test_chat_endpoint(test_case)
            self.results.append(result)
            
            # Save individual result
            result_file = self.output_dir / f"{test_case['name']}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"Saved result to: {result_file}")
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate a summary report of all tests."""
        print(f"\n{'#'*80}")
        print(f"# TEST SUMMARY REPORT")
        print(f"{'#'*80}")
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.get('success'))
        failed_tests = total_tests - successful_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(successful_tests/total_tests*100):.1f}%")
        
        # Performance statistics
        successful_results = [r for r in self.results if r.get('success')]
        if successful_results:
            latencies = [r['latency_seconds'] for r in successful_results]
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            print(f"\nPerformance:")
            print(f"Average latency: {avg_latency:.2f}s")
            print(f"Min latency: {min_latency:.2f}s")
            print(f"Max latency: {max_latency:.2f}s")
        
        # Optimization statistics
        optimized_tests = [r for r in successful_results if r.get('config', {}).get('use_optimizations')]
        standard_tests = [r for r in successful_results if not r.get('config', {}).get('use_optimizations')]
        
        print(f"\nOptimization Usage:")
        print(f"Optimized tests: {len(optimized_tests)}")
        print(f"Standard tests: {len(standard_tests)}")
        
        if optimized_tests:
            avg_optimized_latency = sum(r['latency_seconds'] for r in optimized_tests) / len(optimized_tests)
            print(f"Avg latency (optimized): {avg_optimized_latency:.2f}s")
        
        if standard_tests:
            avg_standard_latency = sum(r['latency_seconds'] for r in standard_tests) / len(standard_tests)
            print(f"Avg latency (standard): {avg_standard_latency:.2f}s")
        
        # Format detection statistics
        format_types = {}
        for result in successful_results:
            if result.get('optimization_metadata', {}).get('format_detection'):
                fmt = result['optimization_metadata']['format_detection'].get('format_type', 'unknown')
                format_types[fmt] = format_types.get(fmt, 0) + 1
        
        if format_types:
            print(f"\nFormat Detection:")
            for fmt, count in format_types.items():
                print(f"  {fmt}: {count}")
        
        # Save summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "successful": successful_tests,
            "failed": failed_tests,
            "success_rate": successful_tests/total_tests*100,
            "performance": {
                "avg_latency": avg_latency if successful_results else None,
                "min_latency": min_latency if successful_results else None,
                "max_latency": max_latency if successful_results else None
            },
            "optimization_stats": {
                "optimized_tests": len(optimized_tests),
                "standard_tests": len(standard_tests),
                "avg_optimized_latency": avg_optimized_latency if optimized_tests else None,
                "avg_standard_latency": avg_standard_latency if standard_tests else None
            },
            "format_types": format_types,
            "results": self.results
        }
        
        summary_file = self.output_dir / "summary_report.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\nSaved summary report to: {summary_file}")
        print(f"\n{'#'*80}")


def main():
    """Main test execution."""
    print("API Integration Test Suite")
    print("=" * 80)
    
    # Check if token is set
    if TEST_TOKEN == "test-token-placeholder":
        print("\n⚠ WARNING: TEST_TOKEN is not set!")
        print("Please update TEST_TOKEN in this script with a valid authentication token.")
        print("\nYou can generate a test token using:")
        print("  python generate_test_token.py")
        print("\nOr set it manually in test_api_integration.py")
        return
    
    # Initialize tester
    tester = APIIntegrationTester(API_BASE_URL, TEST_TOKEN)
    
    # Run all tests
    tester.run_all_tests()
    
    print("\n✓ All tests completed!")
    print(f"Results saved to: {tester.output_dir}")


if __name__ == "__main__":
    main()
