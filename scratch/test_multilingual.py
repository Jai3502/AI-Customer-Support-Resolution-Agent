import sys
import os
from pathlib import Path

# Force UTF-8 output encoding for windows console
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.i18n import detect_language, translate_query_for_search, translate_text, t, SUPPORTED_LANGUAGES
from memory.runtime import Persistence
from agent.runtime import create_agent

def test_i18n():
    print("--- 1. Testing Supported Languages ---")
    print(f"Supported languages: {list(SUPPORTED_LANGUAGES.keys())}")

    print("\n--- 2. Testing UI String Localization t() ---")
    print("English:", t("view_chat", "English"))
    print("Hindi:", t("view_chat", "Hindi"))
    print("Spanish:", t("view_chat", "Spanish"))
    print("French:", t("view_chat", "French"))

    print("\n--- 3. Testing Language Detection ---")
    samples = {
        "English": "Where is my order ORD1001?",
        "Hindi": "मेरा ऑर्डर ORD1001 कहां है?",
        "Arabic": "أين هو طلبي ORD1001؟",
        "Japanese": "私の注文 ORD1001 はどこにありますか？",
        "Spanish": "¿Dónde está mi pedido ORD1001?",
    }

    for expected, text in samples.items():
        detected = detect_language(text)
        print(f"Text: '{text}' => Detected: '{detected}' (Expected: '{expected}')")

    print("\n--- 4. Testing Query Translation for Knowledge Base Search ---")
    hi_query = "रिफंड पॉलिसी क्या है?"
    translated_query = translate_query_for_search(hi_query, "Hindi")
    print(f"Hindi Query: '{hi_query}' => Translated for Search: '{translated_query}'")

    print("\n--- 5. Testing Full Multilingual Agent Invocation ---")
    persistence = Persistence()
    graph = create_agent(
        checkpointer=persistence.checkpointer,
        store=persistence.store,
    )

    hindi_input = "नमस्ते, मेरा ऑर्डर ORD1001 का स्टेटस क्या है?"
    config = {"configurable": {"thread_id": "test_thread_hindi"}}
    result = graph.invoke(
        {
            "user_id": "CUST001",
            "user_message": hindi_input,
            "language": "Hindi",
        },
        config=config
    )

    print("Agent steps:", result.get("agent_steps"))
    print("Detected language:", result.get("detected_language"))
    print("\nAgent Hindi Response:\n", result.get("response"))

if __name__ == "__main__":
    test_i18n()
