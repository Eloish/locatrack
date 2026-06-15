import os
import pandas as pd


def validate_file(path: str) -> bool:
    if not os.path.exists(path):
        print(f"[VALIDATOR] Fichier manquant : {path}")
        return False
    if os.path.getsize(path) == 0:
        print(f"[VALIDATOR] Fichier vide : {path}")
        return False
    try:
        pd.read_parquet(path, columns=[])
        return True
    except Exception as e:
        print(f"[VALIDATOR] Fichier corrompu {path} : {e}")
        return False


def validate_columns(df: pd.DataFrame, required: list[str], source: str = "") -> bool:
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"[VALIDATOR] {source} — colonnes manquantes : {missing}")
        return False
    return True


def validate_not_null(df: pd.DataFrame, cols: list[str], source: str = "") -> pd.DataFrame:
    before = len(df)
    df = df.dropna(subset=cols)
    dropped = before - len(df)
    if dropped:
        print(f"[VALIDATOR] {source} — {dropped} lignes supprimées (nulls sur {cols})")
    return df


def validate_range(df: pd.DataFrame, col: str, min_val=None, max_val=None, source: str = "") -> pd.DataFrame:
    before = len(df)
    if min_val is not None:
        df = df[df[col] >= min_val]
    if max_val is not None:
        df = df[df[col] <= max_val]
    dropped = before - len(df)
    if dropped:
        print(f"[VALIDATOR] {source} — {dropped} lignes hors plage [{min_val}, {max_val}] sur '{col}'")
    return df


def validate_fk(df: pd.DataFrame, col: str, valid_set: set, source: str = "") -> pd.DataFrame:
    before = len(df)
    df = df[df[col].isin(valid_set)]
    dropped = before - len(df)
    if dropped:
        print(f"[VALIDATOR] {source} — {dropped} lignes rejetées (FK '{col}' invalide)")
    return df


def nettoyer_colonnes_sql(df: pd.DataFrame) -> pd.DataFrame:
    seen = {}
    new_cols = []
    for i, col in enumerate(df.columns):
        col = str(col).strip()
        if col == "" or col.lower() == "nan":
            col = f"col_sans_nom_{i}"
        col = col.replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        if col in seen:
            seen[col] += 1
            col = f"{col}_{seen[col]}"
        else:
            seen[col] = 0
        new_cols.append(col)
    df.columns = new_cols
    return df


def nettoyer_float(series: pd.Series) -> pd.Series:
    if series.dtype == object:
        return (
            series.astype(str)
            .str.replace(",", ".")
            .pipe(pd.to_numeric, errors="coerce")
        )
    return pd.to_numeric(series, errors="coerce")
