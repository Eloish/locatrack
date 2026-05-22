import pandas as pd

df = pd.read_csv("data/mapping_observatory_communes.csv", dtype=str)
print(df.groupby("observatory_b")["code_insee"].count().sort_values(ascending=False).to_string())