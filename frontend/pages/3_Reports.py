"""
pages/3_Reports.py  –  State-of-the-art historical progress and mathematics dashboard.
"""
import json, os, sys, streamlit as st, pandas as pd, plotly.express as px, plotly.graph_objects as go
import numpy as np

# Add root directory to sys.path for backend imports
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

from database import SessionLocal, init_db, SessionLog, ExercisePlan

init_db()
st.set_page_config(page_title="Analytics | PhysioTracker", page_icon="📈", layout="wide")

from frontend.theme import apply_theme
apply_theme()

st.title("📈 Physiotherapy Analytics Dashboard")

if "user_id" not in st.session_state:
    st.warning("Please complete the Intake form first to view personalized analytics.")
    st.stop()

uid = st.session_state["user_id"]
db  = SessionLocal()
logs  = db.query(SessionLog).filter(SessionLog.user_id == uid).all()
plans = db.query(ExercisePlan).filter(ExercisePlan.user_id == uid).all()
db.close()

if not logs:
    st.info("No session data recorded yet. Complete an exercise session to generate mathematical reports.")
    st.stop()

# ── Build DataFrames & Mathematical Models ──────────────────────────────────
rows = []
for log in logs:
    errors = json.loads(log.form_errors or "{}")
    total_errors = sum(errors.values())
    
    # Mathematical Form Score Algorithm: 
    # Starts at 100. Deducts points based on errors per rep.
    # Severity weight (assumed 1.0 for now) can be tuned later.
    reps = max(log.reps_completed, 1) # Prevent division by zero
    error_ratio = total_errors / reps
    
    # Sigmoid penalty or linear penalty. Let's use an exponential decay for a smoother score:
    # Score = 100 * exp(-k * error_ratio), where k=0.5
    form_score = 100 * np.exp(-0.5 * error_ratio)
    
    # Try to find side from plan
    side = "both"
    for p in plans:
        if p.exercise_id == log.exercise_id:
            side = p.side
            break
            
    rows.append({
        "date": log.date, 
        "date_only": log.date.date(),
        "exercise": log.exercise_id,
        "side": side,
        "reps": log.reps_completed, 
        "duration": log.duration_seconds,
        "total_errors": total_errors,
        "form_score": round(form_score, 1),
        **{f"err_{k}": v for k, v in errors.items()}
    })

df = pd.DataFrame(rows)

# ── Adherence Metric Calculation ──────────────────────────────────────────────
plan_map = {p.exercise_id: p.target_reps * p.target_sets for p in plans}
df["target"] = df["exercise"].map(plan_map).fillna(1)
df["adherence"] = (df["reps"] / df["target"]).clip(0, 1) * 100

# ── Top Level KPIs ────────────────────────────────────────────────────────────
st.markdown("### 🎯 Global Performance Metrics")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

avg_adherence = df["adherence"].mean()
avg_form_score = df["form_score"].mean()

# Calculate Consistency Score (100 - CV of adherence)
if len(df) > 1:
    cv_adherence = (df["adherence"].std() / df["adherence"].mean()) * 100 if df["adherence"].mean() > 0 else 0
    consistency = max(0, 100 - cv_adherence)
else:
    consistency = 100.0

total_time = df["duration"].sum() // 60

kpi1.metric("Overall Plan Adherence", f"{avg_adherence:.1f}%", delta=f"{avg_adherence - 75:.1f}% vs Goal" if avg_adherence != 75 else None)
kpi2.metric("Average Form Score", f"{avg_form_score:.1f} / 100", help="Calculated using exponential decay penalty on errors per rep.")
kpi3.metric("Consistency Score", f"{consistency:.1f} / 100", help="Mathematical stability of your adherence over time (Low variance = High consistency).")
kpi4.metric("Total Time Exercising", f"{total_time} mins")

st.markdown("---")

# ── Advanced Data Visualization ───────────────────────────────────────────────
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("📈 Reps Progression")
    fig1 = px.area(df.sort_values("date"), x="date", y="reps",
                   color="exercise", markers=True, template="plotly_dark",
                   title="Volume (Reps) over Time")
    fig1.update_layout(margin=dict(l=20, r=20, t=40, b=20), hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

with col_chart2:
    st.subheader("🤖 Form Score Quality Trend")
    fig_score = px.line(df.sort_values("date"), x="date", y="form_score", 
                        color="exercise", markers=True, template="plotly_dark",
                        title="Form Quality Degradation/Improvement")
    fig_score.update_yaxes(range=[0, 105])
    fig_score.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_score, use_container_width=True)

st.markdown("---")

col_radar, col_bar = st.columns([1, 1.2])

with col_radar:
    st.subheader("🎯 Error Type Distribution (Radar)")
    err_cols = [c for c in df.columns if c.startswith("err_")]
    if err_cols:
        err_totals = df[err_cols].sum().reset_index()
        err_totals.columns = ["Error Type", "Count"]
        err_totals["Error Type"] = err_totals["Error Type"].str.replace("err_", "").str.replace("_", " ").str.title()
        
        fig_radar = px.line_polar(err_totals, r="Count", theta="Error Type", line_close=True, template="plotly_dark")
        fig_radar.update_traces(fill='toself')
        fig_radar.update_layout(margin=dict(l=40, r=40, t=20, b=20))
        st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.success("No form errors detected across any sessions. Perfect form!")

with col_bar:
    st.subheader("⚠️ Cumulative Error Frequency")
    if err_cols:
        fig_bar = px.bar(err_totals.sort_values("Count", ascending=True), 
                         x="Count", y="Error Type", orientation='h', template="plotly_dark",
                         color="Count", color_continuous_scale="Reds")
        fig_bar.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Bar chart unavailable due to zero errors.")

st.markdown("---")

col_heat, col_side = st.columns(2)

with col_heat:
    st.subheader("📅 Workout Frequency Heatmap")
    daily_reps = df.groupby("date_only")["reps"].sum().reset_index()
    fig_heat = px.density_heatmap(daily_reps, x="date_only", y="reps", 
                                  title="Daily Rep Volume Density",
                                  color_continuous_scale="Viridis", template="plotly_dark")
    fig_heat.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_heat, use_container_width=True)

with col_side:
    st.subheader("⚖️ Left vs Right Limb Comparison")
    side_df = df[df["side"].isin(["left", "right"])]
    if not side_df.empty:
        fig_side = px.box(side_df, x="side", y="form_score", color="side",
                          title="Form Score Distribution by Limb", template="plotly_dark",
                          points="all")
        fig_side.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_side, use_container_width=True)
    else:
        st.info("No unilateral (left/right specific) exercises logged yet.")

# ── Detailed Raw Logs ─────────────────────────────────────────────────────────
with st.expander("🔍 View Raw Session Mathematics (Tabular)"):
    display_cols = ["date", "exercise", "side", "reps", "target", "adherence", "total_errors", "form_score", "duration"]
    st.dataframe(df[display_cols].sort_values("date", ascending=False).style.format({
        "adherence": "{:.1f}%",
        "form_score": "{:.1f}",
        "duration": "{}s"
    }), use_container_width=True)
