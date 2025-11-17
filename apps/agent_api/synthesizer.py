"""
Synthesizer for CENTEF RAG system.
Combines retrieval results and generates answers using Gemini.
"""
import logging
import os
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote

from dotenv import load_dotenv
import vertexai
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig

# Load environment variables
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
SOURCE_OBJECT_PREFIX = os.getenv("SOURCE_OBJECT_PREFIX", "sources")

DOCUMENT_LABEL_PATTERN = re.compile(r"(?i)Document\s+(\d+)")
CHUNK_LABEL_PATTERN = re.compile(r"(?i)Chunk\s+(\d+)")
BRACKET_CONTENT_PATTERN = re.compile(r"\[(.*?)\]", re.DOTALL)

# Fallback models in case of rate limits or errors
FALLBACK_MODELS = [
    "gemini-2.0-flash-exp",      # Primary (experimental, faster but has rate limits)
    "gemini-1.5-flash-002",       # Fallback 1 (stable, fast)
    "gemini-1.5-pro-002",         # Fallback 2 (stable, more capable)
    "gemini-2.5-flash",           # Fallback 3 (newest stable)
]

# Use GEMINI_MODEL as primary if set, otherwise use first fallback
if GEMINI_MODEL and GEMINI_MODEL not in FALLBACK_MODELS:
    FALLBACK_MODELS.insert(0, GEMINI_MODEL)

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=GENERATION_LOCATION)


def build_synthesis_prompt(
    query: str,
    summary_results: List[Dict[str, Any]],
    chunk_results: List[Dict[str, Any]]
) -> str:
    """
    Build a prompt for Gemini that includes query and retrieval results.
    
    Args:
        query: User's question
        summary_results: List of summary search results
        chunk_results: List of chunk search results
    
    Returns:
        Formatted prompt string
    """
    prompt_parts = [
        "You are an expert assistant for the CENTEF (Center for Research of Terror Financing) knowledge base.",
        "Your role is to provide accurate, comprehensive answers about terrorism financing, money laundering,",
        "counter-terrorism finance (CTF), and related topics based on the provided documents.",
        "",
        "IMPORTANT CONTEXT:",
        "- AML = Anti-Money Laundering",
        "- CTF/CFT = Counter-Terrorism Financing / Combating the Financing of Terrorism",
        "- FATF = Financial Action Task Force",
        "",
        "CRITICAL CITATION REQUIREMENTS:",
        "1. You MUST include at least 5 explicit inline citations in your answer",
        "2. Use this format for citations: [Document Title, Page X] or [Document Title] for summaries",
        "3. Cite specific sources when making claims or providing facts",
        "4. At the end of your answer, include a '---CITATIONS---' section listing:",
        "   - All documents you explicitly cited in brackets",
        "   - Format: CITED: Document Title (Page X) or (Summary)",
        "",
        "INSTRUCTIONS:",
        "1. Answer the user's question using the information from the provided summaries and chunks below",
        "2. Include AT LEAST 5 explicit citations in your answer using the [Document, Page] format",
        "3. If abbreviations like AML, CTF, CFT appear in the documents, use the full terms in your answer",
        "4. Synthesize information across multiple sources when relevant",
        "5. Structure your answer clearly with relevant sections if appropriate",
        "6. End with the ---CITATIONS--- section listing each cited source",
        "",
        f"USER QUESTION: {query}",
        "",
        "=" * 80,
        "DOCUMENT SUMMARIES:",
        "=" * 80,
    ]
    
    # Add summaries
    if summary_results:
        for i, summary in enumerate(summary_results, 1):
            prompt_parts.append(f"\n[Document {i}] {summary.get('title', 'Unknown')}")
            if summary.get('filename'):
                prompt_parts.append(f"File: {summary['filename']}")
            if summary.get('author'):
                prompt_parts.append(f"Author: {summary['author']}")
            if summary.get('organization'):
                prompt_parts.append(f"Organization: {summary['organization']}")
            if summary.get('date'):
                prompt_parts.append(f"Date: {summary['date']}")
            prompt_parts.append(f"\nSummary:")
            prompt_parts.append(summary.get('summary_text', ''))
            prompt_parts.append("")
    else:
        prompt_parts.append("(No document summaries available)")
    
    # Add chunks
    prompt_parts.append("\n" + "=" * 80)
    prompt_parts.append("RELEVANT DETAILED CHUNKS:")
    prompt_parts.append("=" * 80)
    
    if chunk_results:
        for i, chunk in enumerate(chunk_results, 1):
            prompt_parts.append(f"\n[Chunk {i}] Source: {chunk.get('title', 'Unknown')}")
            
            # Add location information
            location_parts = []
            if chunk.get('filename'):
                location_parts.append(f"File: {chunk['filename']}")
            if chunk.get('page_number') is not None:
                location_parts.append(f"Page: {chunk['page_number']}")
            elif chunk.get('start_sec') is not None:
                start = format_timestamp(chunk['start_sec'])
                end = format_timestamp(chunk.get('end_sec', chunk['start_sec']))
                location_parts.append(f"Timestamp: {start} - {end}")
            
            if location_parts:
                prompt_parts.append(", ".join(location_parts))
            
            prompt_parts.append(f"\nContent:")
            prompt_parts.append(chunk.get('content', ''))
            prompt_parts.append("")
    else:
        prompt_parts.append("(No detailed chunks available)")
    
    prompt_parts.append("\n" + "=" * 80)
    prompt_parts.append("ANSWER FORMAT:")
    prompt_parts.append("=" * 80)
    prompt_parts.append("Provide a comprehensive answer with AT LEAST 5 inline citations using [Document Title, Page X] format.")
    prompt_parts.append("End your response with:")
    prompt_parts.append("---CITATIONS---")
    prompt_parts.append("CITED: [List each document you cited, with format: Document Title (Page X) or (Summary)]")
    prompt_parts.append("")
    
    return "\n".join(prompt_parts)


def format_timestamp(seconds: float) -> str:
    """
    Format seconds as MM:SS or HH:MM:SS.
    
    Args:
        seconds: Time in seconds
    
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def format_page_range(pages: List[int]) -> str:
    """
    Format a list of page numbers into a readable range string.
    Examples:
        [1, 2, 3, 5, 6, 10] -> "1-3, 5-6, 10"
        [5] -> "5"
        [1, 3, 5] -> "1, 3, 5"
    
    Args:
        pages: Sorted list of page numbers
    
    Returns:
        Formatted page range string
    """
    if not pages:
        return ""
    
    if len(pages) == 1:
        return str(pages[0])
    
    ranges = []
    start = pages[0]
    end = pages[0]
    
    for i in range(1, len(pages)):
        if pages[i] == end + 1:
            # Continue the range
            end = pages[i]
        else:
            # End current range and start new one
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = pages[i]
            end = pages[i]
    
    # Add final range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    
    return ", ".join(ranges)


def build_authorized_url(source_uri: Optional[str]) -> Optional[str]:
    """
    Convert a gs:// URI into a browser-accessible https URL.

    Args:
        source_uri: The raw source URI (gs:// or https://)

    Returns:
        HTTPS URL suitable for browser access, or None if unavailable
    """
    if not source_uri:
        return None

    if source_uri.startswith("http://") or source_uri.startswith("https://"):
        return source_uri

    if source_uri.startswith("gs://"):
        path = source_uri[len("gs://") :]
        if not path:
            return None

        bucket, _, object_path = path.partition("/")
        if not bucket:
            return None

        if object_path:
            encoded_path = "/".join(quote(part, safe="") for part in object_path.split("/"))
            return f"https://storage.cloud.google.com/{bucket}/{encoded_path}"
        return f"https://storage.cloud.google.com/{bucket}"

    return source_uri


def resolve_source_uri(
    manifest_entry: Optional["ManifestEntry"],
    primary_metadata: Optional[Dict[str, Any]] = None,
    secondary_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Determine the best available URI for a source.
    Tries manifest, metadata, and finally constructs a GCS path using filename.
    """
    if manifest_entry and manifest_entry.source_uri:
        return manifest_entry.source_uri

    def _extract_candidate(metadata: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(metadata, dict):
            return None
        for key in ("source_uri", "sourceUrl", "source_url", "gcs_uri", "gcsUrl", "url"):
            value = metadata.get(key)
            if value:
                return value
        return None

    candidate = _extract_candidate(primary_metadata) or _extract_candidate(secondary_metadata)
    if candidate:
        return candidate

    filename = None
    if manifest_entry and manifest_entry.filename:
        filename = manifest_entry.filename
    else:
        if isinstance(primary_metadata, dict):
            filename = primary_metadata.get("filename")
        if not filename and isinstance(secondary_metadata, dict):
            filename = secondary_metadata.get("filename")

    if filename and SOURCE_BUCKET:
        prefix = SOURCE_OBJECT_PREFIX.strip("/")
        filename_part = filename.lstrip("/")
        if prefix:
            return f"gs://{SOURCE_BUCKET}/{prefix}/{filename_part}"
        return f"gs://{SOURCE_BUCKET}/{filename_part}"

    return None


def _replace_label_token(text: str, pattern: re.Pattern, label_map: Dict[str, str]) -> str:
    def _sub(match: re.Match) -> str:
        key = match.group(1)
        return label_map.get(key, match.group(0))

    return pattern.sub(_sub, text)


def normalize_citation_labels(
    citations: List[str],
    document_label_map: Dict[str, str],
    chunk_label_map: Dict[str, str],
) -> List[str]:
    """
    Replace placeholder labels like 'Document 1' with real titles for consistency.

    Args:
        citations: Raw citations parsed from the model output
        document_label_map: Mapping of document indices to titles
        chunk_label_map: Mapping of chunk indices to titles

    Returns:
        Cleaned list of citations referencing actual document titles
    """
    if not citations:
        return []

    normalized = []
    seen = set()

    for citation in citations:
        updated = _replace_label_token(citation, DOCUMENT_LABEL_PATTERN, document_label_map)
        updated = _replace_label_token(updated, CHUNK_LABEL_PATTERN, chunk_label_map)
        updated = updated.strip()
        if updated and updated not in seen:
            normalized.append(updated)
            seen.add(updated)

    return normalized


def replace_inline_placeholder_labels(
    text: str,
    document_label_map: Dict[str, str],
    chunk_label_map: Dict[str, str],
) -> str:
    """
    Replace inline [Document N, ...] / [Chunk N, ...] tokens with actual titles.
    """
    def _sub(match: re.Match) -> str:
        content = match.group(1)
        replaced = _replace_label_token(content, DOCUMENT_LABEL_PATTERN, document_label_map)
        replaced = _replace_label_token(replaced, CHUNK_LABEL_PATTERN, chunk_label_map)
        return f"[{replaced}]"

    return BRACKET_CONTENT_PATTERN.sub(_sub, text)


def parse_citations_from_answer(answer_text: str) -> tuple[str, List[str]]:
    """
    Parse the answer to extract the main text and explicit citations.
    
    Args:
        answer_text: Full answer from Gemini including citations section
    
    Returns:
        Tuple of (main_answer, list_of_citations)
        Citations are in format "Document Title (Page X)" or "Document Title (Summary)"
    """
    # Split on the citations marker
    if "---CITATIONS---" in answer_text:
        parts = answer_text.split("---CITATIONS---")
        main_answer = parts[0].strip()
        citations_section = parts[1].strip() if len(parts) > 1 else ""
        
        # Extract citations from the citations section
        citations = []
        for line in citations_section.split('\n'):
            line = line.strip()
            if line.startswith("CITED:"):
                # Remove "CITED:" prefix and parse
                citation = line.replace("CITED:", "").strip()
                if citation:
                    citations.append(citation)
            elif line and not line.startswith("---"):
                # Also capture lines that might not have CITED: prefix
                citations.append(line)
        
        return main_answer, citations
    else:
        # No citations section found, return full text
        return answer_text, []


def synthesize_answer(
    query: str,
    summary_results: List[Dict[str, Any]],
    chunk_results: List[Dict[str, Any]],
    temperature: float = 0.2,
    max_output_tokens: int = 2048
) -> Dict[str, Any]:
    """
    Generate an answer using Gemini based on retrieval results.
    
    Args:
        query: User's question
        summary_results: Summary search results
        chunk_results: Chunk search results
        temperature: Model temperature (0.0 - 1.0)
        max_output_tokens: Maximum length of generated answer
    
    Returns:
        Dictionary with answer text and metadata
    """
    logger.info(f"Synthesizing answer for query: {query}")
    logger.info(f"Using {len(summary_results)} summaries and {len(chunk_results)} chunks")
    
    # Build prompt
    prompt = build_synthesis_prompt(query, summary_results, chunk_results)
    
    logger.info(f"Prompt length: {len(prompt)} characters")
    
    # Configure generation
    generation_config = GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        top_p=0.95,
    )
    
    # Try models in order until one succeeds
    answer_text = None
    model_used = None
    last_error = None
    usage_metadata = None  # Track token usage
    
    for model_name in FALLBACK_MODELS:
        try:
            logger.info(f"Attempting model: {model_name}")
            model = GenerativeModel(model_name)
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            answer_text = response.text
            model_used = model_name
            
            # Extract token usage if available
            if hasattr(response, 'usage_metadata'):
                usage_metadata = {
                    'prompt_token_count': getattr(response.usage_metadata, 'prompt_token_count', 0),
                    'candidates_token_count': getattr(response.usage_metadata, 'candidates_token_count', 0),
                    'total_token_count': getattr(response.usage_metadata, 'total_token_count', 0),
                }
                logger.info(f"Token usage: {usage_metadata}")
            
            logger.info(f"✅ Success with {model_name} - Generated {len(answer_text)} characters")
            break
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"❌ Model {model_name} failed: {error_msg}")
            last_error = e
            
            # Check if it's a rate limit error (429)
            if "429" in error_msg or "Resource exhausted" in error_msg:
                logger.info(f"Rate limit hit on {model_name}, trying next fallback...")
                continue
            
            # Check if it's a quota error
            if "quota" in error_msg.lower() or "insufficient" in error_msg.lower():
                logger.info(f"Quota issue on {model_name}, trying next fallback...")
                continue
            
            # For other errors, try next model but log more details
            logger.error(f"Unexpected error with {model_name}: {error_msg}")
            continue
    
    # If all models failed, use fallback response
    if answer_text is None:
        logger.error(f"All models failed. Last error: {last_error}")
        answer_text = (
            f"I apologize, but I'm currently experiencing high demand and cannot generate an answer. "
            f"However, I found {len(summary_results)} relevant document summaries and "
            f"{len(chunk_results)} detailed chunks that contain information about: {query}\n\n"
            f"Please try again in a few moments, or contact support if the issue persists."
        )
        model_used = "fallback-none"
    
    # Parse answer to extract main text and explicit citations
    main_answer, explicit_citations = parse_citations_from_answer(answer_text)
    logger.info(f"Parsed {len(explicit_citations)} explicit citations from answer")
    
    # Extract source citations from results
    # Track sources with their page numbers/timestamps
    source_map = {}  # source_id -> source info with pages list
    document_label_map: Dict[str, str] = {}
    chunk_label_map: Dict[str, str] = {}
    
    # Import manifest to get source_uri
    from shared.manifest import get_manifest_entry

    manifest_cache: Dict[str, Optional["ManifestEntry"]] = {}

    def fetch_manifest_entry(source_id: Optional[str]):
        if not source_id:
            return None
        if source_id not in manifest_cache:
            manifest_cache[source_id] = get_manifest_entry(source_id)
        return manifest_cache[source_id]

    # Add summaries (no page numbers, represent whole document)
    for idx, summary in enumerate(summary_results, 1):
        source_id = summary.get('source_id')
        manifest_entry = fetch_manifest_entry(source_id)
        summary_title = (
            summary.get('title')
            or (manifest_entry.title if manifest_entry else None)
            or summary.get('filename')
            or source_id
            or f"Document {idx}"
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
    
    # Add chunks (with page numbers/timestamps)
    for idx, chunk in enumerate(chunk_results, 1):
        source_id = chunk.get('source_id')
        manifest_entry = fetch_manifest_entry(source_id)
        chunk_metadata = chunk.get('metadata') if isinstance(chunk.get('metadata'), dict) else {}
        chunk_title = (
            chunk.get('title')
            or (manifest_entry.title if manifest_entry else None)
            or chunk.get('filename')
            or source_id
            or f"Chunk {idx}"
        )
        chunk_label_map[str(idx)] = chunk_title

        if not source_id:
            continue

        raw_source_uri = resolve_source_uri(
            manifest_entry,
            chunk,
            chunk_metadata
        )

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
        
        # Add page number if available
        page = chunk.get('page_number')
        if page is None:
            page = chunk.get('page')
        if page is not None and page not in source_map[source_id]['pages']:
            source_map[source_id]['pages'].append(page)
        
        # Add timestamp if available (for video/audio)
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
    
    # Convert to list and format page numbers
    all_sources = []
    for source_info in source_map.values():
        # Sort pages and format them
        if source_info['pages']:
            source_info['pages'].sort()
            source_info['page_range'] = format_page_range(source_info['pages'])
        
        all_sources.append(source_info)
    
    # Separate cited sources from context-only sources
    # For now, all retrieved sources are "context sources"
    # The explicit_citations from the answer tell us which were actually cited

    normalized_citations = normalize_citation_labels(
        explicit_citations,
        document_label_map,
        chunk_label_map,
    )
    
    main_answer = replace_inline_placeholder_labels(
        main_answer,
        document_label_map,
        chunk_label_map,
    )
    sanitized_full_answer = replace_inline_placeholder_labels(
        answer_text,
        document_label_map,
        chunk_label_map,
    )

    result = {
        "query": query,
        "answer": main_answer,  # Main answer without citations section
        "full_answer": sanitized_full_answer,  # Full answer including citations section
        "explicit_citations": normalized_citations,  # List of citation strings
        "sources": all_sources,  # All sources used for context
        "num_summaries_used": len(summary_results),
        "num_chunks_used": len(chunk_results),
        "model_used": model_used or "unknown",
        "temperature": temperature
    }
    
    # Add token usage if available
    if usage_metadata:
        result["input_tokens"] = usage_metadata.get('prompt_token_count', 0)
        result["output_tokens"] = usage_metadata.get('candidates_token_count', 0)
        result["total_tokens"] = usage_metadata.get('total_token_count', 0)
    
    return result


def generate_follow_up_questions(
    query: str,
    answer: str,
    num_questions: int = 3
) -> List[str]:
    """
    Generate follow-up questions based on the query and answer.
    
    Args:
        query: Original user query
        answer: Generated answer
        num_questions: Number of follow-up questions to generate
    
    Returns:
        List of follow-up question strings
    """
    logger.info(f"Generating {num_questions} follow-up questions")
    
    # TODO: Use Gemini to generate follow-up questions
    # prompt = f"""
    # Based on this Q&A exchange, generate {num_questions} relevant follow-up questions:
    # 
    # Question: {query}
    # Answer: {answer}
    # 
    # Generate {num_questions} natural follow-up questions that would help the user explore this topic further.
    # Return only the questions, one per line.
    # """
    
    # Placeholder response
    logger.warning("Using placeholder follow-up questions")
    return [
        f"Can you provide more details about this topic?",
        f"What are the key findings related to this?",
        f"Are there any related documents I should review?"
    ][:num_questions]
