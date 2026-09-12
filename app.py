import uuid
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

import streamlit as st

from memory.runtime import Persistence
from memory.manager import MemoryManager
from agent.runtime import create_agent
from auth import (
    has_permission,
    PERM_CHAT_SUPPORT,
    PERM_VIEW_ADMIN_DESK,
    PERM_VIEW_ANALYTICS,
    PERM_VIEW_PERFORMANCE,
    PERM_MANAGE_CHANNELS,
)
from views.auth_view import render_auth_view
from views.chat_view import render_chat_view
from views.admin_view import render_admin_dashboard
from views.analytics_view import render_analytics_dashboard
from views.omnichannel_view import render_omnichannel_view
from tools.i18n import SUPPORTED_LANGUAGES, t

# ---------------------------------------------------------------------------
# Page Configuration & Modern Design System
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Customer Support Portal",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0e1117;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
    }
    
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
    }
    
    .role-badge {
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        color: white;
    }
    .role-admin { background: linear-gradient(135deg, #4f46e5, #7c3aed); }
    .role-agent { background: linear-gradient(135deg, #2563eb, #0284c7); }
    .role-auditor { background: linear-gradient(135deg, #d97706, #b45309); }
    .role-customer { background: linear-gradient(135deg, #059669, #10b981); }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Global Graph & Persistence Initialization
# ---------------------------------------------------------------------------
@st.cache_resource
def get_persistence():
    return Persistence()


persistence = get_persistence()
graph = create_agent(
    checkpointer=persistence.checkpointer,
    store=persistence.store,
)
memory_mgr = MemoryManager(persistence.store)

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user" not in st.session_state:
    st.session_state.user = None

if "role" not in st.session_state:
    st.session_state.role = None

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "customer_id" not in st.session_state:
    st.session_state.customer_id = "CUST001"

if "active_view" not in st.session_state:
    st.session_state.active_view = "🎧 AI Support Chat"

if "language" not in st.session_state:
    st.session_state.language = "English"

# ---------------------------------------------------------------------------
# Authentication Routing Guard
# ---------------------------------------------------------------------------
if not st.session_state.authenticated:
    render_auth_view()
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar User Profile & Navigation Controls
# ---------------------------------------------------------------------------
user = st.session_state.user or {}
user_role = (st.session_state.get("role") or "customer").lower()

role_badge_class = f"role-{user_role}"
role_label = user_role.capitalize()
if user_role == "admin":
    role_label = "👨💼 Super Admin"
elif user_role == "agent":
    role_label = "🎧 Support Agent"
elif user_role == "auditor":
    role_label = "📊 Auditor"
else:
    role_label = "👤 Customer"

lang_code = st.session_state.get("language", "English")

with st.sidebar:
    st.markdown(f"### 👋 {user.get('name', 'User')} <span class='role-badge {role_badge_class}'>{role_label}</span>", unsafe_allow_html=True)
    st.caption(f"📧 `{user.get('email', '')}`")

    st.divider()

    # --- Global Language Selector ---
    lang_keys = list(SUPPORTED_LANGUAGES.keys())
    current_idx = lang_keys.index(lang_code) if lang_code in lang_keys else 0
    selected_lang = st.selectbox(
        t("select_language", lang_code),
        options=lang_keys,
        format_func=lambda x: f"{SUPPORTED_LANGUAGES[x]['flag']} {x} ({SUPPORTED_LANGUAGES[x]['native']})",
        index=current_idx,
        key="global_lang_select",
    )
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.rerun()

    st.divider()

    st.markdown(f"### {t('nav_portal', lang_code)}")

    # Generate available views according to RBAC permissions
    views = []
    if has_permission(user_role, PERM_CHAT_SUPPORT):
        views.append("🎧 AI Support Chat")

    if has_permission(user_role, PERM_VIEW_ADMIN_DESK):
        views.append("👨💼 Admin Dashboard")

    if has_permission(user_role, PERM_MANAGE_CHANNELS):
        views.append("📡 Email & WhatsApp Hub")

    if has_permission(user_role, PERM_VIEW_ANALYTICS) or has_permission(user_role, PERM_VIEW_PERFORMANCE):
        views.append("📊 Support & APM Analytics")

    if not views:
        views = ["🎧 AI Support Chat"]

    if st.session_state.active_view not in views:
        st.session_state.active_view = views[0]

    selected_view = st.radio(
        "Select Module",
        options=views,
        format_func=lambda v: {
            "🎧 AI Support Chat": t("view_chat", lang_code),
            "👨💼 Admin Dashboard": t("view_admin", lang_code),
            "📡 Email & WhatsApp Hub": t("view_omnichannel", lang_code),
            "📊 Support & APM Analytics": t("view_analytics", lang_code),
        }.get(v, v),
        index=views.index(st.session_state.active_view),
        key="nav_radio",
    )

    st.session_state.active_view = selected_view

    st.divider()

    if st.button(t("sign_out", lang_code), use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.role = None
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------------------------
# View Rendering Switcher
# ---------------------------------------------------------------------------
if st.session_state.active_view == "🎧 AI Support Chat":
    render_chat_view(graph, memory_mgr)

elif st.session_state.active_view == "👨💼 Admin Dashboard" and has_permission(user_role, PERM_VIEW_ADMIN_DESK):
    render_admin_dashboard(memory_mgr)

elif st.session_state.active_view == "📡 Email & WhatsApp Hub" and has_permission(user_role, PERM_MANAGE_CHANNELS):
    render_omnichannel_view(graph, memory_mgr)

elif st.session_state.active_view == "📊 Support & APM Analytics" and (has_permission(user_role, PERM_VIEW_ANALYTICS) or has_permission(user_role, PERM_VIEW_PERFORMANCE)):
    render_analytics_dashboard()

else:
    render_chat_view(graph, memory_mgr)