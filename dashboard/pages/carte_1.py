import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import plotly.express as px
from db import query

st.set_page_config(page_title="Carte", page_icon="🗺️", layout="wide")
st.title("🗺️ Carte des tensions locatives")

# ── Filtres ────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    annee = st.selectbox("Année", [2025,2024,2023, 2022, 2021], index=0)

with col2:
    type_bien = st.selectbox("Type de bien", ["Tous", "Appartement", "Maison"])

with col3:
    indicateur = st.selectbox("Indicateur", [
        "score_tension",
        "prix_m2_moyen",
        "hausse_prix_pct"
    ])

# ── Données ────────────────────────────────────────────────────────────────
filtre_type = f"AND type_local = '{type_bien}'" if type_bien != "Tous" else ""

df = query(f"""
    SELECT
        code_insee,
        nom_commune,
        code_departement,
        type_local,
        {indicateur},
        categorie_tension
    FROM public.dynamisme_marche
    WHERE annee = {annee}
      AND {indicateur} IS NOT NULL
      {filtre_type}
    ORDER BY {indicateur} DESC
""")

if df.empty:
    st.warning("Aucune donnée pour ces filtres.")
    st.stop()

# ── Carte choroplèthe par département ─────────────────────────────────────
st.markdown("### Par département")

df_dep = df.groupby("code_departement")[indicateur].mean().reset_index()
df_dep.columns = ["code_departement", "valeur"]
df_dep["code_departement"] = df_dep["code_departement"].astype(str).str.zfill(2)

import requests

@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    return requests.get(url).json()

geojson = load_geojson()

fig = px.choropleth(
    df_dep,
    geojson=geojson,
    locations="code_departement",
    featureidkey="properties.code",
    color="valeur",
    color_continuous_scale="RdYlGn_r",
    labels={"valeur": indicateur},
    title=f"{indicateur} par département — {annee}"
)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(height=500, margin={"r":0,"t":40,"l":0,"b":0})
st.plotly_chart(fig, use_container_width=True)

# ── Top 20 villes les plus tendues ─────────────────────────────────────────
st.markdown("### Top 20 villes les plus tendues")

top20 = df.head(30)
fig2 = px.bar(
    top20,
    x="nom_commune",
    y=indicateur,
    color="categorie_tension",
    color_discrete_map={
        "Très tendu": "#d73027",
        "Tendu":      "#fc8d59",
        "Modéré":     "#fee08b",
        "Détendu":    "#1a9850"
    },
    title=f"Top 20 — {indicateur} ({annee})"
)
fig2.update_layout(xaxis_tickangle=-45, height=400)
st.plotly_chart(fig2, use_container_width=True)

# ── Tableau détaillé ───────────────────────────────────────────────────────
with st.expander("Voir le tableau complet"):
    st.dataframe(df, use_container_width=True)