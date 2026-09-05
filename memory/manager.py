import uuid
from typing import List, Dict, Any, Optional


class MemoryManager:
    """
    Manages long-term memory operations over LangGraph's SqliteStore.
    Provides structured memory storage, query-based search, profile fallback,
    deduplication, and prompt formatting.
    """

    def __init__(self, store: Optional[Any] = None):
        self.store = store

    def _get_namespace(self, user_id: str) -> tuple:
        return ("users", user_id, "memories")

    def search_memories(self, user_id: str, query: str = "", limit: int = 5) -> List[str]:
        """
        Searches long-term memories for a user.
        If no query-specific match is found or query is short/generic,
        returns all available durable memories for the user up to limit.
        """
        if not self.store or not user_id:
            return []

        namespace = self._get_namespace(user_id)
        retrieved_texts: List[str] = []
        seen_texts = set()

        # Attempt query search if query provided
        if query and len(query.strip()) > 2:
            try:
                results = self.store.search(namespace, query=query.strip(), limit=limit)
                for item in results:
                    val = item.value
                    text = val.get("text", str(val)) if isinstance(val, dict) else str(val)
                    if text not in seen_texts:
                        seen_texts.add(text)
                        retrieved_texts.append(text)
            except Exception:
                pass

        # Fallback / fill up with top profile memories if limit not reached
        if len(retrieved_texts) < limit:
            try:
                all_items = self.store.search(namespace, limit=limit * 2)
                for item in all_items:
                    val = item.value
                    text = val.get("text", str(val)) if isinstance(val, dict) else str(val)
                    if text not in seen_texts:
                        seen_texts.add(text)
                        retrieved_texts.append(text)
                    if len(retrieved_texts) >= limit:
                        break
            except Exception:
                pass

        return retrieved_texts

    def save_memory(self, user_id: str, memory_text: str, category: str = "general") -> bool:
        """
        Saves a single memory string for a user, avoiding duplicate entries.
        """
        if not self.store or not user_id or not memory_text:
            return False

        memory_text = memory_text.strip()
        if not memory_text:
            return False

        # Check existing memories to prevent exact duplicates
        existing = self.search_memories(user_id, query=memory_text, limit=10)
        for text in existing:
            if text.lower() == memory_text.lower():
                return False

        namespace = self._get_namespace(user_id)
        memory_id = str(uuid.uuid4())
        try:
            self.store.put(
                namespace,
                memory_id,
                {
                    "text": memory_text,
                    "category": category,
                },
            )
            return True
        except Exception:
            return False

    def get_all_user_memories(self, user_id: str) -> List[str]:
        """
        Returns all stored memory strings for a given user.
        """
        return self.search_memories(user_id=user_id, query="", limit=50)

    @staticmethod
    def format_memories_for_prompt(memories: List[str]) -> str:
        """
        Formats retrieved memories into a clean string for inclusion in LLM prompt context.
        """
        if not memories:
            return "No stored memories found for this customer."
        formatted = [f"- {m}" for m in memories]
        return "\n".join(formatted)
