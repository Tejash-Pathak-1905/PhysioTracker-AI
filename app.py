"""
app.py  –  Streamlit entry point / home screen.
Run with:  streamlit run app.py
"""
import streamlit as st
from database import init_db

init_db()   # ensure tables exist on first launch

st.set_page_config(
    page_title="PhysioTracker AI",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💪 AI-Assisted Physiotherapy & CV Tracker")
st.markdown("""
Welcome to **PhysioTracker** — your AI-powered physiotherapy companion.

### How it works
| Step | Page | What happens |
|------|------|--------------|
| 1️⃣ | **Intake** | Enter your name, describe your injury, rate your pain. Gemini AI generates a personalised exercise plan. |
| 2️⃣ | **Exercise Session** | Your webcam streams to a MediaPipe CV engine that counts reps and logs form errors in real time. |
| 3️⃣ | **Reports** | View adherence, progression charts, and your most common form mistakes over time. |

Use the **sidebar** to navigate between pages.
""")

if "user_name" in st.session_state:
    st.info(f"Currently logged in as **{st.session_state['user_name']}**")
else:
    st.warning("👈 Start by heading to the **Intake** page to set up your profile.")
