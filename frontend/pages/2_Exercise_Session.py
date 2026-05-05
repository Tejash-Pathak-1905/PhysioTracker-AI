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

from frontend.theme import apply_theme
apply_theme()

st.title("🏃 Exercise Session")

if "user_id" not in st.session_state:
    st.warning("Please complete the Intake form first.")
    st.stop()

if "current_ex_idx" not in st.session_state:
    st.session_state.current_ex_idx = 0

db       = SessionLocal()
plans    = db.query(ExercisePlan)\
             .filter(ExercisePlan.user_id == st.session_state["user_id"])\
             .order_by(ExercisePlan.priority).all()
db.close()

if not plans:
    st.info("No exercise plan found. Go to the Intake page to generate one.")
    st.stop()

if st.session_state.current_ex_idx >= len(plans):
    st.balloons()
    st.markdown(
        """<div style='background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(99,102,241,0.1));
        border:1px solid rgba(34,197,94,0.4); border-radius:12px; padding:2rem; text-align:center; margin:2rem 0;'>
        <p style='font-size:2rem; margin:0;'>🎉</p>
        <p style='font-size:1.4rem; font-weight:700; color:#22c55e; margin:0.5rem 0;'>Session Complete!</p>
        <p style='color:#94a3b8; margin:0;'>You've completed all exercises in your programme. Well done!</p>
        </div>""",
        unsafe_allow_html=True
    )
    rc1, rc2 = st.columns(2)
    with rc1:
        if st.button("📋 View My Report", type="primary", use_container_width=True):
            st.switch_page("pages/3_Reports.py")
    with rc2:
        if st.button("🔄 Start New Session", use_container_width=True):
            st.session_state.current_ex_idx = 0
            st.rerun()
    st.stop()

exercise_names = {p.exercise_id: f"{p.exercise_id.replace('_',' ').title()} ({p.target_sets}×{p.target_reps})" for p in plans}
plan_keys = list(exercise_names.keys())

# Ensure index is within bounds (in case plans changed)
if st.session_state.current_ex_idx >= len(plan_keys):
    st.session_state.current_ex_idx = 0

# ── Progress indicator ───────────────────────────────────────────────────────
current_idx = st.session_state.current_ex_idx
total_ex    = len(plan_keys)
st.markdown(
    f"""<div style='background:rgba(99,102,241,0.08); border-radius:8px;
    padding:0.6rem 1.2rem; margin-bottom:0.8rem; display:flex; align-items:center; gap:1rem;'>
    <span style='color:#a78bfa; font-weight:700; font-size:0.9rem;'>Exercise {current_idx+1} of {total_ex}</span>
    </div>""",
    unsafe_allow_html=True
)
st.progress((current_idx) / total_ex)

selected_id    = st.selectbox("Choose an exercise", plan_keys, index=current_idx,
                               format_func=lambda x: exercise_names[x])
selected_plan  = next(p for p in plans if p.exercise_id == selected_id)

# Update session state index if user manually selects a different exercise
try:
    if plan_keys.index(selected_id) != st.session_state.current_ex_idx:
        st.session_state.current_ex_idx = plan_keys.index(selected_id)
except ValueError:
    pass

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

# ── WebRTC video processor ───────────────────────────────────────────────────
class PoseProcessor(VideoProcessorBase):
    def __init__(self):
        self.evaluator = ExerciseEvaluator(selected_plan)

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        bgr = frame.to_ndarray(format="bgr24")
        out = self.evaluator.process_frame(bgr)
        return av.VideoFrame.from_ndarray(out, format="bgr24")

with col_vid:
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
    if st.button("🚨 End Session Early", help="Ends the entire session immediately and saves progress."):
        if ctx.video_processor:
            log_data = ctx.video_processor.evaluator.get_session_log()
            db = SessionLocal()
            db.add(SessionLog(user_id=st.session_state["user_id"], **log_data))
            db.commit(); db.close()
            st.warning("Session ended early. Progress has been saved.")
        st.session_state.current_ex_idx = len(plans)
        st.rerun()
with col2:
    if st.button("✅ End Exercise", type="primary", help="Saves progress and moves to the next exercise."):
        if ctx.video_processor:
            log_data = ctx.video_processor.evaluator.get_session_log()
            db = SessionLocal()
            db.add(SessionLog(user_id=st.session_state["user_id"], **log_data))
            db.commit(); db.close()
            st.success(f"Exercise saved! Reps: {log_data['reps_completed']}, Duration: {log_data['duration_seconds']}s")
        st.session_state.current_ex_idx += 1
        st.rerun()
