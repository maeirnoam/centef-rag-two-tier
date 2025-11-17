"""
Vertex AI Search retriever for CENTEF RAG system.
Handles querying both chunk and summary datastores.
"""
import logging
import os
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from google.cloud import discoveryengine_v1beta as discoveryengine

# Load environment variables first
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
VERTEX_SEARCH_LOCATION = os.getenv("VERTEX_SEARCH_LOCATION", "global")
DISCOVERY_SERVING_CONFIG = os.getenv("DISCOVERY_SERVING_CONFIG")
CHUNKS_DATASTORE_ID = os.getenv("CHUNKS_DATASTORE_ID")
SUMMARIES_DATASTORE_ID = os.getenv("SUMMARIES_DATASTORE_ID")


def search_chunks(
    query: str,
    max_results: int = 10,
    filter_expression: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search the chunk datastore using Vertex AI Search.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        filter_expression: Optional filter (e.g., "source_id: ANY('xyz')")
    
    Returns:
        List of chunk results with content and metadata
    """
    logger.info(f"Searching chunks with query: {query}")
    
    try:
        # Initialize Discovery Engine Search client
        client = discoveryengine.SearchServiceClient()
        
        # Build serving config for chunks datastore
        serving_config = (
            f"projects/{PROJECT_ID}/"
            f"locations/{VERTEX_SEARCH_LOCATION}/"
            f"collections/default_collection/"
            f"dataStores/{CHUNKS_DATASTORE_ID}/"
            f"servingConfigs/default_config"
        )
        
        logger.info(f"Using chunks serving config: {serving_config}")
        
        # Build search request
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=max_results,
            query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
            ),
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
        )
        
        if filter_expression:
            request.filter = filter_expression
            logger.info(f"Applied filter: {filter_expression}")
        
        # Execute search
        response = client.search(request=request)
        
        # Process results
        results = []
        for result in response.results:
            doc = result.document
            
            # Convert struct_data to regular dict
            struct_data = dict(doc.struct_data) if doc.struct_data else {}
            page_number = struct_data.get("page_number")
            if page_number is None:
                page_number = struct_data.get("page")
            
            results.append({
                "id": doc.id,
                "content": struct_data.get("content", ""),
                "page_number": page_number,
                "page": page_number,  # legacy key for backward compatibility
                "start_sec": struct_data.get("start_sec"),
                "end_sec": struct_data.get("end_sec"),
                "source_id": struct_data.get("source_id"),
                "filename": struct_data.get("filename"),
                "title": struct_data.get("title"),
                "score": getattr(result, 'relevance_score', 0.0),
                "metadata": struct_data
            })
        
        logger.info(f"Found {len(results)} chunk results from Vertex AI Search")
        return results
        
    except Exception as e:
        logger.error(f"Error searching chunks: {e}", exc_info=True)
        raise


def search_summaries(
    query: str,
    max_results: int = 5,
    filter_expression: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search the summary datastore using Vertex AI Search.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        filter_expression: Optional filter
    
    Returns:
        List of summary results with content and metadata
    """
    logger.info(f"Searching summaries with query: {query}")
    
    try:
        # Initialize Discovery Engine Search client
        client = discoveryengine.SearchServiceClient()
        
        # Build serving config for summaries datastore
        serving_config = (
            f"projects/{PROJECT_ID}/"
            f"locations/{VERTEX_SEARCH_LOCATION}/"
            f"collections/default_collection/"
            f"dataStores/{SUMMARIES_DATASTORE_ID}/"
            f"servingConfigs/default_config"
        )
        
        logger.info(f"Using summaries serving config: {serving_config}")
        
        # Build search request
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=max_results,
            query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
            ),
            spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
                mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
            ),
        )
        
        if filter_expression:
            request.filter = filter_expression
            logger.info(f"Applied filter: {filter_expression}")
        
        # Execute search
        response = client.search(request=request)
        
        # Process results
        results = []
        for result in response.results:
            doc = result.document
            
            # Convert struct_data to regular dict
            struct_data = dict(doc.struct_data) if doc.struct_data else {}
            
            results.append({
                "id": doc.id,
                "summary_text": struct_data.get("summary_text", ""),
                "source_id": struct_data.get("source_id"),
                "filename": struct_data.get("filename"),
                "title": struct_data.get("title"),
                "author": struct_data.get("author"),
                "organization": struct_data.get("organization"),
                "date": struct_data.get("date"),
                "publisher": struct_data.get("publisher"),
                "tags": struct_data.get("tags", []),
                "score": getattr(result, 'relevance_score', 0.0),
                "metadata": struct_data
            })
        
        logger.info(f"Found {len(results)} summary results from Vertex AI Search")
        return results
        
    except Exception as e:
        logger.error(f"Error searching summaries: {e}", exc_info=True)
        raise


def search_two_tier(
    query: str,
    max_chunk_results: int = 10,
    max_summary_results: int = 5
) -> Dict[str, Any]:
    """
    Perform two-tier search across both chunks and summaries.
    
    Args:
        query: Search query string
        max_chunk_results: Maximum chunk results
        max_summary_results: Maximum summary results
    
    Returns:
        Combined results from both tiers
    """
    logger.info(f"Performing two-tier search for query: {query}")
    
    # Search both datastores
    chunk_results = search_chunks(query, max_results=max_chunk_results)
    summary_results = search_summaries(query, max_results=max_summary_results)
    
    return {
        "query": query,
        "chunks": chunk_results,
        "summaries": summary_results,
        "total_chunks": len(chunk_results),
        "total_summaries": len(summary_results)
    }


def retrieve_by_source_id(source_id: str) -> Dict[str, Any]:
    """
    Retrieve all chunks and summary for a specific source_id.
    
    Args:
        source_id: The source_id to retrieve
    
    Returns:
        All chunks and summary for the document
    """
    logger.info(f"Retrieving all content for source_id={source_id}")
    
    # Use filter to get only this source
    filter_expr = f'source_id: ANY("{source_id}")'
    
    chunk_results = search_chunks("*", max_results=1000, filter_expression=filter_expr)
    summary_results = search_summaries("*", max_results=1, filter_expression=filter_expr)
    
    return {
        "source_id": source_id,
        "chunks": chunk_results,
        "summary": summary_results[0] if summary_results else None,
        "total_chunks": len(chunk_results)
    }
