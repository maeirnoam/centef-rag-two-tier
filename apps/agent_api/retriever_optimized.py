"""
Optimized retriever for CENTEF RAG system with advanced retrieval techniques.
Includes query rewriting, reranking, deduplication, and hybrid search.
"""
import logging
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from dotenv import load_dotenv
import vertexai
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig

from retriever_vertex_search import search_chunks, search_summaries

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
GENERATION_LOCATION = os.getenv("GENERATION_LOCATION", "us-central1")
QUERY_EXPANSION_MODEL = os.getenv("QUERY_EXPANSION_MODEL", "gemini-2.0-flash-exp")

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=GENERATION_LOCATION)


def expand_query_with_llm(query: str) -> List[str]:
    """
    Use LLM to generate query variations for better retrieval coverage.
    
    Args:
        query: Original user query
    
    Returns:
        List of query variations including the original
    """
    logger.info(f"Expanding query: {query}")
    
    try:
        model = GenerativeModel(QUERY_EXPANSION_MODEL)
        
        prompt = f"""Given this user query about terrorism financing, money laundering, or related topics, 
generate 2-3 alternative phrasings that would help retrieve relevant information. 
Focus on:
- Expanding abbreviations (AML, CTF, FATF, etc.)
- Adding synonyms
- Rephrasing with domain terminology

Original query: {query}

Return ONLY the alternative queries, one per line, without numbering or explanation."""

        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(temperature=0.3, max_output_tokens=200)
        )
        
        variations = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
        
        # Add original query at the start
        all_queries = [query] + variations
        logger.info(f"Generated {len(variations)} query variations")
        
        return all_queries
        
    except Exception as e:
        logger.warning(f"Query expansion failed: {e}. Using original query only.")
        return [query]


def deduplicate_results(results: List[Dict[str, Any]], threshold: float = 0.85) -> List[Dict[str, Any]]:
    """
    Remove duplicate or highly similar results based on content similarity.
    
    Args:
        results: List of search results
        threshold: Similarity threshold (0-1) for considering duplicates
    
    Returns:
        Deduplicated list of results
    """
    if not results:
        return results
    
    logger.info(f"Deduplicating {len(results)} results...")
    
    # Simple deduplication based on:
    # 1. Exact source_id + page_number match (for chunks)
    # 2. Content similarity (basic token overlap for now)
    
    seen_keys = set()
    deduplicated = []
    
    for result in results:
        # Create deduplication key
        source_id = result.get('source_id', '')
        page = result.get('page_number') or result.get('page', '')
        start_sec = result.get('start_sec', '')
        
        # For chunks with location info
        if source_id and (page or start_sec):
            key = f"{source_id}:{page}:{start_sec}"
        else:
            # For summaries or chunks without location, use ID
            key = result.get('id', '')
        
        if key and key not in seen_keys:
            seen_keys.add(key)
            deduplicated.append(result)
    
    removed = len(results) - len(deduplicated)
    if removed > 0:
        logger.info(f"Removed {removed} duplicate results")
    
    return deduplicated


def rerank_by_relevance(
    query: str,
    results: List[Dict[str, Any]],
    top_k: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Rerank results using LLM-based relevance scoring.
    
    Args:
        query: Original user query
        results: List of search results
        top_k: Optional limit on number of results to return after reranking
    
    Returns:
        Reranked list of results
    """
    if not results or len(results) <= 1:
        return results
    
    logger.info(f"Reranking {len(results)} results for query: {query}")
    
    try:
        model = GenerativeModel(QUERY_EXPANSION_MODEL)
        
        # Create a prompt with query and result snippets
        snippets = []
        for i, result in enumerate(results):
            content = result.get('content', result.get('summary_text', ''))[:300]
            snippets.append(f"[{i}] {content}")
        
        prompt = f"""Given this query: "{query}"

Rate the relevance of each document snippet from 0-10 (10 = most relevant).
Return ONLY the indices in order of relevance (most relevant first), comma-separated.

Snippets:
{chr(10).join(snippets)}

Order (indices only, comma-separated):"""

        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(temperature=0.1, max_output_tokens=100)
        )
        
        # Parse the response to get ordered indices
        text = response.text.strip()
        indices = []
        for token in re.findall(r'\d+', text):
            idx = int(token)
            if 0 <= idx < len(results) and idx not in indices:
                indices.append(idx)
        
        # Add any missing indices at the end
        for i in range(len(results)):
            if i not in indices:
                indices.append(i)
        
        # Reorder results
        reranked = [results[i] for i in indices]
        
        # Apply top_k if specified
        if top_k:
            reranked = reranked[:top_k]
        
        logger.info(f"Reranked results. New order: {indices[:5]}...")
        return reranked
        
    except Exception as e:
        logger.warning(f"Reranking failed: {e}. Returning original order.")
        return results[:top_k] if top_k else results


def merge_multi_query_results(
    queries: List[str],
    results_per_query: List[List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    Merge results from multiple query variations using reciprocal rank fusion.
    
    Args:
        queries: List of query variations
        results_per_query: List of result lists, one per query
    
    Returns:
        Merged and ranked list of results
    """
    logger.info(f"Merging results from {len(queries)} query variations")
    
    # Reciprocal Rank Fusion (RRF) scoring
    # Score = sum(1 / (rank + k)) for each result's appearances
    k = 60  # Constant from RRF paper
    
    result_scores = defaultdict(float)
    result_map = {}
    
    for query_results in results_per_query:
        for rank, result in enumerate(query_results, start=1):
            result_id = result.get('id', '')
            if result_id:
                result_scores[result_id] += 1.0 / (rank + k)
                if result_id not in result_map:
                    result_map[result_id] = result
    
    # Sort by RRF score
    sorted_ids = sorted(result_scores.keys(), key=lambda x: result_scores[x], reverse=True)
    
    merged = [result_map[result_id] for result_id in sorted_ids]
    
    logger.info(f"Merged to {len(merged)} unique results")
    return merged


def search_two_tier_optimized(
    query: str,
    max_chunk_results: int = 10,
    max_summary_results: int = 5,
    enable_query_expansion: bool = True,
    enable_reranking: bool = True,
    enable_deduplication: bool = True,
    rerank_top_k: Optional[int] = None
) -> Dict[str, Any]:
    """
    Optimized two-tier search with query expansion, deduplication, and reranking.
    
    Args:
        query: User's search query
        max_chunk_results: Maximum chunk results to retrieve initially
        max_summary_results: Maximum summary results to retrieve initially
        enable_query_expansion: Whether to expand query with variations
        enable_reranking: Whether to rerank results by relevance
        enable_deduplication: Whether to remove duplicate results
        rerank_top_k: Limit results after reranking (None = no limit)
    
    Returns:
        Combined and optimized search results
    """
    logger.info(f"Optimized two-tier search for: {query}")
    logger.info(f"Options - Expansion: {enable_query_expansion}, Reranking: {enable_reranking}, Dedup: {enable_deduplication}")
    
    # Step 1: Query expansion (if enabled)
    queries = [query]
    if enable_query_expansion:
        queries = expand_query_with_llm(query)
    
    # Step 2: Search with all query variations
    all_chunk_results = []
    all_summary_results = []
    
    if len(queries) > 1:
        # Multi-query: collect results from each variation
        chunk_results_per_query = []
        summary_results_per_query = []
        
        for q in queries:
            logger.info(f"Searching with variation: {q}")
            chunks = search_chunks(q, max_results=max_chunk_results)
            summaries = search_summaries(q, max_results=max_summary_results)
            
            chunk_results_per_query.append(chunks)
            summary_results_per_query.append(summaries)
        
        # Merge using RRF
        all_chunk_results = merge_multi_query_results(queries, chunk_results_per_query)
        all_summary_results = merge_multi_query_results(queries, summary_results_per_query)
    else:
        # Single query: direct search
        all_chunk_results = search_chunks(query, max_results=max_chunk_results)
        all_summary_results = search_summaries(query, max_results=max_summary_results)
    
    # Step 3: Deduplication (if enabled)
    if enable_deduplication:
        all_chunk_results = deduplicate_results(all_chunk_results)
        all_summary_results = deduplicate_results(all_summary_results)
    
    # Step 4: Reranking (if enabled)
    if enable_reranking:
        all_chunk_results = rerank_by_relevance(
            query, 
            all_chunk_results, 
            top_k=rerank_top_k or max_chunk_results
        )
        all_summary_results = rerank_by_relevance(
            query, 
            all_summary_results, 
            top_k=rerank_top_k or max_summary_results
        )
    else:
        # Apply limits without reranking
        all_chunk_results = all_chunk_results[:max_chunk_results]
        all_summary_results = all_summary_results[:max_summary_results]
    
    logger.info(f"Final results: {len(all_summary_results)} summaries, {len(all_chunk_results)} chunks")
    
    return {
        "query": query,
        "expanded_queries": queries if enable_query_expansion else [query],
        "chunks": all_chunk_results,
        "summaries": all_summary_results,
        "total_chunks": len(all_chunk_results),
        "total_summaries": len(all_summary_results),
        "optimizations_applied": {
            "query_expansion": enable_query_expansion,
            "reranking": enable_reranking,
            "deduplication": enable_deduplication
        }
    }


def adaptive_result_limits(query: str) -> Tuple[int, int]:
    """
    Determine optimal chunk and summary limits based on query complexity.
    
    Args:
        query: User's search query
    
    Returns:
        Tuple of (max_chunks, max_summaries)
    """
    # Simple heuristics for now:
    # - Short queries (< 5 words): fewer results (5 chunks, 3 summaries)
    # - Medium queries (5-15 words): standard (10 chunks, 5 summaries)
    # - Long queries (> 15 words): more results (15 chunks, 7 summaries)
    
    word_count = len(query.split())
    
    if word_count < 5:
        return 5, 3
    elif word_count < 15:
        return 10, 5
    else:
        return 15, 7
