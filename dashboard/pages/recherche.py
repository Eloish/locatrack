import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from db import query

st.set_page_config(page_title="Recherche de ville", page_icon="🔍", layout="wide")
st.title("🔍 Trouver la ville la plus accessible")

st.info(
    "Les loyers affichés sont des **médianes** calculées par observatoire local des loyers. "
    "Les liens commune↔agglomération sont approximatifs : un observatoire peut couvrir plusieurs agglomérations."
)

# ── Filtres ──────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    budget = st.number_input("Budget loyer mensuel (€)", min_value=300, max_value=3000, value=800, step=50)
with col2:
    type_habitat = st.selectbox("Type de logement", ["Ensemble", "Appartement", "Maison"])
with col3:
    nb_pieces = st.selectbox("Nombre de pièces", ["Tous", "1P", "2P", "3P", "4P+"])
with col4:
    departement = st.text_input("Département (code)", placeholder="Ex: 75, 69...")
with col5:
    st.markdown("<br>", unsafe_allow_html=True)
    rechercher = st.button("🔍 Rechercher", use_container_width=True)

if rechercher:
    type_filter   = f"AND fl.type_habitat = '{type_habitat}'" if type_habitat != "Ensemble" else ""
    pieces_filter = f"AND fl.nombre_pieces ILIKE '%%{nb_pieces}%%'" if nb_pieces != "Tous" else ""
    dep_filter_commune = f"AND dc.code_departement = '{departement.strip()}'" if departement.strip() else ""
    dep_filter_agglo   = f"AND LEFT(bco2.code_insee, 2) = '{departement.strip()}'" if departement.strip() else ""

    # ── Tableau 1 : par agglomération ──
    df_agglo = query(f"""
        WITH derniere_annee AS (
            SELECT observatory_b, MAX(annee) AS max_annee
            FROM silver.fact_loyers
            GROUP BY observatory_b
        )
        SELECT
            da.nom_agglomeration,
            fl.observatory_b,
            da2.max_annee                                                       AS annee_donnees,
            ROUND(AVG(fl.loyer_mensuel_median)::numeric, 0)                     AS loyer_median,
            ROUND(
                (AVG(fl.loyer_mensuel_median) / NULLIF(AVG(fr2.revenu_median) / 12, 0) * 100)::numeric, 1
            )                                                                   AS taux_effort_pct,
            SUM(fl.nombre_observations)                                         AS nb_observations
        FROM silver.fact_loyers fl
        JOIN derniere_annee da2         ON fl.observatory_b = da2.observatory_b AND fl.annee = da2.max_annee
        JOIN silver.bridge_observatoire_agglomeration boa ON fl.observatory_b = boa.observatory_b
        JOIN silver.dim_agglomeration da                  ON boa.id_agglomeration = da.id_agglomeration
        LEFT JOIN silver.bridge_commune_observatoire bco2 ON fl.observatory_b = bco2.observatory_b
        LEFT JOIN silver.fact_revenus fr2                 ON bco2.code_insee = fr2.code_insee
          AND fr2.annee = (SELECT MAX(annee) FROM silver.fact_revenus)
        WHERE fl.loyer_mensuel_median IS NOT NULL
          {type_filter}
          {pieces_filter}
          {dep_filter_agglo}
        GROUP BY da.nom_agglomeration, fl.observatory_b, da2.max_annee
        HAVING AVG(fl.loyer_mensuel_median) <= {budget}
        ORDER BY da.nom_agglomeration ASC
    """)

    # ── Tableau 2 : par commune ──
    df_commune = query(f"""
        WITH derniere_annee AS (
            SELECT observatory_b, MAX(annee) AS max_annee
            FROM silver.fact_loyers
            GROUP BY observatory_b
        )
        SELECT
            dc.nom_commune,
            dc.code_departement,
            fl.observatory_b,
            da.max_annee                                                        AS annee_donnees,
            ROUND(AVG(fl.loyer_mensuel_median)::numeric, 0)                     AS loyer_median,
            ROUND(AVG(fr.revenu_median)::numeric, 0)                            AS revenu_moyen,
            ROUND(
                (AVG(fl.loyer_mensuel_median) / NULLIF(AVG(fr.revenu_median) / 12, 0) * 100)::numeric, 1
            )                                                                   AS taux_effort_pct,
            SUM(fl.nombre_observations)                                         AS nb_observations
        FROM silver.fact_loyers fl
        JOIN derniere_annee da          ON fl.observatory_b = da.observatory_b AND fl.annee = da.max_annee
        JOIN silver.bridge_commune_observatoire bco ON fl.observatory_b = bco.observatory_b
        JOIN silver.dim_commune dc                  ON bco.code_insee = dc.code_insee
        LEFT JOIN silver.fact_revenus fr            ON dc.code_insee = fr.code_insee
          AND fr.annee = (SELECT MAX(annee) FROM silver.fact_revenus)
        WHERE fl.loyer_mensuel_median IS NOT NULL
          {type_filter}
          {pieces_filter}
          {dep_filter_commune}
        GROUP BY dc.nom_commune, dc.code_departement, fl.observatory_b, da.max_annee
        HAVING AVG(fl.loyer_mensuel_median) <= {budget}
        ORDER BY dc.nom_commune ASC
    """)

    st.session_state["df_agglo"]  = df_agglo
    st.session_state["df_commune"] = df_commune

# ── Affichage ─────────────────────────────────────────────
if "df_agglo" in st.session_state:
    df_agglo   = st.session_state["df_agglo"]
    df_commune = st.session_state["df_commune"]

    recherche = st.text_input("🔎 Filtrer par nom", placeholder="Ex: Lyon, Bordeaux...")

    st.markdown("---")

    # Tableau agglomérations
    st.subheader(f"Par agglomération — {len(df_agglo)} résultat(s)")
    st.caption("⚠️ Un observatoire peut couvrir plusieurs agglomérations — lien approximatif.")

    if df_agglo.empty:
        st.warning("Aucune agglomération trouvée.")
    else:
        df_agglo["Loyer médian"]    = df_agglo["loyer_median"].apply(lambda x: f"{x:,.0f} €")
        df_agglo["Taux d'effort"]   = df_agglo["taux_effort_pct"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
        df_agglo["Nb observations"] = df_agglo["nb_observations"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")

        df_a = df_agglo[df_agglo["nom_agglomeration"].str.contains(recherche, case=False, na=False)] if recherche else df_agglo
        st.dataframe(
            df_a[["nom_agglomeration", "observatory_b", "Loyer médian", "Taux d'effort", "Nb observations", "annee_donnees"]],
            use_container_width=True, hide_index=True,
            column_config={"nom_agglomeration": "Agglomération", "observatory_b": "Observatoire", "annee_donnees": "Année"}
        )

    st.markdown("---")

    # Tableau communes
    st.subheader(f"Par commune — {len(df_commune)} résultat(s)")
    st.caption("⚠️ Le loyer est celui de l'observatoire couvrant la commune — pas spécifique à la commune.")

    if df_commune.empty:
        st.warning("Aucune commune trouvée.")
    else:
        df_commune["Loyer médian"]    = df_commune["loyer_median"].apply(lambda x: f"{x:,.0f} €")
        df_commune["Revenu moyen"]    = df_commune["revenu_moyen"].apply(lambda x: f"{x:,.0f} €" if pd.notna(x) else "N/A")
        df_commune["Taux d'effort"]   = df_commune["taux_effort_pct"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
        df_commune["Nb observations"] = df_commune["nb_observations"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")

        df_c = df_commune[df_commune["nom_commune"].str.contains(recherche, case=False, na=False)] if recherche else df_commune
        st.dataframe(
            df_c[["nom_commune", "code_departement", "observatory_b", "Loyer médian", "Revenu moyen", "Taux d'effort", "Nb observations", "annee_donnees"]],
            use_container_width=True, hide_index=True,
            column_config={"nom_commune": "Commune", "code_departement": "Dép.", "observatory_b": "Observatoire", "annee_donnees": "Année"}
        )
        st.caption("Taux d'effort = loyer mensuel / revenu mensuel. Seuil recommandé : 33%.")
