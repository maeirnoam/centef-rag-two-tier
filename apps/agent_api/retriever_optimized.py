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

from apps.agent_api.retriever_vertex_search import search_chunks, search_summaries

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
    max_chunk_results: Optional[int] = None,
    max_summary_results: Optional[int] = None,
    enable_query_expansion: Optional[bool] = None,
    enable_reranking: Optional[bool] = None,
    enable_deduplication: Optional[bool] = None,
    rerank_top_k: Optional[int] = None,
    use_adaptive_strategy: bool = True,
    filter_logic: str = "OR"
) -> Dict[str, Any]:
    """
    Optimized two-tier search with dynamic strategy selection.
    Now adapts result counts, search methods, and filters based on query analysis.
    
    Args:
        query: User's search query
        max_chunk_results: Maximum chunk results (None = auto-determine)
        max_summary_results: Maximum summary results (None = auto-determine)
        enable_query_expansion: Whether to expand query (None = auto-determine)
        enable_reranking: Whether to rerank results (None = auto-determine)
        enable_deduplication: Whether to remove duplicates (None = auto-determine)
        rerank_top_k: Limit results after reranking (None = no limit)
        use_adaptive_strategy: Whether to use query analysis for dynamic decisions
        filter_logic: "OR" (match any filter) or "AND" (match all filters)
    
    Returns:
        Combined and optimized search results with metadata
    """
    logger.info(f"Optimized two-tier search for: {query}")
    
    # Step 1: Analyze query characteristics (if using adaptive strategy)
    query_characteristics = None
    if use_adaptive_strategy:
        query_characteristics = analyze_query_characteristics(query)
        logger.info(f"Query analysis: type={query_characteristics['query_type']}, "
                   f"complexity={query_characteristics['complexity']}, "
                   f"scope={query_characteristics['scope']}")
    
    # Step 2: Determine search strategy
    if use_adaptive_strategy:
        strategy = select_search_strategy(query, query_characteristics)
        
        # Override with explicit parameters if provided
        if enable_query_expansion is None:
            enable_query_expansion = strategy['enable_query_expansion']
        if enable_reranking is None:
            enable_reranking = strategy['enable_reranking']
        if enable_deduplication is None:
            enable_deduplication = strategy['enable_deduplication']
        
        # Determine which searches to run
        search_chunks_enabled = strategy['search_chunks']
        search_summaries_enabled = strategy['search_summaries']
    else:
        # Default: all optimizations enabled, both searches
        if enable_query_expansion is None:
            enable_query_expansion = True
        if enable_reranking is None:
            enable_reranking = True
        if enable_deduplication is None:
            enable_deduplication = True
        search_chunks_enabled = True
        search_summaries_enabled = True
    
    # Step 3: Determine result limits
    if max_chunk_results is None or max_summary_results is None:
        auto_chunks, auto_summaries = adaptive_result_limits(query, query_characteristics)
        if max_chunk_results is None:
            max_chunk_results = auto_chunks
        if max_summary_results is None:
            max_summary_results = auto_summaries
    
    logger.info(f"Strategy - Expansion: {enable_query_expansion}, Reranking: {enable_reranking}, "
               f"Dedup: {enable_deduplication}, Chunks: {search_chunks_enabled}, Summaries: {search_summaries_enabled}")
    logger.info(f"Result limits - Chunks: {max_chunk_results}, Summaries: {max_summary_results}")
    
    # Step 4: Build metadata filter (only if explicitly requested, not automatic)
    filter_expression = None
    # Disable automatic filtering - only use explicit user-provided filters
    # if use_adaptive_strategy and query_characteristics:
    #     filter_expression = build_metadata_filter(query, query_characteristics, filter_logic=filter_logic)
    
    # Step 5: Query expansion (if enabled)
    queries = [query]
    if enable_query_expansion:
        queries = expand_query_with_llm(query)
    
    # Step 6: Execute searches
    all_chunk_results = []
    all_summary_results = []
    
    if len(queries) > 1:
        # Multi-query: collect results from each variation
        chunk_results_per_query = []
        summary_results_per_query = []
        
        for q in queries:
            logger.info(f"Searching with variation: {q}")
            
            if search_chunks_enabled:
                chunks = search_chunks(q, max_results=max_chunk_results, filter_expression=filter_expression)
                chunk_results_per_query.append(chunks)
            
            if search_summaries_enabled:
                summaries = search_summaries(q, max_results=max_summary_results, filter_expression=filter_expression)
                summary_results_per_query.append(summaries)
        
        # Merge using RRF
        if chunk_results_per_query:
            all_chunk_results = merge_multi_query_results(queries, chunk_results_per_query)
        if summary_results_per_query:
            all_summary_results = merge_multi_query_results(queries, summary_results_per_query)
    else:
        # Single query: direct search
        if search_chunks_enabled:
            all_chunk_results = search_chunks(query, max_results=max_chunk_results, filter_expression=filter_expression)
        if search_summaries_enabled:
            all_summary_results = search_summaries(query, max_results=max_summary_results, filter_expression=filter_expression)
    
    # Step 7: Deduplication (if enabled)
    if enable_deduplication:
        if all_chunk_results:
            all_chunk_results = deduplicate_results(all_chunk_results)
        if all_summary_results:
            all_summary_results = deduplicate_results(all_summary_results)
    
    # Step 8: Reranking (if enabled)
    if enable_reranking:
        if all_chunk_results:
            all_chunk_results = rerank_by_relevance(
                query, 
                all_chunk_results, 
                top_k=rerank_top_k or max_chunk_results
            )
        if all_summary_results:
            all_summary_results = rerank_by_relevance(
                query, 
                all_summary_results, 
                top_k=rerank_top_k or max_summary_results
            )
    else:
        # Apply limits without reranking
        if all_chunk_results:
            all_chunk_results = all_chunk_results[:max_chunk_results]
        if all_summary_results:
            all_summary_results = all_summary_results[:max_summary_results]
    
    logger.info(f"Final results: {len(all_summary_results)} summaries, {len(all_chunk_results)} chunks")
    
    result = {
        "query": query,
        "expanded_queries": queries if enable_query_expansion else [query],
        "chunks": all_chunk_results,
        "summaries": all_summary_results,
        "total_chunks": len(all_chunk_results),
        "total_summaries": len(all_summary_results),
        "optimizations_applied": {
            "query_expansion": enable_query_expansion,
            "reranking": enable_reranking,
            "deduplication": enable_deduplication,
            "adaptive_strategy": use_adaptive_strategy,
            "metadata_filter": filter_expression is not None,
            "filter_logic": filter_logic if filter_expression else None,
            "filter_expression": filter_expression
        }
    }
    
    # Add query characteristics if analyzed
    if query_characteristics:
        result["query_characteristics"] = query_characteristics
    
    return result


def analyze_query_characteristics(query: str) -> Dict[str, Any]:
    """
    Analyze query to determine retrieval strategy.
    
    Returns:
        Dict with query characteristics:
        - query_type: 'factual', 'exploratory', 'comparative', 'procedural', 'analytical'
        - complexity: 'simple', 'moderate', 'complex'
        - scope: 'narrow', 'medium', 'broad'
        - needs_chunks: bool (whether detailed chunks are needed)
        - needs_summaries: bool (whether document summaries are needed)
        - filter_hints: list of metadata filter suggestions
    """
    query_lower = query.lower()
    word_count = len(query.split())
    
    characteristics = {
        'query_type': 'factual',
        'complexity': 'moderate',
        'scope': 'medium',
        'needs_chunks': True,
        'needs_summaries': True,
        'filter_hints': []
    }
    
    # Determine query type
    if any(kw in query_lower for kw in ['what is', 'define', 'definition', 'meaning of']):
        characteristics['query_type'] = 'factual'
        characteristics['needs_chunks'] = True
        characteristics['needs_summaries'] = True  # Search both - data could be in either
    
    elif any(kw in query_lower for kw in ['compare', 'difference', 'versus', 'vs', 'contrast']):
        characteristics['query_type'] = 'comparative'
        characteristics['needs_chunks'] = True
        characteristics['needs_summaries'] = True  # Need overview + details
    
    elif any(kw in query_lower for kw in ['how to', 'steps', 'process', 'procedure', 'protocol']):
        characteristics['query_type'] = 'procedural'
        characteristics['needs_chunks'] = True
        characteristics['needs_summaries'] = True  # Search both for procedures
    
    elif any(kw in query_lower for kw in ['analyze', 'analysis', 'evaluate', 'assess', 'examine']):
        characteristics['query_type'] = 'analytical'
        characteristics['needs_chunks'] = True
        characteristics['needs_summaries'] = True  # Analysis needs both overview and evidence
    
    elif any(kw in query_lower for kw in ['overview', 'about', 'tell me about', 'explain', 'describe']):
        characteristics['query_type'] = 'exploratory'
        characteristics['needs_chunks'] = True
        characteristics['needs_summaries'] = True  # Exploration benefits from both
    
    # Determine complexity
    if word_count < 5:
        characteristics['complexity'] = 'simple'
    elif word_count > 15 or any(kw in query_lower for kw in ['comprehensive', 'detailed', 'thorough', 'in-depth']):
        characteristics['complexity'] = 'complex'
    else:
        characteristics['complexity'] = 'moderate'
    
    # Determine scope
    if any(kw in query_lower for kw in ['specific', 'particular', 'exact', 'precise']):
        characteristics['scope'] = 'narrow'
    elif any(kw in query_lower for kw in ['all', 'every', 'comprehensive', 'complete', 'entire', 'global']):
        characteristics['scope'] = 'broad'
    else:
        characteristics['scope'] = 'medium'
    
    # Extract filter hints from query
    # Look for organization mentions (case-insensitive partial match)
    orgs = {
        'fatf': 'FATF',
        'financial action task force': 'FATF',
        'fiu': 'FIU',
        'financial intelligence unit': 'FIU',
        'un': 'UN',
        'united nations': 'UN',
        'imf': 'IMF',
        'international monetary fund': 'IMF',
        'world bank': 'World Bank',
        'egmont': 'Egmont Group',
        'egmont group': 'Egmont Group',
        'wolfsberg': 'Wolfsberg Group',
        'wolfsberg group': 'Wolfsberg Group',
        'basel': 'Basel Committee',
        'basel committee': 'Basel Committee',
        'oecd': 'OECD'
    }
    
    for org_key, org_value in orgs.items():
        if org_key in query_lower:
            characteristics['filter_hints'].append(('organization', org_value))
            break  # Take first match to avoid duplicates
    
    # Look for topic/tag hints based on common AML/CTF terminology
    # These should match the tags generated by summarize_chunks.py
    topic_keywords = {
        # Virtual assets / Crypto
        ('crypto', 'virtual asset', 'vasp', 'cryptocurrency', 'bitcoin', 'digital currency'): 'virtual_assets',
        # Sanctions
        ('sanction', 'sanctions', 'sanctioned', 'embargo'): 'sanctions',
        # Beneficial ownership
        ('beneficial ownership', 'beneficial owner', 'bo', 'ubo', 'ultimate beneficial'): 'beneficial_ownership',
        # Customer due diligence
        ('cdd', 'customer due diligence', 'kyc', 'know your customer'): 'customer_due_diligence',
        # Enhanced due diligence
        ('edd', 'enhanced due diligence'): 'enhanced_due_diligence',
        # PEPs
        ('pep', 'peps', 'politically exposed', 'politically exposed person'): 'peps',
        # Risk assessment
        ('risk assessment', 'risk based approach', 'rba', 'risk management'): 'risk_assessment',
        # Transaction monitoring
        ('transaction monitoring', 'suspicious transaction', 'unusual transaction'): 'transaction_monitoring',
        # SAR/STR
        ('sar', 'str', 'suspicious activity report', 'suspicious transaction report'): 'suspicious_activity_reporting',
        # Wire transfers
        ('wire transfer', 'funds transfer', 'remittance'): 'wire_transfers',
        # Trade-based money laundering
        ('tbml', 'trade based', 'trade finance'): 'trade_based_money_laundering',
        # Correspondent banking
        ('correspondent bank', 'correspondent banking', 'nostro', 'vostro'): 'correspondent_banking',
        # DNFBPs
        ('dnfbp', 'designated non-financial', 'casino', 'real estate', 'lawyer', 'accountant'): 'dnfbps',
        # NPOs
        ('npo', 'non-profit', 'nonprofit', 'charity', 'charitable'): 'non_profit_organizations',
        # Terrorism financing
        ('terrorism financing', 'terrorist financing', 'ctf', 'cft', 'counter terrorism'): 'terrorism_financing',
        # Money laundering
        ('money laundering', 'aml', 'anti money laundering', 'laundering'): 'money_laundering',
        # Proliferation financing
        ('proliferation financing', 'wmd', 'weapons of mass destruction'): 'proliferation_financing'
    }
    
    for keywords, tag_value in topic_keywords.items():
        if any(kw in query_lower for kw in keywords):
            characteristics['filter_hints'].append(('topic', tag_value))
            # Only add first matching topic to avoid over-filtering
            break
    
    return characteristics


def adaptive_result_limits(query: str, query_characteristics: Optional[Dict[str, Any]] = None) -> Tuple[int, int]:
    """
    Determine optimal chunk and summary limits based on query characteristics.
    
    Args:
        query: User's search query
        query_characteristics: Optional pre-analyzed characteristics
    
    Returns:
        Tuple of (max_chunks, max_summaries)
    """
    if query_characteristics is None:
        query_characteristics = analyze_query_characteristics(query)
    
    query_type = query_characteristics['query_type']
    complexity = query_characteristics['complexity']
    scope = query_characteristics['scope']
    
    # Base limits
    base_chunks = 10
    base_summaries = 5
    
    # Adjust by query type
    if query_type == 'factual':
        # Factual: need fewer but precise chunks
        base_chunks = 5
        base_summaries = 2
    elif query_type == 'procedural':
        # Procedural: need more chunks (step-by-step), fewer summaries
        base_chunks = 12
        base_summaries = 3
    elif query_type == 'comparative':
        # Comparative: need balanced sources for comparison
        base_chunks = 8
        base_summaries = 6
    elif query_type == 'analytical':
        # Analytical: need comprehensive evidence
        base_chunks = 15
        base_summaries = 7
    elif query_type == 'exploratory':
        # Exploratory: balanced approach
        base_chunks = 10
        base_summaries = 5
    
    # Adjust by complexity
    if complexity == 'simple':
        base_chunks = max(3, int(base_chunks * 0.6))
        base_summaries = max(2, int(base_summaries * 0.6))
    elif complexity == 'complex':
        base_chunks = int(base_chunks * 1.5)
        base_summaries = int(base_summaries * 1.4)
    
    # Adjust by scope
    if scope == 'narrow':
        base_chunks = max(3, int(base_chunks * 0.7))
        base_summaries = max(2, int(base_summaries * 0.7))
    elif scope == 'broad':
        base_chunks = int(base_chunks * 1.3)
        base_summaries = int(base_summaries * 1.3)
    
    # Cap at reasonable limits
    max_chunks = min(base_chunks, 20)
    max_summaries = min(base_summaries, 10)
    
    logger.info(f"Adaptive limits for {query_type}/{complexity}/{scope}: {max_chunks} chunks, {max_summaries} summaries")
    
    return (max_chunks, max_summaries)


def build_metadata_filter(
    query: str, 
    query_characteristics: Optional[Dict[str, Any]] = None,
    filter_logic: str = "OR"
) -> Optional[str]:
    """
    Build Vertex AI Search filter expression based on query characteristics.
    
    Available filter fields in Vertex AI Search:
    - source_id: string (unique document identifier)
    - filename: string (original filename)
    - title: string (document title)
    - author: string (document author)
    - organization: string (authoring organization)
    - date: string (ISO date YYYY-MM-DD)
    - publisher: string (publisher name)
    - tags: array of strings (topic keywords)
    - mimetype: string (content type, chunks only)
    - page_number/page: number (page reference, chunks only)
    
    Filter syntax: field: ANY("value1", "value2") for arrays
                   field: "value" for strings
                   field > value or field < value for numbers/dates
    
    Args:
        query: User's search query
        query_characteristics: Optional pre-analyzed characteristics
        filter_logic: "OR" (match any filter) or "AND" (match all filters)
    
    Returns:
        Filter expression string or None if no filters apply
    """
    if query_characteristics is None:
        query_characteristics = analyze_query_characteristics(query)
    
    filter_hints = query_characteristics.get('filter_hints', [])
    
    if not filter_hints:
        return None
    
    # Separate filters by type for intelligent grouping
    org_filters = []
    author_filters = []
    publisher_filters = []
    topic_filters = []
    other_filters = []
    
    for field, value in filter_hints:
        # Map logical field names to actual schema fields
        if field == 'organization':
            org_filters.append(f'organization: "{value}"')
        elif field == 'author':
            author_filters.append(f'author: "{value}"')
        elif field == 'publisher':
            publisher_filters.append(f'publisher: "{value}"')
        elif field == 'topic':
            # Tags is an array - use ANY for array matching
            topic_filters.append(f'tags: ANY("{value}")')
        elif field == 'doc_type':
            # Document type might be in tags or title
            topic_filters.append(f'tags: ANY("{value}")')
        elif field == 'mimetype':
            other_filters.append(f'mimetype: "{value}"')
    
    # Build filter expression based on logic
    all_filters = org_filters + author_filters + publisher_filters + topic_filters + other_filters
    
    if not all_filters:
        return None
    
    if filter_logic.upper() == "AND":
        # AND logic: must match all criteria
        # Group same-type filters with OR, then AND across types
        filter_groups = []
        if org_filters:
            filter_groups.append(' OR '.join(org_filters) if len(org_filters) > 1 else org_filters[0])
        if author_filters:
            filter_groups.append(' OR '.join(author_filters) if len(author_filters) > 1 else author_filters[0])
        if publisher_filters:
            filter_groups.append(' OR '.join(publisher_filters) if len(publisher_filters) > 1 else publisher_filters[0])
        if topic_filters:
            filter_groups.append(' OR '.join(topic_filters) if len(topic_filters) > 1 else topic_filters[0])
        if other_filters:
            filter_groups.append(' OR '.join(other_filters) if len(other_filters) > 1 else other_filters[0])
        
        if len(filter_groups) > 1:
            filter_expr = '(' + ') AND ('.join(filter_groups) + ')'
        else:
            filter_expr = filter_groups[0]
    else:
        # OR logic: match any criterion (more permissive)
        filter_expr = ' OR '.join(all_filters)
    
    logger.info(f"Built metadata filter ({filter_logic}): {filter_expr}")
    return filter_expr


def select_search_strategy(query: str, query_characteristics: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
    """
    Determine which search optimizations to apply based on query.
    
    Args:
        query: User's search query
        query_characteristics: Optional pre-analyzed characteristics
    
    Returns:
        Dict with strategy flags:
        - enable_query_expansion: bool
        - enable_reranking: bool
        - enable_deduplication: bool
        - search_chunks: bool
        - search_summaries: bool
        - use_filters: bool
    """
    if query_characteristics is None:
        query_characteristics = analyze_query_characteristics(query)
    
    query_type = query_characteristics['query_type']
    complexity = query_characteristics['complexity']
    
    strategy = {
        'enable_query_expansion': False,
        'enable_reranking': True,  # Generally beneficial
        'enable_deduplication': True,  # Generally beneficial
        'search_chunks': query_characteristics['needs_chunks'],
        'search_summaries': query_characteristics['needs_summaries'],
        'use_filters': len(query_characteristics.get('filter_hints', [])) > 0
    }
    
    # Query expansion is expensive - use selectively
    if complexity == 'complex' or query_type in ['analytical', 'exploratory', 'comparative']:
        strategy['enable_query_expansion'] = True
    
    # For simple factual queries, expansion might add noise
    if query_type == 'factual' and complexity == 'simple':
        strategy['enable_query_expansion'] = False
    
    logger.info(f"Search strategy for {query_type}/{complexity}: {strategy}")
    
    return strategy


def old_adaptive_result_limits(query: str) -> Tuple[int, int]:
    """
    DEPRECATED: Use adaptive_result_limits() with query_characteristics instead.
    
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
