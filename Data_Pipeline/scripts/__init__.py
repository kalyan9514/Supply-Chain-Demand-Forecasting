"""
Data_Pipeline/scripts/__init__.py

Initializes the Data_Pipeline.scripts package.
Supports both absolute imports (used in Airflow DAGs)
and relative imports (used in unit tests and local development).
"""

try:
    from .logger import logger
    from .post_validation import main as post_validation_main
    from .pre_validation import main as pre_validation_main
    from .preprocessing import main as preprocessing_main
    from .utils import (
        load_bucket_data,
        send_email,
        setup_gcp_credentials,
        upload_to_gcs,
    )
except ImportError:
    from Data_Pipeline.scripts.logger import logger
    from Data_Pipeline.scripts.post_validation import main as post_validation_main
    from Data_Pipeline.scripts.pre_validation import main as pre_validation_main
    from Data_Pipeline.scripts.preprocessing import main as preprocessing_main
    from Data_Pipeline.scripts.utils import (
        load_bucket_data,
        send_email,
        setup_gcp_credentials,
        upload_to_gcs,
    )

__all__ = [
    "logger",
    "setup_gcp_credentials",
    "load_bucket_data",
    "send_email",
    "upload_to_gcs",
    "pre_validation_main",
    "preprocessing_main",
    "post_validation_main",
]
