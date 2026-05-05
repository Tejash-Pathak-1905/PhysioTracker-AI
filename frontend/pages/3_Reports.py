"""
pages/3_Reports.py  –  Personalised AI-powered physiotherapy progress report.
"""
import json, os, sys, streamlit as st, pandas as pd, plotly.express as px, plotly.graph_objects as go
import numpy as np

# Add root directory to sys.path for backend imports
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

from database import SessionLocal, init_db, SessionLog, ExercisePlan, Assessment
from llm_client import generate_report_insights

init_db()
st.set_page_config(page_title="My Report | PhysioTracker", page_icon="📋", layout="wide")

from frontend.theme import apply_theme
apply_theme()

# ── Page Header ───────────────────────────────────────────────────────────────
st.title("📋 Your Physiotherapy Progress Report")

if "user_id" not in st.session_state:
    st.warning("Please complete the Intake form first to view your personalised report.")
    st.stop()

uid        = st.session_state["user_id"]
user_name  = st.session_state.get("user_name", "Patient")
db         = SessionLocal()
user       = db.query(User).filter(User.id == uid).first()
logs       = db.query(SessionLog).filter(SessionLog.user_id == uid).all()
plans      = db.query(ExercisePlan).filter(ExercisePlan.user_id == uid).all()
assessment = db.query(Assessment).filter(Assessment.user_id == uid).order_by(Assessment.id.desc()).first()

# Extract age and gender
age        = user.age if user else None
gender     = user.gender if user else None

db.close()

if not logs:
    st.info("No session data recorded yet. Complete at least one exercise session to generate your report.")
    st.stop()

# ── Pull intake context ───────────────────────────────────────────────────────
complaint   = assessment.complaint if assessment else "Unknown condition"
pain_level  = assessment.pain_level if assessment else 0

# ── Build DataFrame ───────────────────────────────────────────────────────────
rows = []
plan_map  = {p.exercise_id: p for p in plans}
ex_target = {p.exercise_id: p.target_reps * p.target_sets for p in plans}

for log in logs:
    errors      = json.loads(log.form_errors or "{}")
    total_errors = sum(errors.values())
    reps         = max(log.reps_completed, 1)
    error_ratio  = total_errors / reps
    form_score   = round(100 * np.exp(-0.5 * error_ratio), 1)

    plan = plan_map.get(log.exercise_id)
    side = plan.side if plan else "both"
    target_reps = ex_target.get(log.exercise_id, 1)
    adherence   = min((log.reps_completed / max(target_reps, 1)) * 100, 100)

    rows.append({
        "date":        log.date,
        "date_only":   log.date.date(),
        "exercise":    log.exercise_id,
        "ex_label":    log.exercise_id.replace("_", " ").title(),
        "side":        side,
        "reps":        log.reps_completed,
        "target":      target_reps,
        "adherence":   round(adherence, 1),
        "duration":    log.duration_seconds,
        "total_errors": total_errors,
        "form_score":  form_score,
        **{f"err_{k}": v for k, v in errors.items()},
    })

df = pd.DataFrame(rows)

# ── Aggregate stats for AI ────────────────────────────────────────────────────
ex_summary = df.groupby("ex_label").agg(
    sessions=("date", "count"),
    total_reps=("reps", "sum"),
    avg_form=("form_score", "mean"),
    avg_adherence=("adherence", "mean"),
    total_errors=("total_errors", "sum"),
).reset_index()

err_cols     = [c for c in df.columns if c.startswith("err_")]
error_totals = df[err_cols].sum().to_dict() if err_cols else {}
top_error    = max(error_totals, key=error_totals.get, default=None) if error_totals else None

sessions_summary = f"""
Total sessions recorded: {len(df)}
Unique exercises: {df['exercise'].nunique()}
Total reps completed: {int(df['reps'].sum())}
Overall average form score: {df['form_score'].mean():.1f}/100
Overall average plan adherence: {df['adherence'].mean():.1f}%
Total active time: {df['duration'].sum()//60} minutes

Per-exercise breakdown:
{ex_summary.to_string(index=False)}

Most common form error: {top_error.replace('err_','').replace('_',' ').title() if top_error else 'None detected'}
"""

# ── Status badge styling ──────────────────────────────────────────────────────
STATUS_COLORS = {
    "Progressing Well": ("#22c55e", "🟢"),
    "On Track":         ("#3b82f6", "🔵"),
    "Just Started":     ("#f59e0b", "🟡"),
    "Needs Attention":  ("#ef4444", "🔴"),
}

# ── TOP: Patient context banner ───────────────────────────────────────────────
with st.container():
    banner_col, refresh_col = st.columns([4, 1])
    with banner_col:
        st.markdown(
            f"""<div style='background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.1));
            border-left: 4px solid #6366f1; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1rem;'>
            <span style='font-size:0.85rem; color:#a78bfa; font-weight:600; text-transform:uppercase; letter-spacing:1px;'>
            Your Condition</span><br/>
            <span style='font-size:1.15rem; color:#f1f5f9; font-weight:500;'>{complaint}</span>
            &nbsp;&nbsp;<span style='color:#94a3b8;'>|</span>&nbsp;&nbsp;
            <span style='font-size:0.9rem; color:#94a3b8;'>Initial Pain: {pain_level}/10</span>
            </div>""",
            unsafe_allow_html=True
        )
    with refresh_col:
        st.markdown("<div style='padding-top:0.5rem'></div>", unsafe_allow_html=True)
        generate_ai = st.button("🤖 Generate AI Insights", type="primary", use_container_width=True)

# ── AI Insights Section ────────────────────────────────────────────────────────
if generate_ai or st.session_state.get("ai_insights"):
    if generate_ai:
        with st.spinner("Analysing your sessions with AI... this takes a few seconds."):
            insights = generate_report_insights(complaint, pain_level, sessions_summary, age=age, gender=gender)
            st.session_state["ai_insights"] = insights
    else:
        insights = st.session_state["ai_insights"]

    if insights:
        status = insights.get("recovery_status", "On Track")
        color, emoji = STATUS_COLORS.get(status, ("#6366f1", "🔵"))

        st.markdown("---")
        st.markdown("### 🤖 AI Physiotherapist Analysis")

        # Headline + Status
        h_col, s_col = st.columns([3, 1])
        with h_col:
            st.markdown(
                f"""<div style='background:rgba(99,102,241,0.08); border-radius:10px;
                padding:1rem 1.5rem; margin-bottom:0.5rem;'>
                <p style='font-size:1.2rem; font-weight:600; color:#e2e8f0; margin:0;'>
                {emoji} {insights.get("headline","")}</p></div>""",
                unsafe_allow_html=True
            )
        with s_col:
            st.markdown(
                f"""<div style='background:{color}22; border:2px solid {color};
                border-radius:10px; padding:0.8rem 1rem; text-align:center; margin-bottom:0.5rem;'>
                <p style='font-size:0.75rem; color:{color}; font-weight:700; text-transform:uppercase;
                letter-spacing:1px; margin:0 0 4px 0;'>Recovery Status</p>
                <p style='font-size:1.1rem; color:{color}; font-weight:700; margin:0;'>{status}</p>
                </div>""",
                unsafe_allow_html=True
            )

        # Narrative
        st.markdown(
            f"""<div style='background:rgba(15,23,42,0.6); border-radius:10px;
            padding:1.2rem 1.5rem; border:1px solid rgba(99,102,241,0.2); margin-bottom:1rem;'>
            <p style='color:#cbd5e1; line-height:1.8; margin:0; font-size:1rem;'>
            {insights.get("progress_narrative","")}</p>
            </div>""",
            unsafe_allow_html=True
        )

        # 4-tile insight grid
        i1, i2, i3, i4 = st.columns(4)
        tiles = [
            (i1, "💪 Strongest Exercise", insights.get("strongest_exercise",""), "#22c55e"),
            (i2, "🎯 Needs Work",          insights.get("needs_work",""),           "#f59e0b"),
            (i3, "🔬 Form Insight",        insights.get("form_insight",""),         "#3b82f6"),
            (i4, "💡 Next Session Tip",    insights.get("next_session_tip",""),     "#a855f7"),
        ]
        for col, label, text, clr in tiles:
            with col:
                st.markdown(
                    f"""<div style='background:rgba(15,23,42,0.7); border:1px solid {clr}44;
                    border-top:3px solid {clr}; border-radius:10px; padding:1rem; height:100%;'>
                    <p style='font-size:0.78rem; color:{clr}; font-weight:700; text-transform:uppercase;
                    letter-spacing:1px; margin:0 0 8px 0;'>{label}</p>
                    <p style='color:#cbd5e1; font-size:0.9rem; line-height:1.6; margin:0;'>{text}</p>
                    </div>""",
                    unsafe_allow_html=True
                )

        st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
        c_col, m_col = st.columns(2)

        with c_col:
            cons_text = insights.get("consistency_advice","")
            if cons_text:
                st.info(f"📅 **Consistency:** {cons_text}")

        with m_col:
            mot_text = insights.get("motivational_message","")
            if mot_text:
                st.success(f"🌟 {mot_text}")

        caution = insights.get("caution_flag","")
        if caution:
            st.warning(f"⚠️ **Therapist Note:** {caution}")
    else:
        st.error("Could not generate AI insights. Check your GEMINI_API_KEY and try again.")

st.markdown("---")

# ── KPI Metrics ───────────────────────────────────────────────────────────────
st.markdown("### 📊 Your Session Summary")

avg_adherence = df["adherence"].mean()
avg_form      = df["form_score"].mean()
total_mins    = df["duration"].sum() // 60
total_sessions = len(df)

if len(df) > 1 and df["adherence"].mean() > 0:
    cv = (df["adherence"].std() / df["adherence"].mean()) * 100
    consistency = max(0, 100 - cv)
else:
    consistency = 100.0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Sessions Done",        str(total_sessions))
k2.metric("Plan Adherence",       f"{avg_adherence:.0f}%",
          delta=f"{avg_adherence-75:.0f}% vs 75% goal")
k3.metric("Avg Form Score",       f"{avg_form:.0f}/100")
k4.metric("Consistency",          f"{consistency:.0f}/100",
          help="How steady your adherence is across sessions. Low variance = high score.")
k5.metric("Total Active Time",    f"{total_mins} mins")

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
st.markdown("### 📈 Progress Over Time")
c1, c2 = st.columns(2)

with c1:
    fig_reps = px.area(
        df.sort_values("date"), x="date", y="reps", color="ex_label",
        markers=True, template="plotly_dark",
        labels={"reps": "Reps Completed", "date": "Date", "ex_label": "Exercise"},
        title="Reps Completed Per Session"
    )
    fig_reps.update_layout(margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified", legend_title_text="")
    st.plotly_chart(fig_reps, use_container_width=True)

with c2:
    fig_form = px.line(
        df.sort_values("date"), x="date", y="form_score", color="ex_label",
        markers=True, template="plotly_dark",
        labels={"form_score": "Form Score", "date": "Date", "ex_label": "Exercise"},
        title="Form Quality Trend (100 = Perfect)"
    )
    fig_form.update_yaxes(range=[0, 105])
    fig_form.update_layout(margin=dict(l=10, r=10, t=40, b=10), legend_title_text="")
    st.plotly_chart(fig_form, use_container_width=True)

# ── Per-exercise adherence bar ────────────────────────────────────────────────
st.markdown("### 🎯 Exercise-by-Exercise Breakdown")

ex_df = df.groupby("ex_label").agg(
    avg_adherence=("adherence",  "mean"),
    avg_form=("form_score", "mean"),
    total_reps=("reps",      "sum"),
    sessions=("date",     "count"),
).reset_index().sort_values("avg_adherence", ascending=False)

bar_col, breakdown_col = st.columns([1.4, 1])

with bar_col:
    fig_adhere = go.Figure()
    fig_adhere.add_trace(go.Bar(
        name="Avg Adherence %", x=ex_df["ex_label"], y=ex_df["avg_adherence"],
        marker_color="#6366f1", text=ex_df["avg_adherence"].map("{:.0f}%".format), textposition="outside"
    ))
    fig_adhere.add_trace(go.Bar(
        name="Avg Form Score", x=ex_df["ex_label"], y=ex_df["avg_form"],
        marker_color="#22c55e", text=ex_df["avg_form"].map("{:.0f}".format), textposition="outside"
    ))
    fig_adhere.update_layout(
        barmode="group", template="plotly_dark", title="Adherence & Form by Exercise",
        margin=dict(l=10, r=10, t=40, b=10), legend_title_text="",
        yaxis=dict(range=[0, 120])
    )
    st.plotly_chart(fig_adhere, use_container_width=True)

with breakdown_col:
    st.markdown("##### Exercise Scorecard")
    for _, row in ex_df.iterrows():
        adh_color = "#22c55e" if row["avg_adherence"] >= 80 else "#f59e0b" if row["avg_adherence"] >= 50 else "#ef4444"
        form_color = "#22c55e" if row["avg_form"] >= 80 else "#f59e0b" if row["avg_form"] >= 60 else "#ef4444"
        st.markdown(
            f"""<div style='background:rgba(15,23,42,0.6); border:1px solid rgba(99,102,241,0.2);
            border-radius:8px; padding:0.7rem 1rem; margin-bottom:0.5rem;'>
            <span style='color:#e2e8f0; font-weight:600;'>{row["ex_label"]}</span><br/>
            <span style='font-size:0.82rem; color:{adh_color};'>Adherence: {row["avg_adherence"]:.0f}%</span>
            &nbsp;|&nbsp;
            <span style='font-size:0.82rem; color:{form_color};'>Form: {row["avg_form"]:.0f}/100</span>
            &nbsp;|&nbsp;
            <span style='font-size:0.82rem; color:#94a3b8;'>{int(row["total_reps"])} total reps over {int(row["sessions"])} session(s)</span>
            </div>""",
            unsafe_allow_html=True
        )

# ── Form Error Breakdown ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### ⚠️ Form Error Analysis")

if err_cols:
    err_totals = df[err_cols].sum().reset_index()
    err_totals.columns = ["Error Type", "Count"]
    err_totals["Error Type"] = err_totals["Error Type"].str.replace("err_", "").str.replace("_", " ").str.title()
    err_totals = err_totals[err_totals["Count"] > 0].sort_values("Count", ascending=False)

    if not err_totals.empty:
        e1, e2 = st.columns(2)
        with e1:
            fig_err = px.bar(
                err_totals, x="Count", y="Error Type", orientation="h",
                template="plotly_dark", color="Count",
                color_continuous_scale="Oranges",
                title="Most Frequent Form Errors (All Sessions)"
            )
            fig_err.update_layout(margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
            st.plotly_chart(fig_err, use_container_width=True)

        with e2:
            fig_pie = px.pie(
                err_totals, names="Error Type", values="Count",
                template="plotly_dark",
                title="Error Distribution",
                color_discrete_sequence=px.colors.sequential.Purples_r
            )
            fig_pie.update_layout(margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

        st.caption(
            "These form errors are detected by the AI posture system during your exercises. "
            "Repeated errors in the same category suggest a specific technique to address with your physiotherapist."
        )
    else:
        st.success("✅ No form errors detected across all your sessions. Excellent technique!")
else:
    st.success("✅ No form errors detected across all your sessions.")

# ── Left/Right comparison ─────────────────────────────────────────────────────
side_df = df[df["side"].isin(["left", "right"])]
if not side_df.empty:
    st.markdown("---")
    st.markdown("### ⚖️ Left vs Right Side Comparison")
    st.caption(f"For your condition (*{complaint}*), tracking side-by-side symmetry helps monitor bilateral recovery.")
    fig_side = px.box(
        side_df, x="side", y="form_score", color="side",
        points="all", template="plotly_dark",
        labels={"side": "Side", "form_score": "Form Score"},
        title="Form Score Distribution – Left vs Right"
    )
    fig_side.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_side, use_container_width=True)

# ── Raw Logs ──────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🔍 Full Session Log (All Exercises)"):
    display_cols = ["date", "ex_label", "side", "reps", "target", "adherence", "form_score", "total_errors", "duration"]
    display_df = df[display_cols].rename(columns={
        "ex_label": "Exercise", "reps": "Reps Done", "target": "Target Reps",
        "adherence": "Adherence %", "form_score": "Form Score",
        "total_errors": "Form Errors", "duration": "Duration (s)"
    }).sort_values("date", ascending=False)

    st.dataframe(
        display_df.style.format({
            "Adherence %": "{:.0f}%",
            "Form Score":  "{:.1f}",
        }).background_gradient(subset=["Form Score"], cmap="RdYlGn", vmin=0, vmax=100),
        use_container_width=True
    )
