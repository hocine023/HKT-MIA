from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

SCRIPTS_DIR = "/opt/airflow/scripts"

default_args = {
    "owner": "hkt-mia",
    "retries": 1,
}

with DAG(
    dag_id="hkt_mia_pipeline",
    default_args=default_args,
    description="Raw ingestion -> OCR -> Structured extraction -> LLM validation",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["hkt-mia", "ocr", "llm"],
) as dag:

    ingest_raw = BashOperator(
        task_id="ingest_raw",
        bash_command=(
            f"cd /opt/airflow && "
            f"python {SCRIPTS_DIR}/ingest_raw.py --batch-id '{{{{ dag_run.conf[\"batch_id\"] }}}}'"
        ),
    )

    build_clean = BashOperator(
        task_id="build_clean",
        bash_command=(
            f"cd /opt/airflow && "
            f"python {SCRIPTS_DIR}/build_clean.py --batch-id '{{{{ dag_run.conf[\"batch_id\"] }}}}'"
        ),
    )

    build_curated = BashOperator(
        task_id="build_curated",
        bash_command=(
            f"cd /opt/airflow && "
            f"python {SCRIPTS_DIR}/build_curated.py --batch-id '{{{{ dag_run.conf[\"batch_id\"] }}}}'"
        ),
    )

    validate_llm = BashOperator(
        task_id="validate_bundle_llm",
        bash_command=(
            f"cd /opt/airflow && "
            f"python {SCRIPTS_DIR}/validate_bundle_llm.py --batch-id '{{{{ dag_run.conf[\"batch_id\"] }}}}'"
        ),
    )

    ingest_raw >> build_clean >> build_curated >> validate_llm