"""
Summarization tool for CENTEF RAG system.
Reads chunks, generates summary and extracts metadata using Gemini.
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

import vertexai
from vertexai.generative_models import GenerativeModel
from google.cloud import storage

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.schemas import Chunk, Summary, read_chunks_from_jsonl, write_summary_to_jsonl
from shared.manifest import get_manifest_entry, update_manifest_entry, DocumentStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
GENERATION_LOCATION = os.getenv("GENERATION_LOCATION", "us-central1")
TARGET_BUCKET = os.getenv("TARGET_BUCKET", "centef-rag-chunks")
SUMMARY_MODEL = os.environ.get("SUMMARY_MODEL", "gemini-2.5-flash")


def download_chunks_from_gcs(source_id: str) -> str:
    """
    Download chunks JSONL from GCS to local temp file.
    
    Args:
        source_id: The source_id
    
    Returns:
        Path to local temp file
    """
    logger.info(f"Downloading chunks for source_id={source_id}")
    
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(TARGET_BUCKET.replace("gs://", ""))
    blob = bucket.blob(f"data/{source_id}.jsonl")
    
    local_path = f"/tmp/{source_id}_chunks.jsonl"
    blob.download_to_filename(local_path)
    
    logger.info(f"Downloaded to {local_path}")
    return local_path


def summarize_with_gemini(chunks: List[Chunk]) -> Dict[str, Any]:
    """
    Use Gemini to summarize chunks and extract metadata.
    
    Args:
        chunks: List of Chunk objects
    
    Returns:
        Dictionary with summary_text and extracted metadata fields
    """
    logger.info(f"Summarizing {len(chunks)} chunks with Gemini")
    
    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=GENERATION_LOCATION)
    
    # Combine all chunk content
    combined_text = "\n\n".join([
        f"[Chunk {i+1}] {chunk.content}"
        for i, chunk in enumerate(chunks)
    ])
    
    # Limit content size to avoid token limits
    max_chars = 30000
    if len(combined_text) > max_chars:
        combined_text = combined_text[:max_chars] + "\n\n[Content truncated...]"
    
    # Build prompt
    prompt = f"""
Analyze the following document content and provide:
1. A comprehensive summary (2-3 paragraphs)
2. Extracted metadata in JSON format with these fields:
   - author: string or null
   - organization: string or null
   - date: ISO date string or null (format: YYYY-MM-DD)
   - publisher: string or null
   - tags: array of relevant topic tags (3-7 tags)

Document content:
{combined_text}

Respond ONLY with valid JSON in this exact format:
{{
  "summary_text": "...",
  "author": "...",
  "organization": "...",
  "date": "...",
  "publisher": "...",
  "tags": ["tag1", "tag2", ...]
}}
"""
    
    try:
        # Call Gemini with generation config to ensure valid JSON
        model = GenerativeModel(SUMMARY_MODEL)
        
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        # Parse JSON response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Try to parse JSON
        result = json.loads(response_text)
        logger.info("Successfully generated summary with Gemini")
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        logger.info(f"Problematic response text: {response_text[:500]}...")
        
        # Try to extract JSON using regex as fallback
        import re
        try:
            # Look for JSON object pattern
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                logger.info("Successfully extracted JSON using regex fallback")
                return result
        except Exception as regex_err:
            logger.error(f"Regex fallback also failed: {regex_err}")
        
        # Try simplified prompt as last resort
        logger.warning("Attempting retry with simplified prompt")
        try:
            simplified_prompt = f"""
Summarize this document in 2-3 paragraphs. Then extract: author name, organization, date (YYYY-MM-DD), publisher, and 3-7 topic tags.

Content:
{combined_text[:20000]}

Return ONLY valid JSON with no markdown formatting:
{{"summary_text": "summary here", "author": "name or null", "organization": "org or null", "date": "YYYY-MM-DD or null", "publisher": "publisher or null", "tags": ["tag1", "tag2"]}}
"""
            
            retry_response = model.generate_content(
                simplified_prompt,
                generation_config=generation_config
            )
            
            retry_text = retry_response.text.strip()
            # Clean markdown
            if retry_text.startswith("```"):
                retry_text = re.sub(r'^```(?:json)?\s*', '', retry_text)
                retry_text = re.sub(r'```\s*$', '', retry_text)
            retry_text = retry_text.strip()
            
            result = json.loads(retry_text)
            logger.info("Successfully generated summary with simplified prompt")
            return result
            
        except Exception as retry_err:
            logger.error(f"Retry with simplified prompt failed: {retry_err}")
        
        logger.warning("All parsing attempts failed, using placeholder")
        
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        logger.warning("Falling back to placeholder response")
        
        # Fallback placeholder response
        result = {
            "summary_text": f"This document contains {len(chunks)} sections covering various topics. "
                           f"(Placeholder summary - Gemini API call failed: {str(e)})",
            "author": None,
            "organization": None,
            "date": None,
            "publisher": None,
            "tags": ["error", "fallback"]
        }
    
    return result


def summarize_chunks(source_id: str) -> str:
    """
    Summarize all chunks for a source and extract metadata.
    
    Args:
        source_id: The source_id from manifest
    
    Returns:
        Path to output summary JSONL in GCS
    """
    logger.info(f"Summarizing chunks for source_id={source_id}")
    
    # Get manifest entry
    entry = get_manifest_entry(source_id)
    if not entry:
        raise ValueError(f"Manifest entry not found for source_id={source_id}")
    
    # Download and read chunks
    local_chunks_path = download_chunks_from_gcs(source_id)
    chunks = read_chunks_from_jsonl(local_chunks_path)
    
    if not chunks:
        raise ValueError(f"No chunks found for source_id={source_id}")
    
    logger.info(f"Loaded {len(chunks)} chunks")
    
    # Summarize with Gemini
    gemini_result = summarize_with_gemini(chunks)
    
    # Create Summary object
    summary = Summary(
        source_id=source_id,
        filename=entry.filename,
        title=entry.title,
        summary_text=gemini_result["summary_text"],
        author=gemini_result.get("author"),
        organization=gemini_result.get("organization"),
        date=gemini_result.get("date"),
        publisher=gemini_result.get("publisher"),
        tags=gemini_result.get("tags", [])
    )
    
    # Write to local temp file
    local_summary_path = f"/tmp/{source_id}_summary.jsonl"
    write_summary_to_jsonl(summary, local_summary_path)
    
    # Upload to GCS
    output_path = f"gs://{TARGET_BUCKET}/summaries/{source_id}.jsonl"
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(TARGET_BUCKET.replace("gs://", ""))
    blob = bucket.blob(f"summaries/{source_id}.jsonl")
    blob.upload_from_filename(local_summary_path)
    
    logger.info(f"Uploaded summary to {output_path}")
    
    # Update manifest with extracted metadata and new status
    update_manifest_entry(source_id, {
        "status": DocumentStatus.PENDING_APPROVAL,
        "summary_path": output_path,
        "author": summary.author,
        "organization": summary.organization,
        "date": summary.date,
        "publisher": summary.publisher,
        "tags": summary.tags
    })
    
    logger.info(f"Updated manifest status to {DocumentStatus.PENDING_APPROVAL}")
    
    return output_path


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Summarize chunks and extract metadata")
    parser.add_argument("--source-id", required=True, help="Source ID from manifest")
    
    args = parser.parse_args()
    
    try:
        output_path = summarize_chunks(args.source_id)
        print(f"Successfully created summary. Output: {output_path}")
        return 0
    except Exception as e:
        logger.error(f"Error summarizing chunks: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
