"""
Synthesizer for CENTEF RAG system.
Combines retrieval results and generates answers using Gemini.
"""
import logging
import os
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

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
        "INSTRUCTIONS:",
        "1. Answer the user's question using the information from the provided summaries and chunks below",
        "2. Be specific and cite sources by mentioning document titles and page numbers",
        "3. If abbreviations like AML, CTF, CFT appear in the documents, use the full terms in your answer",
        "4. Synthesize information across multiple sources when relevant",
        "5. Structure your answer clearly with relevant sections if appropriate",
        "6. If the context is insufficient, clearly state what additional information would be needed",
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
    prompt_parts.append("Please provide a comprehensive answer to the user's question based on the context above.")
    prompt_parts.append("Include specific citations (document titles and page numbers) to support your answer.")
    
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
    
    try:
        # Initialize Gemini model
        model = GenerativeModel(GEMINI_MODEL)
        
        # Configure generation
        generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            top_p=0.95,
        )
        
        # Generate answer
        logger.info(f"Calling Gemini model: {GEMINI_MODEL}")
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        answer_text = response.text
        logger.info(f"Generated answer length: {len(answer_text)} characters")
        
    except Exception as e:
        logger.error(f"Error generating answer with Gemini: {e}")
        # Fallback response
        answer_text = (
            f"I apologize, but I encountered an error while generating an answer. "
            f"However, I found {len(summary_results)} relevant document summaries and "
            f"{len(chunk_results)} detailed chunks that may help answer your question about: {query}"
        )
    
    # Extract source citations from results
    sources = []
    seen_sources = set()
    
    for summary in summary_results:
        source_id = summary.get('source_id')
        if source_id and source_id not in seen_sources:
            sources.append({
                "source_id": source_id,
                "title": summary.get('title'),
                "filename": summary.get('filename'),
                "type": "summary"
            })
            seen_sources.add(source_id)
    
    for chunk in chunk_results:
        source_id = chunk.get('source_id')
        if source_id and source_id not in seen_sources:
            sources.append({
                "source_id": source_id,
                "title": chunk.get('title'),
                "filename": chunk.get('filename'),
                "page": chunk.get('page_number'),
                "start_sec": chunk.get('start_sec'),
                "end_sec": chunk.get('end_sec'),
                "type": "chunk"
            })
            seen_sources.add(source_id)
    
    return {
        "query": query,
        "answer": answer_text,
        "sources": sources,
        "num_summaries_used": len(summary_results),
        "num_chunks_used": len(chunk_results),
        "model": GEMINI_MODEL,
        "temperature": temperature
    }


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
