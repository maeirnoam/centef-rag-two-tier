"""
Synthesizer for CENTEF RAG system.
Combines retrieval results and generates answers using Gemini.
"""
import logging
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote

from dotenv import load_dotenv
import vertexai
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.llm_tracker import track_llm_call
from shared.chat_history import MessageRole
from shared.manifest import ManifestEntry

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
    chunk_results: List[Dict[str, Any]],
    conversation_history: Optional[List[Any]] = None
) -> str:
    """
    Build a prompt for Gemini that includes query and retrieval results.
    
    Args:
        query: User's question
        summary_results: List of summary search results
        chunk_results: List of chunk search results
        conversation_history: Optional list of previous ChatMessage objects
    
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
    ]
    
    # Add conversation history if available
    if conversation_history and len(conversation_history) > 0:
        prompt_parts.append("=" * 80)
        prompt_parts.append("CONVERSATION HISTORY:")
        prompt_parts.append("=" * 80)
        prompt_parts.append("")
        prompt_parts.append("Previous messages in this conversation (for context only):")
        prompt_parts.append("")
        
        for msg in conversation_history:
            role_label = "USER" if msg.role == MessageRole.USER else "ASSISTANT"
            prompt_parts.append(f"{role_label}: {msg.content}")
            prompt_parts.append("")
        
        prompt_parts.append("Use this conversation history to provide contextually relevant answers.")
        prompt_parts.append("If the current question refers to previous topics, acknowledge that context.")
        prompt_parts.append("")
    
    prompt_parts.extend([
        "CITATION REQUIREMENTS:",
        "1. Use information from the provided sources below",
        "2. Cite specific sources when making claims using this format: [Document Title, Page X] or [Document Title, Timestamp X:XX] for videos",
        "3. Place citations immediately after the relevant claim in square brackets",
        "4. If abbreviations like AML, CTF, CFT appear in the documents, use the full terms in your answer",
        "5. Synthesize information across multiple sources when relevant",
        "6. Structure your answer clearly with relevant sections if appropriate",
        "",
        f"USER QUESTION: {query}",
        "",
        "=" * 80,
        "DOCUMENT SUMMARIES:",
        "=" * 80,
    ])
    
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


def extract_inline_citations(answer_text: str) -> List[str]:
    """
    Extract inline citations from answer text (e.g., [Document Title, Page X]).
    
    Args:
        answer_text: Answer text with inline citations
    
    Returns:
        List of unique citation strings found in the text
    """
    citations = []
    # Match [Document Title, Page X] or [Document Title, Timestamp X:XX] patterns
    citation_pattern = re.compile(r'\[([^\]]+)\]')
    
    for match in citation_pattern.finditer(answer_text):
        citation = match.group(1).strip()
        # Filter out citations that look like they have document content (too long)
        if citation and len(citation) < 200 and citation not in citations:
            citations.append(citation)
    
    return citations


def synthesize_answer(
    query: str,
    summary_results: List[Dict[str, Any]],
    chunk_results: List[Dict[str, Any]],
    temperature: float = 0.2,
    max_output_tokens: int = 2048,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    conversation_history: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Generate an answer using Gemini based on retrieval results.

    Args:
        query: User's question
        summary_results: Summary search results
        chunk_results: Chunk search results
        temperature: Model temperature (0.0 - 1.0)
        max_output_tokens: Maximum length of generated answer
        user_id: Optional user ID for tracking
        session_id: Optional session ID for tracking
        conversation_history: Optional list of previous ChatMessage objects for context

    Returns:
        Dictionary with answer text and metadata
    """
    logger.info(f"Synthesizing answer for query: {query}")
    logger.info(f"Using {len(summary_results)} summaries and {len(chunk_results)} chunks")
    if conversation_history:
        logger.info(f"Including {len(conversation_history)} messages from conversation history")

    # Build prompt with conversation history
    prompt = build_synthesis_prompt(query, summary_results, chunk_results, conversation_history)

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
        # Track this LLM call
        with track_llm_call(
            source_function="synthesize_answer",
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

                # Extract token usage if available
                if hasattr(response, 'usage_metadata'):
                    usage_metadata = {
                        'prompt_token_count': getattr(response.usage_metadata, 'prompt_token_count', 0),
                        'candidates_token_count': getattr(response.usage_metadata, 'candidates_token_count', 0),
                        'total_token_count': getattr(response.usage_metadata, 'total_token_count', 0),
                    }
                    logger.info(f"Token usage: {usage_metadata}")

                    # Update tracking with token counts
                    call.update_tokens(
                        input_tokens=usage_metadata['prompt_token_count'],
                        output_tokens=usage_metadata['candidates_token_count'],
                        total_tokens=usage_metadata['total_token_count']
                    )

                logger.info(f"✅ Success with {model_name} - Generated {len(answer_text)} characters")
                break

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"❌ Model {model_name} failed: {error_msg}")
                last_error = e

                # Mark call as error in tracking
                call.set_error(error_msg)

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
    
    # Step 5: Build source map first
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
    
    # Replace placeholder labels in answer
    sanitized_answer = replace_inline_placeholder_labels(
        answer_text,
        document_label_map,
        chunk_label_map,
    )
    
    # Extract inline citations AFTER replacing placeholders (so we get real titles)
    explicit_citations = extract_inline_citations(sanitized_answer)
    logger.info(f"Found {len(explicit_citations)} inline citations in answer")
    
    # Filter sources to only those actually cited in the answer
    cited_sources = []
    for source in all_sources:
        source_title = source['title'].lower()
        # Check if this source appears in any inline citation
        for citation in explicit_citations:
            citation_lower = citation.lower()
            if source_title in citation_lower or source['source_id'] in citation:
                cited_sources.append(source)
                break
    
    logger.info(f"Filtered {len(all_sources)} sources to {len(cited_sources)} cited sources")
    
    # Generate follow-up questions
    follow_up_questions = generate_follow_up_questions(query, sanitized_answer, num_questions=3)
    
    result = {
        "query": query,
        "answer": sanitized_answer,
        "full_answer": sanitized_answer,
        "explicit_citations": explicit_citations,
        "sources": cited_sources,  # Only sources explicitly referenced in answer
        "follow_up_questions": follow_up_questions,
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
    
    try:
        # Initialize Vertex AI
        vertexai.init(project=PROJECT_ID, location=GENERATION_LOCATION)
        
        prompt = f"""Based on this Q&A exchange, generate {num_questions} relevant follow-up questions that would help the user explore this topic further.

Original Question: {query}

Answer: {answer[:1000]}...

Generate exactly {num_questions} natural, specific follow-up questions. Return ONLY the questions, one per line, without numbering or bullets."""
        
        model = GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(
                temperature=0.7,
                max_output_tokens=200
            )
        )
        
        questions_text = response.text.strip()
        questions = [q.strip() for q in questions_text.split('\n') if q.strip() and not q.strip().startswith('#')]
        
        # Remove any numbering (1., 2., etc.)
        cleaned_questions = []
        for q in questions:
            q = q.strip()
            # Remove leading numbers/bullets
            import re
            q = re.sub(r'^[\d]+[\.\)\-]\s*', '', q)
            q = re.sub(r'^[•\-*]\s*', '', q)
            if q and len(q) > 10:  # Filter out too-short questions
                cleaned_questions.append(q)
        
        result = cleaned_questions[:num_questions]
        logger.info(f"Generated {len(result)} follow-up questions")
        return result if result else ["What else would you like to know about this topic?"]
        
    except Exception as e:
        logger.error(f"Error generating follow-up questions: {e}")
        return [
            "What specific aspect would you like to explore further?",
            "Are there related topics you'd like to learn about?",
            "Would you like more detailed information on any part of this answer?"
        ][:num_questions]
