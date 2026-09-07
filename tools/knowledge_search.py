import re
from pathlib import Path
from database.vector_db import search_knowledge_vectors

KNOWLEDGE_BASE_DIR = Path("knowledge_base")

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "with", "about", "against", "between", "into", "through", "during",
    "before", "after", "above", "below", "from", "up", "down", "of", "off",
    "over", "under", "again", "further", "then", "once", "here", "there",
    "when", "where", "why", "how", "all", "any", "both", "each", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "can", "will", "just",
    "should", "now", "what", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "my", "i", "me",
    "you", "your", "it", "its", "this", "that", "please", "tell"
}


def search_knowledge_base(query: str) -> str:
    """
    Searches the knowledge base using Vector DB Semantic Search (Cosine Similarity).
    Falls back to weighted keyword scoring if vector matches are sparse.
    """
    if not query or not query.strip():
        return "No relevant knowledge-base information was found."

    # 1. Primary Path: Vector Database Semantic Search
    try:
        vector_results = search_knowledge_vectors(query, top_k=3, min_similarity=0.05)
        if vector_results:
            formatted = []
            for item in vector_results:
                score_pct = int(item['similarity_score'] * 100) if isinstance(item.get('similarity_score'), (int, float)) else 0
                formatted.append(f"--- Document: {item['filename']} (Semantic Relevance: {score_pct}%, Engine: {item.get('source', 'Vector DB')}) ---\n{item['content']}")
            return "\n\n".join(formatted)
    except Exception as e:
        pass

    # 2. Fallback Path: Keyword search over knowledge_base/*.txt files
    words = re.findall(r"\w+", query.lower())
    query_tokens = [w for w in words if w not in STOP_WORDS and len(w) > 1]

    if not query_tokens:
        query_tokens = [w for w in words if len(w) > 1]

    if not query_tokens:
        return "No relevant knowledge-base information was found."

    results = []

    if not KNOWLEDGE_BASE_DIR.exists():
        return "Knowledge base directory not found."

    for file_path in KNOWLEDGE_BASE_DIR.glob("*.txt"):
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        content_lower = content.lower()
        score = 0.0

        # Title match boost
        first_line = content.splitlines()[0].lower() if content.splitlines() else ""
        for token in query_tokens:
            if token in first_line:
                score += 3.0
            score += content_lower.count(token) * 1.0

        # Exact phrase match boost
        if query.strip().lower() in content_lower:
            score += 5.0

        if score > 0:
            results.append((score, file_path.name, content.strip()))

    results.sort(key=lambda x: x[0], reverse=True)

    if not results:
        return "No relevant knowledge-base information was found."

    top_results = results[:3]

    formatted = []
    for score, filename, content in top_results:
        formatted.append(f"--- Document: {filename} ---\n{content}")

    return "\n\n".join(formatted)

