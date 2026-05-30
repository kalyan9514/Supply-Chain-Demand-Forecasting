"""
Data_Pipeline/scripts/dvc_versioning.py

Handles DVC-based versioning of datasets stored in GCS buckets.
Versions processed data files so each model training run can be
traced back to the exact dataset it was trained on.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

try:
    from logger import logger
except ImportError:
    from Data_Pipeline.scripts.logger import logger


def run_command(cmd: list[str], cwd: str | None = None) -> str:
    """
    Run a shell command and return its stdout.
    Raises an exception if the command fails.
    """
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    return result.stdout.strip()


def init_dvc(repo_path: str) -> None:
    """Initialize DVC in the given directory if not already initialized."""
    dvc_dir = os.path.join(repo_path, ".dvc")
    if os.path.exists(dvc_dir):
        logger.info("DVC already initialized at %s.", repo_path)
        return
    run_command(["dvc", "init"], cwd=repo_path)
    logger.info("DVC initialized at %s.", repo_path)


def configure_gcs_remote(
    repo_path: str,
    remote_name: str,
    bucket_uri: str,
) -> None:
    """Configure a GCS bucket as the DVC remote storage."""
    run_command(
        ["dvc", "remote", "add", "-d", remote_name, bucket_uri],
        cwd=repo_path,
    )
    run_command(
        ["dvc", "remote", "modify", remote_name, "credentialpath",
         os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")],
        cwd=repo_path,
    )
    logger.info("DVC remote %s configured to %s.", remote_name, bucket_uri)


def track_file(repo_path: str, file_path: str) -> None:
    """Add a file to DVC tracking."""
    run_command(["dvc", "add", file_path], cwd=repo_path)
    logger.info("DVC tracking added for %s.", file_path)


def push_to_remote(repo_path: str) -> None:
    """Push all tracked DVC files to the configured remote."""
    run_command(["dvc", "push"], cwd=repo_path)
    logger.info("DVC push completed.")


def pull_from_remote(repo_path: str) -> None:
    """Pull all tracked DVC files from the configured remote."""
    run_command(["dvc", "pull"], cwd=repo_path)
    logger.info("DVC pull completed.")


def version_dataset(
    repo_path: str,
    file_path: str,
    remote_name: str,
    bucket_uri: str,
) -> None:
    """
    Full workflow to version a dataset file with DVC.

    Initializes DVC if needed, configures the GCS remote,
    tracks the file, and pushes it to remote storage.
    """
    init_dvc(repo_path)
    configure_gcs_remote(repo_path, remote_name, bucket_uri)
    track_file(repo_path, file_path)
    push_to_remote(repo_path)
    logger.info("Dataset versioning complete for %s.", file_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Version a dataset file with DVC.")
    parser.add_argument("--repo-path", required=True, help="Path to the git repo root")
    parser.add_argument("--file-path", required=True, help="Path to the file to version")
    parser.add_argument("--remote-name", default="gcs-remote", help="DVC remote name")
    parser.add_argument("--bucket-uri", required=True, help="GCS bucket URI for DVC remote")
    args = parser.parse_args()

    version_dataset(
        repo_path=args.repo_path,
        file_path=args.file_path,
        remote_name=args.remote_name,
        bucket_uri=args.bucket_uri,
    )
    