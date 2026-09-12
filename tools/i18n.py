import os
import re
import warnings
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Lazy-loaded LLM instance for fast translation & detection
_llm = None

def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
        )
    return _llm


# ---------------------------------------------------------------------------
# Supported Languages Registry
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    "English": {"code": "en", "flag": "🇬🇧", "native": "English", "dir": "ltr"},
    "Hindi": {"code": "hi", "flag": "🇮🇳", "native": "हिन्दी", "dir": "ltr"},
    "Spanish": {"code": "es", "flag": "🇪🇸", "native": "Español", "dir": "ltr"},
    "French": {"code": "fr", "flag": "🇫🇷", "native": "Français", "dir": "ltr"},
    "German": {"code": "de", "flag": "🇩🇪", "native": "Deutsch", "dir": "ltr"},
    "Japanese": {"code": "ja", "flag": "🇯🇵", "native": "日本語", "dir": "ltr"},
    "Arabic": {"code": "ar", "flag": "🇸🇦", "native": "العربية", "dir": "rtl"},
}

DEFAULT_LANGUAGE = "English"

# ---------------------------------------------------------------------------
# Comprehensive UI Localization Dictionary (i18n)
# ---------------------------------------------------------------------------
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # App & Navigation
    "app_title": {
        "English": "AI Customer Support Portal",
        "Hindi": "एआई ग्राहक सेवा पोर्टल",
        "Spanish": "Portal de Atención al Cliente IA",
        "French": "Portail d'Assistance Client IA",
        "German": "KI-Kundendienstportal",
        "Japanese": "AIカスタマーサポートポータル",
        "Arabic": "بوابة خدمة العملاء بالذكاء الاصطناعي",
    },
    "select_language": {
        "English": "🌐 Preferred Language",
        "Hindi": "🌐 पसंदीदा भाषा",
        "Spanish": "🌐 Idioma preferido",
        "French": "🌐 Langue préférée",
        "German": "🌐 Bevorzugte Sprache",
        "Japanese": "🌐 優先言語",
        "Arabic": "🌐 اللغة المفضلة",
    },
    "nav_portal": {
        "English": "🧭 Portal Navigation",
        "Hindi": "🧭 पोर्टल नेविगेशन",
        "Spanish": "🧭 Navegación del portal",
        "French": "🧭 Navigation du portail",
        "German": "🧭 Portal-Navigation",
        "Japanese": "🧭 ポータルナビゲーション",
        "Arabic": "🧭 التنقل في البوابة",
    },
    "view_chat": {
        "English": "🎧 AI Support Chat",
        "Hindi": "🎧 एआई सपोर्ट चैट",
        "Spanish": "🎧 Chat de Soporte IA",
        "French": "🎧 Chat Support IA",
        "German": "🎧 KI-Support-Chat",
        "Japanese": "🎧 AIサポートチャット",
        "Arabic": "🎧 الدردشة مع الدعم الذكي",
    },
    "view_admin": {
        "English": "👨💼 Admin Dashboard",
        "Hindi": "👨💼 एडमिन डैशबोर्ड",
        "Spanish": "👨💼 Panel de Administración",
        "French": "👨💼 Tableau de bord Admin",
        "German": "👨💼 Admin-Dashboard",
        "Japanese": "👨💼 管理者ダッシュボード",
        "Arabic": "👨💼 لوحة التحكم الإدارية",
    },
    "view_omnichannel": {
        "English": "📡 Email & WhatsApp Hub",
        "Hindi": "📡 ईमेल और व्हाट्सएप हब",
        "Spanish": "📡 Centro de Email y WhatsApp",
        "French": "📡 Hub E-mail & WhatsApp",
        "German": "📡 E-Mail & WhatsApp Hub",
        "Japanese": "📡 メール＆WhatsAppハブ",
        "Arabic": "📡 مركز البريد والواتساب",
    },
    "view_analytics": {
        "English": "📊 Support & APM Analytics",
        "Hindi": "📊 सपोर्ट और एपीएम एनालिटिक्स",
        "Spanish": "📊 Analítica de Soporte y APM",
        "French": "📊 Analytics Support & APM",
        "German": "📊 Support & APM Analysen",
        "Japanese": "📊 サポート＆APMアナリティクス",
        "Arabic": "📊 تحليلات الدعم وأداء النظام",
    },
    "sign_out": {
        "English": "🚪 Sign Out",
        "Hindi": "🚪 साइन आउट करें",
        "Spanish": "🚪 Cerrar sesión",
        "French": "🚪 Déconnexion",
        "German": "🚪 Abmelden",
        "Japanese": "🚪 サインアウト",
        "Arabic": "🚪 تسجيل الخروج",
    },

    # Customer Profile & Memory Labels
    "customer_profile": {
        "English": "👤 Customer Profile Context",
        "Hindi": "👤 ग्राहक प्रोफ़ाइल संदर्भ",
        "Spanish": "👤 Contexto del Perfil de Cliente",
        "French": "👤 Contexte du Profil Client",
        "German": "👤 Kundenprofil-Kontext",
        "Japanese": "👤 顧客プロファイルコンテキスト",
        "Arabic": "👤 سياق ملف العميل",
    },
    "tier": {
        "English": "Tier",
        "Hindi": "स्तर (Tier)",
        "Spanish": "Nivel",
        "French": "Niveau",
        "German": "Stufe",
        "Japanese": "ティア",
        "Arabic": "الفئة",
    },
    "lang": {
        "English": "Lang",
        "Hindi": "भाषा",
        "Spanish": "Idioma",
        "French": "Langue",
        "German": "Sprache",
        "Japanese": "言語",
        "Arabic": "اللغة",
    },
    "orders": {
        "English": "Orders",
        "Hindi": "ऑर्डर",
        "Spanish": "Pedidos",
        "French": "Commandes",
        "German": "Bestellungen",
        "Japanese": "注文数",
        "Arabic": "الطلبات",
    },
    "city": {
        "English": "City",
        "Hindi": "शहर",
        "Spanish": "Ciudad",
        "French": "Ville",
        "German": "Stadt",
        "Japanese": "都市",
        "Arabic": "المدينة",
    },
    "my_tickets": {
        "English": "🎫 My Support Tickets",
        "Hindi": "🎫 मेरे सहायता टिकट",
        "Spanish": "🎫 Mis Tickets de Soporte",
        "French": "🎫 Mes Tickets de Support",
        "German": "🎫 Meine Support-Tickets",
        "Japanese": "🎫 サポートチケット一覧",
        "Arabic": "🎫 تذاكر الدعم الخاصة بي",
    },
    "no_tickets": {
        "English": "No open tickets.",
        "Hindi": "कोई खुला टिकट नहीं है।",
        "Spanish": "No hay tickets abiertos.",
        "French": "Aucun ticket ouvert.",
        "German": "Keine offenen Tickets.",
        "Japanese": "オープンなチケットはありません。",
        "Arabic": "لا توجد تذاكر مفتوحة.",
    },
    "agent_memory": {
        "English": "🧠 Agent Long-Term Memory",
        "Hindi": "🧠 एजेंट दीर्घकालिक स्मृति (Memory)",
        "Spanish": "🧠 Memoria a largo plazo del Agente",
        "French": "🧠 Mémoire à long terme de l'Agent",
        "German": "🧠 Langzeitgedächtnis des Agenten",
        "Japanese": "🧠 エージェントの長期記憶",
        "Arabic": "🧠 الذاكرة طويلة المدى للوكيل",
    },
    "no_memories": {
        "English": "No long-term memories saved yet.",
        "Hindi": "अभी तक कोई दीर्घकालिक यादें सहेजी नहीं गई हैं।",
        "Spanish": "No hay memorias a largo plazo guardadas aún.",
        "French": "Aucune mémoire à long terme enregistrée.",
        "German": "Noch keine Langzeiterinnerungen gespeichert.",
        "Japanese": "長期記憶はまだ保存されていません。",
        "Arabic": "لم يتم حفظ أي ذكريات طويلة المدى بعد.",
    },
    "new_conversation": {
        "English": "🆕 New Conversation",
        "Hindi": "🆕 नई बातचीत",
        "Spanish": "🆕 Nueva Conversación",
        "French": "🆕 Nouvelle Conversation",
        "German": "🆕 Neue Unterhaltung",
        "Japanese": "🆕 新しい会話",
        "Arabic": "🆕 محادثة جديدة",
    },

    # Chat Input & Actions
    "chat_placeholder": {
        "English": "Ask a question about your order, returns, or support...",
        "Hindi": "अपने ऑर्डर, रिटर्न या सहायता के बारे में प्रश्न पूछें...",
        "Spanish": "Haz una pregunta sobre tu pedido, devoluciones o soporte...",
        "French": "Posez une question sur votre commande, retours ou assistance...",
        "German": "Stellen Sie eine Frage zu Ihrer Bestellung, Rückgabe oder Support...",
        "Japanese": "注文、返品、またはサポートについて質問する...",
        "Arabic": "إطرح سؤالاً حول طلبك، الإرجاع، أو الدعم...",
    },
    "thinking": {
        "English": "Thinking & Resolving...",
        "Hindi": "सोच रहा है और समाधान निकाल रहा है...",
        "Spanish": "Pensando y resolviendo...",
        "French": "Réflexion et résolution en cours...",
        "German": "Nachdenken und Lösen...",
        "Japanese": "思考中および解決中...",
        "Arabic": "جاري التفكير والتنفيذ...",
    },
    "ticket_created": {
        "English": "Ticket Created",
        "Hindi": "टिकट बनाया गया",
        "Spanish": "Ticket Creado",
        "French": "Ticket Créé",
        "German": "Ticket Erstellt",
        "Japanese": "チケット作成済み",
        "Arabic": "تم إنشاء التذكرة",
    },

    # Admin Desk Labels
    "admin_title": {
        "English": "👨💼 Human Support & Admin Desk",
        "Hindi": "👨💼 मानव सहायता और व्यवस्थापक डेस्क",
        "Spanish": "👨💼 Mesa de Administración y Soporte Humano",
        "French": "👨💼 Support Humain & Bureau Admin",
        "German": "👨💼 Menschlicher Support & Admin-Desk",
        "Japanese": "👨💼 人工サポート＆管理者デスク",
        "Arabic": "👨💼 مكتب الدعم البشري والإدارة",
    },

    # Auth View Labels
    "auth_title": {
        "English": "🔐 Support Portal Authentication",
        "Hindi": "🔐 सहायता पोर्टल प्रमाणीकरण",
        "Spanish": "🔐 Autenticación del Portal de Soporte",
        "French": "🔐 Authentification du Portail Support",
        "German": "🔐 Support-Portal Authentifizierung",
        "Japanese": "🔐 サポートポータル認証",
        "Arabic": "🔐 مصادقة بوابة الدعم",
    },
    "login_button": {
        "English": "🚀 Log In to Portal",
        "Hindi": "🚀 पोर्टल में लॉगिन करें",
        "Spanish": "🚀 Iniciar Sesión en el Portal",
        "French": "🚀 Connexion au Portail",
        "German": "🚀 Am Portal Anmelden",
        "Japanese": "🚀 ポータルにログイン",
        "Arabic": "🚀 تسجيل الدخول إلى البوابة",
    },
}


def t(key: str, lang: Optional[str] = None) -> str:
    """Look up localized string for `key` in `lang` (fallback to English)."""
    if not lang:
        lang = DEFAULT_LANGUAGE

    # Normalize language name
    lang_normalized = lang.capitalize()
    if lang_normalized not in SUPPORTED_LANGUAGES:
        lang_normalized = DEFAULT_LANGUAGE

    entry = TRANSLATIONS.get(key, {})
    return entry.get(lang_normalized, entry.get(DEFAULT_LANGUAGE, key))


# ---------------------------------------------------------------------------
# Language Detection & AI Translation Utilities
# ---------------------------------------------------------------------------
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


def detect_language(text: str) -> str:
    """Detect the primary language of the text."""
    if not text or len(text.strip()) == 0:
        return "English"

    # Fast script heuristics
    # Devanagari script (Hindi)
    if re.search(r"[\u0900-\u097F]", text):
        return "Hindi"
    # Arabic script
    if re.search(r"[\u0600-\u06FF]", text):
        return "Arabic"
    # Japanese script (Hiragana, Katakana, Kanji)
    if re.search(r"[\u3040-\u30FF\u4E00-\u9FFF]", text):
        return "Japanese"

    # Fallback to LLM language detector for European/Latin script ambiguities
    try:
        llm_instance = get_llm()
        prompt = f"""
Identify the primary language of this customer message.
Message: "{text}"

Return ONLY one language name from this list:
English, Hindi, Spanish, French, German, Japanese, Arabic.
"""
        response = llm_instance.invoke(prompt)
        res_text = _extract_text(response.content)
        detected = res_text.strip().capitalize()
        for lang_name in SUPPORTED_LANGUAGES.keys():
            if lang_name in detected:
                return lang_name
    except Exception:
        pass

    return "English"


def translate_text(text: str, target_language: str) -> str:
    """Translate arbitrary text to target_language using Gemini."""
    if not text or target_language == "English":
        # Check if text is mostly English already
        return text

    try:
        llm_instance = get_llm()
        prompt = f"""
Translate the following text into {target_language}.
Maintain the exact meaning, technical terms, order numbers (e.g. ORD1001), tracking codes, product names, and formatting.

Text to translate:
{text}

Translated output:
"""
        response = llm_instance.invoke(prompt)
        translated = _extract_text(response.content)
        return translated.strip()
    except Exception:
        return text


def translate_query_for_search(query: str, detected_lang: str) -> str:
    """Translate a non-English search query into English for vector knowledge base retrieval."""
    if detected_lang == "English":
        return query

    try:
        llm_instance = get_llm()
        prompt = f"""
Translate this customer search query from {detected_lang} into English for semantic vector database search.
Keep it concise and preserve key technical nouns, order numbers, and return terms.

Query: "{query}"

English Search Query:
"""
        response = llm_instance.invoke(prompt)
        res_text = _extract_text(response.content)
        return res_text.strip()
    except Exception:
        return query
