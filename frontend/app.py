"""
app.py  –  Streamlit entry point / home screen.
Run with:  streamlit run app.py
"""
import os, sys
import streamlit as st

# Add parent directory to sys.path for backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import init_db
from frontend.theme import apply_theme

init_db()   # ensure tables exist on first launch

st.set_page_config(
    page_title="PhysioTracker AI",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_theme()

# Redirect immediately to the intake page
st.switch_page("pages/1_Intake.py")

