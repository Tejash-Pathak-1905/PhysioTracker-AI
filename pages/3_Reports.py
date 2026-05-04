"""
pages/3_Reports.py  –  Historical progress dashboard.
"""
import json, streamlit as st, pandas as pd, plotly.express as px
from database import SessionLocal, init_db, SessionLog, ExercisePlan

init_db()
st.set_page_config(page_title="Reports | PhysioTracker", page_icon="📊")
st.title("📊 Progress Reports")

if "user_id" not in st.session_state:
    st.warning("Please complete the Intake form first.")
    st.stop()

uid = st.session_state["user_id"]
db  = SessionLocal()
logs  = db.query(SessionLog).filter(SessionLog.user_id == uid).all()
plans = db.query(ExercisePlan).filter(ExercisePlan.user_id == uid).all()
db.close()

if not logs:
    st.info("No session data yet. Complete an exercise session to see your progress.")
    st.stop()

# ── Build DataFrames ─────────────────────────────────────────────────────────
rows = []
for log in logs:
    errors = json.loads(log.form_errors or "{}")
    rows.append({
        "date": log.date, "exercise": log.exercise_id,
        "reps": log.reps_completed, "duration": log.duration_seconds,
        **{f"err_{k}": v for k, v in errors.items()}
    })
df = pd.DataFrame(rows)

# ── Adherence metric ─────────────────────────────────────────────────────────
plan_map = {p.exercise_id: p.target_reps * p.target_sets for p in plans}
df["target"] = df["exercise"].map(plan_map).fillna(1)
df["adherence"] = (df["reps"] / df["target"]).clip(0, 1) * 100
st.metric("Overall Adherence", f"{df['adherence'].mean():.1f}%")

# ── Reps over time ───────────────────────────────────────────────────────────
st.subheader("Reps Completed Over Time")
fig1 = px.line(df.sort_values("date"), x="date", y="reps",
               color="exercise", markers=True)
st.plotly_chart(fig1, use_container_width=True)

# ── Form error bar chart ─────────────────────────────────────────────────────
st.subheader("Most Common Form Errors")
err_cols = [c for c in df.columns if c.startswith("err_")]
if err_cols:
    err_totals = df[err_cols].sum().rename(lambda x: x.replace("err_","")).sort_values(ascending=False)
    fig2 = px.bar(err_totals, labels={"index":"Error","value":"Count"}, title="Cumulative Form Errors")
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No form errors recorded yet — great form!")

# ── Session history table ────────────────────────────────────────────────────
st.subheader("Session History")
st.dataframe(df[["date","exercise","reps","duration","adherence"]].sort_values("date", ascending=False),
             use_container_width=True)
