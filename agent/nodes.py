import os
import re
import json
import time
import uuid
import warnings
from typing import Literal

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI

from agent.prompts import SYSTEM_PROMPT
from tools.knowledge_search import search_knowledge_base
from tools.customer_lookup import get_customer
from tools.order_lookup import get_order, get_customer_orders
from tools.escalation import escalate_to_human
from tools.advanced_tools import (
    calculate_refund_and_fees,
    live_policy_search,
    diagnose_product_issue,
    check_inventory_and_restock,
    generate_shipping_label,
)
from tools.performance import log_trace
from memory.manager import MemoryManager
from tools.i18n import detect_language, translate_query_for_search, translate_text

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
)


def _extract_text(content) -> str:
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
# Node 1: Classify Intent
# ---------------------------------------------------------------------------
def classify_intent(state):
    t0 = time.time()
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

    detected_lang = detect_language(user_message)
    target_lang = state.get("language") or detected_lang

    elapsed_ms = (time.time() - t0) * 1000

    # Initialize node_latencies dict in state
    latencies = state.get("node_latencies", {})
    latencies["classify_intent"] = elapsed_ms

    return {
        "intent": intent,
        "confidence": confidence,
        "language": target_lang,
        "detected_language": detected_lang,
        "node_latencies": latencies,
        "agent_steps": [f"Intent classified & language detected ({target_lang})"],
    }


# ---------------------------------------------------------------------------
# Node 2: Load Memory
# ---------------------------------------------------------------------------
def load_memory(state, config, *, store):
    t0 = time.time()
    user_id = state.get("user_id", "anonymous")
    user_message = state.get("user_message", "")

    mgr = MemoryManager(store)
    memories = mgr.search_memories(user_id=user_id, query=user_message, limit=5)

    elapsed_ms = (time.time() - t0) * 1000
    latencies = state.get("node_latencies", {})
    latencies["load_memory"] = elapsed_ms

    return {
        "memories": memories,
        "node_latencies": latencies,
        "agent_steps": ["Long-term memory retrieved"],
    }


# ---------------------------------------------------------------------------
# Node 3: Retrieve Knowledge & Advanced Tools Execution
# ---------------------------------------------------------------------------
def retrieve_knowledge(state):
    t0 = time.time()
    intent = state.get("intent", "OTHER")
    user_message = state.get("user_message", "")
    detected_lang = state.get("detected_language") or detect_language(user_message)

    # Translate query to English for vector DB search precision if non-English
    search_query = translate_query_for_search(user_message, detected_lang)

    context = ""
    advanced_tool_data = {}

    if intent in {"FAQ", "REFUND", "PAYMENT", "CANCELLATION", "COMPLAINT", "OTHER"}:
        context = search_knowledge_base(search_query)
        live_policy = live_policy_search(search_query)
        advanced_tool_data["live_policy"] = live_policy

    if intent in {"COMPLAINT", "OTHER"} or any(w in user_message.lower() for w in ["not working", "broken", "issue", "faulty", "battery"]):
        diag = diagnose_product_issue(category="Hardware", issue_description=search_query)
        advanced_tool_data["diagnostic"] = diag

    if any(w in user_message.lower() for w in ["stock", "available", "inventory", "buy", "headphones", "chair", "monitor", "keyboard", "watch"]):
        inventory = check_inventory_and_restock(search_query)
        advanced_tool_data["inventory_check"] = inventory

    elapsed_ms = (time.time() - t0) * 1000
    latencies = state.get("node_latencies", {})
    latencies["retrieve_knowledge"] = elapsed_ms

    step_msg = "Knowledge base & Advanced AI tools evaluated"
    if detected_lang != "English":
        step_msg += f" (Query translated from {detected_lang} for search)"

    return {
        "knowledge_context": context,
        "advanced_tool_data": advanced_tool_data,
        "node_latencies": latencies,
        "agent_steps": [step_msg],
    }


# ---------------------------------------------------------------------------
# Node 4: Lookup Customer
# ---------------------------------------------------------------------------
def lookup_customer(state):
    t0 = time.time()
    user_id = state.get("user_id")

    if not user_id:
        elapsed_ms = (time.time() - t0) * 1000
        latencies = state.get("node_latencies", {})
        latencies["lookup_customer"] = elapsed_ms
        return {
            "customer_data": {},
            "node_latencies": latencies,
            "agent_steps": ["Customer ID unavailable"],
        }

    customer = get_customer(user_id)

    elapsed_ms = (time.time() - t0) * 1000
    latencies = state.get("node_latencies", {})
    latencies["lookup_customer"] = elapsed_ms

    return {
        "customer_data": customer if isinstance(customer, dict) else {},
        "node_latencies": latencies,
        "agent_steps": ["Customer information retrieved"],
    }


# ---------------------------------------------------------------------------
# Node 5: Lookup Order & Refund Calculation
# ---------------------------------------------------------------------------
def lookup_order(state):
    t0 = time.time()
    user_message = state.get("user_message", "")
    user_id = state.get("user_id")
    intent = state.get("intent", "OTHER")

    match = re.search(r"ORD\d+", user_message.upper())

    order_result = {}
    refund_calc = {}

    if match:
        order_id = match.group()
        order_result = get_order(order_id)

        if intent in ["REFUND", "CANCELLATION"] or "return" in user_message.lower() or "refund" in user_message.lower():
            refund_calc = calculate_refund_and_fees(
                order_id=order_id,
                return_reason=user_message,
                item_condition="Opened" if "opened" in user_message.lower() else "Unopened"
            )

    elif user_id:
        customer_orders = get_customer_orders(user_id)
        if customer_orders:
            order_result = customer_orders[0] if len(customer_orders) == 1 else {"recent_orders": customer_orders}
            target_order_id = customer_orders[0].get("order_id") if isinstance(customer_orders[0], dict) else None

            if target_order_id and (intent in ["REFUND", "CANCELLATION"] or "refund" in user_message.lower()):
                refund_calc = calculate_refund_and_fees(
                    order_id=target_order_id,
                    return_reason=user_message,
                    item_condition="Unopened"
                )

    elapsed_ms = (time.time() - t0) * 1000
    latencies = state.get("node_latencies", {})
    latencies["lookup_order"] = elapsed_ms

    advanced_data = state.get("advanced_tool_data", {})
    if refund_calc:
        advanced_data["refund_calculation"] = refund_calc
        if refund_calc.get("eligible"):
            target_id = refund_calc.get("order_id", "ORD1001")
            shipping_label = generate_shipping_label(order_id=target_id, return_reason=user_message)
            advanced_data["return_shipping_label"] = shipping_label

    return {
        "order_data": order_result,
        "advanced_tool_data": advanced_data,
        "node_latencies": latencies,
        "agent_steps": [f"Order information & Refund calculator executed"],
    }


# ---------------------------------------------------------------------------
# Node 6: Check Escalation
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
    t0 = time.time()
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

    elapsed_ms = (time.time() - t0) * 1000
    latencies = state.get("node_latencies", {})
    latencies["check_escalation"] = elapsed_ms

    return {
        "requires_human": requires_human,
        "ticket_data": ticket_data,
        "node_latencies": latencies,
        "agent_steps": steps,
    }


# ---------------------------------------------------------------------------
# Node 7: Response Generator
# ---------------------------------------------------------------------------
def generate_response(state):
    t0 = time.time()
    intent = state.get("intent", "OTHER")
    user_message = state.get("user_message", "")
    human_required = state.get("requires_human", False)
    memory_text = state.get("memories", [])
    knowledge = state.get("knowledge_context", "")
    customer = state.get("customer_data", {})
    order = state.get("order_data", {})
    advanced_tools = state.get("advanced_tool_data", {})

    formatted_memories = MemoryManager.format_memories_for_prompt(memory_text)

    target_lang = state.get("language") or state.get("detected_language") or "English"

    prompt = f"""
{SYSTEM_PROMPT}

TARGET RESPONSE LANGUAGE:
{target_lang}

CURRENT CUSTOMER REQUEST:
{user_message}

INTENT:
{intent}

LONG-TERM MEMORY (CUSTOMER PREFERENCES & HISTORY):
{formatted_memories}

KNOWLEDGE BASE CONTEXT:
{knowledge if knowledge else "No specific policy document matched."}

ADVANCED AI AGENT TOOLS ANALYSIS:
{json.dumps(advanced_tools, indent=2)}

CUSTOMER DATA:
{json.dumps(customer, indent=2)}

ORDER DATA:
{json.dumps(order, indent=2)}

HUMAN ESCALATION REQUIRED:
{human_required}

INSTRUCTIONS:
1. Output your entire customer-facing response natively in {target_lang}.
2. Ensure order numbers (e.g. ORD1001), ticket IDs, monetary values, and exact policy rules are preserved accurately.
3. If advanced tool outputs (like refund calculations or troubleshooting steps) are available, detail them clearly in {target_lang}.
4. If human escalation is required, explain clearly in {target_lang} that a human support ticket has been opened.
5. Maintain an empathetic, warm, natural, and professional tone.
"""

    response = llm.invoke(prompt)
    text = _extract_text(response.content)

    elapsed_ms = (time.time() - t0) * 1000
    latencies = state.get("node_latencies", {})
    latencies["generate_response"] = elapsed_ms

    # Estimate token usage
    prompt_tokens_est = len(prompt.split()) * 2
    completion_tokens_est = len(text.split()) * 2

    return {
        "response": text.strip(),
        "node_latencies": latencies,
        "prompt_tokens": prompt_tokens_est,
        "completion_tokens": completion_tokens_est,
        "agent_steps": ["Response generated"],
    }


# ---------------------------------------------------------------------------
# Node 8: Memory Extraction
# ---------------------------------------------------------------------------
class MemoryExtraction(BaseModel):
    should_save: bool
    memories: list[str] = Field(default_factory=list)


def extract_memory(state):
    t0 = time.time()
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
"""

    try:
        result = extractor.invoke(prompt)
        candidates = result.memories if result.should_save else []
    except Exception:
        candidates = []

    elapsed_ms = (time.time() - t0) * 1000
    latencies = state.get("node_latencies", {})
    latencies["extract_memory"] = elapsed_ms

    return {
        "memory_candidates": candidates,
        "node_latencies": latencies,
        "agent_steps": ["Memory extraction analyzed"],
    }


# ---------------------------------------------------------------------------
# Node 9: Save Memory & Telemetry Log
# ---------------------------------------------------------------------------
def save_memory(state, config, *, store):
    t0 = time.time()
    user_id = state.get("user_id", "anonymous")
    candidates = state.get("memory_candidates", [])

    mgr = MemoryManager(store)
    saved_count = 0
    for memory in candidates:
        if mgr.save_memory(user_id, memory):
            saved_count += 1

    elapsed_ms = (time.time() - t0) * 1000
    latencies = state.get("node_latencies", {})
    latencies["save_memory"] = elapsed_ms

    # Compute total latency across all nodes
    total_ms = sum(latencies.values())

    thread_id = config.get("configurable", {}).get("thread_id", str(uuid.uuid4()))
    intent = state.get("intent", "General")

    # Record trace into Performance Monitor APM
    log_trace(
        thread_id=thread_id,
        user_id=user_id,
        intent=intent,
        total_latency_ms=total_ms,
        node_latencies=latencies,
        prompt_tokens=state.get("prompt_tokens", 500),
        completion_tokens=state.get("completion_tokens", 150),
        status="success"
    )

    return {
        "node_latencies": latencies,
        "agent_steps": [f"Long-term memory updated ({saved_count} new) & APM trace logged"],
    }