"""
pages/2_Exercise_Session.py  –  Live CV session with streamlit-webrtc.
"""
import json, av, os, sys, streamlit as st

# Add root directory to sys.path for backend imports
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

from dotenv import load_dotenv
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration
from database import SessionLocal, init_db, ExercisePlan, SessionLog
from cv_engine import ExerciseEvaluator

load_dotenv()
RTC_CONFIG = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})

init_db()
st.set_page_config(page_title="Session | PhysioTracker", page_icon="🏃")
st.title("🏃 Exercise Session")

if "user_id" not in st.session_state:
    st.warning("Please complete the Intake form first.")
    st.stop()

db       = SessionLocal()
plans    = db.query(ExercisePlan)\
             .filter(ExercisePlan.user_id == st.session_state["user_id"])\
             .order_by(ExercisePlan.priority).all()
db.close()

if not plans:
    st.info("No exercise plan found. Go to the Intake page to generate one.")
    st.stop()

exercise_names = {p.exercise_id: f"{p.exercise_id.replace('_',' ').title()} ({p.target_sets}×{p.target_reps})" for p in plans}
selected_id    = st.selectbox("Choose an exercise", list(exercise_names.keys()),
                               format_func=lambda x: exercise_names[x])
selected_plan  = next(p for p in plans if p.exercise_id == selected_id)

# ── Load instructions ────────────────────────────────────────────────────────
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(os.path.join(root_dir, "frontend", "exercises.json")) as f:
    exercises_db = json.load(f)
selected_exercise_info = next((e for e in exercises_db if e["id"] == selected_id), {})
instructions = selected_exercise_info.get("instructions", [])

if selected_plan.caution:
    st.warning(f"⚠️ Caution: {selected_plan.caution}")

col_vid, col_inst = st.columns([2, 1])

with col_inst:
    st.subheader("📝 Instructions")
    if instructions:
        for i, step in enumerate(instructions, 1):
            st.markdown(f"**{i}.** {step}")
    else:
        st.info("No instructions available.")
    if selected_plan.side != "both":
        st.info(f"👉 **Side:** Perform on your **{selected_plan.side}** side.")

with col_vid:
    # ── WebRTC video processor ───────────────────────────────────────────────────
class PoseProcessor(VideoProcessorBase):
    def __init__(self):
        self.evaluator = ExerciseEvaluator(selected_plan)

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        bgr = frame.to_ndarray(format="bgr24")
        out = self.evaluator.process_frame(bgr)
        return av.VideoFrame.from_ndarray(out, format="bgr24")

ctx = webrtc_streamer(
    key=f"session_{selected_id}",
    video_processor_factory=PoseProcessor,
    rtc_configuration=RTC_CONFIG,
    media_stream_constraints={"video": True, "audio": False},
    async_processing=True,
)

# ── Early-end / save button ──────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    if st.button("✅ Complete / End Session", type="primary"):
        if ctx.video_processor:
            log_data = ctx.video_processor.evaluator.get_session_log()
            db = SessionLocal()
            db.add(SessionLog(user_id=st.session_state["user_id"], **log_data))
            db.commit(); db.close()
            st.success(f"Session saved! Reps: {log_data['reps_completed']}, Duration: {log_data['duration_seconds']}s")
with col2:
    if st.button("🚨 End Early (pain / emergency)"):
        if ctx.video_processor:
            log_data = ctx.video_processor.evaluator.get_session_log()
            db = SessionLocal()
            db.add(SessionLog(user_id=st.session_state["user_id"], **log_data))
            db.commit(); db.close()
            st.warning("Session ended early. Progress has been saved.")
