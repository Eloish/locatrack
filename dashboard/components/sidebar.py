import streamlit as st


def render_sidebar():
    st.markdown("""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        /* ── Fond général ── */
        .stApp { background-color: #f5f7fa; }

        /* ── st.metric font size ── */
        [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
        [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }

        /* ── Sidebar ── */
        section[data-testid="stSidebar"] { background: #1a2e4a !important; }
        section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
        [data-testid="stSidebarNav"]::before {
            content: "🏠 LocaTrack";
            display: block;
            font-size: 1.4rem;
            font-weight: 700;
            color: white;
            padding: 1.2rem 1rem 0.2rem 1rem;
        }
        [data-testid="stSidebarNav"]::after {
            content: "Observatoire locatif français";
            display: block;
            font-size: 0.75rem;
            color: #a0aec0;
            padding: 0 1rem 1rem 1rem;
            border-bottom: 1px solid rgba(255,255,255,0.15);
            margin-bottom: 0.5rem;
        }
        section[data-testid="stSidebar"] > div { padding-top: 0 !important; }

        /* ── Hero ── */
        .hero {
            background: linear-gradient(135deg, #1a2e4a 0%, #2d5282 100%);
            padding: 3rem 2.5rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            color: white;
        }
        .hero h1 { font-size: 2.6rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
        .hero p  { font-size: 1.1rem; opacity: 0.85; margin-top: 0.5rem; }
        .hero .badge {
            display: inline-block;
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 20px;
            padding: 0.2rem 0.8rem;
            font-size: 0.8rem;
            margin-top: 1rem;
        }

        /* ── Métriques ── */
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 1.4rem 1.6rem;
            border-left: 4px solid #2d5282;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }
        .metric-card .label { font-size: 0.82rem; color: #718096; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
        .metric-card .value { font-size: 1.4rem; font-weight: 700; color: #1a2e4a; margin-top: 0.2rem; }
        .metric-card .sub   { font-size: 0.78rem; color: #a0aec0; margin-top: 0.2rem; }

        /* ── Cartes pages ── */
        .page-card {
            background: white;
            border-radius: 10px;
            padding: 1.6rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
            height: 100%;
            border-top: 3px solid #2d5282;
        }
        .page-card .icon { font-size: 2rem; margin-bottom: 0.6rem; }
        .page-card h3    { font-size: 1.1rem; font-weight: 700; color: #1a2e4a; margin: 0 0 0.5rem 0; }
        .page-card p     { font-size: 0.88rem; color: #4a5568; line-height: 1.5; }
        .page-card .tag  { display: inline-block; background: #ebf4ff; color: #2d5282; border-radius: 4px; padding: 0.15rem 0.5rem; font-size: 0.75rem; margin-top: 0.8rem; font-weight: 500; }

        /* ── Sources ── */
        .source-card {
            background: white;
            border-radius: 8px;
            padding: 1rem 1.2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border: 1px solid #e2e8f0;
        }
        .source-card .src-name { font-weight: 600; color: #1a2e4a; font-size: 0.9rem; }
        .source-card .src-desc { font-size: 0.8rem; color: #718096; margin-top: 0.2rem; }
        .source-card .src-date { font-size: 0.75rem; color: #a0aec0; margin-top: 0.3rem; }

        /* ── Titres de section ── */
        .section-title {
            font-size: 1rem;
            font-weight: 700;
            color: #2d3748;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.4rem;
            border-bottom: 2px solid #e2e8f0;
        }
    </style>
    """, unsafe_allow_html=True)
