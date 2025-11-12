"""
Image processing tool for CENTEF RAG system.
Extracts text from images using OCR (Tesseract or Google Cloud Vision API).
"""
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from PIL import Image
from google.cloud import storage

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Google Cloud Vision API for better OCR (optional, falls back to Tesseract)
try:
    from google.cloud import vision
    VISION_API_AVAILABLE = True
except ImportError:
    VISION_API_AVAILABLE = False
    logger.warning("Google Cloud Vision API not available, will use Tesseract")

# Tesseract OCR (fallback)
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.schemas import Chunk, ChunkMetadata, ChunkAnchor, write_chunks_to_jsonl
from shared.manifest import get_manifest_entry, update_manifest_entry, DocumentStatus

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID")
TARGET_BUCKET = os.getenv("TARGET_BUCKET", "centef-rag-chunks")
USE_VISION_API = os.getenv("USE_VISION_API", "true").lower() == "true"


def download_from_gcs(gcs_path: str, local_path: str) -> str:
    """
    Download file from GCS if needed.
    
    Args:
        gcs_path: GCS path (gs://bucket/path) or local path
        local_path: Where to save locally
    
    Returns:
        Local file path
    """
    if not gcs_path.startswith("gs://"):
        return gcs_path
    
    logger.info(f"Downloading {gcs_path} to {local_path}")
    
    # Parse GCS path
    parts = gcs_path.replace("gs://", "").split("/", 1)
    bucket_name = parts[0]
    blob_path = parts[1]
    
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.download_to_filename(local_path)
    
    return local_path


def extract_text_with_vision_api(image_path: str) -> str:
    """
    Extract text from image using Google Cloud Vision API.
    
    Args:
        image_path: Path to image file
    
    Returns:
        Extracted text
    """
    logger.info(f"Using Google Cloud Vision API for OCR: {image_path}")
    
    client = vision.ImageAnnotatorClient()
    
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    
    if response.error.message:
        raise Exception(f"Vision API error: {response.error.message}")
    
    texts = response.text_annotations
    
    if texts:
        # First annotation contains the entire detected text
        extracted_text = texts[0].description
        logger.info(f"Extracted {len(extracted_text)} characters using Vision API")
        return extracted_text
    else:
        logger.warning("No text detected in image")
        return ""


def extract_text_with_tesseract(image_path: str) -> str:
    """
    Extract text from image using Tesseract OCR.
    
    Args:
        image_path: Path to image file
    
    Returns:
        Extracted text
    """
    logger.info(f"Using Tesseract for OCR: {image_path}")
    
    if not TESSERACT_AVAILABLE:
        raise ImportError(
            "pytesseract is not installed. Install it with: pip install pytesseract\n"
            "Also install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki"
        )
    
    # Open image with Pillow
    image = Image.open(image_path)
    
    # Extract text
    text = pytesseract.image_to_string(image)
    
    logger.info(f"Extracted {len(text)} characters using Tesseract")
    return text


def extract_image_text(image_path: str) -> str:
    """
    Extract text from image using available OCR method.
    
    Tries Google Cloud Vision API first, falls back to Tesseract.
    
    Args:
        image_path: Path to image file (local or GCS)
    
    Returns:
        Extracted text
    """
    logger.info(f"Extracting text from image: {image_path}")
    
    # Download from GCS if needed
    if image_path.startswith("gs://"):
        local_path = f"/tmp/{os.path.basename(image_path)}"
        image_path = download_from_gcs(image_path, local_path)
    
    try:
        # Try Vision API first if enabled and available
        if USE_VISION_API and VISION_API_AVAILABLE:
            return extract_text_with_vision_api(image_path)
        else:
            return extract_text_with_tesseract(image_path)
    
    except Exception as e:
        logger.error(f"Error extracting text from image: {e}", exc_info=True)
        raise


def process_image(source_id: str, input_path: str) -> str:
    """
    Process an image file and extract text using OCR.
    
    Args:
        source_id: The source_id from manifest
        input_path: Path to image file (local or GCS)
    
    Returns:
        Path to output JSONL file in GCS
    """
    logger.info(f"Processing image for source_id={source_id}, input={input_path}")
    
    # Get manifest entry
    entry = get_manifest_entry(source_id)
    if not entry:
        raise ValueError(f"Manifest entry not found for source_id={source_id}")
    
    # Extract text using OCR
    text = extract_image_text(input_path)
    
    if not text or len(text.strip()) < 10:
        logger.warning(f"Very little text extracted from image ({len(text)} chars)")
    
    # Create a single chunk for the image
    chunk_id = f"{source_id}_image"
    
    metadata = ChunkMetadata(
        id=chunk_id,
        source_id=source_id,
        filename=entry.filename,
        title=entry.title,
        mimetype=entry.mimetype,
        author=entry.author,
        organization=entry.organization,
        date=entry.date,
        publisher=entry.publisher,
        tags=entry.tags
    )
    
    # Images don't have page or timestamp anchors
    anchor = ChunkAnchor()
    
    chunk = Chunk(
        metadata=metadata,
        anchor=anchor,
        content=text,
        chunk_index=0
    )
    
    chunks = [chunk]
    
    logger.info(f"Created 1 chunk from image with {len(text)} characters")
    
    # Write to GCS
    output_path = f"gs://{TARGET_BUCKET}/data/{source_id}.jsonl"
    
    # Write locally then upload
    local_output = f"/tmp/{source_id}.jsonl"
    write_chunks_to_jsonl(chunks, local_output)
    
    # Upload to GCS
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(TARGET_BUCKET.replace("gs://", ""))
    blob = bucket.blob(f"data/{source_id}.jsonl")
    blob.upload_from_filename(local_output)
    
    logger.info(f"Uploaded chunks to {output_path}")
    
    # Update manifest status
    update_manifest_entry(source_id, {
        "status": DocumentStatus.PENDING_SUMMARY,
        "data_path": output_path
    })
    
    logger.info(f"Updated manifest status to {DocumentStatus.PENDING_SUMMARY}")
    
    return output_path


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Process image with OCR")
    parser.add_argument("--source-id", required=True, help="Source ID from manifest")
    parser.add_argument("--input", required=True, help="Path to input image file")
    
    args = parser.parse_args()
    
    try:
        output_path = process_image(args.source_id, args.input)
        print(f"Successfully processed image. Output: {output_path}")
        return 0
    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
