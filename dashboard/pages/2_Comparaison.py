import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from components.sidebar import render_sidebar
from db import query

st.set_page_config(page_title="Comparaison", page_icon="⚖️", layout="wide")
render_sidebar()
st.title("⚖️ Comparaison des agglomérations")
st.markdown("""
Comparez les agglomérations sur leurs indicateurs locatifs et immobiliers.
**Loyers & revenus** proviennent des Observatoires Locaux des Loyers (OLL) et de l'INSEE (Filosofi).
**Marché immobilier** est calculé à partir des transactions DVF.
""")

onglet_loyers, onglet_marche = st.tabs(["Loyers & revenus", "Marché immobilier"])

# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 1 — Loyers & revenus (gold.ratio_loyer_revenu + gold.inegalites)
# ══════════════════════════════════════════════════════════════════════════════
with onglet_loyers:
    @st.cache_data(ttl=300)
    def load_agglos():
        return query("""
            SELECT DISTINCT nom_agglomeration
            FROM gold.ratio_loyer_revenu
            ORDER BY nom_agglomeration
        """)["nom_agglomeration"].tolist()

    agglos_dispo = load_agglos()

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        selection = st.multiselect(
            "Agglomérations à comparer (2 à 8)",
            options=agglos_dispo,
            default=agglos_dispo[:4] if len(agglos_dispo) >= 4 else agglos_dispo,
            max_selections=8,
            key="sel_agglos",
        )
    with col2:
        type_habitat = st.selectbox("Type logement", ["Appartement", "Maison"], key="th_loyers")
    with col3:
        profil = st.selectbox(
            "Profil revenu", ["Médian", "Modeste (D1)", "Aisé (D9)"], key="profil"
        )

    if len(selection) < 2:
        st.warning("Sélectionnez au moins 2 agglomérations.")
    else:
        agglos_sql = "', '".join(a.replace("'", "''") for a in selection)
        PALETTE = ["#1a2e4a", "#e05c2a", "#2d8a5e", "#c0392b", "#8e44ad", "#1abc9c", "#f39c12", "#2980b9"]
        color_map = {a: PALETTE[i % len(PALETTE)] for i, a in enumerate(selection)}
        taux_col = {
            "Médian":       "taux_effort_median_pct",
            "Modeste (D1)": "taux_effort_modeste_pct",
            "Aisé (D9)":    "taux_effort_aise_pct",
        }[profil]

        df_ratio = query(f"""
            WITH derniere AS (
                SELECT nom_agglomeration, MAX(annee) AS max_annee
                FROM gold.ratio_loyer_revenu
                WHERE nom_agglomeration IN ('{agglos_sql}')
                  AND type_habitat = '{type_habitat}' AND nombre_pieces = 'Tous'
                GROUP BY nom_agglomeration
            )
            SELECT rlr.nom_agglomeration, rlr.annee,
                   rlr.loyer_mensuel_median, rlr.revenu_mensuel_moyen, rlr.ratio_tension_pct
            FROM gold.ratio_loyer_revenu rlr
            JOIN derniere d ON rlr.nom_agglomeration = d.nom_agglomeration AND rlr.annee = d.max_annee
            WHERE rlr.type_habitat = '{type_habitat}' AND rlr.nombre_pieces = 'Tous'
            ORDER BY rlr.loyer_mensuel_median ASC
        """)

        df_ineg = query(f"""
            WITH derniere AS (
                SELECT nom_agglomeration, MAX(annee) AS max_annee
                FROM gold.inegalites
                WHERE nom_agglomeration IN ('{agglos_sql}')
                  AND type_habitat = '{type_habitat}'
                GROUP BY nom_agglomeration
            )
            SELECT i.nom_agglomeration, i.revenu_d1, i.revenu_median, i.revenu_d9,
                   i.taux_effort_modeste_pct, i.taux_effort_median_pct, i.taux_effort_aise_pct,
                   i.evolution_loyer_pct, i.evolution_revenu_pct
            FROM gold.inegalites i
            JOIN derniere d ON i.nom_agglomeration = d.nom_agglomeration AND i.annee = d.max_annee
            WHERE i.type_habitat = '{type_habitat}'
        """)

        df_evol = query(f"""
            SELECT nom_agglomeration, annee, loyer_mensuel_median, ratio_tension_pct
            FROM gold.ratio_loyer_revenu
            WHERE nom_agglomeration IN ('{agglos_sql}')
              AND type_habitat = '{type_habitat}' AND nombre_pieces = 'Tous'
            ORDER BY nom_agglomeration, annee
        """)

        # Métriques synthèse
        st.markdown("### Synthèse — dernière année disponible")
        st.caption("Loyer mensuel et part du revenu dépensée pour se loger, pour la dernière année disponible.")
        cols_m = st.columns(len(df_ratio))
        for i, (_, row) in enumerate(df_ratio.iterrows()):
            with cols_m[i]:
                st.metric(
                    label=row["nom_agglomeration"][:28],
                    value=f"{row['loyer_mensuel_median']:,.0f} €/mois",
                    delta=f"Taux effort : {row['ratio_tension_pct']:.1f}%",
                    delta_color="inverse",
                )

        st.markdown("---")
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader("Loyer mensuel médian")
            st.caption("Combien coûte en moyenne un loyer dans chaque ville ?")
            fig1 = px.bar(
                df_ratio, x="nom_agglomeration", y="loyer_mensuel_median",
                color="nom_agglomeration", text_auto=True,
                color_discrete_map=color_map,
                labels={"loyer_mensuel_median": "Loyer (€/mois)", "nom_agglomeration": ""},
            )
            fig1.update_layout(showlegend=False, height=360, xaxis_tickangle=-30)
            st.plotly_chart(fig1, use_container_width=True)

        with col_g2:
            st.subheader(f"Taux d'effort — profil {profil}")
            st.caption("Quelle part du revenu part dans le loyer ? Au-dessus de 33% (ligne rouge), le logement est considéré trop cher.")
            if not df_ineg.empty:
                fig2 = px.bar(
                    df_ineg.sort_values(taux_col),
                    x="nom_agglomeration", y=taux_col,
                    color="nom_agglomeration", text_auto=True,
                    color_discrete_map=color_map,
                    labels={taux_col: "Taux d'effort (%)", "nom_agglomeration": ""},
                )
                fig2.add_hline(y=33, line_dash="dash", line_color="red",
                               annotation_text="Seuil 33%")
                fig2.update_layout(showlegend=False, height=360, xaxis_tickangle=-30)
                st.plotly_chart(fig2, use_container_width=True)

        # Évolution temporelle
        st.markdown("---")
        st.subheader("Évolution du loyer dans le temps")
        st.caption("Les loyers augmentent-ils d'une année à l'autre ?")
        fig3 = px.line(
            df_evol, x="annee", y="loyer_mensuel_median",
            color="nom_agglomeration", markers=True,
            color_discrete_map=color_map,
            labels={"loyer_mensuel_median": "Loyer médian (€/mois)",
                    "annee": "Année", "nom_agglomeration": "Agglomération"},
        )
        fig3.update_layout(height=380)
        st.plotly_chart(fig3, use_container_width=True)

        # Tableau détaillé
        if not df_ineg.empty:
            st.markdown("---")
            st.subheader("Tableau comparatif détaillé")
            st.caption(
                "**Revenu médian** = revenu annuel du ménage médian (INSEE Filosofi) · "
                "**Taux effort médian** = loyer mensuel / revenu mensuel médian (%) · "
                "**Taux effort modeste** = loyer mensuel / revenu mensuel D1 — mesure la pression sur les ménages modestes · "
                "**Évol. loyer** = variation du loyer médian par rapport à l'année précédente (source OLL)"
            )
            df_t = df_ineg[["nom_agglomeration", "revenu_median", "taux_effort_median_pct", "taux_effort_modeste_pct", "evolution_loyer_pct"]].rename(columns={
                "nom_agglomeration":        "Agglomération",
                "revenu_median":            "Revenu médian (€/an)",
                "taux_effort_median_pct":   "Taux effort médian (%)",
                "taux_effort_modeste_pct":  "Taux effort modeste (%)",
                "evolution_loyer_pct":      "Évol. loyer (% vs an préc.)",
            })
            st.dataframe(df_t, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 2 — Marché immobilier (gold.prix_m2_par_ville + gold.dynamisme_marche)
# ══════════════════════════════════════════════════════════════════════════════
with onglet_marche:
    @st.cache_data(ttl=300)
    def load_villes(type_bien):
        return query(f"""
            SELECT DISTINCT nom_commune, code_insee
            FROM gold.prix_m2_par_ville
            WHERE type_local = '{type_bien}' AND nb_transactions >= 10
            ORDER BY nom_commune
        """)

    col_m1, col_m2, col_m3 = st.columns([2, 2, 1])
    with col_m3:
        type_bien = st.selectbox("Type de bien", ["Appartement", "Maison"], key="tb_marche")

    villes = load_villes(type_bien)
    liste  = villes["nom_commune"].tolist()
    def idx(nom): return liste.index(nom) if nom in liste else 0

    with col_m1:
        v1_nom = st.selectbox("Ville 1", liste, index=idx("Paris"), key="v1")
    with col_m2:
        v2_nom = st.selectbox("Ville 2", liste, index=idx("Marseille"), key="v2")

    v1_insee = villes[villes["nom_commune"] == v1_nom]["code_insee"].values[0]
    v2_insee = villes[villes["nom_commune"] == v2_nom]["code_insee"].values[0]

    @st.cache_data(ttl=300)
    def get_prix(code):
        return query(f"""
            SELECT annee, prix_m2_median, prix_m2_moyen, nb_transactions,
                   evolution_annuelle_pct, moving_avg_3ans
            FROM gold.prix_m2_par_ville
            WHERE code_insee = '{code}' AND type_local = '{type_bien}'
            ORDER BY annee
        """)

    @st.cache_data(ttl=300)
    def get_tension(code):
        return query(f"""
            SELECT annee, score_tension, categorie_tension, hausse_prix_pct
            FROM gold.dynamisme_marche
            WHERE code_insee = '{code}' AND type_local = '{type_bien}'
            ORDER BY annee
        """)

    df1 = get_prix(v1_insee)
    df2 = get_prix(v2_insee)
    t1  = get_tension(v1_insee)
    t2  = get_tension(v2_insee)

    def last(df, col):
        if df.empty or col not in df.columns: return None
        v = df.sort_values("annee").iloc[-1][col]
        return v if pd.notna(v) else None

    st.markdown("### Indicateurs — dernière année")
    st.caption("Basé sur les ventes immobilières enregistrées (source DVF, DGFiP).")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(f"Prix m² {v1_nom}", f"{last(df1,'prix_m2_median'):,.0f} €" if last(df1,'prix_m2_median') else "N/A")
        st.metric(f"Prix m² {v2_nom}", f"{last(df2,'prix_m2_median'):,.0f} €" if last(df2,'prix_m2_median') else "N/A")
    with c2:
        st.metric(f"Évolution {v1_nom}", f"{last(df1,'evolution_annuelle_pct'):+.1f}%" if last(df1,'evolution_annuelle_pct') else "N/A")
        st.metric(f"Évolution {v2_nom}", f"{last(df2,'evolution_annuelle_pct'):+.1f}%" if last(df2,'evolution_annuelle_pct') else "N/A")
    with c3:
        st.metric(f"Score tension {v1_nom}", f"{last(t1,'score_tension'):.1f}/100" if last(t1,'score_tension') else "N/A")
        st.metric(f"Score tension {v2_nom}", f"{last(t2,'score_tension'):.1f}/100" if last(t2,'score_tension') else "N/A")
    with c4:
        st.metric(f"Transactions {v1_nom}", f"{int(last(df1,'nb_transactions')):,}" if last(df1,'nb_transactions') else "N/A")
        st.metric(f"Transactions {v2_nom}", f"{int(last(df2,'nb_transactions')):,}" if last(df2,'nb_transactions') else "N/A")

    st.markdown("---")
    st.subheader("Évolution du prix au m²")
    st.caption("Prix au m² par année. La ligne pointillée est la moyenne sur 3 ans pour lisser les variations. La hausse annuelle n'est affichée que si les deux années comparées ont au moins 25 transactions.")

    fig_m = go.Figure()
    for nom, df_v in [(v1_nom, df1), (v2_nom, df2)]:
        if not df_v.empty:
            fig_m.add_trace(go.Scatter(
                x=df_v["annee"], y=df_v["prix_m2_median"],
                name=f"{nom} — médian", mode="lines+markers", line=dict(width=2)))
            fig_m.add_trace(go.Scatter(
                x=df_v["annee"], y=df_v["moving_avg_3ans"],
                name=f"{nom} — moy. 3 ans", mode="lines", line=dict(dash="dot", width=1)))
    fig_m.update_layout(xaxis_title="Année", yaxis_title="Prix m² (€)",
                        hovermode="x unified", height=400,
                        legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig_m, use_container_width=True)

    st.markdown("---")
    st.subheader("Score de tension locative")
    st.caption("Score de 0 à 100 : plus il est élevé, plus il est difficile de se loger. < 25 détendu · 25–50 modéré · 50–75 tendu · > 75 très tendu.")
    if not t1.empty and not t2.empty:
        t1p = t1.copy(); t1p["ville"] = v1_nom
        t2p = t2.copy(); t2p["ville"] = v2_nom
        fig_t = px.bar(
            pd.concat([t1p, t2p]), x="annee", y="score_tension",
            color="ville", barmode="group",
            labels={"score_tension": "Score (0-100)", "annee": "Année"},
        )
        fig_t.update_layout(height=350)
        st.plotly_chart(fig_t, use_container_width=True)
