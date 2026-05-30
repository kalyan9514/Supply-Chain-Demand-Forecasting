"""
dags/supply_chain_common.py

Shared configuration and task factory for supply chain Airflow DAGs.
Defines default arguments and creates the standard preprocessing
task sequence used by both scheduled and on-demand DAGs.
"""

from datetime import datetime, timedelta

import docker
from airflow.exceptions import AirflowSkipException
from airflow.operators.python import PythonOperator
from airflow import DAG

DEFAULT_ARGS = {
    "owner": "supply-chain",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2024, 1, 1),
}

DOCKER_IMAGE = "us-central1-docker.pkg.dev/{project_id}/airflow-docker-image/data-pipeline:latest"


def run_docker_task(image: str, command: str, environment: dict) -> None:
    """
    Run a Docker container for a pipeline task.
    Raises AirflowSkipException if no data is available to process.
    """
    client = docker.from_env()
    try:
        logs = client.containers.run(
            image=image,
            command=command,
            environment=environment,
            remove=True,
            detach=False,
        )
        print(logs.decode("utf-8") if isinstance(logs, bytes) else logs)
    except docker.errors.ContainerError as e:
        if "no files found" in str(e.stderr).lower():
            raise AirflowSkipException("No files to process, skipping task.")
        raise


def make_pre_validation_task(dag: DAG, image: str, env: dict) -> PythonOperator:
    """Create the pre-validation Airflow task."""
    return PythonOperator(
        task_id="pre_validation",
        python_callable=run_docker_task,
        op_kwargs={
            "image": image,
            "command": "python scripts/pre_validation.py --bucket {{ var.value.raw_bucket }}",
            "environment": env,
        },
        dag=dag,
    )


def make_preprocessing_task(dag: DAG, image: str, env: dict) -> PythonOperator:
    """Create the preprocessing Airflow task."""
    return PythonOperator(
        task_id="preprocessing",
        python_callable=run_docker_task,
        op_kwargs={
            "image": image,
            "command": (
                "python scripts/preprocessing.py "
                "--source-bucket {{ var.value.raw_bucket }} "
                "--destination-bucket {{ var.value.processed_bucket }}"
            ),
            "environment": env,
        },
        dag=dag,
    )


def make_post_validation_task(dag: DAG, image: str, env: dict) -> PythonOperator:
    """Create the post-validation Airflow task."""
    return PythonOperator(
        task_id="post_validation",
        python_callable=run_docker_task,
        op_kwargs={
            "image": image,
            "command": "python scripts/post_validation.py --bucket {{ var.value.processed_bucket }}",
            "environment": env,
        },
        dag=dag,
    )


def make_dvc_versioning_task(dag: DAG, image: str, env: dict) -> PythonOperator:
    """Create the DVC versioning Airflow task."""
    return PythonOperator(
        task_id="dvc_versioning",
        python_callable=run_docker_task,
        op_kwargs={
            "image": image,
            "command": (
                "python scripts/dvc_versioning.py "
                "--repo-path /app "
                "--file-path /app/data/processed.csv "
                "--bucket-uri {{ var.value.dvc_bucket }}"
            ),
            "environment": env,
        },
        dag=dag,
    )


def create_preprocessing_tasks(dag: DAG) -> dict:
    """
    Create and wire all preprocessing tasks for a DAG.
    Returns a dict of task objects with dependencies set.
    """
    import os
    project_id = os.getenv("GCP_PROJECT_ID", "")
    image = DOCKER_IMAGE.format(project_id=project_id)
    env = {
        "GCP_PROJECT_ID": project_id,
        "GCP_SERVICE_ACCOUNT_KEY": os.getenv("GCP_SERVICE_ACCOUNT_KEY", ""),
        "MYSQL_HOST": os.getenv("MYSQL_HOST", ""),
        "MYSQL_USER": os.getenv("MYSQL_USER", ""),
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", ""),
        "SMTP_EMAIL": os.getenv("SMTP_EMAIL", ""),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD", ""),
    }

    pre_val = make_pre_validation_task(dag, image, env)
    preprocess = make_preprocessing_task(dag, image, env)
    post_val = make_post_validation_task(dag, image, env)
    dvc = make_dvc_versioning_task(dag, image, env)

    pre_val >> preprocess >> post_val >> dvc

    return {
        "pre_validation": pre_val,
        "preprocessing": preprocess,
        "post_validation": post_val,
        "dvc_versioning": dvc,
    }
