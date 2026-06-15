import streamlit as st

st.set_page_config(
    page_title="LocaTrack",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏠 LocaTrack")
st.subheader("Observatoire intelligent du marché locatif français")

st.markdown("""
Bienvenue sur **LocaTrack** — analysez la tension locative en France.

### Que pouvez-vous faire ici ?

- 🗺️ **Carte** — visualisez les tensions locatives par ville et département
- 📊 **Comparaison** — comparez les villes entre elles
- 🔍 **Recherche** — trouvez la ville la plus accessible pour votre revenu

---
Utilisez le menu à gauche pour naviguer.
""")

# Métriques rapides
st.markdown("### Chiffres clés")

from db import query

col1, col2, col3 = st.columns(3)

with col1:
    nb = query("SELECT COUNT(DISTINCT nom_commune) as n FROM public.prix_m2_par_ville")
    st.metric("Communes analysées", f"{nb['n'][0]:,}")

with col2:
    ratio = query("SELECT ROUND(AVG(ratio_tension_pct)::numeric, 1) as r FROM public.ratio_loyer_revenu")
    st.metric("Ratio loyer/revenu moyen", f"{ratio['r'][0]} %")

with col3:
    tendu = query("""
        SELECT COUNT(DISTINCT nom_commune) as n 
        FROM public.dynamisme_marche 
        WHERE categorie_tension IN ('Très tendu', 'Tendu')
        AND annee = 2023
    """)
    st.metric("Villes tendues (2023)", f"{tendu['n'][0]:,}")