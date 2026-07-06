import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.express as px
import requests
from db import query
from components.sidebar import render_sidebar

render_sidebar()

st.title("🗺️ Carte des tensions locatives")
st.markdown("""
Le **score de tension** mesure à quel point il est difficile de se loger dans une commune.
Un score élevé signifie que les prix augmentent vite, que les loyers pèsent lourd sur les revenus,
et que les transactions sont nombreuses — autrement dit, la demande dépasse l'offre.
""")

# ── Filtres ────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    annees_dispo = query("SELECT DISTINCT annee FROM gold.dynamisme_marche ORDER BY annee DESC")["annee"].tolist()
    annee = st.selectbox("Année", annees_dispo, index=0)
with col2:
    type_bien = st.selectbox("Type de bien", ["Tous", "Appartement", "Maison"])
with col3:
    indicateur = st.selectbox("Indicateur", [
        "score_tension", "prix_m2_moyen", "hausse_prix_pct",
    ], format_func=lambda x: {
        "score_tension":   "Score de tension (0-100)",
        "prix_m2_moyen":   "Prix au m² moyen (€)",
        "hausse_prix_pct": "Hausse des prix (%)",
    }[x])
with col4:
    regions = query("SELECT DISTINCT reg FROM silver.dim_commune WHERE reg IS NOT NULL ORDER BY reg")
    region_options = ["Toutes"] + regions["reg"].tolist()
    region = st.selectbox("Région", region_options)

# ── Requête principale ─────────────────────────────────────────────────────────
filtre_type   = f"AND gd.type_local = '{type_bien}'" if type_bien != "Tous" else ""
filtre_region = f"AND dc.reg = '{region}'" if region != "Toutes" else ""

df = query(f"""
    SELECT
        gd.code_insee, gd.nom_commune, gd.code_departement,
        gd.type_local,
        ROUND(gd.score_tension::numeric, 1)    AS score_tension,
        ROUND(gd.prix_m2_moyen::numeric, 0)    AS prix_m2_moyen,
        ROUND(gd.hausse_prix_pct::numeric, 1)  AS hausse_prix_pct,
        gd.nb_transactions, gd.categorie_tension, dc.reg
    FROM gold.dynamisme_marche gd
    JOIN silver.dim_commune dc ON gd.code_insee = dc.code_insee
    WHERE gd.annee = {annee}
      AND gd.{indicateur} IS NOT NULL
      {filtre_type}
      {filtre_region}
    ORDER BY gd.{indicateur} DESC, gd.nom_commune ASC
""")

if df.empty:
    st.warning("Aucune donnée pour ces filtres.")
    st.stop()

# ── Label indicateur ──────────────────────────────────────────────────────────
label = {
    "score_tension":   "Score tension",
    "prix_m2_moyen":   "Prix m² (€)",
    "hausse_prix_pct": "Hausse prix (%)",
}[indicateur]

# ── KPI ────────────────────────────────────────────────────────────────────────
commune_top = df.groupby("nom_commune")[indicateur].mean().idxmax()
val_moyenne   = round(df[indicateur].mean(), 1)
nb_communes   = df["nom_commune"].nunique()
nb_tres_tendu = df[df["categorie_tension"] == "Très tendu"]["nom_commune"].nunique()

unite = {"score_tension": "", "prix_m2_moyen": " €", "hausse_prix_pct": " %"}[indicateur]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Communes analysées", f"{nb_communes:,}")
k2.metric(f"{label} moyen", f"{val_moyenne}{unite}")
k3.metric("Commune en tête", commune_top)
if indicateur == "score_tension":
    k4.metric("Marchés très tendus", f"{nb_tres_tendu:,}")
else:
    k4.metric("Valeur max", f"{df[indicateur].max():.1f}{unite}")

if indicateur == "hausse_prix_pct":
    st.caption("La hausse est calculée uniquement pour les communes ayant au moins 25 transactions les deux années comparées. En dessous de ce seuil, la médiane n'est pas fiable.")

st.divider()

# ── Légende ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; gap:1.5rem; margin-bottom:1rem; font-size:0.85rem;">
    <span>🟢 <b>Détendu</b> 0–25</span>
    <span>🟡 <b>Modéré</b> 25–50</span>
    <span>🟠 <b>Tendu</b> 50–75</span>
    <span>🔴 <b>Très tendu</b> 75–100</span>
</div>
""", unsafe_allow_html=True)

# ── Carte choroplèthe ──────────────────────────────────────────────────────────
df_dep = df.groupby("code_departement").agg(
    valeur       =(indicateur,         "mean"),
    prix_m2_moyen=("prix_m2_moyen",    "mean"),
    score_moyen  =("score_tension",    "mean"),
    hausse_moy   =("hausse_prix_pct",  "mean"),
).reset_index()
df_dep["valeur"]        = df_dep["valeur"].round(1)
df_dep["prix_m2_moyen"] = df_dep["prix_m2_moyen"].round(0)
df_dep["score_moyen"]   = df_dep["score_moyen"].round(1)
df_dep["hausse_moy"]    = df_dep["hausse_moy"].round(1)
df_dep["code_departement"] = df_dep["code_departement"].astype(str).str.zfill(2)

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
    range_color=[0, 100] if indicateur == "score_tension" else None,
    labels={"valeur": label},
    hover_data={
        "code_departement": True,
        "valeur":           True,
        "prix_m2_moyen":    True,
        "score_moyen":      True,
        "hausse_moy":       True,
    },
    title=f"{label} par département — {annee}",
)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(height=540, margin={"r": 0, "t": 40, "l": 0, "b": 0})
st.plotly_chart(fig, use_container_width=True)

# ── Méthodologie ───────────────────────────────────────────────────────────────
with st.expander("ℹ️ Méthodologie — Comment est calculé le score de tension ?"):
    st.markdown("""
    Le **score de tension (0-100)** est construit à partir de 3 signaux du marché immobilier,
    chacun normalisé entre 0 et 100 puis combiné avec un **poids** (importance relative) :

    > 💡 Le **poids** indique l'importance de chaque signal dans le score final.
    > Par exemple, un poids de 40 % signifie que cet indicateur compte pour 40 points sur 100.

    | Signal | Poids | Ce que ça mesure |
    |--------|-------|-----------------|
    | **Hausse des prix au m²** | 40 % | La vitesse à laquelle les prix augmentent — signe d'une forte demande |
    | **Ratio loyer / revenu** | 40 % | La part du revenu consacrée au loyer — signe d'une pression financière sur les ménages |
    | **Volume de transactions** | 20 % | Le nombre de ventes — signe d'un marché actif |

    **Lecture du score :**
    - 🟢 **0–25** : marché détendu, offre suffisante
    - 🟡 **25–50** : tensions modérées
    - 🟠 **50–75** : marché tendu, logement difficile à trouver
    - 🔴 **75–100** : marché très tendu, forte pression sur les prix et les loyers
    """)
