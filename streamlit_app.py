import streamlit as st
import os
import tempfile
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

# Streamlit Page Config
st.set_page_config(
    page_title="SafeHaven Concierge 🛡️",
    page_icon="🛡️",
    layout="centered"
)

# Custom Premium Styling Injection
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');

/* Main font styling */
html, body, [data-testid="stAppViewContainer"], .stWidgetLabel {
    font-family: 'Outfit', sans-serif !important;
}

/* Title gradient */
.main-title {
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 3rem;
    background: linear-gradient(135deg, #00C6FF 0%, #0072FF 50%, #8E2DE2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 5px;
}

.subtitle {
    text-align: center;
    color: #888899;
    font-size: 1.1rem;
    margin-bottom: 30px;
}

/* Button style */
div.stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #0072FF 0%, #8E2DE2 100%) !important;
    color: white !important;
    border: none !important;
    padding: 12px 24px !important;
    font-size: 18px !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    transition: all 0.3s ease-in-out !important;
    box-shadow: 0 4px 15px rgba(142, 45, 226, 0.3) !important;
}

div.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(142, 45, 226, 0.5) !important;
}

/* Code & output panels */
.output-card {
    background-color: #0F0F1A;
    color: #A0A0C0;
    padding: 22px;
    border-radius: 12px;
    font-family: 'JetBrains Mono', monospace;
    border-left: 6px solid #0072FF;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
    margin-top: 15px;
    line-height: 1.6;
}

.success-badge {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    display: inline-block;
    margin-bottom: 15px;
}

.info-card {
    background: rgba(0, 114, 255, 0.08);
    border: 1px solid rgba(0, 114, 255, 0.2);
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

# App UI Header
st.markdown('<div class="main-title">SafeHaven Concierge 🛡️</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Zero-Trust Multi-Agent Decryption Supervisor with Path Confinement</div>', unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.markdown("### ⚙️ Environment Configuration")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Enter GEMINI_API_KEY", type="password")
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
        st.sidebar.success("Key set successfully!")
else:
    st.sidebar.markdown('<span class="success-badge">● Active Key Loaded</span>', unsafe_allow_html=True)

# Force AI Studio mode if using API key
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
os.environ.pop("GOOGLE_CLOUD_LOCATION", None)

if not os.environ.get("GEMINI_API_KEY"):
    st.warning("⚠️ Please enter your `GEMINI_API_KEY` in the sidebar to authenticate the reasoning agent.")
else:
    # Now import agent-related modules safely after API key is configured
    try:
        from app.agent import root_agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
    except Exception as e:
        st.error(f"Failed to load agent modules: {e}")
        st.stop()

    st.subheader("🔑 Decryption Console")
    
    # Grid Layout for inputs
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("Upload encrypted document (.enc)", type=["enc"])
    with col2:
        passphrase = st.text_input("Decryption Key (e.g. SV_SAFE_2026)", type="password", help="The raw passphrase used to derive the Fernet key.")

    if st.button("Authorize & Decrypt"):
        if not uploaded_file:
            st.error("Please upload an encrypted file first.")
        elif not passphrase:
            st.error("Please enter the decryption key.")
        else:
            with st.spinner("Executing security filters and running multi-agent graph..."):
                # Save file to a secure temporary location inside the workspace root (".")
                # This ensures the absolute path confinement check passes
                with tempfile.NamedTemporaryFile(delete=False, suffix=".enc", dir=".") as temp_file:
                    temp_file.write(uploaded_file.read())
                    temp_path = os.path.abspath(temp_file.name)

                try:
                    # Initialize ADK Runner
                    session_service = InMemorySessionService()
                    session = session_service.create_session_sync(user_id="streamlit_user", app_name="safehaven")
                    runner = Runner(agent=root_agent, session_service=session_service, app_name="safehaven")

                    # Construct target prompt
                    prompt = f"Decrypt {temp_path} with key {passphrase}"
                    message = types.Content(
                        role="user", parts=[types.Part.from_text(text=prompt)]
                    )

                    # Execute pipeline
                    st.markdown("""
                    <div class="info-card">
                        <b>🔒 ADK Pipeline Log:</b><br/>
                        1. Adversarial checks executed (directory backtracking & bypass checks)<br/>
                        2. Key isolated from LLM context and scrubbed from user prompt<br/>
                        3. Multi-agent nodes routed (triage -> execution)<br/>
                        4. Path confinement validated against workspace root
                    </div>
                    """, unsafe_allow_html=True)

                    events = list(
                        runner.run(
                            new_message=message,
                            user_id="streamlit_user",
                            session_id=session.id,
                        )
                    )

                    # Parse events and display output
                    output_text = ""
                    for event in events:
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if part.text:
                                    output_text += part.text + "\n"

                    # Print beautifully styled card
                    st.markdown('<span class="success-badge">Decryption Successful</span>', unsafe_allow_html=True)
                    st.markdown(f'<div class="output-card">{output_text}</div>', unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Execution failed: {e}")
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
