"""
Live API Test - Optimizations with Vertex AI Search

Tests the optimized /chat endpoint with actual Vertex AI Search retrieval.
"""

import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8001"  # Updated to port 8001
TEST_TOKEN = None  # Will try to load from environment or generate

# Test queries optimized for your CENTEF content
TEST_QUERIES = [
    {
        "name": "simple_factual",
        "query": "What is CENTEF?",
        "config": {
            "use_optimizations": False  # Baseline
        }
    },
    {
        "name": "simple_factual_optimized",
        "query": "What is CENTEF?",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_reranking": True
        }
    },
    {
        "name": "exploratory_standard",
        "query": "Explain Catholic social teaching on economic justice",
        "config": {
            "use_optimizations": False,
            "max_chunks": 8,
            "max_summaries": 3
        }
    },
    {
        "name": "exploratory_optimized",
        "query": "Explain Catholic social teaching on economic justice",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_query_expansion": True,
            "enable_reranking": True,
            "enable_deduplication": True
        }
    },
    {
        "name": "tweet_format",
        "query": "Write a tweet about Pope Francis's encyclical on care for creation",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_reranking": True
        }
    },
    {
        "name": "comprehensive_analysis",
        "query": "Provide a comprehensive analysis of the Catholic Church's teaching on labor rights, including key encyclicals and their historical context",
        "config": {
            "use_optimizations": True,
            "enable_adaptive_limits": True,
            "enable_query_expansion": True,
            "enable_reranking": True,
            "enable_deduplication": True
        }
    }
]


class LiveAPITester:
    """Test optimizations with live API and Vertex AI Search."""
    
    def __init__(self, base_url: str, auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.output_dir = Path("test_outputs/live_api")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
        
    def get_auth_token(self) -> str:
        """Get authentication token."""
        if self.auth_token:
            return self.auth_token
            
        # Try to generate a test token
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from generate_test_token import generate_token
            
            token_data = generate_token(
                user_id="test_user",
                email="test@example.com",
                username="Test User"
            )
            return token_data['access_token']
        except Exception as e:
            print(f"⚠ Could not generate token: {e}")
            print("Please set TEST_TOKEN or ensure API authentication is configured")
            return None
    
    def test_chat(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single chat request."""
        print(f"\n{'='*80}")
        print(f"TEST: {test_case['name']}")
        print(f"{'='*80}")
        print(f"Query: {test_case['query']}")
        print(f"Config: {json.dumps(test_case['config'], indent=2)}")
        
        # Get auth token
        if not self.auth_token:
            self.auth_token = self.get_auth_token()
            if not self.auth_token:
                return {
                    "test_name": test_case['name'],
                    "success": False,
                    "error": "No authentication token available"
                }
        
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
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Extract metrics
                result = {
                    "test_name": test_case['name'],
                    "query": test_case['query'],
                    "config": test_case['config'],
                    "success": True,
                    "latency_seconds": latency,
                    "answer_length": len(response_data.get('answer', '')),
                    "num_sources": len(response_data.get('sources', [])),
                    "num_citations": len(response_data.get('explicit_citations', [])),
                    "model_used": response_data.get('model_used'),
                    "optimization_metadata": response_data.get('optimization_metadata'),
                    "answer": response_data.get('answer'),
                    "sources": response_data.get('sources', []),
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
                    print(f"\n📊 Optimization Metadata:")
                    opt_meta = result['optimization_metadata']
                    
                    if 'query_analysis' in opt_meta:
                        qa = opt_meta['query_analysis']
                        print(f"  Query Type: {qa.get('query_type')}")
                        print(f"  Complexity: {qa.get('complexity')}")
                        print(f"  Scope: {qa.get('scope')}")
                    
                    if 'adaptive_limits' in opt_meta:
                        limits = opt_meta['adaptive_limits']
                        print(f"  Adaptive Limits: {limits.get('max_chunks')} chunks, {limits.get('max_summaries')} summaries")
                    
                    if 'format_detection' in opt_meta:
                        fmt = opt_meta['format_detection']
                        print(f"  Detected Format: {fmt.get('format_type')}")
                        print(f"  Temperature: {fmt.get('temperature')}")
                        print(f"  Max Tokens: {fmt.get('max_tokens')}")
                    
                    if 'search_optimizations' in opt_meta:
                        search_opt = opt_meta['search_optimizations']
                        print(f"  Search Optimizations:")
                        for key, value in search_opt.items():
                            print(f"    {key}: {value}")
                
                print(f"\n📝 Answer Preview:")
                print(response_data.get('answer', '')[:300] + "...")
                
                if result['sources']:
                    print(f"\n📚 Top Sources:")
                    for i, source in enumerate(result['sources'][:3], 1):
                        print(f"  {i}. {source.get('title', 'No title')}")
                
                return result
                
            else:
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
                print(f"Status: {response.status_code}")
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
        """Run all test cases."""
        print(f"\n{'#'*80}")
        print(f"# LIVE API OPTIMIZATION TESTS")
        print(f"# Endpoint: {self.base_url}/chat")
        print(f"# With Vertex AI Search retrieval")
        print(f"# Total tests: {len(TEST_QUERIES)}")
        print(f"{'#'*80}")
        
        for test_case in TEST_QUERIES:
            result = self.test_chat(test_case)
            self.results.append(result)
            
            # Save individual result
            result_file = self.output_dir / f"{test_case['name']}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Saved to: {result_file}")
        
        # Generate comparison report
        self.generate_comparison_report()
    
    def generate_comparison_report(self):
        """Generate comparison between standard and optimized results."""
        print(f"\n{'#'*80}")
        print(f"# COMPARISON REPORT")
        print(f"{'#'*80}")
        
        successful_results = [r for r in self.results if r.get('success')]
        
        if not successful_results:
            print("\n❌ No successful tests to compare")
            return
        
        # Overall statistics
        total_tests = len(self.results)
        successful = len(successful_results)
        
        print(f"\nOverall:")
        print(f"  Total: {total_tests}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {total_tests - successful}")
        print(f"  Success Rate: {(successful/total_tests*100):.1f}%")
        
        # Group by optimization status
        standard_tests = [r for r in successful_results if not r.get('config', {}).get('use_optimizations')]
        optimized_tests = [r for r in successful_results if r.get('config', {}).get('use_optimizations')]
        
        print(f"\nStandard vs Optimized:")
        print(f"  Standard tests: {len(standard_tests)}")
        print(f"  Optimized tests: {len(optimized_tests)}")
        
        if standard_tests:
            avg_std_latency = sum(r['latency_seconds'] for r in standard_tests) / len(standard_tests)
            avg_std_answer_len = sum(r['answer_length'] for r in standard_tests) / len(standard_tests)
            avg_std_sources = sum(r['num_sources'] for r in standard_tests) / len(standard_tests)
            
            print(f"\n📊 Standard Performance:")
            print(f"  Avg Latency: {avg_std_latency:.2f}s")
            print(f"  Avg Answer Length: {avg_std_answer_len:.0f} chars")
            print(f"  Avg Sources: {avg_std_sources:.1f}")
        
        if optimized_tests:
            avg_opt_latency = sum(r['latency_seconds'] for r in optimized_tests) / len(optimized_tests)
            avg_opt_answer_len = sum(r['answer_length'] for r in optimized_tests) / len(optimized_tests)
            avg_opt_sources = sum(r['num_sources'] for r in optimized_tests) / len(optimized_tests)
            
            print(f"\n📊 Optimized Performance:")
            print(f"  Avg Latency: {avg_opt_latency:.2f}s")
            print(f"  Avg Answer Length: {avg_opt_answer_len:.0f} chars")
            print(f"  Avg Sources: {avg_opt_sources:.1f}")
            
            if standard_tests:
                latency_diff = avg_opt_latency - avg_std_latency
                latency_pct = (latency_diff / avg_std_latency * 100) if avg_std_latency > 0 else 0
                
                print(f"\n📈 Comparison:")
                print(f"  Latency Difference: {latency_diff:+.2f}s ({latency_pct:+.1f}%)")
                print(f"  Answer Length Difference: {avg_opt_answer_len - avg_std_answer_len:+.0f} chars")
                print(f"  Sources Difference: {avg_opt_sources - avg_std_sources:+.1f}")
        
        # Format detection summary
        format_counts = {}
        for result in optimized_tests:
            if result.get('optimization_metadata', {}).get('format_detection'):
                fmt = result['optimization_metadata']['format_detection'].get('format_type', 'unknown')
                format_counts[fmt] = format_counts.get(fmt, 0) + 1
        
        if format_counts:
            print(f"\n🎨 Detected Formats:")
            for fmt, count in format_counts.items():
                print(f"  {fmt}: {count}")
        
        # Save summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": self.base_url,
            "total_tests": total_tests,
            "successful": successful,
            "failed": total_tests - successful,
            "standard_tests": len(standard_tests),
            "optimized_tests": len(optimized_tests),
            "standard_metrics": {
                "avg_latency": avg_std_latency if standard_tests else None,
                "avg_answer_length": avg_std_answer_len if standard_tests else None,
                "avg_sources": avg_std_sources if standard_tests else None
            } if standard_tests else None,
            "optimized_metrics": {
                "avg_latency": avg_opt_latency if optimized_tests else None,
                "avg_answer_length": avg_opt_answer_len if optimized_tests else None,
                "avg_sources": avg_opt_sources if optimized_tests else None
            } if optimized_tests else None,
            "format_counts": format_counts,
            "results": self.results
        }
        
        summary_file = self.output_dir / "comparison_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved summary to: {summary_file}")
        print(f"\n{'#'*80}")


def main():
    """Main execution."""
    print("Live API Optimization Tests")
    print("=" * 80)
    print("Testing /chat endpoint with Vertex AI Search")
    print()
    
    # Initialize tester
    tester = LiveAPITester(API_BASE_URL)
    
    # Run tests
    tester.run_all_tests()
    
    print("\n✓ All tests completed!")
    print(f"Results saved to: {tester.output_dir}")
    print("\nReview the comparison_summary.json for detailed metrics.")


if __name__ == "__main__":
    main()
