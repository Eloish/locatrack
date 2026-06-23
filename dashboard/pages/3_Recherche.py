import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from components.sidebar import render_sidebar
from db import query

st.set_page_config(page_title="Recherche de ville", page_icon="🔍", layout="wide")
render_sidebar()
st.title("🔍 Trouver la ville la plus accessible")

st.info(
    "Entrez votre revenu mensuel pour voir le taux d'effort de chaque commune. "
    "Le **taux d'effort (vous)** = loyer / votre revenu. "
    "En dessous de **33%** = accessible. Entre 33% et 50% = tendu. Au-dessus de 50% = difficile."
)

# ── Filtres ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    revenu = st.number_input("Revenu mensuel (€)", min_value=500, max_value=10000, value=2000, step=100)
with col2:
    type_habitat = st.selectbox("Type de logement", ["Appartement", "Maison"])
with col3:
    nb_pieces = st.selectbox("Nombre de pièces", ["Tous", "1P", "2P", "3P", "4P+"])
with col4:
    @st.cache_data(ttl=3600)
    def load_departements():
        from db import query as _q
        return ["(Tous)"] + _q("SELECT DISTINCT code_departement FROM silver.dim_commune ORDER BY code_departement")["code_departement"].tolist()
    deps = load_departements()
    departement = st.selectbox("Département", deps)
with col5:
    @st.cache_data(ttl=3600)
    def load_annees():
        from db import query as _q
        return ["(Dernière)"] + _q("SELECT DISTINCT annee FROM gold.ratio_loyer_revenu ORDER BY annee DESC")["annee"].astype(str).tolist()
    annees = load_annees()
    annee_filtre = st.selectbox("Année", annees)
with col6:
    st.markdown("<br>", unsafe_allow_html=True)
    rechercher = st.button("🔍 Rechercher", use_container_width=True)

if rechercher:
    # Filtre nombre_pieces — deux versions : sans alias (CTE) et avec alias rlr
    if nb_pieces == "Tous":
        pieces_filter_cte = "AND nombre_pieces = 'Tous'"
        pieces_filter     = "AND rlr.nombre_pieces = 'Tous'"
    else:
        pieces_filter_cte = f"AND nombre_pieces ILIKE '%%{nb_pieces}%%'"
        pieces_filter     = f"AND rlr.nombre_pieces ILIKE '%%{nb_pieces}%%'"

    dep_filter  = f"AND dc.code_departement = '{departement}'" if departement != "(Tous)" else ""
    annee_filter_cte = f"AND annee = {annee_filtre}" if annee_filtre != "(Dernière)" else ""
    annee_filter_rlr = f"AND rlr.annee = {annee_filtre}" if annee_filtre != "(Dernière)" else ""

    df = query(f"""
        WITH derniere_annee AS (
            SELECT observatory_b, nom_agglomeration, type_habitat, nombre_pieces,
                   MAX(annee) AS max_annee
            FROM gold.ratio_loyer_revenu
            WHERE type_habitat = '{type_habitat}'
              {pieces_filter_cte}
              {annee_filter_cte}
            GROUP BY observatory_b, nom_agglomeration, type_habitat, nombre_pieces
        ),
        loyers_recents AS (
            SELECT rlr.observatory_b, rlr.nom_agglomeration, rlr.annee,
                   rlr.type_habitat, rlr.nombre_pieces,
                   rlr.loyer_mensuel_median, rlr.revenu_mensuel_moyen,
                   rlr.ratio_tension_pct
            FROM gold.ratio_loyer_revenu rlr
            JOIN derniere_annee da
                ON  rlr.observatory_b    = da.observatory_b
                AND rlr.nom_agglomeration = da.nom_agglomeration
                AND rlr.type_habitat      = da.type_habitat
                AND rlr.nombre_pieces     = da.nombre_pieces
                AND rlr.annee             = da.max_annee
            {pieces_filter}
            {annee_filter_rlr}
        ),
        resultats AS (
        SELECT
            dc.code_insee,
            dc.nom_commune,
            dc.code_departement,
            dc.reg,
            lr.nom_agglomeration,
            lr.annee                                                   AS annee_donnees,
            ROUND(lr.loyer_mensuel_median::numeric, 0)                 AS loyer_median,
            ROUND(lr.revenu_mensuel_moyen::numeric, 0)                 AS revenu_local,
            ROUND(lr.ratio_tension_pct::numeric, 1)                    AS taux_effort_local,
            ROUND((lr.loyer_mensuel_median / {revenu} * 100)::numeric, 1) AS taux_effort_vous
        FROM loyers_recents lr
        JOIN silver.dim_agglomeration da  ON da.nom_agglomeration = lr.nom_agglomeration
        JOIN silver.mapping_uu_agglomeration mua
                ON mua.observatory_b    = lr.observatory_b
               AND mua.id_agglomeration = da.id_agglomeration
        JOIN silver.dim_commune dc ON dc.uu2020 = mua.uu2020
        {dep_filter}
        )
        SELECT DISTINCT ON (code_insee) *
        FROM resultats
        ORDER BY code_insee, annee_donnees DESC, loyer_median ASC
    """)

    st.session_state["df_recherche"] = df
    st.session_state["recherche_params"] = {
        "revenu": revenu, "type_habitat": type_habitat, "nb_pieces": nb_pieces,
    }

# ── Affichage ─────────────────────────────────────────────────────────────────
if "df_recherche" in st.session_state:
    df     = st.session_state["df_recherche"]
    params = st.session_state.get("recherche_params", {})

    n_total = len(df)
    n_accessible = int((df["taux_effort_vous"] < 33).sum()) if not df.empty else 0
    n_tendu = int(((df["taux_effort_vous"] >= 33) & (df["taux_effort_vous"] < 50)).sum()) if not df.empty else 0

    col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
    with col_a:
        filtre_texte = st.text_input(
            "Filtrer par commune ou agglomération",
            placeholder="Ex: Lyon, Bordeaux, Aix..."
        )
    with col_b:
        st.metric("Communes trouvées", n_total)
    with col_c:
        st.metric("Accessibles (<33%)", n_accessible)
    with col_d:
        st.metric("Tendues (33–50%)", n_tendu)

    st.markdown("---")

    if df.empty:
        st.warning("Aucune commune trouvée pour ces critères.")
    else:
        if filtre_texte:
            import unicodedata
            def norm(s):
                return unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()
            q = norm(filtre_texte)
            mask = (
                df["nom_commune"].apply(norm).str.contains(q, na=False) |
                df["nom_agglomeration"].apply(norm).str.contains(q, na=False)
            )
            df = df[mask]

        df_display = df.sort_values("taux_effort_vous").reset_index(drop=True).assign(
            accessibilite=df["taux_effort_vous"].apply(
                lambda x: "🟢 Accessible" if x < 33 else ("🟡 Tendu" if x < 50 else "🔴 Difficile")
            )
        )

        st.dataframe(
            df_display[[
                "nom_commune", "code_departement", "nom_agglomeration",
                "loyer_median", "taux_effort_vous", "accessibilite",
                "taux_effort_local", "revenu_local", "annee_donnees"
            ]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "nom_commune":       st.column_config.TextColumn("Commune"),
                "code_departement":  st.column_config.TextColumn("Dép."),
                "nom_agglomeration": st.column_config.TextColumn("Agglomération"),
                "loyer_median":      st.column_config.NumberColumn("Loyer médian", format="%d €"),
                "taux_effort_vous":  st.column_config.ProgressColumn(
                    "Taux effort (vous)",
                    format="%.1f%%",
                    min_value=0, max_value=100,
                ),
                "accessibilite":     st.column_config.TextColumn("Accessibilité"),
                "taux_effort_local": st.column_config.ProgressColumn(
                    "Taux effort (local)",
                    format="%.1f%%",
                    min_value=0, max_value=100,
                ),
                "revenu_local":      st.column_config.NumberColumn("Revenu local moy.", format="%d €/mois"),
                "annee_donnees":     st.column_config.NumberColumn("Année", format="%d"),
            }
        )

        st.caption(
            "**Taux effort (vous)** = loyer / votre revenu. "
            "**Taux effort (local)** = loyer / revenu médian de la population locale. "
            "🟢 < 33% accessible  🟡 33–50% tendu  🔴 > 50% difficile"
        )
