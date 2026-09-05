from typing import TypedDict, List, Dict, Any


class AgentState(TypedDict, total=False):
    messages: List[Dict[str, Any]]
    user_id: str
    user_message: str
    intent: str
    confidence: float
    memories: List[str]
    memory_candidates: List[str]
    knowledge_context: str
    customer_data: Dict[str, Any]
    order_data: Dict[str, Any]
    ticket_data: Dict[str, Any]
    requires_human: bool
    response: str
    agent_steps: List[str]