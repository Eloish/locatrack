
import  pandas as pd

df_auto = pd.read_csv("data/mapping_auto.csv")
df_manuel = pd.read_csv("data/mapping_manuel.csv")

df_final = pd.concat([df_auto, df_manuel])
df_final = df_final[
    df_final["nom_unite_urbaine_insee"].notna() & 
    (df_final["nom_unite_urbaine_insee"] != "")
]

print(f"Total agglomérations mappées : {len(df_final)}/61")
print(f"Exclus : {61 - len(df_final)}/61")