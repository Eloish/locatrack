import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.express as px
import requests
from db import query

st.set_page_config(page_title="Carte des tensions", page_icon="🗺️", layout="wide")
st.title("🗺️ Carte des tensions locatives")

st.info(
    "Score de tension composite (0-100) combinant : hausse des prix au m², "
    "ratio loyer/revenu, et volume de transactions."
)

# ── Filtres ────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    annee = st.selectbox("Année", [2024, 2023, 2022, 2021], index=0)
with col2:
    type_bien = st.selectbox("Type de bien", ["Tous", "Appartement", "Maison"])
with col3:
    indicateur = st.selectbox("Indicateur", [
        "score_tension",
        "prix_m2_moyen",
        "hausse_prix_pct",
        "taux_effort_median",
        "taux_effort_modeste",
    ], format_func=lambda x: {
        "score_tension":      "Score de tension (0-100)",
        "prix_m2_moyen":      "Prix au m² moyen (€)",
        "hausse_prix_pct":    "Hausse des prix (%)",
        "taux_effort_median": "Taux d'effort — profil médian (%)",
        "taux_effort_modeste":"Taux d'effort — profil modeste (%)",
    }[x])
with col4:
    REG_NOMS = {
        "11": "Île-de-France",
        "24": "Centre-Val de Loire",
        "27": "Bourgogne-Franche-Comté",
        "28": "Normandie",
        "32": "Hauts-de-France",
        "44": "Grand Est",
        "52": "Pays de la Loire",
        "53": "Bretagne",
        "75": "Nouvelle-Aquitaine",
        "76": "Occitanie",
        "84": "Auvergne-Rhône-Alpes",
        "93": "Provence-Alpes-Côte d'Azur",
        "94": "Corse",
    }
    regions = query("""
        SELECT DISTINCT dc.reg
        FROM silver.dim_commune dc
        WHERE dc.reg IS NOT NULL
        ORDER BY dc.reg
    """)
    reg_codes = regions["reg"].tolist()
    reg_labels = {c: REG_NOMS.get(c, f"Région {c}") for c in reg_codes}
    region_options = ["Toutes"] + reg_codes
    region = st.selectbox(
        "Région",
        region_options,
        format_func=lambda c: "Toutes" if c == "Toutes" else reg_labels.get(c, c),
    )

# ── Requête ────────────────────────────────────────────────────────────────
filtre_type   = f"AND gd.type_local = '{type_bien}'" if type_bien != "Tous" else ""
filtre_region = f"AND dc.reg = '{region}'" if region != "Toutes" else ""

# Les indicateurs taux_effort viennent de gold.inegalites (niveau agglomération)
# Les autres viennent de gold.dynamisme_marche (niveau commune)
indicateurs_ineg = {"taux_effort_median", "taux_effort_modeste"}

if indicateur in indicateurs_ineg:
    col_ineg = {
        "taux_effort_median":  "taux_effort_median_pct",
        "taux_effort_modeste": "taux_effort_modeste_pct",
    }[indicateur]
    type_hab = "Appartement" if type_bien != "Tous" else "Appartement"
    df = query(f"""
        WITH derniere AS (
            SELECT nom_agglomeration, MAX(annee) AS max_annee
            FROM gold.inegalites
            WHERE type_habitat = '{type_hab}'
            GROUP BY nom_agglomeration
        ),
        ineg AS (
            SELECT i.nom_agglomeration, i.{col_ineg} AS valeur_indicateur
            FROM gold.inegalites i
            JOIN derniere d ON i.nom_agglomeration = d.nom_agglomeration AND i.annee = d.max_annee
            WHERE i.type_habitat = '{type_hab}'
        )
        SELECT
            dc.code_insee, dc.nom_commune, dc.code_departement, dc.reg,
            da.nom_agglomeration,
            ROUND(ing.valeur_indicateur::numeric, 1) AS {indicateur}
        FROM silver.dim_commune dc
        JOIN silver.mapping_uu_agglomeration mua ON dc.uu2020 = mua.uu2020
        JOIN silver.dim_agglomeration da ON mua.id_agglomeration = da.id_agglomeration
        JOIN ineg ing ON ing.nom_agglomeration = da.nom_agglomeration
        WHERE ing.valeur_indicateur IS NOT NULL
          {filtre_region}
        ORDER BY ing.valeur_indicateur DESC
    """)
else:
    df = query(f"""
        SELECT
            gd.code_insee, gd.nom_commune, gd.code_departement,
            gd.type_local,
            ROUND(gd.score_tension::numeric, 1)   AS score_tension,
            ROUND(gd.prix_m2_moyen::numeric, 0)   AS prix_m2_moyen,
            ROUND(gd.hausse_prix_pct::numeric, 1) AS hausse_prix_pct,
            gd.nb_transactions, gd.categorie_tension, dc.reg
        FROM gold.dynamisme_marche gd
        JOIN silver.dim_commune dc ON gd.code_insee = dc.code_insee
        WHERE gd.annee = {annee}
          AND gd.{indicateur} IS NOT NULL
          {filtre_type}
          {filtre_region}
        ORDER BY gd.{indicateur} DESC
    """)

if df.empty:
    st.warning("Aucune donnée pour ces filtres.")
    st.stop()

# ── Carte choroplèthe par département ─────────────────────────────────────
st.markdown(f"### Carte par département — {len(df):,} communes")

df_dep = df.groupby("code_departement")[indicateur].mean().reset_index()
df_dep.columns = ["code_departement", "valeur"]
df_dep["valeur"] = df_dep["valeur"].round(1)
df_dep["code_departement"] = df_dep["code_departement"].astype(str).str.zfill(2)

@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    return requests.get(url).json()

geojson = load_geojson()

label = {
    "score_tension":      "Score tension",
    "prix_m2_moyen":      "Prix m² (€)",
    "hausse_prix_pct":    "Hausse prix (%)",
    "taux_effort_median": "Taux effort médian (%)",
    "taux_effort_modeste":"Taux effort modeste (%)",
}[indicateur]

fig = px.choropleth(
    df_dep,
    geojson=geojson,
    locations="code_departement",
    featureidkey="properties.code",
    color="valeur",
    color_continuous_scale="RdYlGn_r",
    labels={"valeur": label},
    hover_data={"code_departement": True, "valeur": True},
    title=f"{label} par département — {annee}",
)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(height=520, margin={"r": 0, "t": 40, "l": 0, "b": 0})
st.plotly_chart(fig, use_container_width=True)

# ── Top 20 communes les plus tendues ──────────────────────────────────────
st.markdown("### Top 20 communes les plus tendues")

top20 = df.head(20)
fig2 = px.bar(
    top20,
    x="nom_commune",
    y=indicateur,
    color="categorie_tension",
    color_discrete_map={
        "Très tendu": "#d73027",
        "Tendu":      "#fc8d59",
        "Modéré":     "#fee08b",
        "Détendu":    "#1a9850",
    },
    hover_data=["code_departement", "nb_transactions"],
    title=f"Top 20 — {label} ({annee})",
    labels={indicateur: label, "nom_commune": "Commune"},
)
fig2.update_layout(xaxis_tickangle=-45, height=420)
st.plotly_chart(fig2, use_container_width=True)

# ── Tableau détaillé ───────────────────────────────────────────────────────
with st.expander(f"Voir le tableau complet ({len(df):,} communes)"):
    df_display = df.copy()
    df_display["score_tension"]   = df_display["score_tension"].apply(lambda x: f"{x:.1f}" if x == x else "N/A")
    df_display["prix_m2_moyen"]   = df_display["prix_m2_moyen"].apply(lambda x: f"{x:,.0f} €" if x == x else "N/A")
    df_display["hausse_prix_pct"] = df_display["hausse_prix_pct"].apply(lambda x: f"{x:.1f}%" if x == x else "N/A")
    st.dataframe(
        df_display[[
            "nom_commune", "code_departement", "type_local",
            "score_tension", "prix_m2_moyen", "hausse_prix_pct",
            "nb_transactions", "categorie_tension"
        ]],
        use_container_width=True, hide_index=True,
        column_config={
            "nom_commune":      "Commune",
            "code_departement": "Dép.",
            "type_local":       "Type",
            "score_tension":    "Score tension",
            "prix_m2_moyen":    "Prix m²",
            "hausse_prix_pct":  "Hausse prix",
            "nb_transactions":  "Nb transactions",
            "categorie_tension":"Catégorie",
        }
    )
