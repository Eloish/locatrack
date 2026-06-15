import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from db import query

st.set_page_config(page_title="Recherche de ville", page_icon="🔍", layout="wide")
st.title("🔍 Trouver la ville la plus accessible")

st.info(
    "Les loyers affichés sont des **médianes globales** (tous types et toutes tailles confondus) "
    "calculées par observatoire local des loyers. "
    "Le taux d'effort = loyer mensuel / revenu mensuel — seuil recommandé : 33%."
)

# ── Filtres ──────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    budget = st.number_input("Budget loyer mensuel (€)", min_value=300, max_value=3000, value=800, step=50)
with col2:
    departement = st.text_input("Département (code)", placeholder="Ex: 75, 69, 13...")
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    rechercher = st.button("🔍 Rechercher", use_container_width=True)

if rechercher:
    dep_filter_commune = f"AND dc.code_departement = '{departement.strip()}'" if departement.strip() else ""
    dep_filter_agglo   = f"""AND fl.observatory_b IN (
        SELECT bco.observatory_b FROM silver.bridge_commune_observatoire bco
        JOIN silver.dim_commune dc2 ON bco.code_insee = dc2.code_insee
        WHERE dc2.code_departement = '{departement.strip()}'
    )""" if departement.strip() else ""

    # ── Tableau communes (Ensemble + Tous = un loyer global par observatoire) ──
    # On garde l'agglomération avec le plus d'observations pour éviter les doublons
    df_commune = query(f"""
        WITH derniere_annee AS (
            SELECT observatory_b, MAX(annee) AS max_annee
            FROM silver.fact_loyers
            WHERE type_habitat = 'Ensemble' AND nombre_pieces = 'Tous'
            GROUP BY observatory_b
        ),
        loyer_principal AS (
            SELECT DISTINCT ON (fl.observatory_b)
                fl.observatory_b,
                fl.loyer_mensuel_median,
                fl.nombre_observations,
                da.max_annee
            FROM silver.fact_loyers fl
            JOIN derniere_annee da ON fl.observatory_b = da.observatory_b
                                  AND fl.annee = da.max_annee
            WHERE fl.type_habitat = 'Ensemble'
              AND fl.nombre_pieces = 'Tous'
              AND fl.loyer_mensuel_median IS NOT NULL
            ORDER BY fl.observatory_b, fl.nombre_observations DESC NULLS LAST
        )
        SELECT
            dc.nom_commune,
            dc.code_departement,
            lp.observatory_b,
            lp.max_annee                                                         AS annee_donnees,
            ROUND(lp.loyer_mensuel_median::numeric, 0)                           AS loyer_median,
            ROUND(AVG(fr.revenu_median)::numeric, 0)                             AS revenu_moyen,
            ROUND(
                (lp.loyer_mensuel_median / NULLIF(AVG(fr.revenu_median) / 12, 0) * 100)::numeric, 1
            )                                                                    AS taux_effort_pct
        FROM loyer_principal lp
        JOIN silver.bridge_commune_observatoire bco ON lp.observatory_b = bco.observatory_b
        JOIN silver.dim_commune dc                  ON bco.code_insee = dc.code_insee
        LEFT JOIN silver.fact_revenus fr            ON dc.code_insee = fr.code_insee
          AND fr.annee = (SELECT MAX(annee) FROM silver.fact_revenus)
        WHERE lp.loyer_mensuel_median <= {budget}
          {dep_filter_commune}
        GROUP BY dc.nom_commune, dc.code_departement, lp.observatory_b,
                 lp.max_annee, lp.loyer_mensuel_median
        ORDER BY loyer_median ASC
    """)

    # ── Tableau agglomérations (même logique Ensemble + Tous) ──
    df_agglo = query(f"""
        WITH derniere_annee AS (
            SELECT observatory_b, id_agglomeration, MAX(annee) AS max_annee
            FROM silver.fact_loyers
            WHERE type_habitat = 'Ensemble' AND nombre_pieces = 'Tous'
            GROUP BY observatory_b, id_agglomeration
        )
        SELECT
            da.nom_agglomeration,
            fl.observatory_b,
            da2.max_annee                                AS annee_donnees,
            ROUND(fl.loyer_mensuel_median::numeric, 0)   AS loyer_median,
            fl.nombre_observations
        FROM silver.fact_loyers fl
        JOIN derniere_annee da2      ON fl.observatory_b = da2.observatory_b
                                    AND fl.id_agglomeration = da2.id_agglomeration
                                    AND fl.annee = da2.max_annee
        JOIN silver.dim_agglomeration da ON fl.id_agglomeration = da.id_agglomeration
        WHERE fl.type_habitat = 'Ensemble'
          AND fl.nombre_pieces = 'Tous'
          AND fl.loyer_mensuel_median IS NOT NULL
          AND fl.loyer_mensuel_median <= {budget}
          {dep_filter_agglo}
        ORDER BY loyer_median ASC
    """)

    st.session_state["df_commune"] = df_commune
    st.session_state["df_agglo"]   = df_agglo

# ── Affichage ─────────────────────────────────────────────
if "df_commune" in st.session_state:
    df_commune = st.session_state["df_commune"]
    df_agglo   = st.session_state["df_agglo"]

    recherche = st.text_input("🔎 Filtrer par nom", placeholder="Ex: Lyon, Bordeaux...")

    st.markdown("---")

    # ── Tableau communes EN PREMIER ──
    st.subheader(f"Par commune — {len(df_commune)} résultat(s)")
    st.caption("Loyer médian global (tous types et tailles confondus) de l'observatoire couvrant la commune.")

    if df_commune.empty:
        st.warning("Aucune commune trouvée pour ce budget.")
    else:
        df_commune["Loyer médian"]  = df_commune["loyer_median"].apply(lambda x: f"{x:,.0f} €")
        df_commune["Revenu moyen"]  = df_commune["revenu_moyen"].apply(lambda x: f"{x:,.0f} €" if pd.notna(x) else "N/A")
        df_commune["Taux d'effort"] = df_commune["taux_effort_pct"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")

        df_c = df_commune[df_commune["nom_commune"].str.contains(recherche, case=False, na=False)] if recherche else df_commune
        st.dataframe(
            df_c[["nom_commune", "code_departement", "Loyer médian", "Revenu moyen", "Taux d'effort", "annee_donnees"]],
            use_container_width=True, hide_index=True,
            column_config={
                "nom_commune":      "Commune",
                "code_departement": "Dép.",
                "annee_donnees":    "Année données",
            }
        )
        st.caption("Taux d'effort = loyer mensuel / revenu mensuel. Seuil recommandé : 33%.")

    st.markdown("---")

    # ── Tableau agglomérations EN SECOND ──
    st.subheader(f"Par agglomération — {len(df_agglo)} résultat(s)")
    st.caption("Vue synthétique par zone. Un observatoire peut couvrir plusieurs agglomérations.")

    if df_agglo.empty:
        st.warning("Aucune agglomération trouvée pour ce budget.")
    else:
        df_agglo["Loyer médian"] = df_agglo["loyer_median"].apply(lambda x: f"{x:,.0f} €")

        df_a = df_agglo[df_agglo["nom_agglomeration"].str.contains(recherche, case=False, na=False)] if recherche else df_agglo
        st.dataframe(
            df_a[["nom_agglomeration", "observatory_b", "Loyer médian", "annee_donnees"]],
            use_container_width=True, hide_index=True,
            column_config={
                "nom_agglomeration": "Agglomération",
                "observatory_b":     "Observatoire",
                "annee_donnees":     "Année données",
            }
        )
