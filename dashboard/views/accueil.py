import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from db import query
from components.sidebar import render_sidebar

render_sidebar()

# ── Données métriques ──────────────────────────────────────────────────────────
nb_communes  = query("SELECT COUNT(DISTINCT nom_commune) as n FROM gold.prix_m2_par_ville")['n'][0]
ratio_moyen  = query("SELECT ROUND(AVG(ratio_tension_pct)::numeric, 1) as r FROM gold.ratio_loyer_revenu")['r'][0]
max_annee    = query("SELECT MAX(annee) as a FROM gold.dynamisme_marche")['a'][0]
min_annee    = query("SELECT MIN(annee) as a FROM gold.dynamisme_marche")['a'][0]
nb_tendu     = query(f"""
    SELECT COUNT(DISTINCT nom_commune) as n FROM gold.dynamisme_marche
    WHERE categorie_tension IN ('Très tendu', 'Tendu') AND annee = {max_annee}
""")['n'][0]
nb_obs = query("SELECT COUNT(*) as n FROM silver.dim_observatoire")['n'][0]

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
    <h1>🏠 LocaTrack</h1>
    <p>Observatoire intelligent du marché locatif français — analyse de la tension locative,<br>
    des prix immobiliers et des revenus des ménages à l'échelle communale.</p>
    <span class="badge">📅 Données {min_annee} – {max_annee}</span>
    <span class="badge">🏛️ {nb_obs} observatoires locaux</span>
    <span class="badge">🏙️ {nb_communes:,} communes</span>
</div>
""", unsafe_allow_html=True)

# ── Métriques clés ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Chiffres clés</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Communes analysées</div>
        <div class="value">{nb_communes:,}</div>
        <div class="sub">transactions DVF incluses</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Ratio loyer / revenu moyen</div>
        <div class="value">{ratio_moyen} %</div>
        <div class="sub">part du revenu consacrée au loyer</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Villes tendues ({max_annee})</div>
        <div class="value">{nb_tendu:,}</div>
        <div class="sub">marchés "tendu" ou "très tendu"</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Couverture temporelle</div>
        <div class="value">{max_annee - min_annee + 1} ans</div>
        <div class="sub">{min_annee} à {max_annee}</div>
    </div>""", unsafe_allow_html=True)

# ── Pages disponibles ──────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Explorer les données</div>', unsafe_allow_html=True)

st.markdown("""
<div class="row g-3 mb-2">
    <div class="col-md-4 d-flex">
        <div class="page-card w-100 d-flex flex-column">
            <div class="icon">🗺️</div>
            <h3>Carte de tension locative</h3>
            <p>Visualisez la tension locative par commune et département.
            Identifiez les zones les plus tendues en France à partir des données DVF et loyers.</p>
            <div class="mt-auto">
                <span class="tag">Prix au m²</span>
                <span class="tag">Dynamisme marché</span>
            </div>
        </div>
    </div>
    <div class="col-md-4 d-flex">
        <div class="page-card w-100 d-flex flex-column">
            <div class="icon">📊</div>
            <h3>Comparaison de villes</h3>
            <p>Comparez plusieurs villes sur leurs indicateurs clés — loyers, revenus, ratio tension —
            et suivez leur évolution dans le temps.</p>
            <div class="mt-auto">
                <span class="tag">Évolution temporelle</span>
                <span class="tag">Multi-villes</span>
            </div>
        </div>
    </div>
    <div class="col-md-4 d-flex">
        <div class="page-card w-100 d-flex flex-column">
            <div class="icon">🔍</div>
            <h3>Recherche de ville</h3>
            <p>Trouvez les villes les plus accessibles selon votre budget et vos critères.
            Filtrez par région, revenu médian, type de bien et tension du marché.</p>
            <div class="mt-auto">
                <span class="tag">Filtres personnalisés</span>
                <span class="tag">Budget</span>
            </div>
        </div>
    </div>
</div>

<div class="section-title" style="margin-top:2rem">Sources de données</div>
<div class="row g-3">
    <div class="col-md-3 d-flex">
        <div class="source-card w-100">
            <div class="src-name">📋 DVF — Demandes de Valeurs Foncières</div>
            <div class="src-desc">Transactions immobilières enregistrées par la DGFiP</div>
            <div class="src-date">2021 – 2025 · data.gouv.fr</div>
        </div>
    </div>
    <div class="col-md-3 d-flex">
        <div class="source-card w-100">
            <div class="src-name">📊 INSEE — Revenus des ménages</div>
            <div class="src-desc">Revenus médians par commune (dispositif Filosofi)</div>
            <div class="src-date">2017 – 2021 · insee.fr</div>
        </div>
    </div>
    <div class="col-md-3 d-flex">
        <div class="source-card w-100">
            <div class="src-name">🏘️ OLL — Observatoires Locaux des Loyers</div>
            <div class="src-desc">Loyers médians par agglomération et type de bien</div>
            <div class="src-date">2014 – 2025 · data.gouv.fr</div>
        </div>
    </div>
    <div class="col-md-3 d-flex">
        <div class="source-card w-100">
            <div class="src-name">🗂️ INSEE — Référentiel géographique</div>
            <div class="src-desc">Table d'appartenance communes / unités urbaines 2025</div>
            <div class="src-date">2025 · insee.fr</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
