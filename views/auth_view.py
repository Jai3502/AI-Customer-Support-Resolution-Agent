import streamlit as st
from auth import authenticate_user, register_customer, load_users


def render_auth_view():
    """Render modern login & registration screen with RBAC quick logins."""
    st.markdown(
        """
        <style>
        .auth-container {
            max-width: 520px;
            margin: 2rem auto;
            padding: 2.5rem;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(12px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        .auth-header {
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .auth-header h1 {
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .auth-subtitle {
            color: #94a3b8;
            font-size: 0.95rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2.2, 1])

    with col2:
        st.markdown(
            """
            <div class="auth-header">
                <h1>🎧 AI Support Portal</h1>
                <p class="auth-subtitle">Sign in with RBAC role authorization to get started</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab1, tab2 = st.tabs(["🔐 Sign In", "📝 Create Customer Account"])

        with tab1:
            with st.form("login_form"):
                username_input = st.text_input(
                    "Username or Email",
                    placeholder="e.g. admin, agent1, auditor1, or rahul",
                )
                password_input = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                )
                submit_login = st.form_submit_button("Sign In 🚀", use_container_width=True)

                if submit_login:
                    if not username_input or not password_input:
                        st.error("Please enter both username and password.")
                    else:
                        user = authenticate_user(username_input, password_input)
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            st.session_state.customer_id = user.get("customer_id") or "CUST001"
                            st.session_state.role = user.get("role", "customer")
                            st.success(f"Welcome back, {user.get('name')}!")
                            st.rerun()
                        else:
                            st.error("Invalid credentials. Please check your username and password.")

            st.markdown("---")
            st.markdown("### ⚡ Quick Role Select (Demo)")
            st.caption("Instantly sign in under any RBAC permission tier:")

            dcol1, dcol2 = st.columns(2)
            with dcol1:
                if st.button("👨💼 Super Admin", use_container_width=True):
                    admin_user = authenticate_user("admin", "admin123")
                    if admin_user:
                        st.session_state.authenticated = True
                        st.session_state.user = admin_user
                        st.session_state.customer_id = "CUST001"
                        st.session_state.role = "admin"
                        st.rerun()

                if st.button("📊 Compliance Auditor", use_container_width=True):
                    auditor_user = authenticate_user("auditor1", "auditor123")
                    if auditor_user:
                        st.session_state.authenticated = True
                        st.session_state.user = auditor_user
                        st.session_state.customer_id = "CUST001"
                        st.session_state.role = "auditor"
                        st.rerun()

            with dcol2:
                if st.button("🎧 Support Agent", use_container_width=True):
                    agent_user = authenticate_user("agent1", "agent123")
                    if agent_user:
                        st.session_state.authenticated = True
                        st.session_state.user = agent_user
                        st.session_state.customer_id = "CUST001"
                        st.session_state.role = "agent"
                        st.rerun()

                if st.button("👤 Customer (Rahul)", use_container_width=True):
                    cust_user = authenticate_user("rahul", "customer123")
                    if cust_user:
                        st.session_state.authenticated = True
                        st.session_state.user = cust_user
                        st.session_state.customer_id = "CUST001"
                        st.session_state.role = "customer"
                        st.rerun()

            st.caption("🔑 **Passwords:** Admin (`admin123`) | Agent (`agent123`) | Auditor (`auditor123`) | Customer (`customer123`)")

        with tab2:
            with st.form("register_form"):
                new_username = st.text_input("Username", placeholder="e.g. janesmith")
                new_name = st.text_input("Full Name", placeholder="e.g. Jane Smith")
                new_email = st.text_input("Email Address", placeholder="e.g. jane@example.com")
                new_city = st.text_input("City", placeholder="e.g. Mumbai")
                new_password = st.text_input("Password", type="password", placeholder="Choose a password")
                confirm_password = st.text_input("Confirm Password", type="password")

                submit_reg = st.form_submit_button("Register Customer Account 🎉", use_container_width=True)

                if submit_reg:
                    if new_password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        success, msg, user = register_customer(
                            username=new_username,
                            email=new_email,
                            name=new_name,
                            password=new_password,
                            city=new_city or "Bengaluru"
                        )
                        if success and user:
                            st.success(msg)
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            st.session_state.customer_id = user.get("customer_id")
                            st.session_state.role = "customer"
                            st.rerun()
                        else:
                            st.error(msg)
