"""
dags/preprocessing_scheduled.py

Scheduled Airflow DAG that runs the full data preprocessing
pipeline on a weekly basis.
"""

from airflow import DAG
from supply_chain_common import DEFAULT_ARGS, create_preprocessing_tasks

dag = DAG(
    "gcp_preprocessing_scheduled",
    default_args=DEFAULT_ARGS,
    description="Weekly scheduled preprocessing pipeline",
    schedule_interval="0 2 * * 0",
    catchup=False,
    tags=["supply-chain", "preprocessing", "scheduled"],
)

tasks = create_preprocessing_tasks(dag)