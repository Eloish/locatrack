"""
Pipeline locatrack — orchestration Luigi
Ordre : Ingestion -> Staging -> Silver -> Gold (dbt)

Usage :
    python pipeline.py                   # pipeline complet
    python pipeline.py --from-step silver  # repart depuis silver
    python pipeline.py --from-step gold    # dbt run seulement

UI Luigi (optionnel) :
    luigid --background --port 8082
    puis ouvrir http://localhost:8082
"""
import sys, os, subprocess, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import luigi


# ══════════════════════════════════════════════════════════════════════════════
# INGESTION
# ══════════════════════════════════════════════════════════════════════════════

class IngestLoyers(luigi.Task):
    def run(self):
        from ingestion.ingest_loyers import ingest_all_loyers
        print("[PIPELINE] Ingestion loyers...")
        ingest_all_loyers()
    def output(self):
        return luigi.LocalTarget("data/bronze/loyers/.done")

class IngestDVF(luigi.Task):
    def run(self):
        from ingestion.ingest_dvf import ingest_all_dvf
        print("[PIPELINE] Ingestion DVF...")
        ingest_all_dvf()
    def output(self):
        return luigi.LocalTarget("data/bronze/dvf/.done")

class IngestINSEE(luigi.Task):
    def run(self):
        from ingestion.ingest_insee import ingest_all_insee
        print("[PIPELINE] Ingestion INSEE revenus...")
        ingest_all_insee()
    def output(self):
        return luigi.LocalTarget("data/bronze/insee/.done")

class IngestCommunes(luigi.Task):
    def run(self):
        from ingestion.ingest_communes import ingest_communes
        print("[PIPELINE] Ingestion communes...")
        ingest_communes()
    def output(self):
        return luigi.LocalTarget("data/bronze/communes/.done")

class IngestZonages(luigi.Task):
    def run(self):
        from ingestion.ingest_zonages import ingest_zonages
        print("[PIPELINE] Ingestion zonages...")
        ingest_zonages()
    def output(self):
        return luigi.LocalTarget("data/bronze/zonages/.done")

class IngestRefGeo(luigi.Task):
    def run(self):
        from ingestion.ingest_ref_geo import run_ingest_ref_geo
        print("[PIPELINE] Ingestion ref geo INSEE...")
        run_ingest_ref_geo()
    def output(self):
        return luigi.LocalTarget("data/bronze/ref_geo/.done")


# ══════════════════════════════════════════════════════════════════════════════
# STAGING
# ══════════════════════════════════════════════════════════════════════════════

class StagingLoyers(luigi.Task):
    def requires(self): return IngestLoyers()
    def run(self):
        from staging.load_loyers import run_load_loyers
        print("[PIPELINE] Staging loyers...")
        run_load_loyers()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_loyers.done")

class StagingDVF(luigi.Task):
    def requires(self): return IngestDVF()
    def run(self):
        from staging.load_dvf import run_load_dvf
        print("[PIPELINE] Staging DVF...")
        run_load_dvf()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_dvf.done")

class StagingINSEE(luigi.Task):
    def requires(self): return IngestINSEE()
    def run(self):
        from staging.load_insee import run_load_insee
        print("[PIPELINE] Staging INSEE...")
        run_load_insee()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_insee.done")

class StagingCommunes(luigi.Task):
    def requires(self): return IngestCommunes()
    def run(self):
        from staging.load_communes import run_load_communes
        print("[PIPELINE] Staging communes...")
        run_load_communes()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_communes.done")

class StagingZonages(luigi.Task):
    def requires(self): return IngestZonages()
    def run(self):
        from staging.load_zonages import run_load_zonages
        print("[PIPELINE] Staging zonages...")
        run_load_zonages()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_zonages.done")

class StagingRefGeo(luigi.Task):
    def requires(self): return IngestRefGeo()
    def run(self):
        from staging.load_ref_geo import run_load_ref_geo
        print("[PIPELINE] Staging ref geo...")
        run_load_ref_geo()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_ref_geo.done")

class StagingMapping(luigi.Task):
    def requires(self): return [StagingZonages(), StagingCommunes()]
    def run(self):
        from staging.load_mapping import run_load_mapping
        print("[PIPELINE] Staging mapping...")
        run_load_mapping()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_mapping.done")


# ══════════════════════════════════════════════════════════════════════════════
# SILVER
# ══════════════════════════════════════════════════════════════════════════════

class SilverDimObservatoire(luigi.Task):
    def requires(self): return [StagingLoyers()]
    def run(self):
        from transform.silver_dim_observatoire import run_silver_dim_observatoire
        print("[PIPELINE] Silver dim_observatoire...")
        run_silver_dim_observatoire()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_dim_observatoire.done")

class SilverDimAgglomeration(luigi.Task):
    def requires(self): return [StagingLoyers()]
    def run(self):
        from transform.silver_dim_agglomeration import run_silver_dim_agglomeration
        print("[PIPELINE] Silver dim_agglomeration...")
        run_silver_dim_agglomeration()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_dim_agglomeration.done")

class SilverDimCommune(luigi.Task):
    def requires(self): return [StagingCommunes()]
    def run(self):
        from transform.silver_dim_commune import run_silver_dim_commune
        print("[PIPELINE] Silver dim_commune...")
        run_silver_dim_commune()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_dim_commune.done")

class SilverDimTemps(luigi.Task):
    def requires(self): return [StagingLoyers()]
    def run(self):
        from transform.silver_dim_temps import run_silver_dim_temps
        print("[PIPELINE] Silver dim_temps...")
        run_silver_dim_temps()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_dim_temps.done")

class SilverDimTypeBien(luigi.Task):
    def requires(self): return [StagingDVF()]
    def run(self):
        from transform.silver_dim_type_bien import run_silver_dim_type_bien
        print("[PIPELINE] Silver dim_type_bien...")
        run_silver_dim_type_bien()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_dim_type_bien.done")

class SilverBridge(luigi.Task):
    def requires(self): return [SilverDimObservatoire(), SilverDimCommune()]
    def run(self):
        from transform.silver_bridge_commune_observatoire import run_silver_bridge_commune_observatoire
        print("[PIPELINE] Silver bridge_commune_observatoire...")
        run_silver_bridge_commune_observatoire()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_bridge.done")

class SilverFactLoyers(luigi.Task):
    def requires(self): return [SilverDimObservatoire(), SilverDimAgglomeration(), SilverDimTemps()]
    def run(self):
        from transform.silver_fact_loyers import run_silver_fact_loyers
        print("[PIPELINE] Silver fact_loyers...")
        run_silver_fact_loyers()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_fact_loyers.done")

class SilverFactRevenus(luigi.Task):
    def requires(self): return [StagingINSEE(), SilverDimCommune()]
    def run(self):
        from transform.silver_fact_revenus import run_silver_fact_revenus
        print("[PIPELINE] Silver fact_revenus...")
        run_silver_fact_revenus()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_fact_revenus.done")

class SilverFactTransactions(luigi.Task):
    def requires(self): return [StagingDVF(), SilverDimCommune(), SilverDimTypeBien()]
    def run(self):
        from transform.silver_fact_transactions import run_silver_fact_transactions
        print("[PIPELINE] Silver fact_transactions...")
        run_silver_fact_transactions()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_fact_transactions.done")

class SilverRefGeo(luigi.Task):
    def requires(self): return [StagingRefGeo(), SilverDimCommune(), SilverBridge(), SilverFactLoyers()]
    def run(self):
        from transform.silver_ref_geo import run_silver_ref_geo
        print("[PIPELINE] Silver ref_geo (mapping UU)...")
        run_silver_ref_geo()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_ref_geo.done")


# ══════════════════════════════════════════════════════════════════════════════
# GOLD — dbt
# ══════════════════════════════════════════════════════════════════════════════

class GoldDbt(luigi.Task):
    def requires(self):
        return [
            SilverFactLoyers(), SilverFactRevenus(),
            SilverFactTransactions(), SilverRefGeo(),
        ]

    def run(self):
        dbt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dbt")
        venv_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "Scripts")
        dbt_exe = os.path.join(venv_bin, "dbt.exe") if os.name == "nt" else os.path.join(venv_bin, "dbt")

        print("[PIPELINE] dbt run (gold)...")
        result = subprocess.run([dbt_exe, "run"], cwd=dbt_dir, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout + result.stderr)
            raise RuntimeError("dbt run a echoue")
        print(result.stdout)

        print("[PIPELINE] dbt test...")
        result = subprocess.run([dbt_exe, "test"], cwd=dbt_dir, capture_output=True, text=True)
        if result.returncode != 0:
            print("dbt test : certains tests ont echoue\n" + result.stdout)
        else:
            print(result.stdout)

        self.output().makedirs()
        open(self.output().path, "w").close()

    def output(self):
        return luigi.LocalTarget("data/.gold_dbt.done")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

STEPS = {
    "ingestion": GoldDbt,
    "staging":   GoldDbt,
    "silver":    GoldDbt,
    "gold":      GoldDbt,
}

SILVER_TASKS = [
    SilverDimObservatoire, SilverDimAgglomeration, SilverDimCommune,
    SilverDimTemps, SilverDimTypeBien, SilverBridge,
    SilverFactLoyers, SilverFactRevenus, SilverFactTransactions, SilverRefGeo,
]

STAGING_TASKS = [
    StagingLoyers, StagingDVF, StagingINSEE, StagingCommunes,
    StagingZonages, StagingRefGeo, StagingMapping,
]


INGESTION_TASKS = [
    IngestLoyers, IngestDVF, IngestINSEE, IngestCommunes, IngestZonages, IngestRefGeo,
]

BRONZE_DONE_DIRS = {
    IngestLoyers:   "data/bronze/loyers",
    IngestDVF:      "data/bronze/dvf",
    IngestINSEE:    "data/bronze/insee",
    IngestCommunes: "data/bronze/communes",
    IngestZonages:  "data/bronze/zonages",
    IngestRefGeo:   "data/bronze/ref_geo",
}


def mark_done(task_cls):
    """Cree le fichier .done pour simuler une tache deja realisee."""
    path = task_cls().output().path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").close()


def reset_done_files(from_step: str):
    """
    Selon from_step :
    - supprime les .done des etapes a re-executer
    - cree les .done des etapes a ignorer (deja faites)
    """
    if from_step == "gold":
        # Marquer tout comme fait sauf GoldDbt
        for t in INGESTION_TASKS + STAGING_TASKS + SILVER_TASKS:
            mark_done(t)
        path = GoldDbt().output().path
        if os.path.exists(path):
            os.remove(path)

    elif from_step == "silver":
        # Marquer ingestion + staging comme faits, reset silver + gold
        for t in INGESTION_TASKS + STAGING_TASKS:
            mark_done(t)
        for t in SILVER_TASKS + [GoldDbt]:
            path = t().output().path
            if os.path.exists(path):
                os.remove(path)

    elif from_step == "staging":
        # Marquer ingestion comme faite, reset staging + silver + gold
        for t in INGESTION_TASKS:
            mark_done(t)
        for t in STAGING_TASKS + SILVER_TASKS + [GoldDbt]:
            path = t().output().path
            if os.path.exists(path):
                os.remove(path)

    elif from_step == "ingestion":
        # Reset tout
        for t in INGESTION_TASKS + STAGING_TASKS + SILVER_TASKS + [GoldDbt]:
            path = t().output().path
            if os.path.exists(path):
                os.remove(path)

    print(f"[PIPELINE] Demarrage depuis : {from_step}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-step", dest="from_step",
        choices=["ingestion", "staging", "silver", "gold"],
        default="ingestion",
        help="Etape depuis laquelle relancer le pipeline"
    )
    args = parser.parse_args()

    reset_done_files(args.from_step)

    luigi.build(
        [GoldDbt()],
        local_scheduler=True,
        log_level="INFO",
    )
