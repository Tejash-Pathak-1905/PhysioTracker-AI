"""
pages/1_Intake.py  –  User login + assessment form → LLM plan generation.
(Hot-reload trigger applied)
"""
import json, os, sys, streamlit as st

# Add root directory to sys.path for backend imports
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

from database import SessionLocal, init_db, User, Assessment, ExercisePlan
from llm_client import generate_exercise_plan

init_db()

st.set_page_config(page_title="Intake | PhysioTracker", page_icon="🩺")

from frontend.theme import apply_theme
apply_theme()

st.title("🩺 Patient Intake & Plan Generation")

# ── Load exercise catalogue ──────────────────────────────────────────────────
exercises_path = os.path.join(root_dir, "frontend", "exercises.json")
with open(exercises_path) as f:
    EXERCISES = json.load(f)

# ── User login / creation ────────────────────────────────────────────────────
st.subheader("Step 1 – Tell us about yourself")
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    username = st.text_input("Enter your name / User ID", placeholder="e.g. Alex")
with col2:
    age = st.number_input("Age", min_value=1, max_value=120, value=25)
with col3:
    gender = st.selectbox("Gender", ["Male", "Female", "Others"])

if username:
    db = SessionLocal()
    user = db.query(User).filter(User.name == username).first()
    if not user:
        user = User(name=username, age=age, gender=gender)
        db.add(user); db.commit(); db.refresh(user)
        st.success(f"Welcome, {username}! New profile created.")
    else:
        # Update age and gender if they changed or were missing
        if user.age != age or user.gender != gender:
            user.age = age
            user.gender = gender
            db.commit()
        st.info(f"Welcome back, {username}!")

    st.session_state["user_id"]   = user.id
    st.session_state["user_name"] = user.name
    st.session_state["user_age"]  = user.age
    st.session_state["user_gender"] = user.gender
    db.close()

    # ── Intake form ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Step 2 – Tell us about your condition")
    with st.form("intake_form"):
        complaint   = st.text_area("Describe your injury or goal", height=120,
                                   placeholder="e.g. Right knee pain after running. Difficulty going down stairs.")
        pain_level  = st.slider("Current pain level (0 = none, 10 = severe)", 0, 10, 3)
        past_records = st.text_area("Past Medical Records & Surgeries (Optional)", height=80,
                                    placeholder="e.g. ACL reconstruction in 2018, history of asthma.")
        
        st.markdown("<div style='margin-top: 1rem; margin-bottom: 0.5rem;'><label>Attach Medical Reports / Imaging (Optional)</label></div>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Attach Medical Reports / Imaging",
            type=["pdf", "png", "jpg", "jpeg"],
            label_visibility="collapsed"
        )

        submitted   = st.form_submit_button("🤖 Generate My Plan")

    if submitted and complaint.strip():
        file_bytes = None
        mime_type = ""
        if uploaded_file is not None:
            file_bytes = uploaded_file.getvalue()
            mime_type = uploaded_file.type

        with st.spinner("Generating your personalised programme..."):
            plan = generate_exercise_plan(
                complaint, 
                pain_level, 
                EXERCISES, 
                past_records=past_records,
                media_bytes=file_bytes, 
                media_mime=mime_type,
                age=st.session_state.get("user_age"),
                gender=st.session_state.get("user_gender")
            )

        if plan is None:
            st.error("Could not generate a plan. Check your GEMINI_API_KEY and try again.")
        else:
            db = SessionLocal()
            assessment = Assessment(
                user_id          = st.session_state["user_id"],
                complaint        = complaint,
                pain_level       = pain_level,
                llm_raw_response = plan["_raw_json"],
            )
            db.add(assessment); db.commit(); db.refresh(assessment)

            for item in plan["programme"]:
                db.add(ExercisePlan(
                    assessment_id = assessment.id,
                    user_id       = st.session_state["user_id"],
                    exercise_id   = item["exercise_id"],
                    confidence    = item["confidence"],
                    target_sets   = item["sets"],
                    target_reps   = item["reps"],
                    side          = item.get("side", "both"),
                    caution       = item.get("caution", ""),
                    priority      = item.get("priority", 99),
                ))
            db.commit(); db.close()

            # Reset session index for fresh start
            st.session_state["current_ex_idx"] = 0
            st.session_state.pop("ai_insights", None)

            st.success("✅ Plan saved! Head to the **Exercise Session** page.")
            st.markdown(f"**Condition Summary:** {plan['understood_condition']}")
            st.info(plan["user_summary"])
