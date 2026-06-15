import re
import unicodedata
import pandas as pd


def normaliser_insee(dep, com) -> str:
    dep = str(dep).strip()
    com = str(com).strip().zfill(3)
    if dep in ["2A", "2B"]:
        return dep + com
    return dep.zfill(2) + com


def clean_obs_code(x) -> str | None:
    if pd.isna(x):
        return None
    x = str(x)
    x = x.replace(" ", " ")
    x = unicodedata.normalize("NFKC", x)
    x = re.sub(r"\.0$", "", x)
    x = re.sub(r"\s+", "", x)
    return x.upper().strip()


def clean_text(x) -> str | None:
    if pd.isna(x):
        return None
    x = str(x)
    x = unicodedata.normalize("NFKC", x)
    x = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", x)
    x = re.sub(r"\s+", " ", x)
    return x.strip()
