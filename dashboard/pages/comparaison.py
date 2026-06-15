import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from db import get_engine, query

st.set_page_config(page_title="Comparaison de villes", page_icon="⚖️", layout="wide")
st.title("⚖️ Comparaison de villes")
st.markdown("Comparez deux villes sur leurs indicateurs immobiliers.")

@st.cache_data
def get_villes(type_local: str):
    return query(f"""
        SELECT DISTINCT nom_commune, code_insee
        FROM gold.prix_m2_par_ville
        WHERE type_local = '{type_local}'
          AND nb_transactions >= 10
        ORDER BY nom_commune
    """)

@st.cache_data
def get_data_ville(code_insee: str):
    return query(f"""
        SELECT annee, type_local, prix_m2_median, prix_m2_moyen,
               nb_transactions, evolution_annuelle_pct, moving_avg_3ans
        FROM gold.prix_m2_par_ville
        WHERE code_insee = '{code_insee}'
        ORDER BY annee, type_local
    """)

@st.cache_data
def get_tension_ville(code_insee: str):
    return query(f"""
        SELECT annee, type_local, score_tension, categorie_tension, hausse_prix_pct
        FROM gold.dynamisme_marche
        WHERE code_insee = '{code_insee}'
        ORDER BY annee, type_local
    """)

col1, col2, col3 = st.columns([2, 2, 1])
with col3:
    type_bien = st.selectbox("Type de bien", ["Appartement", "Maison"])

villes = get_villes(type_bien)
liste_villes = villes["nom_commune"].tolist()

with col1:
    ville1_nom = st.selectbox("Ville 1", liste_villes, index=liste_villes.index("Paris") if "Paris" in liste_villes else 0)
with col2:
    ville2_nom = st.selectbox("Ville 2", liste_villes, index=liste_villes.index("Marseille") if "Marseille" in liste_villes else 1)

ville1_insee = villes[villes["nom_commune"] == ville1_nom]["code_insee"].values[0]
ville2_insee = villes[villes["nom_commune"] == ville2_nom]["code_insee"].values[0]

df1 = get_data_ville(ville1_insee)
df2 = get_data_ville(ville2_insee)
t1  = get_tension_ville(ville1_insee)
t2  = get_tension_ville(ville2_insee)

df1_f = df1[df1["type_local"] == type_bien]
df2_f = df2[df2["type_local"] == type_bien]
t1_f  = t1[t1["type_local"] == type_bien]
t2_f  = t2[t2["type_local"] == type_bien]

def get_last(df, col):
    if df.empty or col not in df.columns: return None
    val = df.sort_values("annee").iloc[-1][col]
    return val if pd.notna(val) else None

st.markdown("---")
st.subheader("Indicateurs – dernière année disponible")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric(f"Prix m² – {ville1_nom}", f"{get_last(df1_f, 'prix_m2_median'):,.0f} €" if get_last(df1_f, 'prix_m2_median') else "N/A")
    st.metric(f"Prix m² – {ville2_nom}", f"{get_last(df2_f, 'prix_m2_median'):,.0f} €" if get_last(df2_f, 'prix_m2_median') else "N/A")
with c2:
    v1 = get_last(df1_f, 'evolution_annuelle_pct')
    v2 = get_last(df2_f, 'evolution_annuelle_pct')
    st.metric(f"Évolution – {ville1_nom}", f"{v1:+.1f}%" if v1 else "N/A")
    st.metric(f"Évolution – {ville2_nom}", f"{v2:+.1f}%" if v2 else "N/A")
with c3:
    v1 = get_last(t1_f, 'score_tension')
    v2 = get_last(t2_f, 'score_tension')
    st.metric(f"Score tension – {ville1_nom}", f"{v1:.1f}/100" if v1 else "N/A")
    st.metric(f"Score tension – {ville2_nom}", f"{v2:.1f}/100" if v2 else "N/A")
with c4:
    v1 = get_last(df1_f, 'nb_transactions')
    v2 = get_last(df2_f, 'nb_transactions')
    st.metric(f"Transactions – {ville1_nom}", f"{int(v1):,}" if v1 else "N/A")
    st.metric(f"Transactions – {ville2_nom}", f"{int(v2):,}" if v2 else "N/A")

st.markdown("---")
st.subheader("Évolution du prix au m²")

if not df1_f.empty and not df2_f.empty:
    df1_plot = df1_f.copy(); df1_plot["ville"] = ville1_nom
    df2_plot = df2_f.copy(); df2_plot["ville"] = ville2_nom

    fig = go.Figure()
    for nom, df_v in [(ville1_nom, df1_plot), (ville2_nom, df2_plot)]:
        fig.add_trace(go.Scatter(x=df_v["annee"], y=df_v["prix_m2_median"],
            name=f"{nom} – médian", mode="lines+markers", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=df_v["annee"], y=df_v["moving_avg_3ans"],
            name=f"{nom} – moy. mobile 3 ans", mode="lines", line=dict(dash="dot", width=1)))

    fig.update_layout(xaxis_title="Année", yaxis_title="Prix m² (€)",
        hovermode="x unified", height=400, legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Données insuffisantes pour ce type de bien.")

st.markdown("---")
st.subheader("Score de tension locative")

if not t1_f.empty and not t2_f.empty:
    t1_plot = t1_f.copy(); t1_plot["ville"] = ville1_nom
    t2_plot = t2_f.copy(); t2_plot["ville"] = ville2_nom
    tension = pd.concat([t1_plot, t2_plot])

    fig2 = px.bar(tension, x="annee", y="score_tension", color="ville",
        barmode="group", color_discrete_sequence=["#636EFA", "#EF553B"],
        labels={"score_tension": "Score (0-100)", "annee": "Année"})
    fig2.update_layout(height=350)
    st.plotly_chart(fig2, use_container_width=True)