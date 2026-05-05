import streamlit as st

def apply_theme():
    st.markdown("""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
        
        <style>
        /* Global Theme Variables */
        :root {
            --bg: #FFFFFF;
            --surface: #FAFAF7;
            --surface-2: #F4F2EB;
            --line: #EFEDE6;
            --ink: #1A1A18;
            --ink-light: #5A574E;
            --accent: #7BA68C;
            --accent-deep: #5C8770;
            --warn: #C97C5D;
        }

        /* ── Base App & Typography ── */
        .stApp, .main, .block-container {
            font-family: 'Inter', sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }
        
        /* Elegant spacing for the main container */
        .block-container {
            padding-top: 4rem !important;
            padding-bottom: 5rem !important;
            max-width: 760px !important;
        }

        p, label, li, .stMarkdown {
            font-family: 'Inter', sans-serif !important;
            line-height: 1.6;
        }
        
        .stMarkdown p {
            font-size: 1.1rem !important;
            color: var(--ink-light) !important;
        }

        /* ── Headers ── */
        h1, h2, h3, h4, h5, h6, [class^="st-emotion-cache"] h1, [class^="st-emotion-cache"] h2, [class^="st-emotion-cache"] h3 {
            font-family: 'Instrument Serif', serif !important;
            color: var(--ink) !important;
            font-weight: 400 !important;
            letter-spacing: -0.01em !important;
            margin-top: 2rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        h1 { font-size: 3.2rem !important; line-height: 1.1 !important; margin-bottom: 1.5rem !important; }
        h2 { font-size: 2.2rem !important; }
        h3 { font-size: 1.8rem !important; }

        /* ── Form Container ── */
        [data-testid="stForm"] {
            border: 1px solid var(--line) !important;
            background-color: var(--bg) !important;
            border-radius: 12px !important;
            padding: 2.5rem !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.03) !important;
            margin-top: 1.5rem !important;
            margin-bottom: 1.5rem !important;
        }
        
        /* Form Inputs */
        div[data-baseweb="input"], div[data-baseweb="textarea"] {
            border-radius: 4px !important;
            border: 1px solid var(--line) !important;
        }
        
        /* Hide the sidebar natively for a cleaner look */
        [data-testid="stSidebar"] {
            background-color: var(--surface) !important;
            border-right: 1px solid var(--line) !important;
        }

        /* ── Labels ── */
        label {
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
            color: var(--ink-light) !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Button Typography */
        .stButton button p {
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
        }
        
        /* Primary buttons (Green) get white text */
        .stButton button[kind="primary"] p {
            color: #FFFFFF !important;
        }
        
        /* Secondary buttons (Light) get dark text */
        .stButton button[kind="secondary"] p {
            color: var(--ink) !important;
        }
        
        /* ── Specific Button Overrides ── */
        .stButton button {
            border-radius: 8px !important;
            border: none !important;
            padding: 0.5rem 1.5rem !important;
            transition: all 0.2s ease !important;
        }
        
        .stButton button[kind="primary"] {
            background-color: var(--accent) !important;
        }
        
        .stButton button[kind="primary"]:hover {
            background-color: var(--accent-deep) !important;
            box-shadow: 0 4px 12px rgba(123, 166, 140, 0.3) !important;
        }
        
        .stButton button[kind="secondary"] {
            background-color: var(--surface-2) !important;
            color: var(--ink) !important;
        }
        
        .stButton button[kind="secondary"]:hover {
            background-color: var(--line) !important;
        }
        </style>
    """, unsafe_allow_html=True)


