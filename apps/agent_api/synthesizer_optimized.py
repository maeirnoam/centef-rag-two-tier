"""
Optimized synthesizer for CENTEF RAG system.
Includes context window management, streaming, adaptive temperature, and improved citations.
"""
import logging
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Tuple
from urllib.parse import quote

from dotenv import load_dotenv
import vertexai
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.llm_tracker import track_llm_call

# Import existing synthesizer functions
from synthesizer import (
    build_synthesis_prompt,
    parse_citations_from_answer,
    normalize_citation_labels,
    replace_inline_placeholder_labels,
    resolve_source_uri,
    build_authorized_url,
    format_timestamp,
    format_page_range,
    FALLBACK_MODELS,
    DOCUMENT_LABEL_PATTERN,
    CHUNK_LABEL_PATTERN
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
GENERATION_LOCATION = os.getenv("GENERATION_LOCATION", "us-central1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
SOURCE_BUCKET = os.getenv("SOURCE_BUCKET", "centef-rag-bucket")


def estimate_token_count(text: str) -> int:
    """
    Rough estimation of token count for text.
    Uses ~4 characters per token heuristic.
    
    Args:
        text: Input text
    
    Returns:
        Estimated token count
    """
    return len(text) // 4


def smart_context_truncation(
    summary_results: List[Dict[str, Any]],
    chunk_results: List[Dict[str, Any]],
    max_tokens: int = 24000
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Intelligently truncate context to fit within token limits while preserving most relevant content.
    
    Strategy:
    1. Keep all summaries (usually small)
    2. Prioritize top-ranked chunks
    3. Truncate individual chunk content if needed
    
    Args:
        summary_results: List of summary search results
        chunk_results: List of chunk search results
        max_tokens: Maximum token budget for context
    
    Returns:
        Tuple of (truncated_summaries, truncated_chunks)
    """
    logger.info(f"Truncating context to fit {max_tokens} tokens")
    
    # Reserve tokens for prompt structure (~2000 tokens)
    available_tokens = max_tokens - 2000
    
    # Allocate tokens: 20% for summaries, 80% for chunks
    summary_budget = int(available_tokens * 0.2)
    chunk_budget = int(available_tokens * 0.8)
    
    # Process summaries
    truncated_summaries = []
    used_summary_tokens = 0
    
    for summary in summary_results:
        summary_text = summary.get('summary_text', '')
        tokens = estimate_token_count(summary_text)
        
        if used_summary_tokens + tokens > summary_budget:
            # Truncate this summary
            available = summary_budget - used_summary_tokens
            if available > 100:  # Only include if we can fit meaningful content
                chars = available * 4
                summary_copy = summary.copy()
                summary_copy['summary_text'] = summary_text[:chars] + "..."
                truncated_summaries.append(summary_copy)
                used_summary_tokens += available
            break
        else:
            truncated_summaries.append(summary)
            used_summary_tokens += tokens
    
    # Process chunks
    truncated_chunks = []
    used_chunk_tokens = 0
    
    for chunk in chunk_results:
        content = chunk.get('content', '')
        tokens = estimate_token_count(content)
        
        if used_chunk_tokens + tokens > chunk_budget:
            # Try to fit truncated version
            available = chunk_budget - used_chunk_tokens
            if available > 200:  # Need meaningful chunk content
                chars = available * 4
                chunk_copy = chunk.copy()
                chunk_copy['content'] = content[:chars] + "..."
                truncated_chunks.append(chunk_copy)
                used_chunk_tokens += available
            break
        else:
            truncated_chunks.append(chunk)
            used_chunk_tokens += tokens
    
    logger.info(f"Context truncation: {len(truncated_summaries)}/{len(summary_results)} summaries, "
                f"{len(truncated_chunks)}/{len(chunk_results)} chunks")
    logger.info(f"Token usage: ~{used_summary_tokens + used_chunk_tokens}/{available_tokens}")
    
    return truncated_summaries, truncated_chunks


def detect_output_format(query: str) -> Dict[str, Any]:
    """
    Detect the desired output format and characteristics from the query.
    
    Recognizes requests for:
    - Brief summaries, bullet points, overviews
    - Tweets, social media posts
    - Blog posts, articles, essays
    - Newsletters, reports
    - Outlines, presentations, interviews
    - Protocols, procedures, guidelines
    - Comprehensive analyses
    
    Args:
        query: User's query
    
    Returns:
        Dict with format characteristics: {
            'format_type': str,
            'length': str (brief/medium/long/comprehensive),
            'structure': str (bullets/paragraphs/sections/outline),
            'temperature': float,
            'max_tokens': int,
            'style': str (formal/casual/academic/creative)
        }
    """
    query_lower = query.lower()
    
    # Initialize defaults
    format_info = {
        'format_type': 'general_answer',
        'length': 'medium',
        'structure': 'paragraphs',
        'temperature': 0.2,
        'max_tokens': 2048,
        'style': 'formal'
    }
    
    # Brief/Summary formats (200-500 tokens)
    brief_keywords = [
        'brief', 'summary', 'summarize', 'briefly', 'quick overview', 
        'tldr', 'tl;dr', 'in short', 'key points', 'bullet points',
        'main points', 'highlights'
    ]
    if any(keyword in query_lower for keyword in brief_keywords):
        format_info.update({
            'format_type': 'brief_summary',
            'length': 'brief',
            'structure': 'bullets',
            'temperature': 0.15,
            'max_tokens': 500,
            'style': 'concise'
        })
        logger.info("Detected format: Brief Summary")
        return format_info
    
    # Tweet/Social Media (50-280 characters worth, ~100 tokens)
    social_keywords = [
        'tweet', 'twitter post', 'social media post', 'linkedin post',
        'facebook post', 'instagram caption', '280 characters'
    ]
    if any(keyword in query_lower for keyword in social_keywords):
        format_info.update({
            'format_type': 'social_media',
            'length': 'brief',
            'structure': 'single_paragraph',
            'temperature': 0.4,
            'max_tokens': 150,
            'style': 'casual_engaging'
        })
        logger.info("Detected format: Social Media Post")
        return format_info
    
    # Blog Post/Article (1000-2000 tokens)
    blog_keywords = [
        'blog post', 'article', 'write an article', 'blog about',
        'essay', 'write about', 'detailed article', 'medium post'
    ]
    if any(keyword in query_lower for keyword in blog_keywords):
        format_info.update({
            'format_type': 'blog_post',
            'length': 'long',
            'structure': 'sections',
            'temperature': 0.5,
            'max_tokens': 2500,
            'style': 'engaging_informative'
        })
        logger.info("Detected format: Blog Post/Article")
        return format_info
    
    # Newsletter (800-1500 tokens)
    newsletter_keywords = [
        'newsletter', 'email newsletter', 'weekly update', 'monthly update',
        'news brief', 'digest'
    ]
    if any(keyword in query_lower for keyword in newsletter_keywords):
        format_info.update({
            'format_type': 'newsletter',
            'length': 'medium',
            'structure': 'sections',
            'temperature': 0.4,
            'max_tokens': 1800,
            'style': 'professional_friendly'
        })
        logger.info("Detected format: Newsletter")
        return format_info
    
    # Outline/Presentation (500-1000 tokens)
    outline_keywords = [
        'outline', 'presentation outline', 'talk outline', 'speaking points',
        'presentation', 'prepare a presentation', 'slide outline',
        'interview prep', 'talking points', 'key topics'
    ]
    if any(keyword in query_lower for keyword in outline_keywords):
        format_info.update({
            'format_type': 'outline',
            'length': 'medium',
            'structure': 'hierarchical_bullets',
            'temperature': 0.25,
            'max_tokens': 1200,
            'style': 'structured'
        })
        logger.info("Detected format: Outline/Presentation")
        return format_info
    
    # Protocol/Procedure (800-1500 tokens)
    protocol_keywords = [
        'protocol', 'procedure', 'guidelines', 'step-by-step', 'how to',
        'instructions', 'best practices', 'framework', 'methodology',
        'process', 'workflow'
    ]
    if any(keyword in query_lower for keyword in protocol_keywords):
        format_info.update({
            'format_type': 'protocol',
            'length': 'long',
            'structure': 'numbered_steps',
            'temperature': 0.15,
            'max_tokens': 1800,
            'style': 'precise_formal'
        })
        logger.info("Detected format: Protocol/Procedure")
        return format_info
    
    # Comprehensive/In-depth (2000-4000 tokens)
    comprehensive_keywords = [
        'comprehensive', 'in-depth', 'detailed', 'thorough', 'complete analysis',
        'full report', 'extensive', 'deep dive', 'exhaustive'
    ]
    if any(keyword in query_lower for keyword in comprehensive_keywords):
        format_info.update({
            'format_type': 'comprehensive_analysis',
            'length': 'comprehensive',
            'structure': 'sections_with_subsections',
            'temperature': 0.3,
            'max_tokens': 4000,
            'style': 'academic_thorough'
        })
        logger.info("Detected format: Comprehensive Analysis")
        return format_info
    
    # Report (1200-2000 tokens)
    report_keywords = [
        'report', 'write a report', 'formal report', 'research report',
        'findings', 'assessment report'
    ]
    if any(keyword in query_lower for keyword in report_keywords):
        format_info.update({
            'format_type': 'report',
            'length': 'long',
            'structure': 'formal_sections',
            'temperature': 0.2,
            'max_tokens': 2200,
            'style': 'formal_professional'
        })
        logger.info("Detected format: Report")
        return format_info
    
    # Factual questions (400-800 tokens)
    factual_keywords = ['what is', 'when did', 'who is', 'where is', 'define', 'definition']
    if any(keyword in query_lower for keyword in factual_keywords):
        format_info.update({
            'format_type': 'factual_answer',
            'length': 'medium',
            'structure': 'paragraphs',
            'temperature': 0.15,
            'max_tokens': 800,
            'style': 'clear_concise'
        })
        logger.info("Detected format: Factual Answer")
        return format_info
    
    logger.info("Using default format: General Answer")
    return format_info


def adaptive_temperature(query: str) -> float:
    """
    Determine optimal temperature based on query type.
    Now delegates to detect_output_format for more nuanced detection.
    
    Args:
        query: User's query
    
    Returns:
        Optimal temperature value
    """
    format_info = detect_output_format(query)
    return format_info['temperature']


def build_optimized_synthesis_prompt(
    query: str,
    summary_results: List[Dict[str, Any]],
    chunk_results: List[Dict[str, Any]],
    prioritize_citations: bool = True,
    format_info: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build an optimized prompt with better structure and citation requirements.
    Adapts prompt based on detected output format.
    
    Args:
        query: User's question
        summary_results: List of summary search results
        chunk_results: List of chunk search results
        prioritize_citations: Whether to emphasize citation requirements
        format_info: Optional format information from detect_output_format()
    
    Returns:
        Formatted prompt string
    """
    # Detect format if not provided
    if format_info is None:
        format_info = detect_output_format(query)
    
    prompt_parts = [
        "You are an expert assistant for the CENTEF (Center for Research of Terror Financing) knowledge base.",
        "Your role is to provide accurate, comprehensive answers based on the provided documents.",
        "",
        "DOMAIN CONTEXT:",
        "- AML = Anti-Money Laundering",
        "- CTF/CFT = Counter-Terrorism Financing",
        "- FATF = Financial Action Task Force",
        "- PEP = Politically Exposed Person",
        "- SAR = Suspicious Activity Report",
        "- KYC = Know Your Customer",
        "",
    ]
    
    # Add format-specific instructions
    format_type = format_info.get('format_type', 'general_answer')
    structure = format_info.get('structure', 'paragraphs')
    style = format_info.get('style', 'formal')
    
    prompt_parts.append("OUTPUT FORMAT REQUIREMENTS:")
    
    if format_type == 'brief_summary':
        prompt_parts.extend([
            "- Provide a BRIEF summary with KEY POINTS only",
            "- Use bullet points for clarity",
            "- Keep it concise (3-5 main points)",
            "- Each point should be 1-2 sentences maximum",
        ])
    
    elif format_type == 'social_media':
        prompt_parts.extend([
            "- Write a compelling SOCIAL MEDIA POST (tweet-length)",
            "- Keep it under 280 characters if possible",
            "- Make it engaging and shareable",
            "- Use clear, accessible language",
            "- Include 1-2 key hashtags if appropriate",
        ])
    
    elif format_type == 'blog_post':
        prompt_parts.extend([
            "- Write a comprehensive BLOG POST or ARTICLE",
            "- Structure with clear sections and headings",
            "- Include an engaging introduction",
            "- Develop key points with examples and details",
            "- Conclude with key takeaways or implications",
            "- Use a conversational yet informative tone",
        ])
    
    elif format_type == 'newsletter':
        prompt_parts.extend([
            "- Create a NEWSLETTER-style update",
            "- Start with a brief intro or context",
            "- Use clear section headings",
            "- Keep paragraphs short and scannable",
            "- End with a call-to-action or next steps",
            "- Professional but approachable tone",
        ])
    
    elif format_type == 'outline':
        prompt_parts.extend([
            "- Provide a structured OUTLINE",
            "- Use hierarchical bullet points (main topics → subtopics → details)",
            "- Each main point should have 2-4 supporting sub-points",
            "- Keep it organized and easy to follow",
            "- Perfect for presentations or talks",
        ])
    
    elif format_type == 'protocol':
        prompt_parts.extend([
            "- Write a clear PROTOCOL or PROCEDURE",
            "- Use numbered steps for sequential actions",
            "- Include any prerequisites or requirements",
            "- Be precise and unambiguous",
            "- Add warnings or notes where appropriate",
            "- Formal, authoritative tone",
        ])
    
    elif format_type == 'comprehensive_analysis':
        prompt_parts.extend([
            "- Provide a COMPREHENSIVE, IN-DEPTH analysis",
            "- Structure with main sections and subsections",
            "- Cover all relevant aspects thoroughly",
            "- Include context, details, and implications",
            "- Synthesize information from multiple sources",
            "- Academic or professional depth",
        ])
    
    elif format_type == 'report':
        prompt_parts.extend([
            "- Write a formal REPORT",
            "- Use standard report structure (Executive Summary, Findings, Analysis, Conclusions)",
            "- Present information objectively",
            "- Include relevant data and evidence",
            "- Professional, formal tone",
        ])
    
    else:  # general_answer or factual_answer
        prompt_parts.extend([
            "- Provide a clear, well-structured answer",
            "- Use paragraphs with logical flow",
            "- Include relevant details and context",
            "- Be thorough but concise",
        ])
    
    prompt_parts.append("")
    
    # Citation requirements (adapt based on format and length)
    if prioritize_citations:
        min_citations = 3 if format_info.get('length') == 'brief' else 5
        
        prompt_parts.append("⚠️ CRITICAL CITATION REQUIREMENTS:")
        prompt_parts.extend([
            f"1. You MUST cite sources for ALL factual claims (minimum {min_citations} citations)",
            "2. Use format: [Document Title, Page X] or [Document Title] for summaries",
            "3. Place citations immediately after the relevant claim",
        ])
        
        if format_type != 'social_media':  # Social media posts can skip formal citation section
            prompt_parts.extend([
                "4. End with '---CITATIONS---' section listing all cited sources",
                "5. Format: CITED: Document Title (Page X) or (Summary)",
            ])
        
        prompt_parts.append("")
    
    prompt_parts.extend([
        "ANSWER GUIDELINES:",
        "1. Use information from the provided sources below",
        "2. Expand abbreviations on first use",
        "3. Be accurate and evidence-based",
        f"4. Match the requested format and style ({format_type})",
        "",
        f"USER REQUEST: {query}",
        "",
        "=" * 80,
        "DOCUMENT SUMMARIES:",
        "=" * 80,
    ])
    
    # Add summaries with better formatting
    if summary_results:
        for i, summary in enumerate(summary_results, 1):
            prompt_parts.append(f"\n📄 [Document {i}] {summary.get('title', 'Unknown')}")
            
            # Add metadata
            metadata_parts = []
            if summary.get('author'):
                metadata_parts.append(f"Author: {summary['author']}")
            if summary.get('organization'):
                metadata_parts.append(f"Org: {summary['organization']}")
            if summary.get('date'):
                metadata_parts.append(f"Date: {summary['date']}")
            
            if metadata_parts:
                prompt_parts.append(" | ".join(metadata_parts))
            
            prompt_parts.append(f"\n{summary.get('summary_text', '')}")
            prompt_parts.append("")
    else:
        prompt_parts.append("(No document summaries available)")
    
    # Add chunks with better formatting
    prompt_parts.append("\n" + "=" * 80)
    prompt_parts.append("DETAILED CONTENT CHUNKS:")
    prompt_parts.append("=" * 80)
    
    if chunk_results:
        for i, chunk in enumerate(chunk_results, 1):
            prompt_parts.append(f"\n📎 [Chunk {i}] {chunk.get('title', 'Unknown')}")
            
            # Add location
            location_parts = []
            if chunk.get('filename'):
                location_parts.append(chunk['filename'])
            if chunk.get('page_number') is not None:
                location_parts.append(f"Page {chunk['page_number']}")
            elif chunk.get('start_sec') is not None:
                start = format_timestamp(chunk['start_sec'])
                end = format_timestamp(chunk.get('end_sec', chunk['start_sec']))
                location_parts.append(f"Time: {start}-{end}")
            
            if location_parts:
                prompt_parts.append(" | ".join(location_parts))
            
            prompt_parts.append(f"\n{chunk.get('content', '')}")
            prompt_parts.append("")
    else:
        prompt_parts.append("(No detailed chunks available)")
    
    # Final output format reminder
    if format_type != 'social_media' and prioritize_citations:
        prompt_parts.append("\n" + "=" * 80)
        prompt_parts.append("REQUIRED OUTPUT FORMAT:")
        prompt_parts.append("=" * 80)
        prompt_parts.append(f"1. Provide answer in {format_type.replace('_', ' ').title()} format")
        prompt_parts.append(f"2. Include minimum {min_citations} inline citations [Document Title, Page X]")
        prompt_parts.append("3. End with:")
        prompt_parts.append("---CITATIONS---")
        prompt_parts.append("CITED: [List each source cited, format: Title (Page X) or (Summary)]")
        prompt_parts.append("")
    
    return "\n".join(prompt_parts)


def synthesize_answer_optimized(
    query: str,
    summary_results: List[Dict[str, Any]],
    chunk_results: List[Dict[str, Any]],
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None,
    enable_context_truncation: bool = True,
    enable_adaptive_temperature: bool = True,
    max_context_tokens: int = 24000,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an optimized answer with context management and adaptive parameters.
    Automatically detects desired output format from query.
    
    Args:
        query: User's question
        summary_results: Summary search results
        chunk_results: Chunk search results
        temperature: Model temperature (None = use adaptive/format-based)
        max_output_tokens: Maximum length of generated answer (None = use format-based)
        enable_context_truncation: Whether to truncate context to fit token limits
        enable_adaptive_temperature: Whether to use query-based temperature
        max_context_tokens: Maximum tokens for context (summaries + chunks)
        user_id: Optional user ID for tracking
        session_id: Optional session ID for tracking
    
    Returns:
        Dictionary with answer text, citations, format_info, and metadata
    """
    logger.info(f"Optimized synthesis for query: {query}")
    logger.info(f"Input: {len(summary_results)} summaries, {len(chunk_results)} chunks")
    
    # Detect desired output format
    format_info = detect_output_format(query)
    logger.info(f"Detected format: {format_info['format_type']} (length: {format_info['length']}, structure: {format_info['structure']})")
    
    # Step 1: Context truncation (if enabled)
    if enable_context_truncation:
        summary_results, chunk_results = smart_context_truncation(
            summary_results, 
            chunk_results, 
            max_tokens=max_context_tokens
        )
    
    # Step 2: Adaptive temperature (if enabled and not explicitly set)
    if temperature is None and enable_adaptive_temperature:
        temperature = format_info.get('temperature', 0.2)
    elif temperature is None:
        temperature = 0.2
    
    # Step 3: Get format-specific max_output_tokens if not provided
    if max_output_tokens is None:
        max_output_tokens = format_info.get('max_tokens', 2048)
    
    logger.info(f"Using temperature={temperature}, max_tokens={max_output_tokens} for {format_info['format_type']}")
    
    # Step 4: Build optimized, format-aware prompt
    prompt = build_optimized_synthesis_prompt(
        query, 
        summary_results, 
        chunk_results,
        prioritize_citations=True,
        format_info=format_info
    )
    
    prompt_tokens = estimate_token_count(prompt)
    logger.info(f"Prompt tokens: ~{prompt_tokens}, Temperature: {temperature}")
    
    # Step 5: Generate answer with fallback models
    generation_config = GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        top_p=0.95,
    )
    
    answer_text = None
    model_used = None
    last_error = None
    usage_metadata = None
    
    for model_name in FALLBACK_MODELS:
        with track_llm_call(
            source_function="synthesize_answer_optimized",
            api_provider="gemini",
            api_type="generative",
            model=model_name,
            operation="chat_answer",
            user_id=user_id,
            session_id=session_id,
            temperature=temperature,
            max_tokens=max_output_tokens
        ) as call:
            try:
                logger.info(f"Attempting model: {model_name}")
                model = GenerativeModel(model_name)
                
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                
                answer_text = response.text
                model_used = model_name
                
                # Extract token usage
                if hasattr(response, 'usage_metadata'):
                    usage_metadata = {
                        'prompt_token_count': getattr(response.usage_metadata, 'prompt_token_count', 0),
                        'candidates_token_count': getattr(response.usage_metadata, 'candidates_token_count', 0),
                        'total_token_count': getattr(response.usage_metadata, 'total_token_count', 0),
                    }
                    
                    call.update_tokens(
                        input_tokens=usage_metadata['prompt_token_count'],
                        output_tokens=usage_metadata['candidates_token_count'],
                        total_tokens=usage_metadata['total_token_count']
                    )
                
                logger.info(f"✅ Success with {model_name}")
                break
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"❌ Model {model_name} failed: {error_msg}")
                last_error = e
                call.set_error(error_msg)
                
                # Try next fallback for rate limits or quota errors
                if any(x in error_msg for x in ["429", "Resource exhausted", "quota", "insufficient"]):
                    continue
                logger.error(f"Unexpected error: {error_msg}")
                continue
    
    # Fallback response if all models fail
    if answer_text is None:
        logger.error(f"All models failed. Last error: {last_error}")
        answer_text = (
            f"I apologize, but I'm currently experiencing high demand. "
            f"However, I found {len(summary_results)} relevant documents with information about: {query}\n\n"
            f"Please try again in a few moments."
        )
        model_used = "fallback-none"
    
    # Step 5: Parse citations and build source map
    main_answer, explicit_citations = parse_citations_from_answer(answer_text)
    logger.info(f"Parsed {len(explicit_citations)} explicit citations")
    
    # Build source map
    from shared.manifest import get_manifest_entry
    
    source_map = {}
    document_label_map = {}
    chunk_label_map = {}
    manifest_cache = {}
    
    def fetch_manifest_entry(source_id: Optional[str]):
        if not source_id:
            return None
        if source_id not in manifest_cache:
            manifest_cache[source_id] = get_manifest_entry(source_id)
        return manifest_cache[source_id]
    
    # Process summaries
    for idx, summary in enumerate(summary_results, 1):
        source_id = summary.get('source_id')
        manifest_entry = fetch_manifest_entry(source_id)
        summary_title = (
            summary.get('title') or
            (manifest_entry.title if manifest_entry else None) or
            summary.get('filename') or
            source_id or
            f"Document {idx}"
        )
        document_label_map[str(idx)] = summary_title
        
        if source_id and source_id not in source_map:
            raw_source_uri = resolve_source_uri(manifest_entry, summary)
            filename_value = summary.get('filename') or (manifest_entry.filename if manifest_entry else source_id)
            source_map[source_id] = {
                "source_id": source_id,
                "title": summary_title,
                "filename": filename_value,
                "source_uri": raw_source_uri,
                "authorized_url": build_authorized_url(raw_source_uri),
                "type": "summary",
                "pages": []
            }
    
    # Process chunks
    for idx, chunk in enumerate(chunk_results, 1):
        source_id = chunk.get('source_id')
        manifest_entry = fetch_manifest_entry(source_id)
        chunk_metadata = chunk.get('metadata') if isinstance(chunk.get('metadata'), dict) else {}
        chunk_title = (
            chunk.get('title') or
            (manifest_entry.title if manifest_entry else None) or
            chunk.get('filename') or
            source_id or
            f"Chunk {idx}"
        )
        chunk_label_map[str(idx)] = chunk_title
        
        if not source_id:
            continue
        
        raw_source_uri = resolve_source_uri(manifest_entry, chunk, chunk_metadata)
        
        if source_id not in source_map:
            filename_value = chunk.get('filename') or (manifest_entry.filename if manifest_entry else source_id)
            source_map[source_id] = {
                "source_id": source_id,
                "title": chunk_title,
                "filename": filename_value,
                "source_uri": raw_source_uri,
                "authorized_url": build_authorized_url(raw_source_uri),
                "type": "chunk",
                "pages": []
            }
        else:
            existing = source_map[source_id]
            if raw_source_uri and not existing.get("authorized_url"):
                existing["source_uri"] = existing.get("source_uri") or raw_source_uri
                existing["authorized_url"] = build_authorized_url(raw_source_uri)
        
        # Add page/timestamp info
        page = chunk.get('page_number') or chunk.get('page')
        if page is not None and page not in source_map[source_id]['pages']:
            source_map[source_id]['pages'].append(page)
        
        start_sec = chunk.get('start_sec')
        end_sec = chunk.get('end_sec')
        if start_sec is not None:
            timestamp = {
                'start': format_timestamp(start_sec),
                'end': format_timestamp(end_sec) if end_sec else format_timestamp(start_sec)
            }
            if 'timestamps' not in source_map[source_id]:
                source_map[source_id]['timestamps'] = []
            source_map[source_id]['timestamps'].append(timestamp)
    
    # Format sources
    all_sources = []
    for source_info in source_map.values():
        if source_info['pages']:
            source_info['pages'].sort()
            source_info['page_range'] = format_page_range(source_info['pages'])
        all_sources.append(source_info)
    
    # Normalize citations
    normalized_citations = normalize_citation_labels(
        explicit_citations,
        document_label_map,
        chunk_label_map
    )
    
    main_answer = replace_inline_placeholder_labels(
        main_answer,
        document_label_map,
        chunk_label_map
    )
    
    sanitized_full_answer = replace_inline_placeholder_labels(
        answer_text,
        document_label_map,
        chunk_label_map
    )
    
    result = {
        "query": query,
        "answer": main_answer,
        "full_answer": sanitized_full_answer,
        "explicit_citations": normalized_citations,
        "sources": all_sources,
        "num_summaries_used": len(summary_results),
        "num_chunks_used": len(chunk_results),
        "model_used": model_used or "unknown",
        "temperature": temperature,
        "format_info": format_info,  # Include detected format information
        "optimizations_applied": {
            "context_truncation": enable_context_truncation,
            "adaptive_temperature": enable_adaptive_temperature,
            "estimated_prompt_tokens": prompt_tokens,
            "format_detected": format_info['format_type'],
            "max_tokens_used": max_output_tokens
        }
    }
    
    if usage_metadata:
        result["input_tokens"] = usage_metadata.get('prompt_token_count', 0)
        result["output_tokens"] = usage_metadata.get('candidates_token_count', 0)
        result["total_tokens"] = usage_metadata.get('total_token_count', 0)
    
    return result
