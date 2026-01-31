import streamlit as st
import requests
import time

# --- Configuration ---
# This points to your FastAPI backend (currently running locally)
BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Agentic Researcher", page_icon="🕵️‍♂️", layout="wide")

# --- Custom CSS for a Cleaner Look ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #FF4B4B; 
        color: white;
    }
    .report-box {
        border: 1px solid #ddd;
        padding: 20px;
        border-radius: 10px;
        background-color: #f9f9f9;
    }
    </style>
""", unsafe_allow_html=True)

# --- Header ---
st.title("🕵️‍♂️ Multi-Agent Research Assistant")
st.markdown("Powered by **CrewAI**, **Gemini 2.5**, and **Brave Search**")

# --- Sidebar (Controls) ---
with st.sidebar:
    st.header("⚙️ Research Settings")
    st.info("This system uses a team of AI agents to research and write reports.")
    
    # You can add more settings here later (e.g., Tone, Length)
    st.markdown("---")
    st.write("**Active Agents:**")
    st.success("✅ Research Manager")
    st.success("✅ Web Researcher")
    st.success("✅ Technical Writer")

# --- Main Input ---
col1, col2 = st.columns([3, 1])
with col1:
    topic = st.text_input("What should we research today?", placeholder="e.g. The Future of Quantum Computing")

with col2:
    st.write("") # Spacer
    st.write("") # Spacer
    start_btn = st.button("🚀 Start Research")

# --- Logic ---
if start_btn and topic:
    with st.spinner("🤖 Waking up the agents..."):
        try:
            # 1. Send POST request to Backend
            payload = {"topic": topic}
            response = requests.post(f"{BACKEND_URL}/research", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                job_id = data["job_id"]
                st.toast(f"Research started! Job ID: {job_id}")
                
                # 2. Poll for Results
                status_placeholder = st.empty()
                progress_bar = st.progress(0)
                
                while True:
                    status_res = requests.get(f"{BACKEND_URL}/research/{job_id}")
                    if status_res.status_code == 200:
                        status_data = status_res.json()
                        current_status = status_data.get("status")
                        
                        # Update Status Display
                        if current_status == "running":
                            status_placeholder.info(f"🔄 Agents are working... (This may take 1-2 minutes due to rate limits)")
                            progress_bar.progress(50)
                            time.sleep(5) # Poll every 5 seconds
                        
                        elif current_status == "completed":
                            progress_bar.progress(100)
                            status_placeholder.success("✅ Research Complete!")
                            
                            # 3. Display Result
                            result_text = status_data.get("result", "")
                            
                            # Clean up the result (sometimes CrewAI returns an object string)
                            st.markdown("---")
                            st.subheader("📄 Research Report")
                            st.markdown(result_text)
                            
                            # Download Button
                            st.download_button(
                                label="📥 Download Report",
                                data=result_text,
                                file_name=f"research_{job_id}.md",
                                mime="text/markdown"
                            )
                            break
                        
                        elif current_status == "failed":
                            status_placeholder.error(f"❌ Error: {status_data.get('result')}")
                            break
                    else:
                        st.error("Lost connection to the brain.")
                        break
            else:
                st.error(f"Failed to start job. Status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            st.error("🚨 Could not connect to Backend. Is `python -m src.main` running?")