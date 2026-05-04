"""
pages/1_Intake.py  –  User login + assessment form → LLM plan generation.
"""
import json, streamlit as st
from database import SessionLocal, init_db, User, Assessment, ExercisePlan
from llm_client import generate_exercise_plan

init_db()

st.set_page_config(page_title="Intake | PhysioTracker", page_icon="🩺")
st.title("🩺 Patient Intake & Plan Generation")

# ── Load exercise catalogue ──────────────────────────────────────────────────
with open("exercises.json") as f:
    EXERCISES = json.load(f)

# ── User login / creation ────────────────────────────────────────────────────
st.subheader("Step 1 – Who are you?")
username = st.text_input("Enter your name / User ID", placeholder="e.g. Alex")

if username:
    db = SessionLocal()
    user = db.query(User).filter(User.name == username).first()
    if not user:
        user = User(name=username)
        db.add(user); db.commit(); db.refresh(user)
        st.success(f"Welcome, {username}! New profile created.")
    else:
        st.info(f"Welcome back, {username}!")

    st.session_state["user_id"]   = user.id
    st.session_state["user_name"] = user.name
    db.close()

    # ── Intake form ──────────────────────────────────────────────────────────
    st.subheader("Step 2 – Tell us about your condition")
    with st.form("intake_form"):
        complaint   = st.text_area("Describe your injury or goal", height=120,
                                   placeholder="e.g. Right knee pain after running. Difficulty going down stairs.")
        pain_level  = st.slider("Current pain level (0 = none, 10 = severe)", 0, 10, 3)
        submitted   = st.form_submit_button("🤖 Generate My Plan")

    if submitted and complaint.strip():
        with st.spinner("Generating your personalised programme..."):
            plan = generate_exercise_plan(complaint, pain_level, EXERCISES)

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
                    caution       = item.get("caution", ""),
                    priority      = item.get("priority", 99),
                ))
            db.commit(); db.close()

            st.success("✅ Plan saved! Head to the **Exercise Session** page.")
            st.markdown(f"**Condition Summary:** {plan['understood_condition']}")
            st.info(plan["user_summary"])
