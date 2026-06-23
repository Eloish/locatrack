"""
Transform : mapping UU2020 ↔ agglomérations OLL
  → construit silver.mapping_uu_agglomeration (vote + fuzzy match UU ↔ dim_agglomeration)

Prérequis : staging.communes_geo et staging.uu2020 doivent être chargés
            silver.dim_commune doit être chargé avec uu2020 + reg (via silver_dim_commune)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import pandas as pd
from utils.config import load_config, get_base_dir
from utils.db import get_engine, get_conn


# ══════════════════════════════════════════════════════════════════════════════
# T — TRANSFORM
# ══════════════════════════════════════════════════════════════════════════════


def build_mapping_uu_agglomeration(engine, conn):
    """
    Vote-based fuzzy match : nom_agglomeration (observatoires) <-> nom_uu (INSEE UU2020).
    Les communes de chaque observatoire votent pour leur UU2020 dominant,
    puis on valide par fuzzy match nom_agglo ↔ nom_uu parmi les candidats.
    """
    try:
        from rapidfuzz import process, fuzz
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "rapidfuzz", "-q"])
        from rapidfuzz import process, fuzz

    PREFIXES = re.compile(
        r"agglom[eé]ration\s+(de\s+l[a']?|d[u']?\s+|des\s+|de\s+)?|"
        r"communaut[eé]\s+d.agglom[eé]ration\s+(de\s+|du\s+|d[e']?\s+)?|"
        r"eurom[eé]tropole\s+(de\s+)?|"
        r"unit[eé]\s+urbaine\s+(de\s+l.)?agglom[eé]ration\s+(de\s+)?|"
        r"communaut[eé]s?\s+de\s+communes?\s+",
        re.IGNORECASE
    )

    def normalise(nom: str) -> str:
        nom = re.sub(r'\(.*?\)', '', nom)
        nom = PREFIXES.sub('', nom)
        return nom.strip().lower()

    df_agglo = pd.read_sql("""
        SELECT DISTINCT fl.observatory_b, da.id_agglomeration, da.nom_agglomeration
        FROM silver.fact_loyers fl
        JOIN silver.dim_agglomeration da ON fl.id_agglomeration = da.id_agglomeration
        WHERE da.nom_agglomeration NOT ILIKE '%%rural%%'
          AND da.nom_agglomeration NOT ILIKE '%%hors%%'
    """, engine)


    df_votes = pd.read_sql("""
        SELECT
            bco.observatory_b,
            fl.id_agglomeration,
            dc.uu2020,
            u.nom_uu,
            COUNT(*) AS nb_communes
        FROM silver.bridge_commune_observatoire bco
        JOIN silver.dim_commune dc ON bco.code_insee = dc.code_insee
        JOIN staging.uu2020 u ON dc.uu2020 = u.uu2020
        JOIN silver.fact_loyers fl ON fl.observatory_b = bco.observatory_b
        WHERE dc.uu2020 IS NOT NULL
          AND dc.uu2020 != '01000'
          AND u.nom_uu NOT ILIKE 'Communes hors%%'
        GROUP BY bco.observatory_b, fl.id_agglomeration, dc.uu2020, u.nom_uu
        ORDER BY bco.observatory_b, fl.id_agglomeration, nb_communes DESC
    """, engine)

    # Toutes les UU de France pour le fallback
    df_all_uu = pd.read_sql("SELECT uu2020, nom_uu FROM staging.uu2020", engine)
    all_uu_codes = df_all_uu["uu2020"].tolist()
    all_uu_noms  = df_all_uu["nom_uu"].tolist()
    all_uu_norms = [normalise(n) for n in all_uu_noms]

    # Index des votes par (observatory_b, id_agglomeration)
    votes_idx = df_votes.groupby(["observatory_b", "id_agglomeration"])

    rows = []
    for _, agglo_row in df_agglo.iterrows():
        obs       = agglo_row["observatory_b"]
        id_agglo  = agglo_row["id_agglomeration"]
        nom_agglo      = agglo_row["nom_agglomeration"]
        nom_agglo_norm = normalise(nom_agglo)

        # Candidats UU du vote (communes du bridge)
        grp = votes_idx.get_group((obs, id_agglo)) if (obs, id_agglo) in votes_idx.groups else pd.DataFrame()

        score    = 0
        best_idx = 0
        uu_codes_c = []
        uu_noms_c  = []

        if not grp.empty:
            uu_codes_c = grp["uu2020"].tolist()
            uu_noms_c  = grp["nom_uu"].tolist()
            uu_norms_c = [normalise(n) for n in uu_noms_c]
            result = process.extractOne(nom_agglo_norm, uu_norms_c, scorer=fuzz.partial_ratio)
            score    = result[1] if result else 0
            best_idx = result[2] if result else 0

        # Fallback : si score < 70%, cherche dans toutes les UU de France
        if score < 70:
            result_fb = process.extractOne(nom_agglo_norm, all_uu_norms, scorer=fuzz.partial_ratio)
            if result_fb and result_fb[1] > score:
                fb_idx = result_fb[2]
                rows.append({
                    "uu2020":            all_uu_codes[fb_idx],
                    "nom_uu":            all_uu_noms[fb_idx],
                    "observatory_b":     obs,
                    "id_agglomeration":  id_agglo,
                    "nom_agglomeration": nom_agglo,
                    "score_fuzzy":       round(result_fb[1], 1),
                    "nb_communes_vote":  0,
                })
                continue

        if not uu_codes_c:
            continue

        rows.append({
            "uu2020":            uu_codes_c[best_idx],
            "nom_uu":            uu_noms_c[best_idx],
            "observatory_b":     obs,
            "id_agglomeration":  id_agglo,
            "nom_agglomeration": nom_agglo,
            "score_fuzzy":       round(score, 1),
            "nb_communes_vote":  int(grp.iloc[best_idx]["nb_communes"]),
        })

    df_mapping = pd.DataFrame(rows)

    # Crée la table même si vide (ValidateSilver en a besoin)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS silver.mapping_uu_agglomeration")
    cur.execute("""
        CREATE TABLE silver.mapping_uu_agglomeration (
            uu2020           VARCHAR(10),
            nom_uu           VARCHAR(255),
            observatory_b    VARCHAR(20),
            id_agglomeration INTEGER REFERENCES silver.dim_agglomeration(id_agglomeration),
            nom_agglomeration VARCHAR(255),
            score_fuzzy      FLOAT,
            nb_communes_vote INTEGER,
            PRIMARY KEY (observatory_b, id_agglomeration)
        )
    """)
    conn.commit()
    cur.close()

    if df_mapping.empty:
        print("[REF_GEO] Aucun mapping UU <-> agglomération construit (bridge vide)")
        return

    ambigus = df_mapping[df_mapping["score_fuzzy"] < 70]
    if not ambigus.empty:
        print(f"[REF_GEO] {len(ambigus)} cas ambigus (score < 70) :")
        print(ambigus[["observatory_b", "nom_uu", "nom_agglomeration", "score_fuzzy"]].to_string())

    print(f"[REF_GEO] {len(df_mapping)} mappings construits, score moyen : {df_mapping['score_fuzzy'].mean():.1f}%")

    cur = conn.cursor()
    for _, r in df_mapping.iterrows():
        cur.execute("""
            INSERT INTO silver.mapping_uu_agglomeration
            (uu2020, nom_uu, observatory_b, id_agglomeration, nom_agglomeration, score_fuzzy, nb_communes_vote)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (observatory_b, id_agglomeration) DO UPDATE
                SET uu2020 = EXCLUDED.uu2020,
                    nom_uu = EXCLUDED.nom_uu,
                    score_fuzzy = EXCLUDED.score_fuzzy,
                    nb_communes_vote = EXCLUDED.nb_communes_vote
        """, (r["uu2020"], r["nom_uu"], r["observatory_b"],
              int(r["id_agglomeration"]), r["nom_agglomeration"],
              r["score_fuzzy"], r["nb_communes_vote"]))
    conn.commit()
    cur.close()
    print("[REF_GEO] silver.mapping_uu_agglomeration chargé")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def run_silver_ref_geo():
    engine = get_engine()
    conn   = get_conn()

    print("[REF_GEO] Construction mapping UU <-> agglomération...")
    build_mapping_uu_agglomeration(engine, conn)

    conn.close()
    print("[REF_GEO] Terminé.")


if __name__ == "__main__":
    run_silver_ref_geo()
