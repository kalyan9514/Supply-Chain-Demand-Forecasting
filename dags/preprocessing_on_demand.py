"""
dags/preprocessing_on_demand.py

On-demand Airflow DAG triggered manually or via the backend API
when a new file is uploaded to GCS.
"""

from airflow import DAG
from supply_chain_common import DEFAULT_ARGS, create_preprocessing_tasks

dag = DAG(
    "gcp_preprocessing_on_demand",
    default_args=DEFAULT_ARGS,
    description="On-demand preprocessing pipeline triggered by file upload",
    schedule_interval=None,
    catchup=False,
    tags=["supply-chain", "preprocessing", "on-demand"],
)

tasks = create_preprocessing_tasks(dag)