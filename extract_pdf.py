import argparse
import json
import os
from enum import Enum
from uuid import uuid4
from typing import Dict, Any

import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.chunking import HybridChunker

# Load environment variables first
load_dotenv()

# Constants with type hints
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", 256))
TOKENIZER_MODEL: str = os.getenv("TOKENIZER_MODEL", 
                              "sentence-transformers/all-mpnet-base-v2")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2")
DB_CONFIG: Dict[str, str] = {
    'dbname': os.getenv("DB_NAME"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'host': os.getenv("DB_HOST"),
    'port': os.getenv("DB_PORT")
}

# Validation of required environment variables
required_env_vars = ['DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {missing_vars}")


def convert_to_dict(obj: Any) -> Dict | list | Any:
    """
        Recursively convert objects and nested structures to dictionaries.
    """
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, '__dict__'):
        return {
            key: convert_to_dict(value)
            for key, value in obj.__dict__.items()
            if not key.startswith('_')
        }
    if isinstance(obj, list):
        return [convert_to_dict(item) for item in obj]
    return obj if isinstance(obj, (int, float, str, bool, type(None))) else str(obj)


def extract_pdf(input_doc_path: str) -> list:
    """
        Extracts text chunks from a PDF document.

        Args:
            input_doc_path (str): Path to the input PDF document.

        Returns:
            List[DocChunk]: A list of text chunks extracted from the document.
    """
    from transformers import AutoTokenizer  # Lazy import

    accelerator_options = AcceleratorOptions(
        num_threads=8, 
        device=AcceleratorDevice.AUTO
    )

    pipeline_options = PdfPipelineOptions(
        accelerator_options=accelerator_options,
        images_scale=2.0,
        generate_picture_images=True
    )

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_MODEL)
    chunker = HybridChunker(
        tokenizer=tokenizer,
        max_tokens=MAX_TOKENS,
        merge_peers=True
    )

    return list(chunker.chunk(dl_doc=doc_converter.convert(input_doc_path).document))


def embed_chunks(chunks: list) -> None:
    """
        Embeds the text chunks using a pre-trained model and saves the embeddings to the database.

        Args:
            chunks (List[DocChunk]): List of text chunks to embed.
    """
    from sentence_transformers import SentenceTransformer  # Lazy import

    model = SentenceTransformer(EMBEDDING_MODEL)
    batch_size = 100
    texts = [chunk.text for chunk in chunks]
    
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            register_vector(conn)
            with conn.cursor() as cursor:
                data = []
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i+batch_size]
                    batch_embeddings = model.encode(batch_texts)
                    for text, emb in zip(batch_texts, batch_embeddings):
                        data.append((
                            str(uuid4()),
                            text,
                            json.dumps(convert_to_dict(chunks[i].meta)),
                            emb.tolist()
                        ))
                
                extras.execute_batch(
                    cursor,
                    """INSERT INTO embeddings 
                       (id, doc_fragment, metadata, embedding)
                       VALUES (%s, %s, %s, %s)""",
                    data,
                    page_size=500
                )
            conn.commit()
    except Exception as e:
        print(f"Database operation failed: {e}")
        if 'conn' in locals():
            conn.rollback()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PDF processing and embedding pipeline"
    )
    parser.add_argument("input_doc_path", help="Path to PDF document")
    args = parser.parse_args()

    print(f"Processing {args.input_doc_path}")
    chunks = extract_pdf(args.input_doc_path)
    print(f"Extracted {len(chunks)} chunks")
    embed_chunks(chunks)
    print("Embeddings successfully stored")


if __name__ == "__main__":
    main()