import streamlit as st
import asyncio
import os
from manager import run_manager_agent
import re
st.set_page_config(page_title="Catalogue AI", layout="wide")
session_cache = {
    "logo_path": None,
    "image_path": None,
    "csv_path": None,
    "image_used": None
}
last_pdf_path = {"value": None}
def reset_session_cache():
    for key in session_cache:
        session_cache[key] = None
    last_pdf_path["value"] = None
    pdf_path = "analysis_file.pdf"
    try:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
    except Exception as e:
        print(f"Error removing PDF: {e}")
    print("Session cache cleared.\n")

st.markdown("""
<style>
    .stTextArea textarea {
        font-size: 16px;
        padding: 10px;
        border-radius: 10px;
    }
    .stButton button {
        font-size: 16px;
        border-radius: 10px;
        background-color: #4CAF50;
        color: white;
    }
    .stDownloadButton button {
        font-size: 16px;
        border-radius: 10px;
        background-color: #2196F3;
        color: white;
    }
    .chat-message {
        margin-bottom: 20px;
        padding: 10px;
        border-radius: 10px;
        background-color: #f0f2f6;
    }
    img {
        border-radius: 10px;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)
st.markdown("<h3 style='font-family:Arial; color:#333;'>Catalogue AI</h3>", unsafe_allow_html=True)
st.markdown("<p style='color:gray; font-size: 14px;'>Ask any chart- or data-related question, upload a CSV/PDF/image, and let the agent analyze and respond like ChatGPT.</p>", unsafe_allow_html=True)
if "query_history" not in st.session_state:
    st.session_state.query_history = []
if "result_history" not in st.session_state:
    st.session_state.result_history = []
if "image_path_history" not in st.session_state:
    st.session_state.image_path_history = []
if "reset_triggered" not in st.session_state:
    st.session_state.reset_triggered = False


with st.container():
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.chat_input("Ask me a question about your chart or file...")
    with col2:
        file = st.file_uploader(" ", label_visibility="collapsed", type=["csv", "pdf", "png", "jpg", "jpeg"])
    if query:
        with st.spinner("Analyzing..."):
            file_path = None
            if file:
                file_extension = file.name.split('.')[-1].lower()
                file_path = file.name 
                with open(file_path, "wb") as f:
                    f.write(file.read())
                if file_extension == "pdf":
                    st.info("PDF uploaded. Sending it for analysis...")
                elif file_extension in ["png", "jpg", "jpeg"]:
                    st.info("Image uploaded. Sending it for analysis...")
                elif file_extension == "csv":
                    st.info("CSV uploaded. Sending it for analysis...")
                else:
                    st.warning("Unsupported file format.")
            result = asyncio.run(run_manager_agent(path=file_path,query=query))
            match = re.search(r"([\w./\\-]+\.png)", result)
            image_path = match.group(1) if match and os.path.basename(match.group(1)) == "graph.png" else None
            st.session_state.query_history.append(query)
            st.session_state.result_history.append(result)
            st.session_state.image_path_history.append(image_path)
if st.session_state.query_history:
    for i in reversed(range(len(st.session_state.query_history))):
        q = st.session_state.query_history[i]
        r = st.session_state.result_history[i]
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            st.markdown(r)
            img_path = st.session_state.image_path_history[i]
            if img_path and os.path.exists(img_path):
                st.image(img_path, caption="Generated Chart", use_container_width=True)
with st.sidebar:
    st.header("🛠 Controls")
    if st.button("🔄 Reset Session"):
        reset_session_cache()
        st.session_state.query_history = []
        st.session_state.result_history = []
        st.session_state.image_path_history = []
        st.session_state.reset_triggered = True
        st.success("Session cache and history cleared.")

    st.subheader("📄 Download Latest Report")
    pdf_path = "analysis_file.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 Download analysis_file.pdf",
                data=f.read(),  # read the content immediately
                file_name="analysis_file.pdf",
                mime="application/pdf",
                key=f"download_{len(st.session_state.query_history)}"  # dynamic key to force refresh
            )
