import os
import re
import pandas as pd

# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("🚀 Démarrage de la réconciliation (Version corrigée Regex)...")

# 1. Chargement des données
try:
    # Lecture des fichiers Parquet 
    df_communes = pd.read_parquet(os.path.join(BASE_DIR, "data/bronze/communes/communes.parquet"))
    df_loyers = pd.read_parquet(os.path.join(BASE_DIR, "data/bronze/loyers/annee=2023/loyers_2023.parquet"))
except Exception as e:
    print(f"Erreur de chargement : {e}")
    exit()

agglos_loyers = df_loyers["agglomeration"].unique()
ref_insee = df_communes[["nom_unite_urbaine"]].dropna().drop_duplicates()

def nettoyer_nom(nom):
    if not nom: return ""
    nom = nom.lower()
    # Nettoyage des préfixes types [cite: 5, 41]
    nom = re.sub(r"agglomération (de |d'|du |des |)", "", nom)
    nom = re.sub(r" agglomération$", "", nom)
    nom = re.sub(r"unité urbaine (de |d'|)", "", nom)
    # On remplace les caractères spéciaux par des espaces pour simplifier
    nom = re.sub(r"[-'()]", " ", nom) 
    return nom.strip()

auto = []
manuel = []

# Liste de mots à ignorer pour éviter les faux positifs
STOP_WORDS = ["saint", "sainte", "sur", "sous", "les", "aux", "grand", "grande", "pays", "hors"]

for agglo in sorted(agglos_loyers):
    nom_propre = nettoyer_nom(agglo)
    match_found = False
    
    # Stratégie A : Match exact sur le nom nettoyé
    match = ref_insee[ref_insee["nom_unite_urbaine"].apply(nettoyer_nom) == nom_propre]
    
    if len(match) > 0:
        match_found = True
        valeur_insee = match["nom_unite_urbaine"].iloc[0]
    else:
        # Stratégie B : Tokenisation (recherche par mot)
        mots = nom_propre.split()
        mots_filtres = [m for m in mots if len(m) > 3 and m not in STOP_WORDS]
        
        for mot in mots_filtres:
            # CRUCIAL : regex=False pour éviter l'erreur pyarrow.lib.ArrowInvalid 
            match_mot = ref_insee[ref_insee["nom_unite_urbaine"].str.contains(mot, na=False, case=False, regex=False)]
            if len(match_mot) > 0:
                match_found = True
                valeur_insee = match_mot["nom_unite_urbaine"].iloc[0]
                break 

    if match_found:
        auto.append({"nom_agglomeration_olap": agglo, "nom_unite_urbaine_insee": valeur_insee, "methode": "auto"})
    else:
        manuel.append({"nom_agglomeration_olap": agglo, "nom_unite_urbaine_insee": "", "methode": "manuel"})

# 2. Sauvegarde des résultats 
output_dir = os.path.join(BASE_DIR, "data")
os.makedirs(output_dir, exist_ok=True)

pd.DataFrame(auto).to_csv(os.path.join(output_dir, "mapping_auto.csv"), index=False)
pd.DataFrame(manuel).to_csv(os.path.join(output_dir, "mapping_manuel.csv"), index=False)

print(f"\n✅ Terminé ! Auto: {len(auto)} | Manuel: {len(manuel)}")

# On utilise 2023 car c'est l'année avec le plus d'agglomérations (61)
# Ce mapping est valable pour toutes les années 2014-2025
# car les noms d'agglomérations sont stables dans le temps

