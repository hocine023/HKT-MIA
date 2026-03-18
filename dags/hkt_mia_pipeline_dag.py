"""
HKT-MIA Document Processing Pipeline DAG

Pipeline stages:
  1. build_clean  – OCR on raw PDFs/images → clean JSON (data/clean/)
  2. build_curated – Extract structured fields  → curated JSON (data/curated/)
  3. validate_llm  – LLM cross-document validation → validation JSON
"""

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
    description="OCR → Structured extraction → LLM validation",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["hkt-mia", "ocr", "llm"],
) as dag:

    build_clean = BashOperator(
        task_id="build_clean",
        bash_command=f"cd /opt/airflow && python {SCRIPTS_DIR}/build_clean.py",
    )

    build_curated = BashOperator(
        task_id="build_curated",
        bash_command=f"cd /opt/airflow && python {SCRIPTS_DIR}/build_curated.py",
    )

    validate_llm = BashOperator(
        task_id="validate_bundle_llm",
        bash_command=f"cd /opt/airflow && python {SCRIPTS_DIR}/validate_bundle_llm.py",
    )

    build_clean >> build_curated >> validate_llm
