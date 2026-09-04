"""
Seed Index Script
=================
Reads src/core/config.py, chunks it into SemanticChunk objects, embeds them,
and upserts them into the Qdrant codebase_chunks collection so the
context agent can retrieve real code during the E2E review test.

Usage (inside backend container):
    python src/seed_index.py
"""
import uuid
import sys
import os

sys.path.insert(0, "/app")

from src.core.config import settings
from src.infrastructure.vector_db.qdrant_adapter import QdrantAdapter
from src.infrastructure.embeddings.sentence_transformer_service import SentenceTransformerService
from src.domain.models.chunk import SemanticChunk
from src.application.services.index_manager import IndexManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ID = "64e085e4-1305-4bd7-85a3-80d684351329"
FILE_PATH = "src/core/config.py"
COMMIT_HASH = "e2e-seed-001"

# ---- Read the actual file ----
abs_path = os.path.join("/app", FILE_PATH)
with open(abs_path, "r") as f:
    content = f.read()

print(f"Read {len(content)} chars from {FILE_PATH}")

lines = content.splitlines()
chunks = []

# Split into ~30-line chunks to simulate tree-sitter chunking
chunk_size = 30
for i in range(0, len(lines), chunk_size):
    chunk_lines = lines[i:i + chunk_size]
    chunk_content = "\n".join(chunk_lines)
    if chunk_content.strip():
        chunks.append(SemanticChunk(
            id=str(uuid.uuid4()),
            repo_id=REPO_ID,
            file_path=FILE_PATH,
            content=chunk_content,
            language="python",
            commit_hash=COMMIT_HASH,
            symbol_name=None,
            symbol_type="module",
            start_line=i + 1,
            end_line=min(i + chunk_size, len(lines)),
        ))

print(f"Created {len(chunks)} chunks from {FILE_PATH}")

# ---- Set up services ----
embedding_service = SentenceTransformerService()
vector_db = QdrantAdapter(url=settings.QDRANT_URL)

# ---- Index the chunks directly (skip metrics recording) ----
COLLECTION_NAME = "codebase_chunks"
vector_db.ensure_collection(COLLECTION_NAME, embedding_service.dimension)

# Delete old chunks for this file first
vector_db.delete_by_file(COLLECTION_NAME, REPO_ID, FILE_PATH)

# Generate embeddings and upsert
texts = [c.content for c in chunks]
embeddings = embedding_service.generate_embeddings(texts)
vector_db.upsert_chunks(COLLECTION_NAME, chunks, embeddings)

print(f"\n SUCCESS: Indexed {len(chunks)} chunks for repo {REPO_ID}")
print("   File: src/core/config.py")
print("   Collection: codebase_chunks")
print("   Ready for E2E review test!")
