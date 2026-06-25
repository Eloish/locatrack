import streamlit as st

st.set_page_config(
    page_title="LocaTrack — Observatoire du marché locatif",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Navigation horizontale (menu en haut) ──────────────────────────────────────
accueil = st.Page("views/accueil.py", title="Accueil",     icon="🏠", default=True)
carte   = st.Page("pages/1_Carte.py", title="Carte",        icon="🗺️")
compar  = st.Page("pages/2_Comparaison.py", title="Comparaison", icon="📊")
recherche = st.Page("pages/3_Recherche.py", title="Recherche", icon="🔍")

pg = st.navigation([accueil, carte, compar, recherche], position="top")
pg.run()
