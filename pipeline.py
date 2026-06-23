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
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/bronze/loyers/.done")

class IngestDVF(luigi.Task):
    def run(self):
        from ingestion.ingest_dvf import ingest_all_dvf
        print("[PIPELINE] Ingestion DVF...")
        ingest_all_dvf()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/bronze/dvf/.done")

class IngestINSEE(luigi.Task):
    def run(self):
        from ingestion.ingest_insee import ingest_all_insee
        print("[PIPELINE] Ingestion INSEE revenus...")
        ingest_all_insee()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/bronze/insee/.done")

class IngestCommunes(luigi.Task):
    def run(self):
        from ingestion.ingest_communes import ingest_communes
        print("[PIPELINE] Ingestion communes...")
        ingest_communes()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/bronze/communes/.done")

class IngestZonages(luigi.Task):
    def run(self):
        from ingestion.ingest_zonages import ingest_zonages
        print("[PIPELINE] Ingestion zonages...")
        ingest_zonages()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/bronze/zonages/.done")

class IngestRefGeo(luigi.Task):
    def run(self):
        from ingestion.ingest_ref_geo import run_ingest_ref_geo
        print("[PIPELINE] Ingestion ref geo INSEE...")
        run_ingest_ref_geo()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/bronze/ref_geo/.done")


# ══════════════════════════════════════════════════════════════════════════════
# STAGING
# ══════════════════════════════════════════════════════════════════════════════

class StagingLoyers(luigi.Task):
    def requires(self): return ValidateBronze()
    def run(self):
        from staging.load_loyers import run_load_loyers
        print("[PIPELINE] Staging loyers...")
        run_load_loyers()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_loyers.done")

class StagingDVF(luigi.Task):
    def requires(self): return ValidateBronze()
    def run(self):
        from staging.load_dvf import run_load_dvf
        print("[PIPELINE] Staging DVF...")
        run_load_dvf()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_dvf.done")

class StagingINSEE(luigi.Task):
    def requires(self): return ValidateBronze()
    def run(self):
        from staging.load_insee import run_load_insee
        print("[PIPELINE] Staging INSEE...")
        run_load_insee()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_insee.done")

class StagingCommunes(luigi.Task):
    def requires(self): return ValidateBronze()
    def run(self):
        from staging.load_communes import run_load_communes
        print("[PIPELINE] Staging communes...")
        run_load_communes()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_communes.done")

class StagingZonages(luigi.Task):
    def requires(self): return ValidateBronze()
    def run(self):
        from staging.load_zonages import run_load_zonages
        print("[PIPELINE] Staging zonages...")
        run_load_zonages()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_zonages.done")

class StagingRefGeo(luigi.Task):
    def requires(self): return ValidateBronze()
    def run(self):
        from staging.load_ref_geo import run_load_ref_geo
        print("[PIPELINE] Staging ref geo...")
        run_load_ref_geo()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.staging_ref_geo.done")

# ══════════════════════════════════════════════════════════════════════════════
# SILVER
# ══════════════════════════════════════════════════════════════════════════════

class AllStaging(luigi.Task):
    """Barriere : attend que TOUT le staging soit termine avant de lancer le silver."""
    def requires(self):
        return [StagingLoyers(), StagingDVF(), StagingINSEE(), StagingCommunes(),
                StagingZonages(), StagingRefGeo()]
    def run(self):
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.all_staging.done")


class SilverDimObservatoire(luigi.Task):
    def requires(self): return [AllStaging()]
    def run(self):
        from transform.silver_dim_observatoire import run_silver_dim_observatoire
        print("[PIPELINE] Silver dim_observatoire...")
        run_silver_dim_observatoire()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_dim_observatoire.done")

class SilverDimAgglomeration(luigi.Task):
    def requires(self): return [AllStaging()]
    def run(self):
        from transform.silver_dim_agglomeration import run_silver_dim_agglomeration
        print("[PIPELINE] Silver dim_agglomeration...")
        run_silver_dim_agglomeration()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_dim_agglomeration.done")

class SilverDimCommune(luigi.Task):
    def requires(self): return [AllStaging()]
    def run(self):
        from transform.silver_dim_commune import run_silver_dim_commune
        print("[PIPELINE] Silver dim_commune...")
        run_silver_dim_commune()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_dim_commune.done")

class SilverDimTemps(luigi.Task):
    def requires(self): return [AllStaging()]
    def run(self):
        from transform.silver_dim_temps import run_silver_dim_temps
        print("[PIPELINE] Silver dim_temps...")
        run_silver_dim_temps()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_dim_temps.done")

class SilverDimTypeBien(luigi.Task):
    def requires(self): return [AllStaging()]
    def run(self):
        from transform.silver_dim_type_bien import run_silver_dim_type_bien
        print("[PIPELINE] Silver dim_type_bien...")
        run_silver_dim_type_bien()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_dim_type_bien.done")

class SilverBridge(luigi.Task):
    def requires(self): return [AllStaging(), SilverDimObservatoire(), SilverDimCommune()]
    def run(self):
        from transform.silver_bridge_commune_observatoire import run_silver_bridge_commune_observatoire
        print("[PIPELINE] Silver bridge_commune_observatoire...")
        run_silver_bridge_commune_observatoire()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_bridge.done")

class SilverFactLoyers(luigi.Task):
    def requires(self): return [SilverDimObservatoire(), SilverDimAgglomeration(), SilverDimTemps(), AllStaging()]
    def run(self):
        from transform.silver_fact_loyers import run_silver_fact_loyers
        print("[PIPELINE] Silver fact_loyers...")
        run_silver_fact_loyers()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_fact_loyers.done")

class SilverFactRevenus(luigi.Task):
    def requires(self): return [AllStaging(), SilverDimCommune(), SilverDimTemps()]
    def run(self):
        from transform.silver_fact_revenus import run_silver_fact_revenus
        print("[PIPELINE] Silver fact_revenus...")
        run_silver_fact_revenus()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_fact_revenus.done")

class SilverFactTransactions(luigi.Task):
    def requires(self): return [AllStaging(), SilverDimCommune(), SilverDimTypeBien(), SilverDimTemps()]
    def run(self):
        from transform.silver_fact_transactions import run_silver_fact_transactions
        print("[PIPELINE] Silver fact_transactions...")
        run_silver_fact_transactions()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_fact_transactions.done")

class SilverRefGeo(luigi.Task):
    def requires(self): return [AllStaging(), SilverDimCommune(), SilverBridge(), SilverFactLoyers()]
    def run(self):
        from transform.silver_ref_geo import run_silver_ref_geo
        print("[PIPELINE] Silver ref_geo (mapping UU)...")
        run_silver_ref_geo()
        self.output().makedirs()
        open(self.output().path, "w").close()
    def output(self):
        return luigi.LocalTarget("data/.silver_ref_geo.done")


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION — Great Expectations
# ══════════════════════════════════════════════════════════════════════════════

class ValidateBronze(luigi.Task):
    def requires(self):
        return [IngestLoyers(), IngestDVF(), IngestINSEE(), IngestCommunes(), IngestZonages(), IngestRefGeo()]

    def run(self):
        from tests.ge_bronze import run_ge_bronze
        print("[PIPELINE] Validation qualite bronze (GE)...")
        if not run_ge_bronze():
            raise ValueError("Validation bronze echouee — pipeline arrete")
        self.output().makedirs()
        open(self.output().path, "w").close()

    def output(self):
        return luigi.LocalTarget("data/.validate_bronze.done")


class ValidateSilver(luigi.Task):
    def requires(self):
        return [
            SilverFactLoyers(), SilverFactRevenus(), SilverFactTransactions(),
            SilverRefGeo(), SilverBridge(),
        ]

    def run(self):
        from tests.ge_silver import run_ge_silver
        print("[PIPELINE] Validation qualite silver (GE)...")
        if not run_ge_silver():
            raise ValueError("Validation silver echouee — pipeline arrete")
        self.output().makedirs()
        open(self.output().path, "w").close()

    def output(self):
        return luigi.LocalTarget("data/.validate_silver.done")


# ══════════════════════════════════════════════════════════════════════════════
# GOLD — dbt
# ══════════════════════════════════════════════════════════════════════════════

class GoldDbt(luigi.Task):
    def requires(self):
        return [ValidateSilver()]

    def run(self):
        import shutil
        dbt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dbt")
        dbt_exe = shutil.which("dbt")
        if dbt_exe is None:
            venv_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv",
                                    "Scripts" if os.name == "nt" else "bin")
            dbt_exe = os.path.join(venv_bin, "dbt.exe" if os.name == "nt" else "dbt")

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

INGESTION_TASKS = [
    IngestLoyers, IngestDVF, IngestINSEE, IngestCommunes, IngestZonages, IngestRefGeo,
]

STAGING_TASKS = [
    StagingLoyers, StagingDVF, StagingINSEE, StagingCommunes,
    StagingZonages, StagingRefGeo,
]

SILVER_TASKS = [
    SilverDimObservatoire, SilverDimAgglomeration, SilverDimCommune,
    SilverDimTemps, SilverDimTypeBien, SilverBridge,
    SilverFactLoyers, SilverFactRevenus, SilverFactTransactions, SilverRefGeo,
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
    ALL_TASKS = INGESTION_TASKS + [ValidateBronze] + STAGING_TASKS + [AllStaging] + SILVER_TASKS + [ValidateSilver, GoldDbt]

    if from_step == "gold":
        for t in INGESTION_TASKS + [ValidateBronze] + STAGING_TASKS + [AllStaging] + SILVER_TASKS:
            mark_done(t)
        for t in [ValidateSilver, GoldDbt]:
            path = t().output().path
            if os.path.exists(path):
                os.remove(path)

    elif from_step == "silver":
        for t in INGESTION_TASKS + [ValidateBronze] + STAGING_TASKS + [AllStaging]:
            mark_done(t)
        for t in SILVER_TASKS + [ValidateSilver, GoldDbt]:
            path = t().output().path
            if os.path.exists(path):
                os.remove(path)

    elif from_step == "staging":
        for t in INGESTION_TASKS:
            mark_done(t)
        for t in [ValidateBronze] + STAGING_TASKS + [AllStaging] + SILVER_TASKS + [ValidateSilver, GoldDbt]:
            path = t().output().path
            if os.path.exists(path):
                os.remove(path)

    elif from_step == "ingestion":
        for t in ALL_TASKS:
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
    parser.add_argument(
        "--to-step", dest="to_step",
        choices=["ingestion", "staging", "silver", "gold"],
        default="gold",
        help="Etape jusqu'a laquelle executer le pipeline (incluse)"
    )
    args = parser.parse_args()

    STEP_TARGETS = {
        "ingestion": ValidateBronze,
        "staging":   AllStaging,
        "silver":    ValidateSilver,
        "gold":      GoldDbt,
    }

    reset_done_files(args.from_step)

    target_task = STEP_TARGETS[args.to_step]
    luigi.build(
        [target_task()],
        local_scheduler=True,
        log_level="INFO",
    )
