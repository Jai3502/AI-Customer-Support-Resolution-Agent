import re
from pathlib import Path

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
    Enhanced search over knowledge_base/*.txt files with weighted scoring,
    stop-word filtering, and section matching.
    """
    if not query:
        return "No relevant knowledge-base information was found."

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
