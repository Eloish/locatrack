import pandas as pd
df = pd.read_csv("data/bronze/loyers_zonages/B3400/L3400Zonage2025.csv", sep=";", encoding="latin1")
print(df.columns.tolist())
print(df.head(3))