import pandas as pd

# 1. On récupère un échantillon pour inspecter les colonnes
# On utilise ton 'engine' déjà configuré
df_dvf_sample = pd.read_sql("SELECT * FROM staging.dvf_2024 LIMIT 100", engine)

# 2. Afficher toutes les colonnes disponibles
print("--- Liste des colonnes dans DVF ---")
print(df_dvf_sample.columns.tolist())

# 3. Vérifier s'il existe des colonnes qui ressemblent à un nom de commune
# On cherche des colonnes avec 'nom' ou 'commune' dedans
colonnes_potentielles = [col for col in df_dvf_sample.columns if 'commune' in col.lower() or 'nom' in col.lower()]

print("\n--- Colonnes contenant 'commune' ou 'nom' ---")
if colonnes_potentielles:
    print(colonnes_potentielles)
    # On affiche un aperçu de ces colonnes pour voir si c'est du texte ou du code
    print("\n--- Aperçu des données de ces colonnes ---")
    print(df_dvf_sample[colonnes_potentielles].head())
else:
    print("Aucune colonne ne contient 'commune' ou 'nom'. La source est purement technique (codes uniquement).")