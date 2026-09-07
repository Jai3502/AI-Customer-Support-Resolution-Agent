import os
import json
import re
import math
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from database.pg_client import is_postgres_available, get_db_session
from database.schema import KnowledgeVectorModel, LongTermMemoryModel

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_DIR = Path("knowledge_base")
LOCAL_VECTOR_INDEX_FILE = Path("database/vector_index.json")

# ---------------------------------------------------------------------------
# Vector Embedding Engine
# ---------------------------------------------------------------------------

def generate_embedding(text: str, dim: int = 768) -> List[float]:
    """
    Generates a dense numerical vector embedding for the given text.
    Attempts Google Gemini API Embeddings first; falls back to a deterministic,
    high-dimensional semantic hashing vector representation.
    """
    if not text or not text.strip():
        return [0.0] * dim

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    # Try Google Gemini Embeddings API if key is present
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            # Use text-embedding-004
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=text,
            )
            if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                vec = list(response.embedding.values)
                if vec and len(vec) > 0:
                    return vec
        except Exception as e:
            logger.debug(f"Gemini API Embedding fallback: {e}")

    # Fallback: High-precision token hashing & character n-gram dense embedding vector
    clean_text = text.lower().strip()
    words = re.findall(r"\w+", clean_text)
    
    vec = np.zeros(dim, dtype=np.float32)
    
    for idx, word in enumerate(words):
        # Hash word to vector index
        word_hash = hash(word) % dim
        # Positional weighting + word length signal
        weight = 1.0 + math.log1p(len(word))
        vec[word_hash] += weight
        
        # Character 3-grams for subword semantic capture
        for j in range(len(word) - 2):
            ngram = word[j:j+3]
            ngram_hash = hash(ngram) % dim
            vec[ngram_hash] += 0.3 * weight

    # L2 Normalization
    norm = np.linalg.norm(vec)
    if norm > 1e-9:
        vec = vec / norm

    return vec.tolist()


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Computes cosine similarity between two numerical vectors.
    """
    if not vec1 or not vec2:
        return 0.0
    
    v1 = np.array(vec1, dtype=np.float32)
    v2 = np.array(vec2, dtype=np.float32)

    # Pad or truncate if dimensions differ
    min_dim = min(len(v1), len(v2))
    v1 = v1[:min_dim]
    v2 = v2[:min_dim]

    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)

    if norm_v1 <= 1e-9 or norm_v2 <= 1e-9:
        return 0.0

    return float(dot_product / (norm_v1 * norm_v2))

# ---------------------------------------------------------------------------
# Vector Indexing & Knowledge Base Chunking
# ---------------------------------------------------------------------------

def chunk_document(filename: str, content: str) -> List[Dict[str, Any]]:
    """
    Splits document content into meaningful logical section chunks for indexing.
    """
    lines = content.strip().splitlines()
    title = lines[0].strip("# ") if lines else filename
    
    chunks = []
    current_chunk = []
    
    for line in lines:
        if line.startswith("##") or line.startswith("---"):
            if current_chunk:
                chunk_text = "\n".join(current_chunk).strip()
                if len(chunk_text) > 20:
                    chunks.append({
                        "filename": filename,
                        "title": title,
                        "content": chunk_text
                    })
                current_chunk = [line]
        else:
            current_chunk.append(line)
            
    if current_chunk:
        chunk_text = "\n".join(current_chunk).strip()
        if len(chunk_text) > 20:
            chunks.append({
                "filename": filename,
                "title": title,
                "content": chunk_text
            })

    # If document has no clear headers, add full text as a fallback chunk
    if not chunks and content.strip():
        chunks.append({
            "filename": filename,
            "title": title,
            "content": content.strip()
        })

    return chunks


def reindex_knowledge_base() -> Dict[str, Any]:
    """
    Reads all knowledge base document files, generates vector embeddings for chunks,
    and indexes them in PostgreSQL and local vector store.
    """
    if not KNOWLEDGE_BASE_DIR.exists():
        return {"status": "error", "message": "Knowledge base directory not found."}

    chunks_to_index = []
    for file_path in KNOWLEDGE_BASE_DIR.glob("*.txt"):
        try:
            content = file_path.read_text(encoding="utf-8")
            doc_chunks = chunk_document(file_path.name, content)
            chunks_to_index.extend(doc_chunks)
        except Exception as e:
            logger.error(f"Error reading {file_path.name}: {e}")

    if not chunks_to_index:
        return {"status": "warning", "message": "No text chunks found to index."}

    indexed_records = []
    
    for idx, item in enumerate(chunks_to_index):
        emb = generate_embedding(item["content"])
        chunk_id = f"vec_{item['filename']}_{idx}"
        
        record = {
            "id": chunk_id,
            "filename": item["filename"],
            "title": item["title"],
            "content": item["content"],
            "embedding": emb,
            "dim": len(emb)
        }
        indexed_records.append(record)

    # Save to Local JSON vector index file
    try:
        LOCAL_VECTOR_INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_VECTOR_INDEX_FILE.write_text(
            json.dumps(indexed_records, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"Error saving local vector index: {e}")

    # Sync to PostgreSQL if available
    pg_synced = 0
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                # Clear existing knowledge vectors
                session.query(KnowledgeVectorModel).delete()
                
                for rec in indexed_records:
                    kv = KnowledgeVectorModel(
                        id=rec["id"],
                        filename=rec["filename"],
                        title=rec["title"],
                        content=rec["content"],
                        embedding_json=json.dumps(rec["embedding"]),
                        vector_dim=rec["dim"]
                    )
                    session.add(kv)
                
                session.commit()
                pg_synced = len(indexed_records)
            except Exception as e:
                session.rollback()
                logger.error(f"Error writing vectors to PostgreSQL: {e}")
            finally:
                session.close()

    return {
        "status": "success",
        "total_chunks_indexed": len(indexed_records),
        "postgres_vectors_synced": pg_synced,
        "local_vector_file": str(LOCAL_VECTOR_INDEX_FILE)
    }

# ---------------------------------------------------------------------------
# Semantic Vector Search Implementation
# ---------------------------------------------------------------------------

def search_knowledge_vectors(query: str, top_k: int = 3, min_similarity: float = 0.05) -> List[Dict[str, Any]]:
    """
    Performs vector semantic search over knowledge base chunks using cosine similarity.
    Queries PostgreSQL database when available; falls back to local vector index file.
    """
    if not query or not query.strip():
        return []

    query_vector = generate_embedding(query)
    results: List[Tuple[float, Dict[str, Any]]] = []

    # 1. Try PostgreSQL Vector Query first
    if is_postgres_available():
        session = get_db_session()
        if session:
            try:
                db_vectors = session.query(KnowledgeVectorModel).all()
                if db_vectors:
                    for kv in db_vectors:
                        emb = json.loads(kv.embedding_json)
                        sim = cosine_similarity(query_vector, emb)
                        if sim >= min_similarity:
                            results.append((sim, {
                                "id": kv.id,
                                "filename": kv.filename,
                                "title": kv.title,
                                "content": kv.content,
                                "similarity_score": round(sim, 4),
                                "source": "PostgreSQL Vector DB"
                            }))
            except Exception as e:
                logger.error(f"PostgreSQL vector search error: {e}")
            finally:
                session.close()

    # 2. Fallback to Local Vector Index File if no results yet
    if not results and LOCAL_VECTOR_INDEX_FILE.exists():
        try:
            records = json.loads(LOCAL_VECTOR_INDEX_FILE.read_text(encoding="utf-8"))
            for rec in records:
                emb = rec.get("embedding", [])
                sim = cosine_similarity(query_vector, emb)
                if sim >= min_similarity:
                    results.append((sim, {
                        "id": rec.get("id"),
                        "filename": rec.get("filename"),
                        "title": rec.get("title"),
                        "content": rec.get("content"),
                        "similarity_score": round(sim, 4),
                        "source": "Local Vector Index"
                    }))
        except Exception as e:
            logger.error(f"Local vector file search error: {e}")

    # 3. If vector index is missing or empty, trigger auto-indexing once
    if not results and not LOCAL_VECTOR_INDEX_FILE.exists():
        reindex_knowledge_base()
        return search_knowledge_vectors(query, top_k=top_k, min_similarity=min_similarity)

    # Sort descending by similarity score
    results.sort(key=lambda x: x[0], reverse=True)
    
    top_matches = [item[1] for item in results[:top_k]]
    return top_matches


def search_memory_vectors(user_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Performs vector similarity search over long-term stored customer memories.
    """
    if not is_postgres_available() or not user_id:
        return []

    session = get_db_session()
    if session is None:
        return []

    try:
        memories = session.query(LongTermMemoryModel).filter(
            LongTermMemoryModel.user_id == user_id
        ).all()

        if not memories:
            return []

        query_vec = generate_embedding(query)
        scored_memories = []

        for mem in memories:
            if mem.embedding_json:
                emb = json.loads(mem.embedding_json)
            else:
                emb = generate_embedding(mem.memory_text)

            sim = cosine_similarity(query_vec, emb)
            scored_memories.append((sim, {
                "id": mem.id,
                "text": mem.memory_text,
                "category": mem.category,
                "similarity": round(sim, 4)
            }))

        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_memories[:top_k]]
    except Exception as e:
        logger.error(f"Error performing vector memory search: {e}")
        return []
    finally:
        session.close()
