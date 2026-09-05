import os
import re
import json
import uuid
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI

from agent.prompts import SYSTEM_PROMPT
from tools.knowledge_search import search_knowledge_base
from tools.customer_lookup import get_customer
from tools.order_lookup import get_order, get_customer_orders
from tools.escalation import escalate_to_human
from memory.manager import MemoryManager

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    temperature=0.2,
    thinking_level="minimal",
)


def _extract_text(content) -> str:
    """
    Gemini 3.x can return content as a plain string OR as a list of
    content blocks, e.g. [{'type': 'text', 'text': '...', 'extras': {...}}].
    Pull only the actual text out, ignore signatures/extras/thinking blocks.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and "text" in block:
                    parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)

    return str(content)


# ---------------------------------------------------------------------------
# PART 16 -- Intent schema
# ---------------------------------------------------------------------------
class IntentResult(BaseModel):
    intent: Literal[
        "FAQ",
        "ORDER",
        "PAYMENT",
        "REFUND",
        "CANCELLATION",
        "COMPLAINT",
        "OTHER",
    ]
    confidence: float = Field(ge=0, le=1)
    reason: str


# ---------------------------------------------------------------------------
# PART 17 -- Intent classifier
# ---------------------------------------------------------------------------
def classify_intent(state):
    user_message = state.get("user_message", "")

    classifier = llm.with_structured_output(IntentResult)

    prompt = f"""
Classify the customer's request.

Customer message:
{user_message}

Choose exactly one intent:
FAQ
ORDER
PAYMENT
REFUND
CANCELLATION
COMPLAINT
OTHER

Return the intent, confidence and a short reason.
"""

    try:
        result = classifier.invoke(prompt)
        intent = result.intent
        confidence = result.confidence
    except Exception:
        intent = "OTHER"
        confidence = 0.5

    return {
        "intent": intent,
        "confidence": confidence,
        "agent_steps": ["Intent classified"],
    }


# ---------------------------------------------------------------------------
# PART 18 -- Load long-term memory
# ---------------------------------------------------------------------------
def load_memory(state, config, *, store):
    user_id = state.get("user_id", "anonymous")
    user_message = state.get("user_message", "")

    mgr = MemoryManager(store)
    memories = mgr.search_memories(user_id=user_id, query=user_message, limit=5)

    return {
        "memories": memories,
        "agent_steps": ["Long-term memory retrieved"],
    }


# ---------------------------------------------------------------------------
# PART 19 -- Knowledge retrieval
# ---------------------------------------------------------------------------
def retrieve_knowledge(state):
    intent = state.get("intent", "OTHER")
    user_message = state.get("user_message", "")

    if intent in {"FAQ", "REFUND", "PAYMENT", "CANCELLATION", "COMPLAINT", "OTHER"}:
        context = search_knowledge_base(user_message)
    else:
        context = ""

    return {
        "knowledge_context": context,
        "agent_steps": ["Knowledge base searched"],
    }


# ---------------------------------------------------------------------------
# PART 20 -- Customer lookup
# ---------------------------------------------------------------------------
def lookup_customer(state):
    user_id = state.get("user_id")

    if not user_id:
        return {
            "customer_data": {},
            "agent_steps": ["Customer ID unavailable"],
        }

    customer = get_customer(user_id)

    return {
        "customer_data": customer if isinstance(customer, dict) else {},
        "agent_steps": ["Customer information retrieved"],
    }


# ---------------------------------------------------------------------------
# PART 21 -- Order lookup
# ---------------------------------------------------------------------------
def lookup_order(state):
    user_message = state.get("user_message", "")
    user_id = state.get("user_id")

    match = re.search(r"ORD\d+", user_message.upper())

    if match:
        order_id = match.group()
        order = get_order(order_id)
        return {
            "order_data": order,
            "agent_steps": [f"Order {order_id} retrieved"],
        }

    # If no explicit order ID in query, search recent orders for this customer
    if user_id:
        customer_orders = get_customer_orders(user_id)
        if customer_orders:
            # Return list of orders if multiple, or single dict if 1
            return {
                "order_data": customer_orders[0] if len(customer_orders) == 1 else {"recent_orders": customer_orders},
                "agent_steps": [f"Retrieved {len(customer_orders)} customer orders"],
            }

    return {
        "order_data": {},
        "agent_steps": ["No order records found"],
    }


# ---------------------------------------------------------------------------
# PART 22 -- Human escalation check
# ---------------------------------------------------------------------------
HIGH_RISK_WORDS = [
    "fraud",
    "scam",
    "double charged",
    "charged twice",
    "duplicate payment",
    "lawsuit",
    "legal",
    "angry",
    "complaint",
    "terrible",
    "threat",
]

LOW_CONFIDENCE_THRESHOLD = 0.50


def check_escalation(state):
    intent = state.get("intent", "OTHER")
    user_message = state.get("user_message", "").lower()
    confidence = state.get("confidence", 1.0)
    customer_data = state.get("customer_data", {}) or {}

    risky = any(word in user_message for word in HIGH_RISK_WORDS)
    low_confidence = confidence < LOW_CONFIDENCE_THRESHOLD

    requires_human = bool(risky or intent == "COMPLAINT" or low_confidence)

    steps = ["Escalation checked"]
    ticket_data = {}

    if requires_human:
        customer_id = customer_data.get("customer_id", state.get("user_id", "unknown"))
        reason = f"Intent={intent}, confidence={confidence:.2f}. Message: {state.get('user_message', '')}"

        result = escalate_to_human(
            customer_id=customer_id,
            reason=reason,
            priority="High" if risky else "Medium",
        )
        ticket_data = result.get("ticket", {})
        steps.append(f"Escalated to human ({ticket_data.get('ticket_id', 'unknown')})")

    return {
        "requires_human": requires_human,
        "ticket_data": ticket_data,
        "agent_steps": steps,
    }


# ---------------------------------------------------------------------------
# PART 23 -- Response generator
# ---------------------------------------------------------------------------
def generate_response(state):
    intent = state.get("intent", "OTHER")
    user_message = state.get("user_message", "")
    human_required = state.get("requires_human", False)
    memory_text = state.get("memories", [])
    knowledge = state.get("knowledge_context", "")
    customer = state.get("customer_data", {})
    order = state.get("order_data", {})

    formatted_memories = MemoryManager.format_memories_for_prompt(memory_text)

    prompt = f"""
{SYSTEM_PROMPT}

CURRENT CUSTOMER REQUEST:
{user_message}

INTENT:
{intent}

LONG-TERM MEMORY (CUSTOMER PREFERENCES & HISTORY):
{formatted_memories}

KNOWLEDGE BASE CONTEXT:
{knowledge if knowledge else "No specific policy document matched."}

CUSTOMER DATA:
{json.dumps(customer, indent=2)}

ORDER DATA:
{json.dumps(order, indent=2)}

HUMAN ESCALATION REQUIRED:
{human_required}

Generate the best customer-facing response.
If human escalation is required:
- Clearly explain that the issue is being escalated for human agent review.
- Provide reassurance and mention the created support ticket if available.
Keep the response warm, natural, and helpful.
"""

    response = llm.invoke(prompt)
    text = _extract_text(response.content)

    return {
        "response": text.strip(),
        "agent_steps": ["Response generated"],
    }


# ---------------------------------------------------------------------------
# PART 24 -- Memory extraction
# ---------------------------------------------------------------------------
class MemoryExtraction(BaseModel):
    should_save: bool
    memories: list[str] = Field(default_factory=list)


def extract_memory(state):
    user_message = state.get("user_message", "")
    response = state.get("response", "")

    extractor = llm.with_structured_output(MemoryExtraction)

    prompt = f"""
You are a long-term memory extraction system.

Analyze this customer interaction.

USER:
{user_message}

ASSISTANT:
{response}

Extract only durable information that is useful in future customer interactions.
Good memories include:
- Customer's preferred language or communication style
- Customer's preferred name or title
- Product preferences or specific concerns (e.g. ergonomic interest, tech enthusiasm)
- Specific persistent complaints or past delivery preferences

Do NOT save:
- Generic greetings ("Hi", "Hello")
- Standard operational facts already in database (like order status or address)
- Temporary one-time status checks

Return should_save=true only if useful durable context exists.
"""

    try:
        result = extractor.invoke(prompt)
        candidates = result.memories if result.should_save else []
    except Exception:
        candidates = []

    return {
        "memory_candidates": candidates,
        "agent_steps": ["Memory extraction analyzed"],
    }


# ---------------------------------------------------------------------------
# PART 25 -- Save long-term memory
# ---------------------------------------------------------------------------
def save_memory(state, config, *, store):
    user_id = state.get("user_id", "anonymous")
    candidates = state.get("memory_candidates", [])

    mgr = MemoryManager(store)
    saved_count = 0
    for memory in candidates:
        if mgr.save_memory(user_id, memory):
            saved_count += 1

    return {
        "agent_steps": [f"Long-term memory updated ({saved_count} new)"],
    }